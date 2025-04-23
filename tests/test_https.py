#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
HTTPS服务器测试工具
"""

import os
import sys
from pathlib import Path
import logging
import importlib.metadata

# 设置基本日志
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 将项目根目录添加到系统路径
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

def run_test_https_server():
    """运行测试HTTPS服务器"""
    from flask import Flask, redirect, url_for, request
    import ssl
    
    # 创建一个简单的Flask应用
    app = Flask(__name__)
    
    # 设置调试日志
    app.logger.setLevel(logging.DEBUG)
    
    @app.route('/')
    def index():
        """根路由处理程序"""
        # 记录详细的请求信息，用于调试
        app.logger.debug(f"访问根路径 - 请求方案: {request.scheme}")
        app.logger.debug(f"主机: {request.host}")
        app.logger.debug(f"路径: {request.path}")
        app.logger.debug(f"是否安全: {request.is_secure}")
        app.logger.debug(f"头信息: {request.headers}")
        
        # 简单重定向到测试页面
        return redirect('/test')
    
    @app.route('/test')
    def test():
        """测试页面"""
        return """
        <!DOCTYPE html>
        <html>
        <head>
            <title>HTTPS测试页面</title>
            <style>
                body { font-family: Arial, sans-serif; margin: 40px; line-height: 1.6; }
                h1 { color: #4CAF50; }
                .success { color: #4CAF50; font-weight: bold; }
                .info { background: #f5f5f5; padding: 15px; border-radius: 5px; }
            </style>
        </head>
        <body>
            <h1>HTTPS连接测试成功！</h1>
            <div class="success">✓ 您已成功连接到HTTPS测试服务器</div>
            <p>这个页面表明SSL/TLS握手已经成功完成，并且您的浏览器已经接受了证书。</p>
            
            <div class="info">
                <h3>请求信息：</h3>
                <pre id="requestInfo">正在加载...</pre>
            </div>
            
            <script>
                // 获取请求信息
                fetch('/request-info')
                    .then(response => response.text())
                    .then(data => {
                        document.getElementById('requestInfo').textContent = data;
                    })
                    .catch(error => {
                        document.getElementById('requestInfo').textContent = "获取请求信息失败: " + error;
                    });
            </script>
        </body>
        </html>
        """
    
    @app.route('/request-info')
    def request_info():
        """返回请求信息用于诊断"""
        info = []
        info.append(f"请求方案: {request.scheme}")
        info.append(f"主机: {request.host}")
        info.append(f"路径: {request.path}")
        info.append(f"是否安全: {request.is_secure}")
        info.append(f"用户代理: {request.user_agent}")
        info.append(f"Cookie数量: {len(request.cookies)}")
        
        return "\n".join(info)
    
    # 获取SSL证书路径
    ssl_dir = project_root / "ssl"
    cert_path = ssl_dir / "cert.pem"
    key_path = ssl_dir / "key.pem"
    
    # 检查并确保SSL证书存在
    if not cert_path.exists() or not key_path.exists():
        logger.error("未找到SSL证书文件，尝试生成...")
        try:
            # 尝试使用证书生成脚本
            gen_script = project_root / "scripts" / "generate_web_cert"
            if gen_script.exists():
                logger.info("正在使用证书生成脚本...")
                import subprocess
                subprocess.run([sys.executable, str(gen_script)], check=True)
            else:
                logger.error("无法找到证书生成脚本，请确保scripts/generate_web_cert存在")
                return False
        except Exception as e:
            logger.error(f"生成证书失败: {str(e)}")
            return False
    
    try:
        # 获取Flask版本
        try:
            flask_version = importlib.metadata.version("flask")
            logger.info(f"Flask版本: {flask_version}")
        except:
            logger.warning("无法获取Flask版本信息")
        
        # 创建SSL上下文
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        context.load_cert_chain(cert_path, key_path)
        
        # 输出指导信息
        print("\n" + "="*50)
        print("测试HTTPS服务器正在启动!")
        print("请在浏览器中访问: https://127.0.0.1:5000/")
        print("如果出现证书警告，请点击'继续访问'")
        print("服务器已禁用自动重新加载，以确保SSL握手后不丢失会话")
        print("="*50 + "\n")
        
        # 运行Flask应用，禁用自动重新加载
        app.run(host='127.0.0.1', port=5000, ssl_context=context, 
                debug=True, use_reloader=False)
                
    except Exception as e:
        logger.error(f"启动HTTPS服务器失败: {str(e)}")
        return False
    
    return True

if __name__ == "__main__":
    run_test_https_server() 