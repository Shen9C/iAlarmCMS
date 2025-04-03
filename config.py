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


# # PostgreSQL数据库配置
# DB_USER = os.environ.get('DB_USER') or 'postgres'
# DB_PASSWORD = os.environ.get('DB_PASSWORD') or 'password'
# DB_HOST = os.environ.get('DB_HOST') or 'localhost'
# DB_PORT = os.environ.get('DB_PORT') or '5432'
# DB_NAME = os.environ.get('DB_NAME') or 'oilfield_web'

# PostgreSQL数据库配置
DB_USER = 'shen9c'
DB_PASSWORD = '123456'
DB_HOST = 'localhost'
DB_PORT = '25432'
DB_NAME = 'oilfield_web'
# 构建PostgreSQL连接URI
SQLALCHEMY_DATABASE_URI = f'postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}'