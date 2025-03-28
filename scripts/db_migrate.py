import os
import sys
import logging
from logging.handlers import RotatingFileHandler
import shutil
from datetime import datetime
import subprocess
import click

# 添加项目根目录到 Python 路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app, db

# 确保logs文件夹存在
logs_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'logs')
os.makedirs(logs_dir, exist_ok=True)

# 配置日志
log_file_path = os.path.join(logs_dir, 'db_migrate.log')
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

def run_flask_command(command):
    """运行Flask命令"""
    project_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    try:
        result = subprocess.run(
            f"cd {project_dir} && flask {command}", 
            shell=True, 
            capture_output=True, 
            text=True
        )
        if result.returncode != 0:
            logger.error(f"命令执行失败: flask {command}")
            logger.error(f"错误信息: {result.stderr}")
            return False
        logger.info(f"命令执行成功: flask {command}")
        logger.debug(f"输出: {result.stdout}")
        return True
    except Exception as e:
        logger.error(f"执行命令时出错: {str(e)}")
        return False

@click.group()
def cli():
    """数据库迁移工具"""
    pass

@cli.command()
def init():
    """初始化迁移仓库"""
    logger.info("初始化迁移仓库...")
    if run_flask_command("db init"):
        logger.info("迁移仓库初始化成功")
    else:
        logger.error("迁移仓库初始化失败")

@cli.command()
@click.option('--message', '-m', default="migration", help='迁移说明信息')
def migrate(message):
    """创建迁移脚本"""
    logger.info(f"创建迁移脚本，说明: {message}...")
    if run_flask_command(f'db migrate -m "{message}"'):
        logger.info("迁移脚本创建成功")
    else:
        logger.error("迁移脚本创建失败")

@cli.command()
def upgrade():
    """应用迁移"""
    logger.info("应用迁移...")
    if run_flask_command("db upgrade"):
        logger.info("迁移应用成功")
    else:
        logger.error("迁移应用失败")

@cli.command()
@click.option('--revision', '-r', default="head", help='回退到指定版本，默认为head')
def downgrade(revision):
    """回退迁移"""
    logger.info(f"回退迁移到版本: {revision}...")
    if run_flask_command(f"db downgrade {revision}"):
        logger.info("迁移回退成功")
    else:
        logger.error("迁移回退失败")

@cli.command()
def reset():
    """重置迁移仓库"""
    app = create_app()
    
    # 获取迁移目录路径
    migrations_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'migrations')
    
    # 如果迁移目录存在，先备份再删除
    if os.path.exists(migrations_dir):
        try:
            # 创建备份目录
            backup_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'backups')
            os.makedirs(backup_dir, exist_ok=True)
            
            # 备份迁移目录
            migrations_backup_dir = os.path.join(
                backup_dir, 
                f'migrations_backup_{datetime.now().strftime("%Y%m%d_%H%M%S")}'
            )
            shutil.copytree(migrations_dir, migrations_backup_dir)
            logger.info(f"迁移目录已备份到: {migrations_backup_dir}")
            
            # 删除迁移目录
            shutil.rmtree(migrations_dir)
            logger.info("已删除旧的迁移目录")
            
            # 重新初始化迁移仓库
            if run_flask_command("db init"):
                logger.info("迁移仓库重置成功")
                
                # 创建新的迁移
                if run_flask_command('db migrate -m "Initial migration after reset"'):
                    logger.info("初始迁移创建成功")
                    
                    # 应用迁移
                    if run_flask_command("db upgrade"):
                        logger.info("初始迁移应用成功")
                        return
            
            logger.error("迁移仓库重置失败")
            
        except Exception as e:
            logger.error(f"重置迁移仓库失败: {str(e)}")
            logger.error("请确保没有其他程序正在使用迁移目录，或者手动关闭Flask应用后再试")
    else:
        logger.info("迁移目录不存在，将创建新的迁移仓库")
        if run_flask_command("db init"):
            logger.info("迁移仓库创建成功")
            
            # 创建新的迁移
            if run_flask_command('db migrate -m "Initial migration"'):
                logger.info("初始迁移创建成功")
                
                # 应用迁移
                if run_flask_command("db upgrade"):
                    logger.info("初始迁移应用成功")
                    return
        
        logger.error("迁移仓库创建失败")

@cli.command()
def status():
    """显示迁移状态"""
    logger.info("获取迁移状态...")
    run_flask_command("db current")
    run_flask_command("db history")

if __name__ == '__main__':
    cli()