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
import socket
import signal

from flask import Flask, has_request_context, request, jsonify
from flask.logging import default_handler
from logging.config import dictConfig
from sqlalchemy.sql import text

# 将项目根目录添加到系统路径
project_root = Path(__file__).resolve().parent
sys.path.insert(0, str(project_root))

# 导入应用和配置
from app import create_web_app, create_api_app, db
from app.utils.yaml_config_loader import load_app_config
from app.utils.logger_config import setup_logger
from app.utils.web_auth import get_ssl_context as get_web_ssl_context
from app.utils.machine_auth import get_ssl_context as get_machine_ssl_context

# 设置日志
logger = setup_logger()

# 全局变量用于控制服务运行状态
running = True

def signal_handler(signum, frame):
    """处理信号"""
    global running
    logger.info(f"接收到信号 {signum}，正在关闭服务...")
    running = False

def is_port_in_use(port):
    """检查端口是否被占用"""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind(('0.0.0.0', port))
            return False
        except socket.error:
            return True

def run_with_debug_wrapper(target_func, func_args, service_name):
    """运行服务并处理调试模式"""
    try:
        logger.info(f"启动{service_name}服务")
        process = multiprocessing.Process(
            target=target_func,
            kwargs=func_args,
            name=service_name
        )
        process.daemon = False
        process.start()
        return process
    except Exception as e:
        logger.error(f"启动{service_name}服务失败: {e}")
        traceback.print_exc()
        return None

def run_web_app(config, host=None, port=None, debug=False, use_ssl=True, use_keep_alive=False):
    """运行Web应用"""
    try:
        app = create_web_app(config)
        
        # 检查端口是否被占用
        target_port = port or config.web_server.port
        if is_port_in_use(target_port):
            logger.error(f"Web服务端口 {target_port} 已被占用，请检查是否有其他服务正在运行")
            return
            
        if use_ssl:
            ssl_context = get_web_ssl_context()
            logger.info("已配置SSL上下文")
        else:
            ssl_context = None
            logger.info("未使用SSL")
            
        # 确保连接正确关闭
        @app.after_request
        def cleanup(response):
            # 设置连接关闭
            response.headers['Connection'] = 'close'
            # 确保响应被正确发送
            response.direct_passthrough = False
            return response
        
        logger.info(f"Web服务监听地址: {host or config.web_server.host}:{target_port}")
        app.run(
            host=host or config.web_server.host,
            port=target_port,
            debug=debug,
            ssl_context=ssl_context,
            use_reloader=False,
            threaded=True  # 使用线程模式
        )
    except Exception as e:
        logger.error(f"Web服务运行失败: {e}")
        traceback.print_exc()

def run_device_api(config, host=None, port=None, debug=False, use_ssl=True, use_keep_alive=False):
    """运行设备API服务"""
    try:
        app = create_api_app(config)
        
        # 检查端口是否被占用
        target_port = port or config.api_server.port
        if is_port_in_use(target_port):
            logger.error(f"API服务端口 {target_port} 已被占用，请检查是否有其他服务正在运行")
            return
            
        if use_ssl:
            ssl_context = get_machine_ssl_context(
                cert_file=config.ssl.api_cert_file,
                key_file=config.ssl.api_key_file
            )
            logger.info("已配置设备API SSL上下文")
        else:
            ssl_context = None
            logger.info("未使用SSL")
            
        # 确保连接正确关闭
        @app.after_request
        def cleanup(response):
            # 设置连接关闭
            response.headers['Connection'] = 'close'
            # 确保响应被正确发送
            response.direct_passthrough = False
            return response
        
        logger.info(f"API服务监听地址: {host or config.api_server.host}:{target_port}")
        app.run(
            host=host or config.api_server.host,
            port=target_port,
            debug=debug,
            ssl_context=ssl_context,
            use_reloader=False,
            threaded=True  # 使用线程模式
        )
    except Exception as e:
        logger.error(f"API服务运行失败: {e}")
        traceback.print_exc()

def main():
    """主函数"""
    # 注册信号处理器
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # 解析命令行参数
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
    
    # 加载配置
    config = load_app_config()
    
    processes = []
    threads = []
    
    try:
        # 启动Web服务
        if not args.api_only:
            if debug:
                web_thread = threading.Thread(
                    target=run_web_app,
                    kwargs={
                        'config': config,
                        'debug': debug,
                        'use_ssl': use_ssl,
                        'use_keep_alive': use_keep_alive
                    },
                    name='WebThread',
                    daemon=True  # 关键：守护线程
                )
                web_thread.start()
                threads.append(web_thread)
                logger.info("Web服务线程已启动")
            else:
                web_process = run_with_debug_wrapper(
                    run_web_app,
                    {
                        'config': config,
                        'debug': debug,
                        'use_ssl': use_ssl,
                        'use_keep_alive': use_keep_alive
                    },
                    'Web'
                )
                if web_process:
                    processes.append(web_process)
                    logger.info("Web服务进程已启动")
        
        # 启动API服务
        if not args.web_only:
            if debug:
                api_thread = threading.Thread(
                    target=run_device_api,
                    kwargs={
                        'config': config,
                        'debug': debug,
                        'use_ssl': use_ssl,
                        'use_keep_alive': use_keep_alive
                    },
                    name='APIThread',
                    daemon=True  # 关键：守护线程
                )
                api_thread.start()
                threads.append(api_thread)
                logger.info("API服务线程已启动")
            else:
                api_process = run_with_debug_wrapper(
                    run_device_api,
                    {
                        'config': config,
                        'debug': debug,
                        'use_ssl': use_ssl,
                        'use_keep_alive': use_keep_alive
                    },
                    'API'
                )
                if api_process:
                    processes.append(api_process)
                    logger.info("API服务进程已启动")
        
        # 等待所有进程和线程完成
        for process in processes:
            process.join()
        
        for thread in threads:
            thread.join()
            
    except KeyboardInterrupt:
        logger.info("接收到中断信号，正在关闭服务...")
        for process in processes:
            process.terminate()
        for thread in threads:
            thread.join(timeout=1)
    except Exception as e:
        logger.error(f"服务运行出错: {e}")
        traceback.print_exc()
    finally:
        # 清理资源
        for process in processes:
            if process.is_alive():
                process.terminate()
        for thread in threads:
            if thread.is_alive():
                thread.join(timeout=1)
        logger.info("服务已关闭")

if __name__ == '__main__':
    print(f"[辅助打印] 当前进程/线程日志级别: {logging.getLogger().getEffectiveLevel()}")
    logging.debug("[辅助打印] 这是DEBUG日志测试")
    logging.info("[辅助打印] 这是INFO日志测试")
    main()