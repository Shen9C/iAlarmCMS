import logging
import logging.config
import multiprocessing
import os
from concurrent_log_handler import ConcurrentRotatingFileHandler
from app.utils.yaml_config_loader import config

def setup_logger():
    # 确保日志目录存在
    log_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'logs')
    os.makedirs(log_dir, exist_ok=True)

    # 从配置文件获取日志级别
    log_level = config.logging.level if hasattr(config, 'logging') and hasattr(config.logging, 'level') else 'DEBUG'
    print(f"设置日志级别为: {log_level}")  # 添加调试输出

    LOGGING_CONFIG = {
        'version': 1,
        'disable_existing_loggers': False,  # 确保不禁用现有日志记录器
        'formatters': {
            'standard': {
                'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            },
        },
        'handlers': {
            'console': {
                'level': log_level,
                'class': 'logging.StreamHandler',
                'formatter': 'standard',
            },
            'file': {
                'level': log_level,
                'class': 'concurrent_log_handler.ConcurrentRotatingFileHandler',
                'filename': os.path.join(log_dir, 'app.log'),
                'maxBytes': 10*1024*1024,
                'backupCount': 5,
                'formatter': 'standard',
            },
        },
        'root': {
            'handlers': ['console', 'file'],
            'level': log_level,
        },
        'loggers': {
            'app': {  # 添加app命名空间的日志配置
                'handlers': ['console', 'file'],
                'level': log_level,
                'propagate': True
            }
        }
    }

    # 配置日志
    logging.config.dictConfig(LOGGING_CONFIG)
    logger = logging.getLogger()

    # 手动设置锁
    for handler in logger.handlers:
        if not hasattr(handler, 'lock'):
            handler.lock = multiprocessing.RLock()

    # 验证日志级别
    print(f"根日志记录器级别: {logging.getLogger().getEffectiveLevel()}")
    print(f"app日志记录器级别: {logging.getLogger('app').getEffectiveLevel()}")

    return logger