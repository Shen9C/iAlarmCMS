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
from app import create_web_app, create_api_app, db, models
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

def run_web_app(host=None, port=None, debug=False, use_ssl=True, use_keep_alive=False):
    """
    运行Web应用服务器
    
    Args:
        host: 主机地址，默认使用配置中的WEB_HOST
        port: 端口号，默认使用配置中的WEB_PORT
        debug: 是否启用调试模式
        use_ssl: 是否使用SSL
        use_keep_alive: 是否使用长连接，默认False表示使用短连接
    """
    # 使用配置中的值作为默认值
    if host is None:
        host = config.WEB_HOST
    if port is None:
        port = config.WEB_PORT
    
    logging.info("正在创建Web应用实例...")
    app = create_web_app()
    logging.info("Web应用实例创建成功")
    
    # 如果不使用长连接，添加全局中间件，设置短连接
    if not use_keep_alive:
        @app.after_request
        def set_connection_close(response):
            response.headers["Connection"] = "close"
            return response
        logging.info("Web应用服务器将使用短连接模式")
    else:
        logging.info("Web应用服务器将使用长连接模式")
    
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
    try:
        # 尝试正常启动服务器 - 删除不支持的keep_alive_timeout参数
        app.run(host=host, port=port, debug=debug, ssl_context=ssl_context, 
                threaded=True, processes=1, use_reloader=debug)
    except OSError as e:
        # 捕获套接字错误
        logging.error(f"启动Web服务器时发生错误: {str(e)}")
        logging.info("尝试使用替代方法启动服务器...")
        
        # 对于Windows环境下的socket.fromfd错误，使用threaded=False和简化的SSL上下文
        if "非套接字上尝试了一个操作" in str(e) or "[WinError 10038]" in str(e):
            # 在Windows上，使用简化的SSL上下文模式
            if use_ssl:
                import ssl
                logging.info("使用简化的SSL上下文...")
                context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
                web_cert_path = config.WEB_SSL_CERT
                web_key_path = config.WEB_SSL_KEY
                context.load_cert_chain(web_cert_path, web_key_path)
                ssl_context = context
            
            # 禁用线程模式和进程模式
            logging.info("以非线程模式启动服务器...")
            app.run(host=host, port=port, debug=debug, ssl_context=ssl_context, 
                   threaded=False, processes=1)
        else:
            # 其他类型的错误，重新抛出
            raise

def run_device_api(host=None, port=None, debug=False, use_ssl=True, use_keep_alive=False):
    """
    运行设备API服务器
    
    Args:
        host: 主机地址，默认使用配置中的API_HOST
        port: 端口号，默认使用配置中的API_PORT
        debug: 是否启用调试模式
        use_ssl: 是否使用SSL
        use_keep_alive: 是否使用长连接，默认False表示使用短连接
    """
    # 使用配置中的值作为默认值
    if host is None:
        host = config.API_HOST
    if port is None:
        port = config.API_PORT
    
    # 检查SSL
    if use_ssl and not check_ssl_files(is_api=True):
        logging.error("API证书文件不存在，无法以HTTPS模式启动，将回退到HTTP模式")
        use_ssl = False
    elif use_ssl:
        # 仅当use_ssl为True且证书文件存在时，才获取SSL上下文
        ssl_context = get_ssl_context(is_api=True)
        if not ssl_context:
            logging.error("无法创建API证书的SSL上下文，无法以HTTPS模式启动，将回退到HTTP模式")
            use_ssl = False
        else:
            logging.info("边缘设备API服务器初始化完成")
            logging.info(f"证书文件: {config.API_SSL_CERT}")
            logging.info(f"密钥文件: {config.API_SSL_KEY}")
    
    # 启动API服务器
    logging.info(f"边缘设备API服务器将在 {'0.0.0.0' if host == '0.0.0.0' else host}:{port} 上启动{'，启用调试模式' if debug else ''}")
    from start_api_server import run_api_server
    run_api_server(host, port, debug, use_ssl, use_keep_alive=use_keep_alive)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='运行Web应用或API服务器')
    parser.add_argument('--host', help='主机地址，默认使用配置中的值')
    parser.add_argument('--port', type=int, help='端口号，默认使用配置中的值')
    parser.add_argument('--api-only', action='store_true', help='仅运行API服务器')
    parser.add_argument('--web-only', action='store_true', help='仅运行Web应用')
    parser.add_argument('--debug', action='store_true', help='启用调试模式')
    parser.add_argument('--no-ssl', action='store_true', help='禁用SSL（默认启用SSL）')
    parser.add_argument('--use-keep-alive', action='store_true', 
                        help='使用长连接（默认为短连接）')
    
    args = parser.parse_args()
    
    # 运行Web应用
    if not args.api_only:
        run_web_app(host=args.host, port=args.port, debug=args.debug, 
                    use_ssl=not args.no_ssl, use_keep_alive=args.use_keep_alive)
    
    # 运行API服务器
    if not args.web_only:
        run_device_api(host=args.host, port=args.port, debug=args.debug, 
                      use_ssl=not args.no_ssl, use_keep_alive=args.use_keep_alive)