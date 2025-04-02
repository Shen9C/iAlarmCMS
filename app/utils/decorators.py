from functools import wraps
from flask import flash, redirect, url_for, request
from flask_login import current_user

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'admin':
            flash('您没有权限执行此操作')
            return redirect(url_for('alarms_view.index', user_token=request.args.get('user_token')))
        return f(*args, **kwargs)
    return decorated_function


# 添加 device_auth_required 装饰器
from functools import wraps
from flask import request, jsonify, current_app
from app.models.edge_devices import EdgeDevice

# 假设已有其他装饰器如 admin_required 等

def device_auth_required(f):
    """验证设备认证的装饰器"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # 从请求头中获取访问密钥和密钥
        access_key = request.headers.get('X-Access-Key')
        secret_key = request.headers.get('X-Secret-Key')
        
        if not access_key or not secret_key:
            return jsonify({"code": 401, "message": "缺少认证信息"}), 401
        
        # 查找设备
        device = EdgeDevice.query.filter_by(access_key=access_key, secret_key=secret_key).first()
        if not device:
            return jsonify({"code": 401, "message": "无效的认证信息"}), 401
        
        # 将设备信息添加到请求上下文
        request.current_device = device
        
        return f(*args, **kwargs)
    return decorated_function