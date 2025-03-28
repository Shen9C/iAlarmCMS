import os
from datetime import timedelta

class Config:
    # 基础配置
    DEBUG_LOG_ENABLED = True
    DEBUG = True
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-key-123'
    BASEDIR = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
    
    # 服务器配置
    HOST = '0.0.0.0'
    PORT = 5000
    
    # 数据库配置
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'sqlite:///' + os.path.join(BASEDIR, 'app.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # 会话配置
    PERMANENT_SESSION_LIFETIME = timedelta(days=7)
    TOKEN_EXPIRATION = timedelta(days=1)
    
    # 日志配置
    LOG_PATH = os.path.join(BASEDIR, 'logs')
    LOG_FILENAME = 'oilfield_gateway.log'
    LOG_MAX_BYTES = 50 * 1024 * 1024  # 50MB
    LOG_BACKUP_COUNT = 20
    LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    
    # 应用配置
    ITEMS_PER_PAGE = 20
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB
    UPLOAD_FOLDER = os.path.join(BASEDIR, 'uploads')
    ALLOWED_EXTENSIONS = {'txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif', 'csv', 'xlsx'}
    
    # 安全配置
    SESSION_COOKIE_SECURE = True
    REMEMBER_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    REMEMBER_COOKIE_HTTPONLY = True

config = Config