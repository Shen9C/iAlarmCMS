#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
油田设备监控系统启动脚本
支持同时运行Web应用和设备API，或者单独运行其中一个
"""

import os
import sys
import time
import logging
import argparse
import threading
from pathlib import Path

from flask import Flask, has_request_context, request
from flask.logging import default_handler
from logging.config import dictConfig
from sqlalchemy.sql import text

# 将项目根目录添加到系统路径
project_root = Path(__file__).resolve().parent
sys.path.insert(0, str(project_root))

# 导入应用和配置
from app import create_app, db, models
from app.utils.yaml_config_loader import config

# 导入模型类，从正确的子模块导入
from app.models.users import User
from app.models.alarms import Alarm
from app.models.tasks import Task
from app.models.oil_wells import OilWell

# 尝试导入设备模型（如果存在）
try:
    from app.models.edge_devices import EdgeDevice as Device
except ImportError:
    # 如果不存在，创建一个空类以保持兼容性
    class Device:
        pass

# 导入自定义SSL模块
try:
    from app.utils.custom_ssl import get_ssl_context, enable_ssl_for_app
except ImportError:
    logging.warning("无法导入自定义SSL模块，请确保app/utils/custom_ssl.py文件存在")

# 设置日志格式
class RequestFormatter(logging.Formatter):
    def format(self, record):
        if has_request_context():
            record.url = request.url
            record.remote_addr = request.remote_addr
        else:
            record.url = None
            record.remote_addr = None
        return super().format(record)

formatter = RequestFormatter(
    '[%(asctime)s] %(remote_addr)s requested %(url)s\n'
    '%(levelname)s in %(module)s: %(message)s'
)
default_handler.setFormatter(formatter)

# 配置日志
dictConfig({
    'version': 1,
    'formatters': {'default': {
        'format': '[%(asctime)s] %(levelname)s in %(module)s: %(message)s',
    }},
    'handlers': {'wsgi': {
        'class': 'logging.StreamHandler',
        'stream': 'ext://sys.stdout',
        'formatter': 'default'
    }},
    'root': {
        'level': 'INFO',
        'handlers': ['wsgi']
    }
})

def clear_all_sessions():
    """清除所有用户会话"""
    with models.db.engine.connect() as conn:
        result = conn.execute(text("UPDATE users SET current_token = NULL"))
        conn.commit()
    print(f"已清除所有用户会话")

def check_ssl_files(is_api=False):
    """
    检查SSL证书和密钥文件是否存在
    
    Args:
        is_api: 是否检查API证书（否则检查Web证书）
    """
    if is_api:
        cert_path = config.API_SSL_CERT
        key_path = config.API_SSL_KEY
    else:
        cert_path = config.WEB_SSL_CERT
        key_path = config.WEB_SSL_KEY
    
    # 检查证书和密钥文件
    if not os.path.exists(cert_path):
        logging.error(f"SSL证书文件不存在: {cert_path}")
        return False
    
    if not os.path.exists(key_path):
        logging.error(f"SSL密钥文件不存在: {key_path}")
        return False
    
    logging.info(f"找到SSL证书: {cert_path}")
    logging.info(f"找到SSL密钥: {key_path}")
    return True

def get_ssl_context(is_api=False):
    """
    获取SSL上下文
    
    Args:
        is_api: 是否获取API证书的SSL上下文
    """
    if is_api:
        cert_path = config.API_SSL_CERT
        key_path = config.API_SSL_KEY
    else:
        cert_path = config.WEB_SSL_CERT
        key_path = config.WEB_SSL_KEY
    
    try:
        # 如果自定义SSL模块可用，使用它
        from app.utils.custom_ssl import get_ssl_context
        return get_ssl_context(cert_path, key_path)
    except (ImportError, TypeError):
        # 否则使用简单的元组
        return (cert_path, key_path)

def run_web_app(host=None, port=None, debug=False, use_ssl=True):
    """运行Web应用服务器"""
    # 使用配置中的值作为默认值
    if host is None:
        host = config.WEB_HOST
    if port is None:
        port = config.WEB_PORT
    
    app = create_app('web')
    
    # 打印当前的路由
    logging.info("Web应用服务器路由:")
    for rule in app.url_map.iter_rules():
        logging.info(f"{rule.endpoint}: {rule.rule}")
    
    # 准备SSL选项
    ssl_context = None
    if use_ssl:
        if not check_ssl_files(is_api=False):
            logging.error("Web证书文件不存在，无法以HTTPS模式启动，将回退到HTTP模式")
            use_ssl = False
        else:
            ssl_context = get_ssl_context(is_api=False)
            if not ssl_context:
                logging.error("无法创建Web证书的SSL上下文，无法以HTTPS模式启动，将回退到HTTP模式")
                use_ssl = False
            else:
                logging.info("Web应用服务器将以HTTPS模式启动")
    
    # 启动服务器
    logging.info(f"Web应用服务器启动于 {'https' if use_ssl else 'http'}://{host}:{port}")
    app.run(host=host, port=port, debug=debug, ssl_context=ssl_context)

def run_device_api(host=None, port=None, debug=False, use_ssl=True):
    """运行边缘设备API服务器"""
    # 使用配置中的值作为默认值
    if host is None:
        host = config.API_HOST
    if port is None:
        port = config.API_PORT
    
    app = create_app('api')
    
    # 打印当前的路由
    logging.info("边缘设备API服务器路由:")
    for rule in app.url_map.iter_rules():
        logging.info(f"{rule.endpoint}: {rule.rule}")
    
    # 准备SSL选项
    ssl_context = None
    if use_ssl:
        if not check_ssl_files(is_api=True):
            logging.error("API证书文件不存在，无法以HTTPS模式启动，将回退到HTTP模式")
            use_ssl = False
        else:
            ssl_context = get_ssl_context(is_api=True)
            if not ssl_context:
                logging.error("无法创建API证书的SSL上下文，无法以HTTPS模式启动，将回退到HTTP模式")
                use_ssl = False
            else:
                logging.info("边缘设备API服务器将以HTTPS模式启动")
    
    # 启动服务器
    logging.info(f"边缘设备API服务器启动于 {'https' if use_ssl else 'http'}://{host}:{port} {'(调试模式)' if debug else ''}")
    app.run(host=host, port=port, debug=debug, ssl_context=ssl_context)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='油田监控系统服务端')
    parser.add_argument('--web-host', default=None, help=f'Web应用主机 (默认: {config.WEB_HOST})')
    parser.add_argument('--web-port', type=int, default=None, help=f'Web应用端口 (默认: {config.WEB_PORT})')
    parser.add_argument('--api-host', default=None, help=f'设备API主机 (默认: {config.API_HOST})')
    parser.add_argument('--api-port', type=int, default=None, help=f'设备API端口 (默认: {config.API_PORT})')
    parser.add_argument('--debug', action='store_true', help='启用调试模式')
    parser.add_argument('--http', action='store_true', help='使用HTTP模式替代默认的HTTPS模式')
    parser.add_argument('--api-only', action='store_true', help='仅启动设备API')
    parser.add_argument('--web-only', action='store_true', help='仅启动Web应用')
    parser.add_argument('--clear-sessions', action='store_true', help='清除所有用户会话')
    
    args = parser.parse_args()
    
    # 设置日志级别
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
        logging.info("调试日志已启用")
    
    # 清除所有会话
    if args.clear_sessions:
        clear_all_sessions()
    
    # 确定是否使用SSL
    use_ssl = not args.http
    
    # 输出用户情况
    try:
        users = User.query.all()
        logging.info(f"系统中有 {len(users)} 个用户")
        for user in users:
            logging.info(f"用户: {user.username}, Email: {user.email if hasattr(user, 'email') else 'N/A'}, 角色: {user.role}")
    except Exception as e:
        logging.warning(f"无法获取用户列表: {str(e)}")
    
    # 如果指定了--api-only，则只启动API服务器
    if args.api_only:
        run_device_api(args.api_host, args.api_port, args.debug, use_ssl)
    # 如果指定了--web-only，则只启动Web应用
    elif args.web_only:
        run_web_app(args.web_host, args.web_port, args.debug, use_ssl)
    # 否则，启动两个服务器
    else:
        # 启动Web应用服务器线程
        web_thread = threading.Thread(
            target=run_web_app,
            args=(args.web_host, args.web_port, args.debug, use_ssl)
        )
        web_thread.daemon = True
        web_thread.start()
        
        # 稍微延迟以确保日志不会混淆
        time.sleep(0.1)
        
        # 启动设备API服务器
        run_device_api(args.api_host, args.api_port, args.debug, use_ssl)