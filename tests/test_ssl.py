#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
SSL证书测试工具

该脚本用于测试SSL证书的有效性和Flask应用的SSL支持。
包括以下功能：
1. 验证证书文件是否存在和有效
2. 测试SSL上下文创建
3. 测试Flask的SSL支持
4. 检查端口可用性

使用方法：
$ python test_ssl.py
"""

import os
import sys
import ssl
import time
import socket
import hashlib
import datetime
import subprocess
from pathlib import Path

# 将项目根目录添加到系统路径
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

# 配置证书路径
SSL_DIR = project_root / 'ssl'
CERT_PATH = SSL_DIR / 'cert.pem'
KEY_PATH = SSL_DIR / 'key.pem'

# 测试端口
TEST_PORT = 5566

def print_header(text):
    """打印带格式的标题"""
    line = "=" * 70
    print(f"\n{line}")
    print(f" {text}")
    print(f"{line}")

def print_success(text):
    """打印成功信息"""
    print(f"✅ {text}")

def print_error(text):
    """打印错误信息"""
    print(f"❌ {text}")

def print_warning(text):
    """打印警告信息"""
    print(f"⚠️ {text}")

def print_info(text):
    """打印信息"""
    print(f"ℹ️ {text}")

def verify_cert_file():
    """验证证书文件是否存在和有效"""
    print_header("1. 检查证书文件")
    
    # 检查文件是否存在
    if not CERT_PATH.exists():
        print_error(f"证书文件不存在: {CERT_PATH}")
        return False
    
    if not KEY_PATH.exists():
        print_error(f"证书密钥文件不存在: {KEY_PATH}")
        return False
    
    print_success(f"证书文件存在：{CERT_PATH}")
    print_success(f"密钥文件存在：{KEY_PATH}")
    
    # 检查文件权限
    try:
        # 读取证书信息
        cert_data = ssl._ssl._test_decode_cert(str(CERT_PATH))
        
        # 打印证书信息
        print_info(f"证书主题: {cert_data['subject']}")
        print_info(f"证书颁发者: {cert_data['issuer']}")
        
        # 解析有效期
        not_before = datetime.datetime.strptime(cert_data['notBefore'], '%b %d %H:%M:%S %Y %Z')
        not_after = datetime.datetime.strptime(cert_data['notAfter'], '%b %d %H:%M:%S %Y %Z')
        now = datetime.datetime.now()
        
        print_info(f"证书有效期: {not_before.strftime('%Y-%m-%d')} 至 {not_after.strftime('%Y-%m-%d')}")
        
        # 检查证书是否过期
        if now > not_after:
            print_error("证书已过期")
            return False
        
        if now < not_before:
            print_warning("证书尚未生效")
        
        # 检查证书指纹
        with open(CERT_PATH, 'rb') as f:
            cert_content = f.read()
        
        fingerprint = hashlib.sha256(cert_content).hexdigest()
        print_info(f"证书SHA256指纹: {fingerprint[:16]}...{fingerprint[-16:]}")
        
        return True
    except Exception as e:
        print_error(f"证书验证失败: {str(e)}")
        return False

def test_ssl_context():
    """测试SSL上下文创建"""
    print_header("2. 测试SSL上下文创建")
    
    try:
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        context.load_cert_chain(CERT_PATH, KEY_PATH)
        print_success("SSL上下文创建成功")
        return context
    except Exception as e:
        print_error(f"SSL上下文创建失败: {str(e)}")
        return None

def check_port_availability(port=TEST_PORT):
    """检查端口是否可用"""
    print_header(f"3. 检查端口 {port} 可用性")
    
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(1)
        result = sock.connect_ex(('127.0.0.1', port))
        sock.close()
        
        if result == 0:
            print_warning(f"端口 {port} 已被占用")
            return False
        else:
            print_success(f"端口 {port} 可用")
            return True
    except Exception as e:
        print_error(f"检查端口时发生错误: {str(e)}")
        return False

def test_flask_ssl():
    """测试Flask的SSL支持"""
    print_header("4. 测试Flask的SSL支持")
    
    try:
        # 检查Flask是否安装
        import flask
        print_success(f"Flask已安装，版本: {flask.__version__}")
        
        # 创建最小化的Flask应用
        from flask import Flask
        app = Flask(__name__)
        
        @app.route('/test-ssl')
        def test_route():
            return 'SSL Test successful!'
        
        # 检查是否可以配置SSL
        if hasattr(app, 'run') and 'ssl_context' in app.run.__code__.co_varnames:
            print_success("Flask支持SSL上下文参数")
            return True
        else:
            print_error("Flask不支持SSL上下文参数")
            return False
    except ImportError:
        print_error("Flask未安装")
        return False
    except Exception as e:
        print_error(f"测试Flask SSL支持时出错: {str(e)}")
        return False

def check_chrome_compatibility():
    """检查是否支持Chrome兼容的证书生成"""
    print_header("5. 检查Chrome兼容的证书支持")
    
    cert_script = project_root / "scripts" / "generate_web_cert"
    if not cert_script.exists():
        print_error(f"Chrome兼容证书生成脚本不存在: {cert_script}")
        return False
    
    try:
        import importlib.util
        spec = importlib.util.spec_from_file_location("generate_web_cert", str(cert_script))
        cert_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cert_module)
        
        if hasattr(cert_module, "generate_chrome_compatible_cert"):
            print_success("支持Chrome兼容证书生成")
            return True
        else:
            print_error("脚本中不包含Chrome兼容证书生成函数")
            return False
    except Exception as e:
        print_error(f"检查Chrome兼容证书支持时出错: {str(e)}")
        return False

def summary(results):
    """总结测试结果"""
    print_header("测试结果总结")
    
    all_passed = all(results.values())
    
    if all_passed:
        print_success("所有测试已通过！您的SSL配置应该可以正常工作。")
    else:
        print_warning("部分测试未通过。请检查以下问题：")
        
        for test, passed in results.items():
            if not passed:
                print_error(f"- {test} 测试失败")
        
        print("\n可能的解决方法：")
        if not results.get("证书验证"):
            print("1. 请确保证书文件存在且有效")
            print("   您可以运行 `python scripts/generate_web_cert` 重新生成证书")
        
        if not results.get("SSL上下文"):
            print("2. SSL上下文创建失败，请检查证书和密钥文件")
        
        if not results.get("端口可用性"):
            print("3. 测试端口已被占用，请确保没有其他服务正在使用该端口")
            print("   您可以使用 `--api-port` 或 `--web-port` 参数指定不同的端口")
        
        if not results.get("Flask SSL支持"):
            print("4. Flask不支持SSL，请确保安装了最新版本的Flask")
            print("   您可以运行 `pip install --upgrade flask` 更新Flask")

def main():
    """主函数"""
    print_header("SSL证书测试工具")
    print_info(f"项目目录: {project_root}")
    print_info(f"证书目录: {SSL_DIR}")
    
    results = {}
    
    # 验证证书文件
    results["证书验证"] = verify_cert_file()
    
    # 测试SSL上下文
    results["SSL上下文"] = test_ssl_context() is not None
    
    # 检查端口可用性
    results["端口可用性"] = check_port_availability()
    
    # 测试Flask SSL支持
    results["Flask SSL支持"] = test_flask_ssl()
    
    # 检查Chrome兼容性
    results["Chrome兼容证书"] = check_chrome_compatibility()
    
    # 总结测试结果
    summary(results)

if __name__ == "__main__":
    main() 