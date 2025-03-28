from flask import Flask
import os
import json
import datetime

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'hard-to-guess-string'
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:///app.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # 告警图片存储路径配置
    ALARM_IMAGES_PATH = "e:/oilfield_data/alarm_images"  # 默认外部路径
    
    # 用户会话配置
    PERMANENT_SESSION_LIFETIME = datetime.timedelta(hours=12)
    
    # 告警配置
    ALARM_RETENTION_DAYS = 30  # 告警数据保留天数
    
    # 边缘设备配置
    EDGE_DEVICE_HEARTBEAT_TIMEOUT = 300  # 边缘设备心跳超时时间(秒)
    
    # 任务配置
    TASK_TIMEOUT = 3600  # 任务超时时间(秒)
    
    # 安全配置
    TOKEN_EXPIRATION = 3600  # 令牌过期时间(秒)
    
    # 分页配置
    ITEMS_PER_PAGE = 20

def load_machine_config():
    """加载机机认证配置"""
    config_path = os.path.join(os.path.dirname(__file__), 'machine_auth.json')
    try:
        if os.path.exists(config_path):
            with open(config_path, 'r') as f:
                return json.load(f)
        else:
            # 默认配置
            return {
                'access_key': 'default_access_key',
                'secret_key': 'default_secret_key'
            }
    except Exception as e:
        print(f"Error loading machine config: {e}")
        return {
            'access_key': 'default_access_key',
            'secret_key': 'default_secret_key'
        }

class DevelopmentConfig(Config):
    """开发环境配置"""
    DEBUG = True

class TestingConfig(Config):
    """测试环境配置"""
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'

class ProductionConfig(Config):
    """生产环境配置"""
    DEBUG = False

# 环境配置映射
config = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}

def get_config(config_name=None):
    """获取配置对象"""
    if not config_name:
        config_name = os.environ.get('FLASK_CONFIG') or 'default'
    return config.get(config_name, config['default'])