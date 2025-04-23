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
import multiprocessing
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
    
    # 打印当前的路由，改为DEBUG级别
    if debug:
        logging.debug("Web应用服务器路由:")
        for rule in app.url_map.iter_rules():
            logging.debug(f"{rule.endpoint}: {rule.rule}")
    
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

def run_with_debug_wrapper(target_func, func_args, service_name):
    """在调试模式下运行服务，提供手动重载功能"""
    import logging
    debug_mode = func_args[2] if len(func_args) > 2 else False
    
    if debug_mode:
        logging.debug(f"调试模式下启动{service_name}")
        target_func(*func_args)
    else:
        logging.info(f"正常模式下启动{service_name}")
        target_func(*func_args)

if __name__ == "__main__":
    # Windows系统下多进程支持
    multiprocessing.freeze_support()
    
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
    
    # 设置日志级别
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
        logging.info("调试日志已启用")
    
    # 确保子进程跳过Flask的自动重载器
    web_args = (args.host, args.port, False, not args.no_ssl, args.use_keep_alive) 
    api_args = (args.host, args.port, False, not args.no_ssl, args.use_keep_alive)
    
    # 使用多进程同时启动Web应用和API服务器
    processes = []
    
    # 运行Web应用的进程
    if not args.api_only:
        web_process = multiprocessing.Process(
            target=run_with_debug_wrapper,
            args=(run_web_app, web_args, "Web应用服务器"),
            name="WebAppProcess"
        )
        web_process.daemon = True  # 设置为守护进程，主进程结束时自动结束
        processes.append(web_process)
        logging.info("创建Web应用进程")
    
    # 运行API服务器的进程
    if not args.web_only:
        # 确保主机和端口不冲突
        if not args.api_only and not args.web_only:
            # 如果同时运行两个服务且没有指定不同端口，使用配置文件中的不同端口
            api_host = args.host if args.host else config.API_HOST
            api_port = args.port if args.port else config.API_PORT
            api_args = (api_host, api_port, False, not args.no_ssl, args.use_keep_alive)
        
        api_process = multiprocessing.Process(
            target=run_with_debug_wrapper,
            args=(run_device_api, api_args, "API服务器"),
            name="APIServerProcess"
        )
        api_process.daemon = True  # 设置为守护进程，主进程结束时自动结束
        processes.append(api_process)
        logging.info("创建API服务器进程")
    
    # 启动所有进程
    for process in processes:
        process.start()
        logging.info(f"进程 {process.name} 已启动 (PID: {process.pid})")
    
    if args.debug:
        logging.info("调试模式下运行，注意Flask的自动重载器已被禁用")
    
    # 主进程等待所有子进程
    try:
        # 使用简单的循环等待，这样可以响应键盘中断
        while any(p.is_alive() for p in processes):
            time.sleep(0.5)
    except KeyboardInterrupt:
        logging.info("收到键盘中断信号，正在关闭服务...")
        # 尝试正常终止所有进程
        for process in processes:
            if process.is_alive():
                process.terminate()
                logging.info(f"进程 {process.name} (PID: {process.pid}) 已终止")
    except Exception as e:
        logging.error(f"发生错误: {str(e)}")
    finally:
        # 确保所有进程都已终止
        for process in processes:
            if process.is_alive():
                process.terminate()
                # 给进程一些时间来终止
                process.join(1)
                if process.is_alive():
                    logging.warning(f"进程 {process.name} (PID: {process.pid}) 无法正常终止，尝试强制结束")
                    if hasattr(process, 'kill'):  # Python 3.7+
                        process.kill()
                    elif sys.platform == 'win32':
                        # Windows上使用taskkill强制终止进程
                        os.system(f"taskkill /F /PID {process.pid} /T")
        
        logging.info("程序退出")