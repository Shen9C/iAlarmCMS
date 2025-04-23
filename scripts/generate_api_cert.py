#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
为边缘设备API服务器优化的SSL证书生成脚本
"""

import os
import sys
import ipaddress
import socket
from pathlib import Path
from datetime import datetime, timedelta
from cryptography import x509
from cryptography.x509.oid import NameOID, ExtensionOID
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization

# 将项目根目录添加到系统路径
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

def generate_api_cert(output_dir):
    """
    生成专门为边缘设备API服务器优化的自签名证书
    """
    # 确保输出目录存在
    os.makedirs(output_dir, exist_ok=True)
    
    print("正在生成专为边缘设备API优化的SSL证书...")
    
    # 获取本机计算机名和IP地址
    hostname = socket.gethostname()
    try:
        local_ip = socket.gethostbyname(hostname)
    except:
        local_ip = "127.0.0.1"
    
    # 定义支持的域名和IP地址，API服务通常更侧重于IP地址
    domains = ["localhost", hostname, "api.localhost", "edge.localhost"]
    ip_addresses = ["127.0.0.1", local_ip, "0.0.0.0"]
    
    # 生成私钥 (使用2048位强度，适合API服务器)
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048
    )
    
    # 准备证书主题和颁发者，针对API服务器
    subject = issuer = x509.Name([
        x509.NameAttribute(NameOID.COUNTRY_NAME, "CN"),
        x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, "Beijing"),
        x509.NameAttribute(NameOID.LOCALITY_NAME, "Beijing"),
        x509.NameAttribute(NameOID.ORGANIZATION_NAME, "Edge Device API"),
        x509.NameAttribute(NameOID.ORGANIZATIONAL_UNIT_NAME, "API Services"),
        x509.NameAttribute(NameOID.COMMON_NAME, "api.localhost")
    ])
    
    # 当前时间
    now = datetime.utcnow()
    
    # 构建主题备用名称扩展
    san_list = []
    for domain in set(domains):  # 使用集合去重
        san_list.append(x509.DNSName(domain))
    
    for ip in set(ip_addresses):  # 使用集合去重
        try:
            san_list.append(x509.IPAddress(ipaddress.ip_address(ip)))
        except ValueError:
            print(f"忽略无效的IP地址: {ip}")
    
    # 构建证书
    cert_builder = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(issuer)
        .public_key(private_key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now)
        .not_valid_after(now + timedelta(days=3650))  # 10年有效期，API服务器通常使用更长时间
    )
    
    # 添加基本约束扩展
    cert_builder = cert_builder.add_extension(
        x509.BasicConstraints(ca=True, path_length=None),
        critical=True
    )
    
    # 添加主题备用名称扩展
    cert_builder = cert_builder.add_extension(
        x509.SubjectAlternativeName(san_list),
        critical=False
    )
    
    # 添加密钥用途扩展
    cert_builder = cert_builder.add_extension(
        x509.KeyUsage(
            digital_signature=True,
            content_commitment=False,
            key_encipherment=True,
            data_encipherment=False,
            key_agreement=False,
            key_cert_sign=True,
            crl_sign=True,
            encipher_only=False,
            decipher_only=False
        ),
        critical=True
    )
    
    # 添加扩展密钥用途扩展 (重要：添加服务器身份验证)
    cert_builder = cert_builder.add_extension(
        x509.ExtendedKeyUsage([
            x509.oid.ExtendedKeyUsageOID.SERVER_AUTH
        ]),
        critical=False
    )
    
    # 使用SHA-256签名证书
    certificate = cert_builder.sign(
        private_key, hashes.SHA256()
    )
    
    # 保存证书
    cert_path = os.path.join(output_dir, "api_cert.pem")
    with open(cert_path, "wb") as f:
        f.write(certificate.public_bytes(serialization.Encoding.PEM))
    
    # 保存私钥
    key_path = os.path.join(output_dir, "api_key.pem")
    with open(key_path, "wb") as f:
        f.write(private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        ))
    
    print(f"✓ API证书生成成功!")
    print(f"✓ 证书路径: {cert_path}")
    print(f"✓ 私钥路径: {key_path}")
    print(f"✓ 支持的域名: {domains}")
    print(f"✓ 支持的IP地址: {ip_addresses}")
    
    return cert_path, key_path

if __name__ == "__main__":
    # SSL证书输出目录
    ssl_dir = os.path.join(project_root, "ssl")
    
    # 生成证书
    cert_path, key_path = generate_api_cert(ssl_dir)
    
    print("\n======= 使用说明 =======")
    print("1. 启动API HTTPS服务器:")
    print("   python run.py --api-only --ssl")
    print()
    print("2. 测试API连接:")
    print("   python scripts/test_edge_device_api.py --https")
    print()
    print("3. 如果仍然无法连接，尝试以下方法:")
    print("   a. 使用HTTP模式: python run.py --api-only")
    print("   b. 检查端口是否被占用")
    print("=============================") 