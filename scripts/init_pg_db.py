import os
import sys
import logging
from logging.handlers import RotatingFileHandler
from datetime import datetime
import click
import psycopg2
from psycopg2 import sql

# 添加项目根目录到 Python 路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app, db
from app.models.users import User
from app.models.alarms import Alarm
from app.models.edge_devices import EdgeDevice
from app.models.tasks import Task
from app.models.settings import SystemConfig, KeyValueSetting
# 直接从config模块导入配置
import config

# 确保logs文件夹存在
logs_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'logs')
os.makedirs(logs_dir, exist_ok=True)

# 配置日志
log_file_path = os.path.join(logs_dir, 'pg_db_init.log')
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

# 直接从config模块获取数据库配置
DB_USER = getattr(config, 'DB_USER', 'postgres')
DB_PASSWORD = getattr(config, 'DB_PASSWORD', 'password')
DB_HOST = getattr(config, 'DB_HOST', 'localhost')
DB_PORT = getattr(config, 'DB_PORT', '5432')
DB_NAME = getattr(config, 'DB_NAME', 'oilfield_web')

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
        conn = psycopg2.connect(
            user=DB_USER,
            password=DB_PASSWORD,
            host=DB_HOST,
            port=DB_PORT,
            database=DB_NAME
        )
        return conn
    except Exception as e:
        logger.error(f"连接数据库失败: {str(e)}")
        return None

def create_database_if_not_exists():
    """如果数据库不存在，则创建数据库"""
    try:
        # 连接到默认的postgres数据库
        conn = psycopg2.connect(
            user=DB_USER,
            password=DB_PASSWORD,
            host=DB_HOST,
            port=DB_PORT,
            database="postgres"  # 连接到默认数据库
        )
        conn.autocommit = True  # 设置自动提交，这对创建数据库很重要
        cursor = conn.cursor()
        
        # 检查数据库是否存在
        cursor.execute(f"SELECT 1 FROM pg_database WHERE datname = '{DB_NAME}'")
        exists = cursor.fetchone()
        
        if not exists:
            logger.info(f"数据库 {DB_NAME} 不存在，正在创建...")
            # 创建数据库，使用sql.SQL和sql.Identifier防止SQL注入
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
        import traceback
        logger.error(traceback.format_exc())
        return False

@cli.command()
def init():
    """初始化PostgreSQL数据库"""
    logger.info("开始初始化PostgreSQL数据库...")
    
    # 创建数据库（如果不存在）
    if not create_database_if_not_exists():
        logger.error("创建数据库失败，尝试继续初始化...")
    
    # 使用Flask-SQLAlchemy创建表
    with app.app_context():
        try:
            # 检查数据库连接
            try:
                conn = get_connection()
                if conn:
                    logger.info("数据库连接测试成功")
                    conn.close()
                else:
                    logger.error("无法连接到数据库，请检查配置")
                    return
            except Exception as e:
                logger.error(f"测试数据库连接时出错: {str(e)}")
                return
            
            # 记录要创建的模型
            logger.info("准备创建以下模型的表:")
            for table in db.metadata.tables:
                logger.info(f" - {table}")
            
            # 打印建表语句
            from sqlalchemy.schema import CreateTable
            logger.info("建表SQL语句:")
            create_statements = []
            
            # 调整表创建顺序，确保alarms表最后创建
            sorted_tables = list(db.metadata.sorted_tables)
            alarm_tables = [table for table in sorted_tables if 'alarms' in table.name.lower()]
            other_tables = [table for table in sorted_tables if 'alarms' not in table.name.lower()]
            
            # 重新排序表，先创建非alarm表，再创建alarm表
            reordered_tables = other_tables + alarm_tables
            logger.info("调整后的表创建顺序:")
            for table in reordered_tables:
                logger.info(f" - {table.name}")
                create_table_sql = str(CreateTable(table).compile(db.engine))
                logger.info(f"表 {table.name} 的创建语句:")
                logger.info(create_table_sql)
                create_statements.append((table.name, create_table_sql))
            
            # 尝试使用SQLAlchemy创建表
            logger.info("尝试使用SQLAlchemy创建表...")
            db.create_all()
            
            # 检查表是否创建成功
            conn = get_connection()
            tables = []
            if conn:
                cursor = conn.cursor()
                cursor.execute("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'")
                tables = cursor.fetchall()
                cursor.close()
                conn.close()
            
            # 如果SQLAlchemy创建失败，尝试直接执行SQL语句
            if not tables:
                logger.info("SQLAlchemy创建表失败，尝试直接执行SQL语句...")
                
                # 为每个表创建单独的连接
                for table_name, create_sql in create_statements:
                    # 创建新的连接
                    new_conn = get_connection()
                    if not new_conn:
                        logger.error(f"无法创建数据库连接，跳过表 {table_name} 的创建")
                        continue
                    
                    try:
                        # 设置自动提交模式
                        new_conn.autocommit = True
                        new_cursor = new_conn.cursor()
                        
                        # 直接执行建表语句
                        logger.info(f"正在创建表 {table_name}...")
                        logger.info(f"SQL: {create_sql}")
                        
                        # 执行建表语句
                        new_cursor.execute(create_sql)
                        logger.info(f"表 {table_name} 创建成功")
                        
                    except Exception as e:
                        logger.error(f"创建表 {table_name} 失败: {str(e)}")
                        import traceback
                        logger.error(traceback.format_exc())
                    finally:
                        # 确保关闭连接
                        if new_cursor:
                            new_cursor.close()
                        if new_conn:
                            new_conn.close()
            
            # 验证表是否创建成功
            try:
                conn = get_connection()
                if conn:
                    cursor = conn.cursor()
                    cursor.execute("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'")
                    tables = cursor.fetchall()
                    logger.info("数据库中的表:")
                    for table in tables:
                        logger.info(f" - {table[0]}")
                    
                    # 检查每个表的结构
                    if tables:
                        for table_name in [t[0] for t in tables]:
                            cursor.execute(f"SELECT column_name, data_type FROM information_schema.columns WHERE table_name = '{table_name}'")
                            columns = cursor.fetchall()
                            logger.info(f"表 {table_name} 的列:")
                            for col in columns:
                                logger.info(f"   - {col[0]} ({col[1]})")
                    else:
                        logger.error("数据库中没有找到任何表，表创建失败")
                    
                    cursor.close()
                    conn.close()
            except Exception as e:
                logger.error(f"验证表创建时出错: {str(e)}")
                import traceback
                logger.error(traceback.format_exc())
            
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
            import traceback
            logger.error(traceback.format_exc())

@cli.command()
def clear_test():
    """清空测试数据（保留管理员账户）"""
    with app.app_context():
        try:
            # 清空告警数据
            Alarm.query.delete()
            # 清空边缘设备数据
            EdgeDevice.query.delete()
            # 删除除管理员外的所有用户
            User.query.filter(User.username != '管理员').delete()
            db.session.commit()
            logger.info('测试数据已清空')
        except Exception as e:
            logger.error(f'清空数据出错: {str(e)}')
            db.session.rollback()

@cli.command(name='clear_all')  # 明确指定命令名称
def clear_all():
    """清空所有数据（包括管理员账户）并删除所有表"""
    with app.app_context():
        try:
            # 先清空表中的数据
            logger.info("清空表中的数据...")
            Alarm.query.delete()
            EdgeDevice.query.delete()
            User.query.delete()
            db.session.commit()
            logger.info('所有数据已清空')
            
            # 然后删除所有表结构
            logger.info("开始删除所有表结构...")
            conn = get_connection()
            if conn:
                conn.autocommit = True
                cursor = conn.cursor()
                
                # 获取所有表名
                cursor.execute("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'")
                tables = cursor.fetchall()
                
                if tables:
                    # 禁用外键约束检查
                    cursor.execute("SET session_replication_role = 'replica';")
                    
                    # 删除所有表
                    for table in tables:
                        table_name = table[0]
                        logger.info(f"删除表: {table_name}")
                        try:
                            cursor.execute(sql.SQL("DROP TABLE IF EXISTS {} CASCADE").format(
                                sql.Identifier(table_name)))
                            logger.info(f"表 {table_name} 已删除")
                        except Exception as e:
                            logger.error(f"删除表 {table_name} 失败: {str(e)}")
                    
                    # 恢复外键约束检查
                    cursor.execute("SET session_replication_role = 'origin';")
                    logger.info("所有表结构已删除")
                else:
                    logger.info("数据库中没有找到任何表")
                
                cursor.close()
                conn.close()
            else:
                logger.error("无法连接到数据库，请检查配置")
        except Exception as e:
            logger.error(f'清空数据和删除表结构出错: {str(e)}')
            import traceback
            logger.error(traceback.format_exc())
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

if __name__ == '__main__':
    cli()