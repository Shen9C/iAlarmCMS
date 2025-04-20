# 删除重复的导入
import os
import sys
import logging
from logging.handlers import RotatingFileHandler
from datetime import datetime
import click
import psycopg2
from psycopg2 import sql
import codecs
import traceback
from sqlalchemy import text, inspect

# 添加项目根目录到 Python 路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 确保logs文件夹存在
logs_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'logs')
os.makedirs(logs_dir, exist_ok=True)

# 创建logger实例
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# 清除现有的处理器，避免重复
if logger.handlers:
    logger.handlers.clear()

# 配置日志文件处理器
log_file_path = os.path.join(logs_dir, 'pg_db_init.log')
rotating_handler = RotatingFileHandler(
    log_file_path,
    maxBytes=50 * 1024 * 1024,
    backupCount=20,
    encoding='utf-8'
)

# 配置控制台处理器
if sys.stdout.encoding != 'utf-8':
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
console_handler = logging.StreamHandler(sys.stdout)

# 设置日志格式
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
rotating_handler.setFormatter(formatter)
console_handler.setFormatter(formatter)

# 添加处理器到logger
logger.addHandler(rotating_handler)
logger.addHandler(console_handler)

# 导入应用相关模块
from app import create_app, db
from app.models.users import User
from app.models.alarms import Alarm
from app.models.edge_devices import EdgeDevice
from app.models.tasks import Task
from app.models.settings import SystemConfig, KeyValueSetting
from config import Config

# 修改成功/失败标记
SUCCESS_MARK = '[成功]'
ERROR_MARK = '[失败]'

# 禁用应用日志处理器，避免日志重复
app = create_app()
app_logger = logging.getLogger('app')
app_logger.handlers.clear()
app_logger.addHandler(logging.NullHandler())

# 从 Config 类获取数据库配置
DB_USER = Config.DB_USER
DB_PASSWORD = Config.DB_PASSWORD
DB_HOST = Config.DB_HOST
DB_PORT = Config.DB_PORT
DB_NAME = Config.DB_NAME

# 记录数据库配置信息
logger.info(f"数据库配置: 主机={DB_HOST}, 端口={DB_PORT}, 数据库名={DB_NAME}, 用户={DB_USER}")

@click.group()
def cli():
    """PostgreSQL数据库管理工具"""
    pass

def get_connection_string():
    """获取PostgreSQL连接字符串"""
    return f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

def get_connection():
    """获取PostgreSQL连接"""
    try:
        # 添加连接超时设置
        conn = psycopg2.connect(
            user=DB_USER,
            password=DB_PASSWORD,
            host=DB_HOST,
            port=DB_PORT,
            database=DB_NAME,
            connect_timeout=10  # 设置连接超时为10秒
        )
        return conn
    except Exception as e:
        logger.error(f"连接数据库失败: {str(e)}")
        return None

def create_database_if_not_exists():
    """如果数据库不存在，则创建数据库"""
    try:
        # 添加连接超时设置
        conn = psycopg2.connect(
            user=DB_USER,
            password=DB_PASSWORD,
            host=DB_HOST,
            port=DB_PORT,
            database="postgres",
            connect_timeout=10
        )
        conn.autocommit = True
        cursor = conn.cursor()
        
        # 使用更高效的查询
        cursor.execute("SELECT 1 FROM pg_database WHERE datname = %s", (DB_NAME,))
        exists = cursor.fetchone()
        
        if not exists:
            logger.info(f"数据库 {DB_NAME} 不存在，正在创建...")
            cursor.execute(sql.SQL("CREATE DATABASE {} WITH ENCODING 'UTF8'").format(
                sql.Identifier(DB_NAME)))
            logger.info(f"数据库 {DB_NAME} 创建成功")
        else:
            logger.info(f"数据库 {DB_NAME} 已存在")
        
        cursor.close()
        conn.close()
        return True
    except Exception as e:
        logger.error(f"创建数据库失败: {str(e)}")
        return False

@cli.command()
def init():
    """初始化PostgreSQL数据库"""
    logger.info("开始初始化PostgreSQL数据库...")
    
    # 快速检查数据库是否存在
    if not create_database_if_not_exists():
        logger.error("创建数据库失败")
        return
    
    with app.app_context():
        try:
            # 快速连接测试
            conn = get_connection()
            if not conn:
                logger.error("无法连接到数据库，请检查配置")
                return
            conn.close()
            
            # 获取所有需要创建的表名
            expected_tables = {
                'users': User,
                'alarms': Alarm,
                'edge_devices': EdgeDevice,
                'tasks': Task,
                'system_config': SystemConfig,
                'key_value_settings': KeyValueSetting
            }
            
            # 检查是否需要先删除旧的表
            try:
                inspector = inspect(db.engine)
                need_rebuild = False
                
                # 检查告警表
                if 'alarms' in inspector.get_table_names():
                    columns = [column['name'] for column in inspector.get_columns('alarms')]
                    if 'alarm_id' in columns and 'alarm_code' not in columns:
                        logger.warning("检测到旧的告警表结构，包含alarm_id但不包含alarm_code")
                        need_rebuild = True
                
                # 检查任务表
                if 'tasks' in inspector.get_table_names():
                    columns = [column['name'] for column in inspector.get_columns('tasks')]
                    if 'detection_type' in columns and 'task_type' not in columns:
                        logger.warning("检测到旧的任务表结构，包含detection_type但不包含task_type")
                        need_rebuild = True
                
                if need_rebuild:
                    logger.warning("建议使用 python scripts/init_pg_db.py rebuild 命令强制重建表结构")
                    confirm = input("是否继续初始化? 如果继续，可能会导致字段不一致问题 (y/n): ").strip().lower()
                    if confirm != 'y':
                        logger.info("操作已取消")
                        return
                    logger.info("继续初始化...")
            except Exception as e:
                logger.error(f"检查表结构出错: {str(e)}")
            
            # 创建所有表 - 使用SQLAlchemy的自动映射
            logger.info("开始创建数据库表...")
            db.create_all()
            logger.info("数据库表创建完成")
            
            # 验证每个表是否创建成功
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'")
            existing_tables = {table[0] for table in cursor.fetchall()}
            
            # 检查每个表是否存在
            for table_name in expected_tables:
                if table_name in existing_tables:
                    logger.info(f"{SUCCESS_MARK} 表 {table_name} 创建成功")
                else:
                    logger.error(f"{ERROR_MARK} 表 {table_name} 创建失败")
                    try:
                        model = expected_tables[table_name]
                        model.__table__.create(db.engine)
                        logger.info(f"{SUCCESS_MARK} 重试创建表 {table_name} 成功")
                    except Exception as e:
                        logger.error(f"重试创建表 {table_name} 失败: {str(e)}")
            
            # 特别检查表的字段
            cursor.execute("SELECT column_name FROM information_schema.columns WHERE table_name = 'alarms'")
            alarm_columns = {col[0] for col in cursor.fetchall()}
            if 'alarm_code' in alarm_columns:
                logger.info(f"{SUCCESS_MARK} 告警表包含alarm_code字段")
            else:
                logger.error(f"{ERROR_MARK} 告警表不包含alarm_code字段")
                if 'alarm_id' in alarm_columns:
                    logger.warning("警告: 告警表仍然使用的是旧的alarm_id字段")
                    logger.warning("建议使用 python scripts/init_pg_db.py rebuild 命令强制重建表结构")
            
            cursor.execute("SELECT column_name FROM information_schema.columns WHERE table_name = 'tasks'")
            task_columns = {col[0] for col in cursor.fetchall()}
            if 'task_type' in task_columns:
                logger.info(f"{SUCCESS_MARK} 任务表包含task_type字段")
            else:
                logger.error(f"{ERROR_MARK} 任务表不包含task_type字段")
                if 'detection_type' in task_columns:
                    logger.warning("警告: 任务表仍然使用的是旧的detection_type字段")
                    logger.warning("建议使用 python scripts/init_pg_db.py rebuild 命令强制重建表结构")
            
            cursor.close()
            conn.close()
            
            # 创建管理员用户
            admin = User.query.filter_by(username='管理员').first()
            default_password = 'admin123'
            
            if admin:
                logger.info("找到现有管理员用户，将更新密码")
                admin.set_password(default_password)
            else:
                logger.info("创建新的管理员用户")
                admin = User(
                    username='管理员',
                    is_admin=True,
                    role='admin',
                    last_login_time=datetime.now(),
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
            
            # 验证数据库状态
            users = User.query.all()
            logger.info(f"\n数据库中的用户列表:")
            logger.info("------------------------")
            for user in users:
                logger.info(f"用户名: {user.username}")
                logger.info(f"角色: {user.role}")
                logger.info(f"是否管理员: {user.is_admin}")
                logger.info("------------------------")
            
            logger.info("数据库初始化完成")
            
        except Exception as e:
            logger.error(f"数据库初始化过程中出错: {str(e)}")
            logger.error(traceback.format_exc())

@cli.command(name='clear-all')  # 使用连字符
def clear_all():
    """清空所有数据（包括管理员账户）并删除所有表"""
    with app.app_context():
        try:
            # 先清空表中的数据
            logger.info("清空表中的数据...")
            try:
                # 按照依赖关系的相反顺序删除数据
                Alarm.query.delete()
                Task.query.delete()
                EdgeDevice.query.delete()
                User.query.delete()
                SystemConfig.query.delete()
                KeyValueSetting.query.delete()
                db.session.commit()
                logger.info("表数据清空成功")
            except Exception as e:
                db.session.rollback()
                logger.error(f"清空数据出错: {str(e)}")
                
            # 删除所有表
            logger.info("开始删除表结构...")
            try:
                # 使用原始SQL删除表，绕过外键约束
                db.session.execute(text("DROP TABLE IF EXISTS alarms CASCADE"))
                db.session.execute(text("DROP TABLE IF EXISTS tasks CASCADE"))
                db.session.execute(text("DROP TABLE IF EXISTS edge_devices CASCADE"))
                db.session.execute(text("DROP TABLE IF EXISTS users CASCADE"))
                db.session.execute(text("DROP TABLE IF EXISTS system_config CASCADE"))
                db.session.execute(text("DROP TABLE IF EXISTS key_value_settings CASCADE"))
                db.session.execute(text("DROP TABLE IF EXISTS alembic_version CASCADE"))  # 删除迁移版本表
                db.session.commit()
                logger.info("表结构删除成功")
            except Exception as e:
                db.session.rollback()
                logger.error(f"删除表结构出错: {str(e)}")
            
            # 重新创建表
            logger.info("重新创建表结构...")
            db.create_all()
            logger.info("表结构创建成功")
            
            # 检查表的字段
            try:
                inspector = inspect(db.engine)
                # 检查告警表字段
                if 'alarms' in inspector.get_table_names():
                    columns = [column['name'] for column in inspector.get_columns('alarms')]
                    if 'alarm_code' in columns:
                        logger.info(f"{SUCCESS_MARK} 告警表包含alarm_code字段")
                    else:
                        logger.error(f"{ERROR_MARK} 告警表不包含alarm_code字段")
                        if 'alarm_id' in columns:
                            logger.warning("警告: 告警表仍然使用的是旧的alarm_id字段")
                            logger.warning("建议使用 python scripts/init_pg_db.py rebuild 命令强制重建表结构")
                
                # 检查任务表字段
                if 'tasks' in inspector.get_table_names():
                    columns = [column['name'] for column in inspector.get_columns('tasks')]
                    if 'task_type' in columns:
                        logger.info(f"{SUCCESS_MARK} 任务表包含task_type字段")
                    else:
                        logger.error(f"{ERROR_MARK} 任务表不包含task_type字段")
                        if 'detection_type' in columns:
                            logger.warning("警告: 任务表仍然使用的是旧的detection_type字段")
                            logger.warning("建议使用 python scripts/init_pg_db.py rebuild 命令强制重建表结构")
            except Exception as e:
                logger.error(f"检查表结构出错: {str(e)}")
            
            logger.info("数据库重置完成")
            
        except Exception as e:
            logger.error(f"清空数据和删除表结构出错: {str(e)}")
            logger.error(traceback.format_exc())

@cli.command(name='clear-test')  # 使用连字符
def clear_test():
    """清空测试数据（保留管理员账户）"""
    with app.app_context():
        try:
            logger.info("开始清理测试数据...")
            
            # 按照外键依赖关系顺序清理数据
            logger.info("清理告警数据...")
            Alarm.query.delete()
            
            logger.info("清理任务数据...")
            Task.query.delete()
            
            logger.info("清理边缘设备数据...")
            EdgeDevice.query.delete()
            
            logger.info("清理非管理员用户数据...")
            User.query.filter(User.username != '管理员').delete()
            
            logger.info("清理系统配置数据...")
            SystemConfig.query.delete()
            
            logger.info("清理键值设置数据...")
            KeyValueSetting.query.delete()
            
            db.session.commit()
            logger.info('测试数据清理完成')
            
            # 验证清理结果
            admin_count = User.query.filter_by(username='管理员').count()
            logger.info(f"管理员账户状态: {'存在' if admin_count == 1 else '不存在'}")
            
        except Exception as e:
            logger.error(f'清理数据出错: {str(e)}')
            db.session.rollback()

@cli.command()
def backup():
    """备份PostgreSQL数据库"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'backups')
    os.makedirs(backup_dir, exist_ok=True)
    
    backup_file = os.path.join(backup_dir, f'{DB_NAME}_backup_{timestamp}.sql')
    
    try:
        import subprocess
        # 使用pg_dump进行备份
        cmd = f'pg_dump -h {DB_HOST} -p {DB_PORT} -U {DB_USER} -F c -b -v -f "{backup_file}" {DB_NAME}'
        
        # 设置环境变量PGPASSWORD
        env = os.environ.copy()
        env['PGPASSWORD'] = DB_PASSWORD
        
        logger.info(f"开始备份数据库到: {backup_file}")
        process = subprocess.Popen(cmd, shell=True, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = process.communicate()
        
        if process.returncode == 0:
            logger.info(f"数据库备份成功: {backup_file}")
        else:
            logger.error(f"数据库备份失败: {stderr.decode('utf-8')}")
    except Exception as e:
        logger.error(f"备份过程中出错: {str(e)}")

@cli.command()
@click.argument('backup_file')
def restore(backup_file):
    """从备份文件恢复PostgreSQL数据库"""
    if not os.path.exists(backup_file):
        logger.error(f"备份文件不存在: {backup_file}")
        return
    
    try:
        import subprocess
        # 使用pg_restore进行恢复
        cmd = f'pg_restore -h {DB_HOST} -p {DB_PORT} -U {DB_USER} -d {DB_NAME} -c -v "{backup_file}"'
        
        # 设置环境变量PGPASSWORD
        env = os.environ.copy()
        env['PGPASSWORD'] = DB_PASSWORD
        
        logger.info(f"开始从备份文件恢复数据库: {backup_file}")
        process = subprocess.Popen(cmd, shell=True, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = process.communicate()
        
        if process.returncode == 0:
            logger.info("数据库恢复成功")
        else:
            logger.error(f"数据库恢复失败: {stderr.decode('utf-8')}")
    except Exception as e:
        logger.error(f"恢复过程中出错: {str(e)}")

@cli.command()
def rebuild():
    """强制重建数据库表，确保使用最新的模型定义（所有数据将丢失）"""
    logger.info("开始强制重建数据库表...")
    
    # 快速检查数据库是否存在
    if not create_database_if_not_exists():
        logger.error("创建数据库失败")
        return
    
    with app.app_context():
        try:
            # 确保在应用上下文内没有重复的日志处理器
            for module_name in ['sqlalchemy.engine', 'alembic', 'werkzeug']:
                module_logger = logging.getLogger(module_name)
                module_logger.handlers.clear()
                module_logger.addHandler(logging.NullHandler())
                module_logger.propagate = False
            
            # 先删除所有表
            logger.info("开始删除所有表...")
            
            # 按依赖关系的反顺序删除
            tables = [
                'alarms',
                'tasks',
                'edge_devices',
                'users',
                'system_config',
                'key_value_settings',
                'alembic_version'  # 如果有使用Alembic进行迁移
            ]
            
            for table in tables:
                try:
                    db.session.execute(text(f"DROP TABLE IF EXISTS {table} CASCADE"))
                    logger.info(f"{SUCCESS_MARK} 表 {table} 删除成功")
                except Exception as e:
                    logger.error(f"{ERROR_MARK} 删除表 {table} 失败: {str(e)}")
            
            db.session.commit()
            logger.info("所有表删除完成")
            
            # 重新创建所有表
            logger.info("开始创建表...")
            db.create_all()
            logger.info("表创建完成")
            
            # 验证表结构
            inspector = inspect(db.engine)
            for model in ['users', 'alarms', 'edge_devices', 'tasks', 'system_config', 'key_value_settings']:
                if model in inspector.get_table_names():
                    logger.info(f"{SUCCESS_MARK} 表 {model} 创建成功")
                    
                    # 如果是告警表，检查字段
                    if model == 'alarms':
                        columns = [column['name'] for column in inspector.get_columns(model)]
                        if 'alarm_code' in columns:
                            logger.info(f"{SUCCESS_MARK} 告警表包含正确的alarm_code字段")
                        else:
                            logger.error(f"{ERROR_MARK} 告警表不包含alarm_code字段")
                        
                        if 'alarm_id' in columns:
                            logger.warning("警告: 告警表仍然包含alarm_id字段")
                    
                    # 如果是任务表，检查字段
                    if model == 'tasks':
                        columns = [column['name'] for column in inspector.get_columns(model)]
                        if 'task_type' in columns:
                            logger.info(f"{SUCCESS_MARK} 任务表包含正确的task_type字段")
                        else:
                            logger.error(f"{ERROR_MARK} 任务表不包含task_type字段")
                        
                        if 'detection_type' in columns:
                            logger.warning("警告: 任务表仍然包含detection_type字段")
                else:
                    logger.error(f"{ERROR_MARK} 表 {model} 创建失败")
            
            # 创建默认管理员账户
            try:
                admin = User(
                    username='管理员',
                    is_admin=True,
                    role='admin',
                    active=True
                )
                admin.set_password('admin123')
                db.session.add(admin)
                db.session.commit()
                logger.info("默认管理员账户创建成功")
                
                logger.info("=== 默认管理员账户信息 ===")
                logger.info(f"用户名: 管理员")
                logger.info(f"密码: admin123")
                logger.info("========================")
            except Exception as e:
                logger.error(f"创建管理员账户失败: {str(e)}")
            
            logger.info("数据库表重建完成")
            
        except Exception as e:
            logger.error(f"重建数据库表过程中出错: {str(e)}")
            logger.error(traceback.format_exc())

# 删除文件末尾的重复代码块
if __name__ == '__main__':
    cli()

