import re
from werkzeug.security import check_password_hash
from functools import wraps
from flask import flash, redirect, url_for, request, current_app
from flask_login import current_user
import logging

def validate_password(password):
    """验证密码复杂度"""
    if len(password) < 8:
        return False, "密码长度至少为8位"
    
    if not re.search(r"[A-Z]", password):
        return False, "密码必须包含大写字母"
    
    if not re.search(r"[a-z]", password):
        return False, "密码必须包含小写字母"
    
    if not re.search(r"\d", password):
        return False, "密码必须包含数字"
    
    if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", password):
        return False, "密码必须包含特殊字符"
    
    return True, "密码符合要求"

def verify_password(user, password):
    """验证用户密码"""
    if not user or not user.password_hash:
        return False
    return check_password_hash(user.password_hash, password)

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'admin':
            flash('您没有权限执行此操作')
            return redirect(url_for('alarms_view.index', user_token=request.args.get('user_token')))
        return f(*args, **kwargs)
    return decorated_function

def get_secret_key():
    """获取密钥的统一方法"""
    try:
        # 从当前应用获取密钥
        key = current_app.config['SECRET_KEY']
        if not key:
            raise KeyError("SECRET_KEY is empty")
        return key
    except (RuntimeError, KeyError):
        # 如果不在应用上下文中或密钥不存在，返回默认密钥
        logger = logging.getLogger(__name__)
        logger.warning("无法从应用配置获取SECRET_KEY，使用默认密钥")
        return "dev-key-123"  # 默认开发密钥