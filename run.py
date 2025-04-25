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
import traceback

from flask import Flask, has_request_context, request, jsonify
from flask.logging import default_handler
from logging.config import dictConfig
from sqlalchemy.sql import text

# 将项目根目录添加到系统路径
project_root = Path(__file__).resolve().parent
sys.path.insert(0, str(project_root))

# 导入应用和配置
from app import create_web_app, create_api_app, db
from app.utils.yaml_config_loader import config
from app.utils.logger import main_logger, db_logger

def run_with_debug_wrapper(target_func, func_args, service_name):
    """运行服务并处理调试模式"""
    try:
        main_logger.info(f"启动{service_name}服务")
        process = multiprocessing.Process(
            target=target_func,
            kwargs=func_args,
            name=service_name
        )
        process.daemon = False
        process.start()
        return process
    except Exception as e:
        main_logger.error(f"启动{service_name}服务失败: {e}")
        traceback.print_exc()
        return None

def run_web_app(host=None, port=None, debug=False, use_ssl=True, use_keep_alive=False):
    """运行Web应用"""
    try:
        app = create_web_app()
        
        if use_ssl:
            ssl_context = get_ssl_context(is_api=False)
        else:
            ssl_context = None
            
        if use_keep_alive:
            @app.after_request
            def set_connection_close(response):
                response.headers['Connection'] = 'close'
                return response
        
        # 在调试模式下，使用线程而不是进程
        if debug:
            main_logger.info("Web服务以调试模式运行")
            app.run(
                host=host or config.web_server.host,
                port=port or config.web_server.port,
                debug=debug,
                ssl_context=ssl_context,
                use_reloader=False,  # 禁用自动重载
                threaded=True  # 使用线程模式
            )
        else:
            app.run(
                host=host or config.web_server.host,
                port=port or config.web_server.port,
                debug=debug,
                ssl_context=ssl_context,
                use_reloader=False  # 禁用自动重载
            )
    except Exception as e:
        main_logger.error(f"Web应用运行失败: {e}")
        traceback.print_exc()

def run_device_api(host=None, port=None, debug=False, use_ssl=True, use_keep_alive=False):
    """运行设备API服务"""
    try:
        main_logger.info("正在创建API应用...")
        app = create_api_app()
        
        if use_ssl:
            ssl_context = get_ssl_context(is_api=True)
            main_logger.info("已配置SSL上下文")
        else:
            ssl_context = None
            main_logger.info("未使用SSL")
            
        if use_keep_alive:
            @app.after_request
            def set_connection_close(response):
                response.headers['Connection'] = 'close'
                return response
        
        # 在调试模式下，使用线程而不是进程
        if debug:
            main_logger.info("API服务以调试模式运行")
            main_logger.info(f"API服务监听地址: {host or config.api_server.host}:{port or config.api_server.port}")
            app.run(
                host=host or config.api_server.host,
                port=port or config.api_server.port,
                debug=debug,
                ssl_context=ssl_context,
                use_reloader=False,  # 禁用自动重载
                threaded=True  # 使用线程模式
            )
        else:
            main_logger.info(f"API服务监听地址: {host or config.api_server.host}:{port or config.api_server.port}")
            app.run(
                host=host or config.api_server.host,
                port=port or config.api_server.port,
                debug=debug,
                ssl_context=ssl_context,
                use_reloader=False  # 禁用自动重载
            )
    except Exception as e:
        main_logger.error(f"设备API服务运行失败: {e}")
        traceback.print_exc()

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='启动油田设备监控系统')
    parser.add_argument('--no-ssl', action='store_true', help='禁用SSL')
    parser.add_argument('--debug', action='store_true', help='启用调试模式')
    parser.add_argument('--no-keep-alive', action='store_true', help='禁用keep-alive')
    parser.add_argument('--web-only', action='store_true', help='只启动Web服务')
    parser.add_argument('--api-only', action='store_true', help='只启动API服务')
    
    args = parser.parse_args()
    
    use_ssl = not args.no_ssl
    debug = args.debug
    use_keep_alive = not args.no_keep_alive
    
    processes = []
    threads = []
    
    try:
        # 启动Web服务
        if not args.api_only:
            if debug:
                # 在调试模式下使用线程
                web_thread = threading.Thread(
                    target=run_web_app,
                    kwargs={
                        'debug': debug,
                        'use_ssl': use_ssl,
                        'use_keep_alive': use_keep_alive
                    },
                    name='WebThread'
                )
                web_thread.daemon = False
                web_thread.start()
                threads.append(web_thread)
                main_logger.info("Web服务线程已启动")
            else:
                web_process = run_with_debug_wrapper(
                    run_web_app,
                    {
                        'debug': debug,
                        'use_ssl': use_ssl,
                        'use_keep_alive': use_keep_alive
                    },
                    'Web'
                )
                if web_process:
                    processes.append(web_process)
                    main_logger.info("Web服务进程已启动")
        
        # 启动API服务
        if not args.web_only:
            if debug:
                # 在调试模式下使用线程
                api_thread = threading.Thread(
                    target=run_device_api,
                    kwargs={
                        'debug': debug,
                        'use_ssl': use_ssl,
                        'use_keep_alive': use_keep_alive
                    },
                    name='APIThread'
                )
                api_thread.daemon = False
                api_thread.start()
                threads.append(api_thread)
                main_logger.info("API服务线程已启动")
            else:
                api_process = run_with_debug_wrapper(
                    run_device_api,
                    {
                        'debug': debug,
                        'use_ssl': use_ssl,
                        'use_keep_alive': use_keep_alive
                    },
                    'API'
                )
                if api_process:
                    processes.append(api_process)
                    main_logger.info("API服务进程已启动")
        
        # 等待所有进程和线程完成
        for process in processes:
            process.join()
        
        for thread in threads:
            thread.join()
            
    except KeyboardInterrupt:
        main_logger.info("接收到中断信号，正在关闭服务...")
        for process in processes:
            process.terminate()
        for thread in threads:
            thread.join(timeout=1)
    except Exception as e:
        main_logger.error(f"服务运行出错: {e}")
        traceback.print_exc()
    finally:
        main_logger.info("服务已关闭")

if __name__ == '__main__':
    main()