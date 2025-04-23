#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
自定义SSL配置模块，为Flask应用提供优化的SSL支持
"""

import os
import ssl
import logging
from pathlib import Path
from app.utils.yaml_config_loader import config

logger = logging.getLogger(__name__)

class CustomSSLProvider:
    """自定义SSL提供器，用于创建和管理SSL上下文"""
    
    @staticmethod
    def get_ssl_context(cert_file=None, key_file=None):
        """
        获取SSL上下文
        
        Args:
            cert_file: 证书文件路径，如果为None则使用默认路径
            key_file: 密钥文件路径，如果为None则使用默认路径
            
        Returns:
            ssl.SSLContext或元组或None
        """
        # 使用默认路径
        if cert_file is None or key_file is None:
            try:
                # 尝试从配置中获取Web证书路径
                cert_file = config.WEB_SSL_CERT
                key_file = config.WEB_SSL_KEY
            except AttributeError:
                # 使用旧的默认路径作为备选
                project_root = Path(__file__).resolve().parent.parent.parent
                ssl_dir = os.path.join(project_root, "ssl")
                cert_file = os.path.join(ssl_dir, "cert.pem")
                key_file = os.path.join(ssl_dir, "key.pem")
        
        # 检查文件是否存在
        if not os.path.exists(cert_file):
            logger.warning(f"证书文件不存在: {cert_file}")
            return None
            
        if not os.path.exists(key_file):
            logger.warning(f"密钥文件不存在: {key_file}")
            return None
        
        logger.info(f"使用证书: {cert_file}")
        logger.info(f"使用密钥: {key_file}")
        
        try:
            # 方法1: 使用SSL模块创建上下文
            context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
            context.load_cert_chain(cert_file, key_file)
            
            # 开发环境宽松设置
            context.check_hostname = False
            context.verify_mode = ssl.CERT_NONE
            
            # 支持所有可用的密码套件，最大化兼容性
            context.set_ciphers('ALL')
            
            logger.info("SSL上下文(方法1)创建成功")
            return context
        except Exception as e:
            logger.error(f"SSL上下文(方法1)创建失败: {str(e)}")
            
            try:
                # 方法2: 使用SSL工厂函数
                context_factory = (cert_file, key_file)
                logger.info("SSL上下文(方法2)创建成功")
                return context_factory
            except Exception as e2:
                logger.error(f"SSL上下文(方法2)创建失败: {str(e2)}")
                return None
    
    @staticmethod
    def is_ssl_available(is_api=False):
        """
        检查SSL是否可用
        
        Args:
            is_api: 是否检查API证书（否则检查Web证书）
        """
        try:
            if is_api:
                cert_file = config.API_SSL_CERT
                key_file = config.API_SSL_KEY
            else:
                cert_file = config.WEB_SSL_CERT
                key_file = config.WEB_SSL_KEY
            
            context = CustomSSLProvider.get_ssl_context(cert_file, key_file)
            return context is not None
        except Exception:
            return False

def get_ssl_context(cert_file=None, key_file=None):
    """
    获取SSL上下文的便捷函数
    
    Args:
        cert_file: 证书文件路径，如果为None则使用默认路径
        key_file: 密钥文件路径，如果为None则使用默认路径
    """
    return CustomSSLProvider.get_ssl_context(cert_file, key_file)

def enable_ssl_for_app(app, is_api=False, ssl_context=None):
    """
    为Flask应用启用SSL
    
    Args:
        app: Flask应用实例
        is_api: 是否为API服务器
        ssl_context: 如果已经创建好SSL上下文，可以直接传入
    """
    if ssl_context is None:
        if is_api:
            cert_file = config.API_SSL_CERT
            key_file = config.API_SSL_KEY
        else:
            cert_file = config.WEB_SSL_CERT
            key_file = config.WEB_SSL_KEY
        
        ssl_context = get_ssl_context(cert_file, key_file)
        
    if ssl_context:
        app.config['PREFERRED_URL_SCHEME'] = 'https'
        return ssl_context
    else:
        app.config['PREFERRED_URL_SCHEME'] = 'http'
        return None 