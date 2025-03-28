from flask import Blueprint, render_template, redirect, url_for, flash, request, session, jsonify
from flask_login import login_user, logout_user, login_required, current_user
from datetime import datetime
import logging
from app.models.users import User
from app import db
from app.utils.auth_helper import validate_password

# 设置日志
logger = logging.getLogger(__name__)
# 强制设置日志级别为DEBUG
logger.setLevel(logging.DEBUG)

bp = Blueprint('web_auth', __name__, url_prefix='/web_auth')  # 添加 url_prefix

@bp.route('/login', methods=['GET', 'POST'])
def web_login():
    """Web端登录页面"""
    # 添加直接打印语句
    print("====== 登录请求开始处理 ======")
    print(f"请求方法: {request.method}")
    
    if request.method == 'POST':
        if request.is_json:
            data = request.get_json()
            print(f"登录数据: {data}")
        elif request.form:
            print(f"表单数据: {dict(request.form)}")
    
    # 在任何处理之前，先打印请求信息
    logger.info(f"收到登录请求: 方法={request.method}, 内容类型={request.headers.get('Content-Type')}")
    
    # 如果是POST请求，立即打印用户名和密码
    if request.method == 'POST':
        # 尝试从不同来源获取用户名和密码
        username = None
        password = None
        
        # 从JSON中获取
        if request.is_json:
            data = request.get_json()
            username = data.get('username')
            password = data.get('password')
            logger.info(f"从JSON获取 - 用户名: {username}, 密码: {password}")
        
        # 从表单中获取
        elif request.form:
            username = request.form.get('username')
            password = request.form.get('password')
            logger.info(f"从表单获取 - 用户名: {username}, 密码: {password}")
        
        # 从请求体中获取
        else:
            try:
                body = request.get_data(as_text=True)
                logger.info(f"请求体内容: {body}")
            except Exception as e:
                logger.error(f"获取请求体失败: {str(e)}")
    
    # GET请求返回登录页面
    if request.method == 'GET':
        logger.info("收到登录页面GET请求")
        return render_template('web_auth/login.html')

    # POST请求处理登录逻辑
    logger.info(f"收到登录POST请求: Content-Type={request.headers.get('Content-Type')}, X-Requested-With={request.headers.get('X-Requested-With')}")
    
    # 检查是否是AJAX请求
    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
    logger.info(f"是否AJAX请求: {is_ajax}")
    
    if is_ajax:
        # 获取JSON数据
        try:
            data = request.get_json()
            username = data.get('username')
            password = data.get('password')
            
            logger.info(f"登录尝试 - 用户名: {username}, 密码: {password}")
            
            logger.info(f"登录尝试 - 用户名: {username}, 密码长度: {len(password) if password else 0}")
            
            # 查询数据库中的所有用户
            all_users = User.query.all()
            logger.info(f"数据库中的用户列表: {[u.username for u in all_users]}")
            
            user = User.query.filter_by(username=username).first()
            if user is None:
                logger.warning(f"登录失败 - 用户不存在: {username}")
                return jsonify({
                    'success': False,
                    'error': '用户名或密码错误'
                })
            
            logger.info(f"找到用户: {user.username}, ID: {user.id}, 是否管理员: {user.is_admin}")
            
            if not user.check_password(password):
                logger.warning(f"登录失败 - 密码错误: 用户={username}")
                return jsonify({
                    'success': False,
                    'error': '用户名或密码错误'
                })
            
            token = user.generate_token()
            user.current_token = token
            user.last_login_time = datetime.utcnow()
            user.login_count = (user.login_count or 0) + 1
            user.last_login_ip = request.remote_addr
            user.token_timestamp = datetime.utcnow()
            db.session.commit()
            
            login_user(user, remember=True)
            logger.info(f"登录成功 - 用户: {username}, 生成Token: {token}")
            
            return jsonify({
                'success': True,
                'data': {
                    'user_token': token
                }
            })
        except Exception as e:
            logger.error(f"登录处理异常: {str(e)}", exc_info=True)
            return jsonify({
                'success': False,
                'error': f'服务器错误: {str(e)}'
            })
    
    # 如果不是AJAX请求，返回错误
    logger.warning("非AJAX登录请求被拒绝")
    return jsonify({
        'success': False,
        'error': '不支持的请求方式'
    })

@bp.route('/change_password', methods=['GET', 'POST'])
@login_required
def web_change_password():
    """Web端修改密码页面"""
    session['_flashes'] = []
    
    if request.method == 'POST':
        old_password = request.form['old_password']
        new_password = request.form['new_password']
        confirm_password = request.form['confirm_password']
        
        if not current_user.check_password(old_password):
            flash('当前密码错误')
        elif new_password != confirm_password:
            flash('两次输入的新密码不一致')
        else:
            is_valid, message = validate_password(new_password)
            if not is_valid:
                flash(message)
            else:
                current_user.set_password(new_password)
                db.session.commit()
                flash('密码修改成功', 'success')
                return redirect(url_for('alarms_view.index'))

    return render_template('web_auth/change_password.html')  # 修改这里

@bp.route('/logout')
@login_required
def web_logout():
    """Web端登出页面"""
    token = request.args.get('user_token')
    if not token or current_user.current_token != token:
        flash('无效的会话', 'error')
        return redirect(url_for('web_auth.login'))  # 修改这里
        
    try:
        current_user.current_token = None
        db.session.commit()
        logout_user()
        flash('您已成功退出系统', 'info')
        return redirect(url_for('web_auth.login'))  # 修改这里
    except Exception as e:
        logger.error(f"[ERROR] 登出过程发生错误: {str(e)}")
        raise

@bp.before_request
def check_web_token():
    """Web端令牌检查"""
    if current_user.is_authenticated and current_user.is_token_expired():
        new_token = current_user.generate_token()
        db.session.commit()
        return redirect(request.url.replace(
            f'user_token={request.args.get("user_token")}',
            f'user_token={new_token}'
        ))