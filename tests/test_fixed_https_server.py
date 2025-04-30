#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
修复版HTTPS服务器，解决SSL接受后无法正确加载页面的问题
"""

import os
import sys
import logging
from pathlib import Path
from flask import Flask, jsonify
import ssl

# 配置详细日志
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# 将项目根目录添加到系统路径
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

# 确保证书文件存在
ssl_dir = os.path.join(project_root, "ssl")
cert_path = os.path.join(ssl_dir, "cert.pem")
key_path = os.path.join(ssl_dir, "key.pem")

if not os.path.exists(cert_path) or not os.path.exists(key_path):
    logger.error(f"证书文件不存在: {cert_path} 或 {key_path}")
    logger.info("尝试生成新的证书...")
    
    # 尝试生成证书
    try:
        cert_script = os.path.join(project_root, "scripts", "generate_web_cert")
        if os.path.exists(cert_script):
            import importlib.util
            spec = importlib.util.spec_from_file_location("generate_web_cert", cert_script)
            cert_module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(cert_module)
            
            if hasattr(cert_module, "generate_chrome_compatible_cert"):
                logger.info("使用Chrome兼容证书生成器...")
                cert_path, key_path = cert_module.generate_chrome_compatible_cert(ssl_dir)
                logger.info(f"证书生成成功: {cert_path}")
        else:
            logger.error(f"证书生成脚本不存在: {cert_script}")
            sys.exit(1)
    except Exception as e:
        logger.error(f"生成证书失败: {str(e)}")
        sys.exit(1)

# 导入Flask应用和自定义SSL模块
from app import create_app
from app.utils.web_auth import get_ssl_context

# 导入Flask核心组件
import flask

def run_fixed_https_server(host='127.0.0.1', port=5000, debug=True):
    """启动优化版HTTPS服务器"""
    # 创建应用
    app = create_app()
    
    # 修改应用配置，解决SSL重定向问题
    app.config['DEBUG'] = debug
    app.config['PREFERRED_URL_SCHEME'] = 'https'
    app.config['SESSION_COOKIE_SECURE'] = False  # 临时允许非HTTPS访问cookie
    app.config['REMEMBER_COOKIE_SECURE'] = False  # 临时允许非HTTPS访问记住我cookie
    app.config['SESSION_COOKIE_HTTPONLY'] = True  # 防止JS访问cookie
    
    # 获取SSL上下文
    ssl_context = get_ssl_context()
    if ssl_context is None:
        logger.error("无法创建SSL上下文，HTTPS服务器启动失败")
        ssl_context = (cert_path, key_path)  # 尝试使用简单方式
    
    protocol = "HTTPS"
    logger.info(f"正在启动{protocol}服务器 在 {host}:{port}，调试模式: {debug}")
    
    try:
        import importlib.metadata
        flask_version = importlib.metadata.version("flask")
        logger.info(f"Flask版本: {flask_version}")
    except:
        logger.info("无法获取Flask版本信息")
    
    # 打印提示信息
    print(f"\n------------------------------------------------------------")
    print(f"🔒 修复版HTTPS服务器已启动")
    print(f"📮 服务地址: https://{host}:{port}/")
    print(f"🧪 测试页面: https://{host}:{port}/test-https")
    print(f"🔍 调试模式: {'启用' if debug else '禁用'}")
    print(f"⚠️ 注意: 已禁用自动重载功能，避免会话丢失")
    print(f"📢 在浏览器中如果遇到证书警告:")
    print(f"   1. 点击高级，然后点击'继续前往127.0.0.1(不安全)'")
    print(f"   2. 或直接在键盘上输入'thisisunsafe'")
    print(f"   3. 如果仍然无法访问，使用HTTP模式: python scripts/http_server.py")
    print(f"------------------------------------------------------------\n")
    
    # 启动服务器，禁用自动重载
    try:
        app.run(
            host=host, 
            port=port, 
            debug=debug, 
            ssl_context=ssl_context,
            use_reloader=False  # 禁用自动重载功能，避免会话丢失
        )
    except Exception as e:
        logger.error(f"HTTPS服务器启动失败: {str(e)}")
        logger.info("尝试使用备用方法启动服务器...")
        
        # 备用启动方法
        try:
            context = ssl.SSLContext(ssl.PROTOCOL_TLSv1_2)
            context.load_cert_chain(cert_path, key_path)
            app.run(host=host, port=port, debug=debug, ssl_context=context, use_reloader=False)
        except Exception as e2:
            logger.error(f"备用方法启动也失败: {str(e2)}")
            logger.info("建议使用HTTP模式: python scripts/http_server.py")

if __name__ == "__main__":
    run_fixed_https_server() 