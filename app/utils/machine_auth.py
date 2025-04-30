import jwt
import logging
from datetime import datetime, timedelta
from app.utils.auth_helper import get_secret_key
from app.models.edge_devices import EdgeDevice
from flask import request, jsonify, current_app
from functools import wraps
import hmac
import hashlib
import ssl
from app.utils.yaml_config_loader import config
import os

def verify_machine_token(token):
    """验证机器令牌"""
    try:
        secret_key = get_secret_key()
        payload = jwt.decode(
            token,
            secret_key,
            algorithms=['HS256']
        )
        return payload
    except Exception as e:
        current_app.logger.error(f"验证机器令牌失败: {str(e)}")
        return None

def create_machine_token(device_id, expires_in=86400):
    """创建机器令牌"""
    try:
        secret_key = get_secret_key()
        payload = {
            'device_id': device_id,
            'exp': datetime.utcnow() + timedelta(seconds=expires_in)
        }
        token = jwt.encode(payload, secret_key, algorithm='HS256')
        return token
    except Exception as e:
        current_app.logger.error(f"创建机器令牌失败: {str(e)}")
        return None

def generate_signature(access_key, timestamp, secret_key):
    """生成签名"""
    message = f"{access_key}{timestamp}".encode('utf-8')
    signature = hmac.new(
        secret_key.encode('utf-8'),
        message,
        hashlib.sha256
    ).hexdigest()
    return signature

def verify_machine_auth(access_key, timestamp, signature):
    """验证机器认证"""
    try:
        secret_key = get_secret_key()
        expected_signature = generate_signature(access_key, timestamp, secret_key)
        return hmac.compare_digest(signature, expected_signature)
    except Exception as e:
        current_app.logger.error(f"机器认证验证失败: {str(e)}")
        return False

def get_machine_auth():
    """获取机器认证配置"""
    try:
        secret_key = get_secret_key()
        return {
            'access_key': current_app.config.get('MACHINE_ACCESS_KEY'),
            'secret_key': secret_key
        }
    except Exception as e:
        current_app.logger.error(f"获取机器认证配置失败: {str(e)}")
        return None

def machine_auth_required(f):
    """机机认证装饰器"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not verify_machine_auth():
            return jsonify({
                'success': False,
                'error': '机机认证失败'
            }), 401
        return f(*args, **kwargs)
    return decorated_function

def device_auth_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        access_key = request.headers.get('X-Access-Key')
        secret_key = request.headers.get('X-Secret-Key')

        if not access_key or not secret_key:
            return jsonify({"code": 401, "message": "缺少认证信息"}), 401

        try:
            device = EdgeDevice.query.filter_by(access_key=access_key, secret_key=secret_key).first()
            if not device:
                return jsonify({"code": 401, "message": "设备认证失败"}), 401

            # 更新设备状态
            device.update_status('在线')
            return f(*args, **kwargs)
        except Exception as e:
            current_app.logger.error(f"设备认证过程中发生错误: {str(e)}")
            return jsonify({"code": 500, "message": "服务器内部错误"}), 500

    return decorated_function

def get_ssl_context(cert_file=None, key_file=None):
    """获取设备API的SSL上下文"""
    try:
        # 如果提供了证书和密钥文件，使用它们
        if cert_file and key_file:
            return (cert_file, key_file)
        
        # 否则从配置中获取
        ssl_config = config.ssl
        if not ssl_config:
            current_app.logger.error("SSL配置不存在")
            return None
            
        cert_file = ssl_config.api_cert_file
        key_file = ssl_config.api_key_file
        
        if not cert_file or not key_file:
            current_app.logger.error("SSL证书或密钥文件未配置")
            return None
            
        # 检查文件是否存在
        if not os.path.exists(cert_file) or not os.path.exists(key_file):
            current_app.logger.error(f"SSL证书或密钥文件不存在: {cert_file}, {key_file}")
            return None
            
        return (cert_file, key_file)
    except Exception as e:
        current_app.logger.error(f"创建SSL上下文失败: {str(e)}")
        return None