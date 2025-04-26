import logging
import logging.config
import multiprocessing
import os
from concurrent_log_handler import ConcurrentRotatingFileHandler

def setup_logger():
    # 确保日志目录存在
    log_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'logs')
    os.makedirs(log_dir, exist_ok=True)

    LOGGING_CONFIG = {
        'version': 1,
        'disable_existing_loggers': False,
        'formatters': {
            'standard': {
                'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            },
        },
        'handlers': {
            'console': {
                'level': 'INFO',
                'class': 'logging.StreamHandler',
                'formatter': 'standard',
            },
            'file': {
                'level': 'INFO',
                'class': 'concurrent_log_handler.ConcurrentRotatingFileHandler',
                'filename': os.path.join(log_dir, 'app.log'),
                'maxBytes': 10*1024*1024,  # 10MB
                'backupCount': 5,
                'formatter': 'standard',
            },
        },
        'root': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
        }
    }

    # 配置日志
    logging.config.dictConfig(LOGGING_CONFIG)
    logger = logging.getLogger()

    # 手动设置锁
    for handler in logger.handlers:
        if not hasattr(handler, 'lock'):
            handler.lock = multiprocessing.RLock()

    return logger