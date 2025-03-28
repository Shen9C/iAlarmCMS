import os
import sys
import logging
from logging.handlers import RotatingFileHandler
import shutil
from datetime import datetime
import subprocess

# 添加项目根目录到 Python 路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app, db
from app.models.users import User
from app.models.alarms import Alarm
import click

# 确保logs文件夹存在
logs_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'logs')
os.makedirs(logs_dir, exist_ok=True)

# 配置日志
log_file_path = os.path.join(logs_dir, 'db_init.log')
rotating_handler = RotatingFileHandler(
    log_file_path,
    maxBytes=50 * 1024 * 1024,  # 50MB
    backupCount=20  # 最多保留20个文件
)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        rotating_handler
    ]
)
logger = logging.getLogger(__name__)

app = create_app()

@click.group()
def cli():
    """数据库管理工具"""
    pass

@cli.command()
def init():
    """初始化数据库"""
    with app.app_context():
        # 确保关闭所有现有连接
        db.session.remove()
        db.engine.dispose()
        
        # 检查数据库文件是否存在，如果存在则删除
        db_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'instance', 'app.db')
        if os.path.exists(db_path):
            try:
                os.remove(db_path)
                click.echo('已删除旧的数据库文件')
            except Exception as e:
                click.echo(f'删除数据库文件失败: {str(e)}')
                click.echo('请确保没有其他程序正在使用数据库文件，或者手动关闭Flask应用后再试')
                return
        
        db.create_all()
        # 检查是否存在管理员账户
        admin = User.query.filter_by(username='管理员').first()
        if not admin:
            admin = User(username='管理员', role='admin', is_admin=True)
            admin.set_password('admin123')
            db.session.add(admin)
            db.session.commit()
        click.echo('数据库初始化完成')

@cli.command()
def clear_test():
    """清空测试数据（保留管理员账户）"""
    with app.app_context():
        try:
            # 清空告警数据
            Alarm.query.delete()
            # 删除除管理员外的所有用户
            User.query.filter(User.username != '管理员').delete()
            db.session.commit()
            click.echo('测试数据已清空')
        except Exception as e:
            click.echo(f'清空数据出错: {str(e)}')

@cli.command()
def clear_all():
    """清空所有数据（包括管理员账户）"""
    with app.app_context():
        try:
            # 清空所有表
            db.session.query(Alarm).delete()
            db.session.query(User).delete()
            db.session.commit()
            click.echo('所有数据已清空')
        except Exception as e:
            click.echo(f'清空数据出错: {str(e)}')

def init_database():
    """初始化数据库"""
    app = create_app()
    
    # 获取数据库文件路径
    db_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'instance', 'app.db')
    
    # 如果数据库文件存在，先备份再删除
    if os.path.exists(db_path):
        try:
            # 确保所有数据库连接已关闭
            with app.app_context():
                db.session.remove()
                db.engine.dispose()
            
            # 创建备份目录
            backup_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'backups')
            os.makedirs(backup_dir, exist_ok=True)
            
            # 备份数据库文件，尝试多次
            backup_file = os.path.join(backup_dir, f'app_db_backup_{datetime.now().strftime("%Y%m%d_%H%M%S")}.db')
            backup_success = False
            max_backup_attempts = 3
            
            for backup_attempt in range(max_backup_attempts):
                try:
                    shutil.copy2(db_path, backup_file)
                    logger.info(f"数据库已备份到: {backup_file}")
                    backup_success = True
                    break
                except Exception as e:
                    if backup_attempt < max_backup_attempts - 1:
                        logger.warning(f"备份尝试 {backup_attempt+1}/{max_backup_attempts} 失败: {str(e)}，等待后重试...")
                        import time
                        time.sleep(2)  # 等待2秒后重试
                    else:
                        logger.error(f"备份失败，已达到最大尝试次数: {str(e)}")
                        raise e
            
            if not backup_success:
                logger.error("无法备份数据库文件，中止操作")
                return False
            
            # 删除原数据库文件，尝试多次
            delete_success = False
            max_delete_attempts = 5
            
            for delete_attempt in range(max_delete_attempts):
                try:
                    os.remove(db_path)
                    logger.info("已删除旧的数据库文件")
                    delete_success = True
                    break
                except Exception as e:
                    if delete_attempt < max_delete_attempts - 1:
                        logger.warning(f"删除尝试 {delete_attempt+1}/{max_delete_attempts} 失败: {str(e)}，等待后重试...")
                        import time
                        time.sleep(2)  # 等待2秒后重试
                    else:
                        logger.error(f"删除失败，已达到最大尝试次数: {str(e)}")
                        logger.error(f"异常类型: {type(e).__name__}")
                        import traceback
                        logger.error(f"详细错误信息:\n{traceback.format_exc()}")
                        # 检查文件是否被其他进程占用
                        try:
                            import psutil
                            for proc in psutil.process_iter(['pid', 'name', 'open_files']):
                                try:
                                    for file in proc.info.get('open_files') or []:
                                        if db_path in file.path:
                                            logger.error(f"文件被进程占用: PID={proc.info['pid']}, 进程名={proc.info['name']}")
                                except (psutil.NoSuchProcess, psutil.AccessDenied):
                                    pass
                        except ImportError:
                            logger.error("无法检查文件占用情况，请安装psutil库: pip install psutil")
                        raise e
            
            if not delete_success:
                logger.error("无法删除数据库文件，中止操作")
                return False
                
        except Exception as e:
            logger.error(f"备份或删除数据库文件失败: {str(e)}")
            logger.error("请确保没有其他程序正在使用数据库文件，或者手动关闭Flask应用后再试")
            return False
    
    # 确保instance目录存在
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    
    # 简化初始化过程，不再处理迁移
    try:
        with app.app_context():
            # 1. 创建新表
            db.create_all()
            logger.info("数据库表创建完成")
            
            # 2. 创建管理员用户 - 修改这里，确保所有字段都有值
            # 先检查是否已存在管理员用户
            try:
                # 直接使用SQL查询，避免ORM映射问题
                admin_exists = db.session.execute(db.text("SELECT COUNT(*) FROM users WHERE username = '管理员'")).scalar() > 0
            except Exception as e:
                logger.warning(f"检查管理员用户时出错: {str(e)}")
                admin_exists = False
            
            default_password = 'admin123'
            
            if admin_exists:
                logger.info("找到现有管理员用户，将更新密码")
                # 使用SQL更新密码
                from werkzeug.security import generate_password_hash
                password_hash = generate_password_hash(default_password)
                db.session.execute(db.text(f"UPDATE users SET password_hash = '{password_hash}' WHERE username = '管理员'"))
            else:
                logger.info("创建新的管理员用户")
                # 创建新的管理员用户，确保所有字段都有值
                from datetime import datetime
                admin = User(
                    username='管理员',
                    is_admin=True,
                    role='admin',
                    last_login_time=datetime.now(),
                    last_login_ip='127.0.0.1',
                    login_count=0,
                    active=True
                )
                admin.set_password(default_password)
                db.session.add(admin)
            
            db.session.commit()
            logger.info("管理员用户设置完成")
            logger.info("=== 默认管理员账户信息 ===")
            logger.info(f"用户名: 管理员")
            logger.info(f"密码: {default_password}")
            logger.info("========================")
            
            # 验证数据库状态 - 使用SQL直接查询，避免ORM映射问题
            try:
                users_result = db.session.execute(db.text("SELECT username, role, is_admin FROM users")).fetchall()
                logger.info(f"\n数据库中的用户列表:")
                logger.info("------------------------")
                for user in users_result:
                    logger.info(f"用户名: {user[0]}")
                    logger.info(f"角色: {user[1]}")
                    logger.info(f"是否管理员: {user[2]}")
                    logger.info("------------------------")
            except Exception as e:
                logger.error(f"查询用户列表时出错: {str(e)}")
            
            logger.info("数据库初始化完成")
            return True
            
    except Exception as e:
        logger.error(f"数据库初始化过程中出错: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return False

if __name__ == '__main__':
    # 检查是否有命令行参数
    if len(sys.argv) > 1:
        # 如果第一个参数是init，则执行init_database函数
        if sys.argv[1] == 'init':
            logger.info("开始初始化数据库...")
            logger.info("提示: 请确保所有Flask应用已关闭，以避免文件访问冲突")
            try:
                if init_database():
                    logger.info("数据库初始化成功")
                else:
                    logger.error("数据库初始化失败")
            except Exception as e:
                logger.critical(f"初始化过程中发生未处理的异常: {str(e)}")
                import traceback
                logger.critical(traceback.format_exc())
            # 初始化完成后直接退出，不再执行cli()
            sys.exit(0)
    
    # 如果没有特定的命令行参数或参数不是init，则执行cli()
    cli()
    