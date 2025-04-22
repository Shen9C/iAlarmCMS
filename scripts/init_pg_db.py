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
from app.models.oil_wells import OilWell
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
                'oil_wells': OilWell,  # 添加油井表
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
            
            # 特别检查告警表
            cursor.execute("SELECT column_name FROM information_schema.columns WHERE table_name = 'alarms'")
            alarm_columns = {col[0] for col in cursor.fetchall()}
            required_alarm_fields = ['alarm_code', 'is_processed', 'is_confirmed', 'well_code']
            missing_fields = [field for field in required_alarm_fields if field not in alarm_columns]
            
            if not missing_fields:
                logger.info(f"{SUCCESS_MARK} 告警表包含所有必需字段")
            else:
                logger.error(f"{ERROR_MARK} 告警表缺少字段: {', '.join(missing_fields)}")
                if 'alarm_id' in alarm_columns and 'alarm_code' not in alarm_columns:
                    logger.warning("警告: 告警表仍然使用的是旧的alarm_id字段")
                    logger.warning("建议使用 python scripts/init_pg_db.py rebuild 命令强制重建表结构")
                if 'processed_status' in alarm_columns:
                    logger.warning("警告: 告警表使用了processed_status字段，应该使用is_processed和is_confirmed")
            
            # 特别检查边缘设备表
            cursor.execute("SELECT column_name FROM information_schema.columns WHERE table_name = 'edge_devices'")
            edge_device_columns = {col[0] for col in cursor.fetchall()}
            required_edge_device_fields = ['device_id', 'device_name', 'ip_address', 'secret_key', 'last_auth_time', 'status']
            missing_edge_device_fields = [field for field in required_edge_device_fields if field not in edge_device_columns]
            
            if not missing_edge_device_fields:
                logger.info(f"{SUCCESS_MARK} 边缘设备表包含所有必需字段")
            else:
                logger.warning(f"边缘设备表缺少字段: {', '.join(missing_edge_device_fields)}")
                logger.warning("请运行数据库迁移或执行rebuild命令添加缺少的字段")

            # 特别检查任务表
            cursor.execute("SELECT column_name FROM information_schema.columns WHERE table_name = 'tasks'")
            task_columns = {col[0] for col in cursor.fetchall()}
            
            # 检查摄像头字段
            if 'camera_username' in task_columns and 'camera_password' in task_columns:
                logger.info(f"{SUCCESS_MARK} 任务表包含摄像头用户名和密码字段")
            else:
                if 'camera_username' not in task_columns or 'camera_password' not in task_columns:
                    logger.warning("警告: 任务表缺少摄像头用户名或密码字段，请运行数据库迁移")
            
            if 'task_type' in task_columns:
                logger.info(f"{SUCCESS_MARK} 任务表结构正确，包含task_type字段")
            else:
                logger.error(f"{ERROR_MARK} 任务表结构不正确，不包含task_type字段")
                if 'detection_type' in task_columns:
                    logger.warning("警告：任务表使用了旧的detection_type字段，请先运行init_pg_db.py清空并重建表结构")
            
            # 特别检查油井表
            cursor.execute("SELECT column_name FROM information_schema.columns WHERE table_name = 'oil_wells'")
            oil_well_columns = {col[0] for col in cursor.fetchall()}
            required_oil_well_fields = ['well_code', 'well_name', 'status', 'location']
            missing_oil_well_fields = [field for field in required_oil_well_fields if field not in oil_well_columns]
            
            if not missing_oil_well_fields:
                logger.info(f"{SUCCESS_MARK} 油井表包含所有必需字段")
            else:
                logger.error(f"{ERROR_MARK} 油井表缺少字段: {', '.join(missing_oil_well_fields)}")
            
            # 清理连接
            cursor.close()
            conn.close()
            
            # 创建管理员账户
            try:
                # 检查是否已有管理员账户
                admin = User.query.filter_by(username='管理员').first()
                if not admin:
                    admin = User(
                        username='管理员',
                        role='admin',
                        is_admin=True,
                        active=True
                    )
                    admin.set_password('admin123')
                    db.session.add(admin)
                    db.session.commit()
                    logger.info(f"{SUCCESS_MARK} 管理员账户创建成功")
                else:
                    logger.info(f"管理员账户已存在，跳过创建")
            except Exception as e:
                logger.error(f"{ERROR_MARK} 创建管理员账户失败: {str(e)}")
            
            logger.info("数据库初始化完成")
        except Exception as e:
            logger.error(f"数据库初始化失败: {str(e)}")
            logger.error(traceback.format_exc())

@cli.command(name='clear-all')  # 使用连字符
def clear_all():
    """清空所有表的数据但保留表结构"""
    with app.app_context():
        try:
            # 清理会话
            clear_user_sessions()
            
            # 添加风险警告
            confirm = input("警告: 此操作将清空所有表的数据！是否继续执行? (yes/no): ").strip().lower()
            if confirm != 'yes':
                logger.info("操作已取消")
                return
            
            # 获取所有表名
            conn = get_connection()
            if not conn:
                logger.error("无法连接到数据库，请检查配置")
                return
                
            cursor = conn.cursor()
            cursor.execute("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_type = 'BASE TABLE'
                AND table_name NOT IN ('alembic_version', 'spatial_ref_sys')
            """)
            tables = [table[0] for table in cursor.fetchall()]
            cursor.close()
            conn.close()
            
            # 清空所有表数据
            inspector = inspect(db.engine)
            existing_tables = inspector.get_table_names()
            
            # 首先清除有外键约束的表
            logger.info("正在清空表数据...")
            
            # 删除顺序非常重要，需要考虑外键引用
            deletion_order = [
                'alarms',          # 先删除告警，因为它可能引用任务和设备
                'tasks',           # 再删除任务，因为它可能引用设备和油井
                'edge_devices',    # 再删除设备
                'oil_wells',       # 再删除油井
                'users',           # 再删除用户
                'system_config',   # 再删除系统配置
                'key_value_settings', # 最后删除键值设置
            ]
            
            # 过滤出实际存在的表
            deletion_order = [table for table in deletion_order if table in existing_tables]
            
            # 添加其他没有列出的表
            other_tables = [table for table in existing_tables if table not in deletion_order and table != 'alembic_version']
            deletion_order.extend(other_tables)
            
            # 执行删除
            for table in deletion_order:
                try:
                    db.session.execute(text(f'DELETE FROM "{table}"'))
                    logger.info(f"{SUCCESS_MARK} 清空表 {table} 成功")
                except Exception as e:
                    logger.error(f"{ERROR_MARK} 清空表 {table} 失败: {str(e)}")
            
            # 提交事务
            db.session.commit()
            
            # 创建管理员账户
            admin = User(
                username='管理员',
                role='admin',
                is_admin=True,
                active=True
            )
            admin.set_password('admin123')
            db.session.add(admin)
            db.session.commit()
            logger.info(f"{SUCCESS_MARK} 管理员账户创建成功")
            
            logger.info("所有表数据已清空，并重新创建了管理员账户")
        except Exception as e:
            db.session.rollback()
            logger.error(f"清空表数据失败: {str(e)}")
            logger.error(traceback.format_exc())

@cli.command(name='clear-test')  # 使用连字符
def clear_test():
    """清空测试数据，但保留用户账户和系统配置"""
    with app.app_context():
        try:
            # 添加风险警告
            confirm = input("警告: 此操作将清空所有测试数据！是否继续执行? (yes/no): ").strip().lower()
            if confirm != 'yes':
                logger.info("操作已取消")
                return
            
            # 清空测试数据表
            test_tables = ['alarms', 'tasks', 'edge_devices', 'oil_wells']
            
            logger.info("正在清空测试数据...")
            
            # 按正确的顺序删除，考虑外键约束
            for table in test_tables:
                try:
                    db.session.execute(text(f'DELETE FROM "{table}"'))
                    logger.info(f"{SUCCESS_MARK} 清空表 {table} 成功")
                except Exception as e:
                    logger.error(f"{ERROR_MARK} 清空表 {table} 失败: {str(e)}")
            
            # 提交事务
            db.session.commit()
            
            logger.info("所有测试数据已清空")
        except Exception as e:
            db.session.rollback()
            logger.error(f"清空测试数据失败: {str(e)}")
            logger.error(traceback.format_exc())

@cli.command()
def backup():
    """备份数据库"""
    try:
        # 生成备份文件名（使用日期和时间）
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_file = f"backup_{DB_NAME}_{timestamp}.sql"
        
        # 构建pg_dump命令
        cmd = f'pg_dump -h {DB_HOST} -p {DB_PORT} -U {DB_USER} -F c -b -v -f "{backup_file}" {DB_NAME}'
        
        # 设置环境变量，支持密码
        os.environ['PGPASSWORD'] = DB_PASSWORD
        
        # 执行备份命令
        logger.info(f"正在备份数据库到 {backup_file}...")
        exit_code = os.system(cmd)
        
        # 清除环境变量中的密码
        os.environ.pop('PGPASSWORD', None)
        
        if exit_code == 0:
            logger.info(f"{SUCCESS_MARK} 数据库备份成功: {backup_file}")
        else:
            logger.error(f"{ERROR_MARK} 数据库备份失败，退出代码: {exit_code}")
    except Exception as e:
        logger.error(f"数据库备份过程中出错: {str(e)}")

@cli.command()
@click.argument('backup_file')
def restore(backup_file):
    """从备份文件恢复数据库"""
    try:
        # 检查备份文件是否存在
        if not os.path.exists(backup_file):
            logger.error(f"备份文件不存在: {backup_file}")
            return
        
        # 添加风险警告
        confirm = input(f"警告: 此操作将用备份文件 {backup_file} 覆盖现有数据库！是否继续执行? (yes/no): ").strip().lower()
        if confirm != 'yes':
            logger.info("操作已取消")
            return
        
        # 构建pg_restore命令
        cmd = f'pg_restore -h {DB_HOST} -p {DB_PORT} -U {DB_USER} -d {DB_NAME} -c -v "{backup_file}"'
        
        # 设置环境变量，支持密码
        os.environ['PGPASSWORD'] = DB_PASSWORD
        
        # 执行恢复命令
        logger.info(f"正在从 {backup_file} 恢复数据库...")
        exit_code = os.system(cmd)
        
        # 清除环境变量中的密码
        os.environ.pop('PGPASSWORD', None)
        
        if exit_code == 0:
            logger.info(f"{SUCCESS_MARK} 数据库恢复成功")
        else:
            logger.error(f"{ERROR_MARK} 数据库恢复失败，退出代码: {exit_code}")
    except Exception as e:
        logger.error(f"数据库恢复过程中出错: {str(e)}")

def clear_user_sessions():
    """清理所有用户会话"""
    try:
        logger.info("正在清理所有用户会话...")
        from app.models.users import User
        users = User.query.all()
        for user in users:
            user.current_token = None
            user.token_timestamp = None
        db.session.commit()
        logger.info(f"{SUCCESS_MARK} 所有用户会话已清理")
    except Exception as e:
        logger.error(f"清理用户会话失败: {str(e)}")

@cli.command()
def rebuild():
    """强制重建数据库表结构（警告：此操作会删除所有数据）"""
    with app.app_context():
        try:
            # 清理会话
            clear_user_sessions()
            
            # 添加风险警告
            confirm = input("警告: 此操作将删除所有表并重新创建，所有数据将丢失！是否继续执行? (yes/no): ").strip().lower()
            if confirm != 'yes':
                logger.info("操作已取消")
                return
            
            # 获取要删除的表名
            logger.info("正在获取数据库表信息...")
            inspector = inspect(db.engine)
            tables = inspector.get_table_names()
            
            # 排除alembic_version表
            tables = [table for table in tables if table != 'alembic_version']
            
            # 检查是否有表需要删除
            if not tables:
                logger.info("数据库中没有需要删除的表")
            else:
                # 首先删除表，必须考虑表之间的依赖关系
                # 按照依赖顺序删除表
                deletion_order = [
                    'alarms',          # 先删除告警，因为它可能引用任务和设备
                    'tasks',           # 再删除任务，因为它可能引用设备和油井
                    'edge_devices',    # 再删除设备
                    'oil_wells',       # 再删除油井
                    'users',           # 再删除用户
                    'system_config',   # 再删除系统配置
                    'key_value_settings', # 最后删除键值设置
                ]
                
                logger.info("正在删除表...")
                
                # 确保只删除存在的表，按照依赖顺序
                for table in deletion_order:
                    if table in tables:
                        try:
                            db.session.execute(text(f'DROP TABLE IF EXISTS "{table}" CASCADE'))
                            logger.info(f"{SUCCESS_MARK} 删除表 {table} 成功")
                        except Exception as e:
                            logger.error(f"{ERROR_MARK} 删除表 {table} 失败: {str(e)}")
                
                # 删除未在列表中但存在的表
                remaining_tables = [table for table in tables if table not in deletion_order]
                for table in remaining_tables:
                    try:
                        db.session.execute(text(f'DROP TABLE IF EXISTS "{table}" CASCADE'))
                        logger.info(f"{SUCCESS_MARK} 删除表 {table} 成功")
                    except Exception as e:
                        logger.error(f"{ERROR_MARK} 删除表 {table} 失败: {str(e)}")
                
                # 提交删除操作
                db.session.commit()
            
            # 重新创建所有表
            logger.info("正在创建新的表结构...")
            db.create_all()
            
            # 验证表是否创建成功
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'")
            existing_tables = {table[0] for table in cursor.fetchall()}
            
            # 检查每个预期的表是否已创建
            expected_tables = {
                'users': User,
                'alarms': Alarm,
                'edge_devices': EdgeDevice,
                'tasks': Task,
                'oil_wells': OilWell,  # 添加油井表
                'system_config': SystemConfig,
                'key_value_settings': KeyValueSetting
            }
            
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
            
            # 验证告警表字段
            cursor.execute("SELECT column_name FROM information_schema.columns WHERE table_name = 'alarms'")
            alarm_columns = {col[0] for col in cursor.fetchall()}
            
            # 检查告警表是否包含alarm_code字段
            if 'alarm_code' in alarm_columns:
                logger.info(f"{SUCCESS_MARK} 告警表结构正确，包含alarm_code字段")
            else:
                logger.error(f"{ERROR_MARK} 告警表结构不正确，不包含alarm_code字段")
            
            # 检查任务表字段
            cursor.execute("SELECT column_name FROM information_schema.columns WHERE table_name = 'tasks'")
            task_columns = {col[0] for col in cursor.fetchall()}
            
            # 检查任务表是否包含task_type字段
            if 'task_type' in task_columns:
                logger.info(f"{SUCCESS_MARK} 任务表结构正确，包含task_type字段")
            else:
                logger.error(f"{ERROR_MARK} 任务表结构不正确，不包含task_type字段")
            
            # 关闭连接
            cursor.close()
            conn.close()
            
            # 创建管理员账户
            admin = User(
                username='管理员',
                role='admin',
                is_admin=True,
                active=True
            )
            admin.set_password('admin123')
            db.session.add(admin)
            db.session.commit()
            logger.info(f"{SUCCESS_MARK} 管理员账户创建成功")
            
            logger.info("数据库表重建完成")
        except Exception as e:
            db.session.rollback()
            logger.error(f"重建表结构失败: {str(e)}")
            logger.error(traceback.format_exc())

if __name__ == '__main__':
    # 检查是否有命令行参数
    if len(sys.argv) > 1:
        cli()
    else:
        # 如果没有提供参数，打印帮助信息
        os.system(f"{sys.executable} {__file__} --help")

