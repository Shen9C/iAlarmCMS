#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Web应用启动脚本
使用gunicorn作为WSGI服务器
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
from app.utils.logger import web_logger as logger

def run_web_app(host=None, port=None, workers=4, use_ssl=False):
    """
    运行Web应用
    
    Args:
        host: 主机地址，默认使用配置中的WEB_HOST
        port: 端口号，默认使用配置中的WEB_PORT
        workers: worker进程数
        use_ssl: 是否使用SSL
    """
    # 使用配置中的值作为默认值
    if host is None:
        host = config.WEB_HOST
    if port is None:
        port = config.WEB_PORT
    
    from app import create_web_app
    
    logger.info("正在创建Web应用实例...")
    app = create_web_app()
    
    # 准备SSL选项
    ssl_context = None
    if use_ssl:
        ssl_context = (config.WEB_SSL_CERT, config.WEB_SSL_KEY)
        logger.info("Web应用将以HTTPS模式启动")
    
    # 启动gunicorn服务器
    logger.info(f"Web应用启动于 {'https' if use_ssl else 'http'}://{host}:{port}")
    try:
        from gunicorn.app.base import BaseApplication
        
        class StandaloneApplication(BaseApplication):
            def __init__(self, app, options=None):
                self.options = options or {}
                self.application = app
                super().__init__()
            
            def load_config(self):
                for key, value in self.options.items():
                    if key in self.cfg.settings and value is not None:
                        self.cfg.set(key.lower(), value)
            
            def load(self):
                return self.application
        
        options = {
            'bind': f'{host}:{port}',
            'workers': workers,
            'worker_class': 'sync',
            'timeout': 120,
            'keepalive': 2,
            'accesslog': '-',
            'errorlog': '-',
            'loglevel': 'info',
            'ssl_version': 'TLSv1_2' if use_ssl else None,
            'certfile': config.WEB_SSL_CERT if use_ssl else None,
            'keyfile': config.WEB_SSL_KEY if use_ssl else None
        }
        
        StandaloneApplication(app, options).run()
    except Exception as e:
        logger.error(f"启动Web应用时发生错误: {str(e)}")
        raise

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='油田监控系统 - Web应用服务器')
    parser.add_argument('--host', default=None, help=f'Web主机 (默认: {config.WEB_HOST})')
    parser.add_argument('--port', type=int, default=None, help=f'Web端口 (默认: {config.WEB_PORT})')
    parser.add_argument('--workers', type=int, default=4, help='worker进程数 (默认: 4)')
    parser.add_argument('--http', action='store_true', help='使用HTTP模式替代默认的HTTPS模式')
    
    args = parser.parse_args()
    
    # 确定是否使用SSL
    use_ssl = not args.http
    
    # 启动Web应用
    run_web_app(args.host, args.port, args.workers, use_ssl)