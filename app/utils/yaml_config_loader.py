#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
YAML配置加载器
负责加载YAML配置文件并转换为Python对象
"""

import os
import yaml
from pathlib import Path
import logging
from datetime import timedelta
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 配置日志
logger = logging.getLogger(__name__)

class ConfigObject:
    """配置对象类，用于将字典转换为对象属性"""
    def __init__(self, config_dict):
        for key, value in config_dict.items():
            if isinstance(value, dict):
                setattr(self, key, ConfigObject(value))
            else:
                setattr(self, key, value)
                
    def __getitem__(self, key):
        return getattr(self, key)
        
    def get(self, key, default=None):
        return getattr(self, key, default)

def load_config(env=None):
    """
    加载配置文件
    
    Args:
        env: 环境名称，如'development', 'production'等
        
    Returns:
        ConfigObject: 配置对象
    """
    # 确定环境
    if env is None:
        env = os.environ.get('FLASK_ENV', 'development')
    
    # 获取配置文件路径
    project_root = Path(__file__).resolve().parent.parent.parent
    config_dir = project_root / "config"
    base_config_path = config_dir / 'settings.yaml'
    env_config_path = config_dir / f'{env}.yaml'
    
    # 读取基础配置
    try:
        with open(base_config_path, 'r', encoding='utf-8') as f:
            config_data = yaml.safe_load(f)
    except Exception as e:
        logger.error(f"无法加载基础配置文件: {str(e)}")
        config_data = {}
    
    # 读取环境特定配置并合并
    if env_config_path.exists():
        try:
            with open(env_config_path, 'r', encoding='utf-8') as f:
                env_config = yaml.safe_load(f)
                if env_config:
                    deep_merge_dict(config_data, env_config)
        except Exception as e:
            logger.error(f"无法加载环境配置文件: {str(e)}")
    
    # 处理特殊类型和环境变量
    process_special_values(config_data)
    
    # 创建配置对象
    config = ConfigObject(config_data)
    
    # 添加数据库URI - 添加到配置对象的顶层
    if hasattr(config, 'database'):
        db = config.database
        # 直接设置SQLALCHEMY_DATABASE_URI作为顶级属性
        config.SQLALCHEMY_DATABASE_URI = f'postgresql://{db.user}:{db.password}@{db.host}:{db.port}/{db.name}'
        config.SQLALCHEMY_TRACK_MODIFICATIONS = False
        
        # 导出数据库配置为顶级属性，方便scripts/init_pg_db.py使用
        config.DB_USER = db.user
        config.DB_PASSWORD = db.password
        config.DB_HOST = db.host 
        config.DB_PORT = db.port
        config.DB_NAME = db.name
    
    # 处理服务器配置
    # 兼容性处理：优先使用专用的web_server和api_server配置，如果不存在则使用顶级host和port配置
    # Web服务器配置
    if hasattr(config, 'web_server'):
        config.WEB_HOST = config.web_server.host
        config.WEB_PORT = config.web_server.port
    else:
        config.WEB_HOST = getattr(config, 'host', '0.0.0.0')
        config.WEB_PORT = getattr(config, 'port', 5000)
    
    # API服务器配置
    if hasattr(config, 'api_server'):
        config.API_HOST = config.api_server.host
        config.API_PORT = config.api_server.port
    else:
        config.API_HOST = getattr(config, 'host', '0.0.0.0')
        config.API_PORT = getattr(config, 'port', 5566)
    
    # 添加Flask应用所需的属性
    config.BASEDIR = os.path.abspath(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
    
    if hasattr(config, 'session'):
        config.PERMANENT_SESSION_LIFETIME = timedelta(days=config.session.permanent_lifetime_days)
        config.TOKEN_EXPIRATION = timedelta(days=config.session.token_expiration_days)
    
    # 处理安全配置
    if hasattr(config, 'security'):
        config.SESSION_COOKIE_SECURE = config.security.session_cookie_secure
        config.REMEMBER_COOKIE_SECURE = config.security.remember_cookie_secure
        config.SESSION_COOKIE_HTTPONLY = config.security.session_cookie_httponly
        config.REMEMBER_COOKIE_HTTPONLY = config.security.remember_cookie_httponly
    
    # 处理其他应用配置
    if hasattr(config, 'application'):
        app = config.application
        config.ITEMS_PER_PAGE = app.items_per_page
        config.MAX_CONTENT_LENGTH = app.max_content_length
        config.UPLOAD_FOLDER = os.path.join(config.BASEDIR, app.upload_folder)
        config.ALLOWED_EXTENSIONS = set(app.allowed_extensions)
    
    # 处理一些Flask特定的配置
    config.DEBUG = config.debug
    config.SECRET_KEY = config.secret_key
    
    if hasattr(config, 'logging'):
        config.LOG_PATH = os.path.join(config.BASEDIR, config.logging.path)
        config.LOG_FILENAME = config.logging.filename
        config.LOG_MAX_BYTES = config.logging.max_bytes
        config.LOG_BACKUP_COUNT = config.logging.backup_count
        config.LOG_FORMAT = config.logging.format
    
    # 处理SSL配置
    if hasattr(config, 'ssl'):
        ssl = config.ssl
        # 证书目录
        ssl_dir = os.path.join(config.BASEDIR, ssl.cert_dir)
        
        # Web服务器SSL配置
        config.WEB_SSL_CERT = os.path.join(ssl_dir, ssl.cert_file)
        config.WEB_SSL_KEY = os.path.join(ssl_dir, ssl.key_file)
        
        # API服务器SSL配置
        config.API_SSL_CERT = os.path.join(ssl_dir, ssl.api_cert_file)
        config.API_SSL_KEY = os.path.join(ssl_dir, ssl.api_key_file)
    
    return config

def deep_merge_dict(base, override):
    """
    深度合并两个字典
    
    Args:
        base: 基础字典
        override: 覆盖字典
    
    Returns:
        dict: 合并后的字典
    """
    for key, value in override.items():
        if key in base and isinstance(base[key], dict) and isinstance(value, dict):
            deep_merge_dict(base[key], value)
        else:
            base[key] = value
    return base

def process_special_values(config_dict):
    """
    处理配置字典中的特殊值，如环境变量
    
    Args:
        config_dict: 配置字典
    """
    for key, value in config_dict.items():
        if isinstance(value, dict):
            process_special_values(value)
        elif isinstance(value, str) and value.startswith('${') and value.endswith('}'):
            # 处理环境变量替换，格式: ${ENV_VAR:-default_value}
            env_var = value[2:-1]
            if ':-' in env_var:
                env_name, default = env_var.split(':-', 1)
                config_dict[key] = os.environ.get(env_name, default)
            else:
                config_dict[key] = os.environ.get(env_var, '')

# 导出配置类和实例
Config = load_config
config = load_config() 