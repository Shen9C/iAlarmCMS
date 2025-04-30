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
import sys
from enum import Enum, auto

# 加载环境变量
load_dotenv()

# 配置日志
logger = logging.getLogger(__name__)

class ConfigEnv(Enum):
    """配置环境枚举"""
    PROD = auto()  # 生产环境
    TEST = auto()  # 测试环境
    DEV = auto()   # 开发环境

def get_config_env():
    """
    获取当前配置环境
    
    优先级：
    1. 命令行参数 --debug
    2. 环境变量 FLASK_ENV
    3. 默认生产环境
    
    Returns:
        ConfigEnv: 配置环境
    """
    # 检查命令行参数
    if '--debug' in sys.argv:
        return ConfigEnv.TEST
    
    # 检查环境变量
    flask_env = os.environ.get('FLASK_ENV', '').lower()
    if flask_env == 'test':
        return ConfigEnv.TEST
    elif flask_env == 'development':
        return ConfigEnv.DEV
    
    # 默认生产环境
    return ConfigEnv.PROD

def get_config_path(env):
    """
    获取指定环境的配置文件路径
    
    Args:
        env: 配置环境
        
    Returns:
        tuple: (基础配置文件路径, 环境配置文件路径)
    """
    config_dir = Path(__file__).parent.parent.parent / "config"
    base_config_path = config_dir / 'settings.yaml'
    
    if env == ConfigEnv.TEST:
        env_config_path = config_dir / 'settings_test.yaml'
    elif env == ConfigEnv.DEV:
        env_config_path = config_dir / 'settings_dev.yaml'
    else:
        env_config_path = None
        
    return base_config_path, env_config_path

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

def load_yaml_config(config_path):
    """
    加载指定的YAML配置文件
    
    Args:
        config_path: YAML配置文件路径
        
    Returns:
        dict: 配置数据
    """
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    except Exception as e:
        logger.error(f"无法加载配置文件 {config_path}: {str(e)}")
        return {}

def merge_configs(base_config, override_config):
    """
    合并两个配置字典
    
    Args:
        base_config: 基础配置
        override_config: 覆盖配置
        
    Returns:
        dict: 合并后的配置
    """
    if not override_config:
        return base_config
        
    result = base_config.copy()
    for key, value in override_config.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = merge_configs(result[key], value)
        else:
            result[key] = value
    return result

def process_config_values(config_dict):
    """
    处理配置字典中的特殊值，如环境变量
    
    Args:
        config_dict: 配置字典
    """
    for key, value in config_dict.items():
        if isinstance(value, dict):
            process_config_values(value)
        elif isinstance(value, str) and value.startswith('${') and value.endswith('}'):
            env_var = value[2:-1]
            if ':-' in env_var:
                env_name, default = env_var.split(':-', 1)
                config_dict[key] = os.environ.get(env_name, default)
            else:
                config_dict[key] = os.environ.get(env_var, '')

def create_config_object(config_dict):
    """
    创建配置对象
    
    Args:
        config_dict: 配置字典
        
    Returns:
        ConfigObject: 配置对象
    """
    # 处理特殊值
    process_config_values(config_dict)
    
    # 创建配置对象
    config = ConfigObject(config_dict)
    
    # 添加数据库URI
    if hasattr(config, 'database'):
        db = config.database
        config.SQLALCHEMY_DATABASE_URI = f'postgresql://{db.user}:{db.password}@{db.host}:{db.port}/{db.name}'
        config.SQLALCHEMY_TRACK_MODIFICATIONS = False
        
        # 导出数据库配置为顶级属性
        config.DB_USER = db.user
        config.DB_PASSWORD = db.password
        config.DB_HOST = db.host 
        config.DB_PORT = db.port
        config.DB_NAME = db.name
    
    # 处理服务器配置
    if hasattr(config, 'web_server'):
        config.WEB_HOST = config.web_server.host
        config.WEB_PORT = config.web_server.port
    else:
        config.WEB_HOST = getattr(config, 'host', '0.0.0.0')
        config.WEB_PORT = getattr(config, 'port', 5000)
    
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
    
    return config

def load_app_config():
    """
    加载应用配置，根据环境自动选择配置文件
    
    Returns:
        ConfigObject: 配置对象
    """
    # 获取当前环境
    env = get_config_env()
    logger.info(f"当前配置环境: {env.name}")
    
    # 获取配置文件路径
    base_config_path, env_config_path = get_config_path(env)
    
    # 加载基础配置
    base_config = load_yaml_config(base_config_path)
    
    # 如果存在环境特定配置，则加载并合并
    if env_config_path and env_config_path.exists():
        env_config = load_yaml_config(env_config_path)
        if env_config:
            logger.info(f"加载{env.name}环境配置")
            config_data = merge_configs(base_config, env_config)
        else:
            config_data = base_config
    else:
        config_data = base_config
    
    # 创建配置对象
    return create_config_object(config_data)

# 导出配置对象
config = load_app_config() 