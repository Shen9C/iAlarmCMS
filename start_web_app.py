#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Web应用启动脚本
单独启动Web应用，避免与API服务器冲突
支持长连接和短连接模式，默认使用短连接，解决连接问题
"""

import os
import sys
import logging
from pathlib import Path

# 将项目根目录添加到系统路径
project_root = Path(__file__).resolve().parent
sys.path.insert(0, str(project_root))

# 从run.py导入必要的函数
from run import config

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s in %(module)s: %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)

def run_web_app(host=None, port=None, debug=False, use_ssl=False, use_keep_alive=False):
    """
    运行Web应用
    
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
    
    from flask import Flask
    from app import create_app
    
    logging.info("正在创建Web应用实例...")
    app = create_app()
    
    # 如果不使用长连接，添加全局中间件，设置短连接
    if not use_keep_alive:
        @app.after_request
        def set_connection_close(response):
            response.headers["Connection"] = "close"
            return response
        logging.info("Web应用将使用短连接模式")
    else:
        logging.info("Web应用将使用长连接模式")
    
    # 打印当前的路由 - 改为DEBUG级别，并仅在debug模式下打印
    if debug:
        logging.debug("Web应用路由:")
        for rule in app.url_map.iter_rules():
            logging.debug(f"{rule.endpoint}: {rule.rule}")
    
    # 准备SSL选项
    ssl_context = None
    if use_ssl:
        ssl_context = (config.WEB_SSL_CERT, config.WEB_SSL_KEY)
        logging.info("Web应用将以HTTPS模式启动")
    
    # 启动服务器
    logging.info(f"Web应用启动于 {'https' if use_ssl else 'http'}://{host}:{port}")
    try:
        app.run(host=host, port=port, debug=debug, ssl_context=ssl_context, 
                threaded=True, processes=1, use_reloader=debug)
    except Exception as e:
        logging.error(f"启动Web应用时发生错误: {str(e)}")
        raise

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='油田监控系统 - Web应用')
    parser.add_argument('--host', default=None, help=f'Web主机 (默认: {config.WEB_HOST})')
    parser.add_argument('--port', type=int, default=None, help=f'Web端口 (默认: {config.WEB_PORT})')
    parser.add_argument('--debug', action='store_true', help='启用调试模式')
    parser.add_argument('--http', action='store_true', help='使用HTTP模式替代默认的HTTPS模式')
    parser.add_argument('--keep-alive', action='store_true', help='使用长连接模式 (默认为短连接)')
    
    args = parser.parse_args()
    
    # 设置日志级别
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
        logging.info("调试日志已启用")
    
    # 确定是否使用SSL
    use_ssl = not args.http
    
    # 启动Web应用 - 参数控制长/短连接模式
    run_web_app(args.host, args.port, args.debug, use_ssl, args.keep_alive)