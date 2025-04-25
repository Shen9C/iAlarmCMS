import os
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
import multiprocessing
import fcntl
import errno
import yaml
import sys
import traceback

# 加载配置文件
def load_config():
    config_path = Path(__file__).parent.parent.parent / 'config' / 'settings.yaml'
    with open(config_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)

# 获取配置
config = load_config()
logging_config = config.get('logging', {})

# 确保日志目录存在
log_dir = Path(logging_config.get('path', 'logs'))
log_dir.mkdir(parents=True, exist_ok=True)

# 禁用所有数据库相关的日志输出
logging.getLogger('sqlalchemy.engine').setLevel(logging.WARNING)
logging.getLogger('sqlalchemy.pool').setLevel(logging.WARNING)
logging.getLogger('sqlalchemy.dialects').setLevel(logging.WARNING)
logging.getLogger('sqlalchemy.orm').setLevel(logging.WARNING)
logging.getLogger('sqlalchemy').setLevel(logging.WARNING)
logging.getLogger('alembic').setLevel(logging.WARNING)
logging.getLogger('app.models').setLevel(logging.WARNING)
logging.getLogger('app.utils.db_connection').setLevel(logging.WARNING)

# 配置Flask的日志
logging.getLogger('werkzeug').setLevel(logging.INFO)
logging.getLogger('flask').setLevel(logging.INFO)

# 从配置文件读取日志格式
LOG_FORMAT = logging_config.get('format', '[%(asctime)s] %(name)s - %(levelname)s - %(message)s')
DATE_FORMAT = logging_config.get('date_format', '%Y-%m-%d %H:%M:%S')

# 设置日志文件路径
log_files = {
    'main': str(log_dir / 'oilfield.log'),
    'db': str(log_dir / logging_config.get('db_log', 'db_init.log'))
}

# 从配置文件读取日志文件大小和备份数量
MAX_BYTES = logging_config.get('max_bytes', 52428800)  # 50MB
BACKUP_COUNT = logging_config.get('backup_count', 20)  # 默认保留20个备份

# 打印日志配置信息
print(f"日志配置: {logging_config}")
print(f"日志目录: {log_dir.absolute()}")
print(f"日志文件: {log_files}")

class LockedRotatingFileHandler(RotatingFileHandler):
    """支持文件锁的RotatingFileHandler"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.lock = None
    
    def _open(self):
        stream = super()._open()
        # 获取文件锁
        try:
            fcntl.lockf(stream.fileno(), fcntl.LOCK_EX)
        except (IOError, OSError) as e:
            if e.errno != errno.EAGAIN:
                raise
        return stream
    
    def emit(self, record):
        try:
            super().emit(record)
        except Exception as e:
            print(f"日志写入失败: {e}")
            raise
    
    def close(self):
        if self.lock:
            try:
                fcntl.lockf(self.stream.fileno(), fcntl.LOCK_UN)
            except (IOError, OSError):
                pass
        super().close()

# 主进程日志记录器字典
_loggers = {}

def get_logger(name='main', level=logging.INFO):
    """
    获取或创建logger实例
    
    Args:
        name: logger名称，默认为'main'
        level: 日志级别，默认为INFO
    
    Returns:
        logging.Logger: 配置好的logger实例
    """
    global _loggers
    
    # 如果是主进程，创建主日志记录器
    if multiprocessing.current_process().name == 'MainProcess':
        if name not in _loggers:
            logger = logging.getLogger(name)
            logger.setLevel(level)
            
            # 如果已经有处理器，先移除
            if logger.handlers:
                for handler in logger.handlers[:]:
                    logger.removeHandler(handler)
            
            # 创建格式化器
            formatter = logging.Formatter(LOG_FORMAT, DATE_FORMAT)
            
            # 确保日志文件所在目录存在
            log_file = log_files.get(name, log_files['main'])
            log_file_path = Path(log_file)
            log_file_path.parent.mkdir(parents=True, exist_ok=True)
            
            # 创建文件处理器
            file_handler = LockedRotatingFileHandler(
                log_file,
                maxBytes=MAX_BYTES,
                backupCount=BACKUP_COUNT,
                encoding='utf-8'
            )
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)
            
            # 添加控制台处理器
            console_handler = logging.StreamHandler()
            console_handler.setFormatter(formatter)
            logger.addHandler(console_handler)
            
            _loggers[name] = logger
        
        return _loggers[name]
    
    # 如果是子进程，返回一个简单的日志记录器
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    # 如果已经有处理器，先移除
    if logger.handlers:
        for handler in logger.handlers[:]:
            logger.removeHandler(handler)
    
    # 添加一个简单的处理器，将日志发送到主进程
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter(LOG_FORMAT, DATE_FORMAT))
    logger.addHandler(handler)
    
    return logger

# 初始化默认日志记录器
main_logger = get_logger('main')
db_logger = get_logger('db')

# 配置Flask的日志记录器
flask_logger = get_logger('flask')
werkzeug_logger = get_logger('werkzeug')

# 测试日志写入
print("\n测试日志写入...")
main_logger.info("这是一条主进程测试日志")
db_logger.info("这是一条数据库测试日志")
flask_logger.info("这是一条Flask测试日志")
werkzeug_logger.info("这是一条Werkzeug测试日志")
print("测试日志写入完成") 