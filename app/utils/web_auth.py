from functools import wraps
from flask import request, jsonify, redirect, url_for, current_app
from flask_login import current_user, logout_user
from datetime import datetime
import os
import ssl
import logging
from pathlib import Path
from app.utils.yaml_config_loader import create_config_object, load_yaml_config

logger = logging.getLogger(__name__)

def get_config():
    """获取当前应用的配置"""
    return current_app.config

def check_user_auth():
    """检查用户认证状态"""
    # 检查用户是否已登录
    if not current_user.is_authenticated:
        return False, '用户未登录'
    
    # 从cookie或URL参数获取用户令牌，优先使用cookie
    user_token = request.cookies.get('user_token') or request.args.get('user_token')
    if not user_token:
        return False, '缺少用户令牌'
    
    # 验证令牌是否匹配
    if current_user.current_token != user_token:
        return False, '无效的用户令牌'
    
    # 检查令牌是否过期
    if current_user.is_token_expired():
        return False, '令牌已过期'
    
    return True, None

def web_auth_required(f):
    """Web用户认证装饰器"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        is_valid, error_msg = check_user_auth()
        if not is_valid:
            # 如果是 AJAX 请求，返回 JSON 响应
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({
                    'success': False,
                    'error': error_msg
                }), 401
            # 如果是普通请求，重定向到登录页面
            logout_user()
            return redirect(url_for('web_auth.web_login'))
            
        return f(*args, **kwargs)
    return decorated_function

class SSLProvider:
    """SSL提供器，用于创建和管理SSL上下文"""
    
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
                cert_file = get_config().ssl.cert_file
                key_file = get_config().ssl.key_file
            except AttributeError:
                logger.error("无法从配置中获取SSL证书路径")
                return None
        
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
                cert_file = get_config().ssl.api_cert_file
                key_file = get_config().ssl.api_key_file
            else:
                cert_file = get_config().ssl.cert_file
                key_file = get_config().ssl.key_file
            
            context = SSLProvider.get_ssl_context(cert_file, key_file)
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
    return SSLProvider.get_ssl_context(cert_file, key_file)

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
            cert_file = get_config().ssl.api_cert_file
            key_file = get_config().ssl.api_key_file
        else:
            cert_file = get_config().ssl.cert_file
            key_file = get_config().ssl.key_file
        
        ssl_context = get_ssl_context(cert_file, key_file)
        
    if ssl_context:
        app.config['PREFERRED_URL_SCHEME'] = 'https'
        return ssl_context
    else:
        app.config['PREFERRED_URL_SCHEME'] = 'http'
        return None
