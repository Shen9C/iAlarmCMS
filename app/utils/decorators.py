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
from app.routes.edge_device_api_server import get_secret_key

# 假设已有其他装饰器如 admin_required 等

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