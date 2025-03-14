import hashlib
import time
import hmac
from flask import request, jsonify, current_app
from functools import wraps

def generate_signature(access_key, timestamp, secret_key):
    """生成签名"""
    message = f"{access_key}{timestamp}"
    signature = hmac.new(
        secret_key.encode('utf-8'),
        message.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()
    return signature

def verify_machine_auth():
    """验证机机认证"""
    access_key = request.headers.get('X-Access-Key')
    timestamp = request.headers.get('X-Timestamp')
    signature = request.headers.get('X-Signature')
    
    if not all([access_key, timestamp, signature]):
        return False
    
    # 从应用配置中获取机机认证信息
    machine_auth = None
    machine_auths = current_app.config.get('MACHINE_AUTH', {})
    for machine in machine_auths.values():
        if machine['access_key'] == access_key:
            machine_auth = machine
            break
    
    if not machine_auth:
        return False
    
    try:
        timestamp_int = int(timestamp)
        # 检查时间戳是否在5分钟内
        if abs(time.time() - timestamp_int) > 300:
            return False
        
        # 验证签名
        expected_signature = generate_signature(
            access_key,
            timestamp,
            machine_auth['secret_key']
        )
        return signature == expected_signature
    except:
        return False

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