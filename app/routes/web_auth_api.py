from flask import Blueprint, jsonify, request
from flask_login import login_user, logout_user, login_required, current_user
from datetime import datetime
import logging
from app.models.users import User
from app import db
from app.utils.auth_helper import validate_password

# 设置日志
logger = logging.getLogger(__name__)

bp = Blueprint('web_auth_api', __name__, url_prefix='/api/web/auth')

@bp.route('/login', methods=['POST'])
def web_login_api():
    """Web端登录API"""
    try:
        data = request.get_json()
        username = data.get('username')
        password = data.get('password')
        
        user = User.query.filter_by(username=username).first()
        if user is None or not user.check_password(password):
            return jsonify({
                'code': 401,
                'message': '用户名或密码错误'
            }), 401
        
        token = user.generate_token()
        user.current_token = token
        user.last_login_time = datetime.utcnow()
        user.login_count = (user.login_count or 0) + 1
        user.last_login_ip = request.remote_addr
        user.token_timestamp = datetime.utcnow()
        db.session.commit()
        
        login_user(user, remember=True)
        
        return jsonify({
            'code': 200,
            'message': '登录成功',
            'data': {
                'token': token,
                'username': user.username,
                'role': user.role
            }
        })
    except Exception as e:
        logger.error(f"[ERROR] 登录过程发生错误: {str(e)}")
        return jsonify({
            'code': 500,
            'message': f'登录失败: {str(e)}'
        }), 500

@bp.route('/logout', methods=['POST'])
@login_required
def web_logout_api():
    """Web端登出API"""
    try:
        token = request.args.get('user_token')
        if not token or current_user.current_token != token:
            return jsonify({
                'code': 401,
                'message': '无效的会话'
            }), 401
        
        current_user.current_token = None
        db.session.commit()
        logout_user()
        
        return jsonify({
            'code': 200,
            'message': '登出成功'
        })
    except Exception as e:
        logger.error(f"[ERROR] 登出过程发生错误: {str(e)}")
        return jsonify({
            'code': 500,
            'message': f'登出失败: {str(e)}'
        }), 500

@bp.route('/change_password', methods=['POST'])
@login_required
def web_change_password_api():
    """Web端修改密码API"""
    try:
        data = request.get_json()
        old_password = data.get('old_password')
        new_password = data.get('new_password')
        
        if not current_user.check_password(old_password):
            return jsonify({
                'code': 400,
                'message': '当前密码错误'
            }), 400
        
        is_valid, message = validate_password(new_password)
        if not is_valid:
            return jsonify({
                'code': 400,
                'message': message
            }), 400
            
        current_user.set_password(new_password)
        db.session.commit()
        
        return jsonify({
            'code': 200,
            'message': '密码修改成功'
        })
    except Exception as e:
        logger.error(f"[ERROR] 修改密码过程发生错误: {str(e)}")
        return jsonify({
            'code': 500,
            'message': f'修改密码失败: {str(e)}'
        }), 500