import hashlib
import time
import hmac
from flask import request, jsonify, current_app
from functools import wraps
from app.routes.edge_device_api_server import get_secret_key

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