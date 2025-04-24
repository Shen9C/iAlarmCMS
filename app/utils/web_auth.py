from functools import wraps
from flask import request, jsonify, redirect, url_for
from flask_login import current_user, logout_user
from datetime import datetime

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
