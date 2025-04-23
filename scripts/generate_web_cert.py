#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
为Web服务器生成兼容Chrome浏览器的SSL证书
Chrome要求证书必须包含subjectAltName扩展
"""

import os
import sys
import logging
import ipaddress  # 添加ipaddress模块导入
from pathlib import Path
from OpenSSL import crypto
from cryptography import x509
from cryptography.x509.oid import NameOID
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization
import datetime

# 配置日志
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
handler = logging.StreamHandler(sys.stdout)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)

def generate_chrome_compatible_cert(ssl_dir, cert_filename="cert.pem", key_filename="key.pem"):
    """
    生成兼容Chrome的证书（包含SubjectAltName扩展）
    
    Args:
        ssl_dir: 证书保存目录
        cert_filename: 证书文件名
        key_filename: 私钥文件名
        
    Returns:
        tuple: (证书路径, 私钥路径)
    """
    logger.info(f"正在生成Chrome兼容的Web证书，保存到: {ssl_dir}")
    
    # 确保目录存在
    os.makedirs(ssl_dir, exist_ok=True)
    
    cert_path = os.path.join(ssl_dir, cert_filename)
    key_path = os.path.join(ssl_dir, key_filename)
    
    # 生成私钥
    key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
    )
    
    # 写入私钥
    with open(key_path, "wb") as f:
        f.write(key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.TraditionalOpenSSL,
            encryption_algorithm=serialization.NoEncryption()
        ))
    
    # 创建证书
    subject = issuer = x509.Name([
        x509.NameAttribute(NameOID.COUNTRY_NAME, u"CN"),
        x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, u"Beijing"),
        x509.NameAttribute(NameOID.LOCALITY_NAME, u"Beijing"),
        x509.NameAttribute(NameOID.ORGANIZATION_NAME, u"Oilfield Web"),
        x509.NameAttribute(NameOID.ORGANIZATIONAL_UNIT_NAME, u"Development"),
        x509.NameAttribute(NameOID.COMMON_NAME, u"localhost"),
    ])
    
    now = datetime.datetime.utcnow()
    cert = x509.CertificateBuilder().subject_name(
        subject
    ).issuer_name(
        issuer
    ).public_key(
        key.public_key()
    ).serial_number(
        x509.random_serial_number()
    ).not_valid_before(
        now
    ).not_valid_after(
        now + datetime.timedelta(days=3650)  # 10年有效期
    ).add_extension(
        x509.SubjectAlternativeName([
            x509.DNSName(u"localhost"),
            x509.IPAddress(ipaddress.IPv4Address('127.0.0.1'))  # 使用ipaddress模块创建IP地址
        ]),
        critical=False,
    ).sign(key, hashes.SHA256())
    
    # 写入证书
    with open(cert_path, "wb") as f:
        f.write(cert.public_bytes(serialization.Encoding.PEM))
    
    logger.info(f"成功生成Web证书: {cert_path}")
    logger.info(f"成功生成Web私钥: {key_path}")
    
    return cert_path, key_path

if __name__ == "__main__":
    # 如果直接运行此脚本
    project_root = Path(__file__).resolve().parent.parent
    ssl_dir = os.path.join(project_root, "ssl")
    generate_chrome_compatible_cert(ssl_dir)
    
    print("\n======= 使用说明 =======")
    print("1. 启动HTTP服务器进行测试:")
    print("   python scripts/run_http_server.py")
    print()
    print("2. 启动HTTPS服务器:")
    print("   python run.py --web-only --ssl")
    print()
    print("3. 在Chrome浏览器中:")
    print("   a. 访问 https://127.0.0.1:5000/test-https")
    print("   b. 点击'高级'")
    print("   c. 点击'继续前往127.0.0.1(不安全)'")
    print("   d. 或在空白处直接键盘输入: thisisunsafe")
    print()
    print("4. 如果仍然无法访问，尝试以下方法:")
    print("   a. 使用HTTP模式: http://127.0.0.1:5000/test-https")
    print("   b. 在Chrome浏览器中访问 chrome://flags/#allow-insecure-localhost")
    print("      将'Allow invalid certificates for resources loaded from localhost'设置为Enabled")
    print("      重启浏览器后再次尝试")
    print("=============================") 