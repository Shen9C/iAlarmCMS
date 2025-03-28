from flask import Blueprint, request, jsonify, render_template
from app.models.users import User
from app import db
from flask_login import login_user, logout_user, current_user
from datetime import datetime

bp = Blueprint('web_api', __name__, url_prefix='/api/v1/web')

@bp.route('/login', methods=['GET', 'POST'])
def login():
    """用户登录接口"""
    if request.method == 'GET':
        return render_template('auth/login.html')
        
    try:
        data = request.get_json()
        
        # 验证必要字段
        if not all(k in data for k in ['username', 'password']):
            return jsonify({
                'success': False,
                'error': '缺少用户名或密码'
            }), 400
            
        user = User.query.filter_by(username=data['username']).first()
        if user and user.check_password(data['password']):
            # 生成新的令牌
            token = user.generate_token()
            # 更新登录时间
            user.last_login_time = datetime.now()
            user.is_active = True
            db.session.commit()
            
            login_user(user)
            
            return jsonify({
                'success': True,
                'message': '登录成功',
                'data': {
                    'user_token': token,
                    'username': user.username,
                    'role': user.role
                }
            })
        else:
            return jsonify({
                'success': False,
                'error': '用户名或密码错误'
            }), 401
            
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'登录失败: {str(e)}'
        }), 500

@bp.route('/logout', methods=['POST'])
def logout():
    """用户登出接口"""
    try:
        if current_user.is_authenticated:
            current_user.current_token = None
            current_user.token_timestamp = None
            db.session.commit()
            logout_user()
            
        return jsonify({
            'success': True,
            'message': '已成功登出'
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'登出失败: {str(e)}'
        }), 500

@bp.route('/refresh-token', methods=['POST'])
def refresh_token():
    """刷新用户令牌"""
    try:
        if not current_user.is_authenticated:
            return jsonify({
                'success': False,
                'error': '用户未登录'
            }), 401
            
        new_token = current_user.generate_token()
        db.session.commit()
        
        return jsonify({
            'success': True,
            'data': {
                'user_token': new_token
            }
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'刷新令牌失败: {str(e)}'
        }), 500