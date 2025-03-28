from flask import Blueprint, request, jsonify
from flask_login import login_user, logout_user, current_user, login_required
from datetime import datetime
import logging
from app.models.users import User
from app import db
from app.utils.auth_helper import validate_password

# 设置日志
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

bp = Blueprint('web_auth_api', __name__, url_prefix='/api/web_auth')

@bp.route('/login', methods=['POST'])
def web_login_api():
    """Web端登录API"""
    # 添加直接打印语句
    print("====== API登录请求开始处理 ======")
    print(f"请求方法: {request.method}")
    print(f"请求头: {dict(request.headers)}")
    
    # 获取JSON数据
    try:
        data = request.get_json()
        print(f"登录数据: {data}")
        
        username = data.get('username')
        password = data.get('password')
        
        print(f"用户名: {username}, 密码: {password}")
        
        # 查询数据库中的所有用户
        all_users = User.query.all()
        print(f"数据库中的用户列表: {[u.username for u in all_users]}")
        
        user = User.query.filter_by(username=username).first()
        if user is None:
            print(f"登录失败 - 用户不存在: {username}")
            return jsonify({
                'success': False,
                'error': '用户名或密码错误'
            })
        
        print(f"找到用户: {user.username}, ID: {user.id}, 是否管理员: {user.is_admin}")
        
        if not user.check_password(password):
            print(f"登录失败 - 密码错误: 用户={username}")
            return jsonify({
                'success': False,
                'error': '用户名或密码错误'
            })
        
        token = user.generate_token()
        user.current_token = token
        # 更新登录信息
        user.last_login_time = datetime.utcnow()
        # 删除这一行: user.last_login_ip = request.remote_addr
        # 删除这一行: user.login_count = (user.login_count or 0) + 1
        
        user.token_timestamp = datetime.utcnow()
        db.session.commit()
        
        login_user(user, remember=True)
        print(f"登录成功 - 用户: {username}, 生成Token: {token}")
        
        return jsonify({
            'success': True,
            'data': {
                'user_token': token
            }
        })
    except Exception as e:
        print(f"登录处理异常: {str(e)}")
        import traceback
        print(traceback.format_exc())
        return jsonify({
            'success': False,
            'error': f'服务器错误: {str(e)}'
        })

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