import os

class Config:
    # 基本配置
    SECRET_KEY = 'dev'
    SQLALCHEMY_DATABASE_URI = 'sqlite:///app.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # 密码策略配置
    PASSWORD_MIN_LENGTH = 8
    PASSWORD_REQUIRE_UPPER = True
    PASSWORD_REQUIRE_LOWER = True
    PASSWORD_REQUIRE_DIGIT = True
    PASSWORD_REQUIRE_SPECIAL = True
    
    # 邮件配置
    MAIL_SERVER = 'smtp.163.com'
    MAIL_PORT = 587
    MAIL_USE_TLS = True
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')
    
    # 告警配置
    ALARM_RETENTION_DAYS = 30
    ALARM_REFRESH_INTERVAL = 30