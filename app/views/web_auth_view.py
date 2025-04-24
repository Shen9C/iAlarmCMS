from flask import Blueprint, render_template, redirect, url_for, flash, request, session, jsonify
from flask_login import login_user, logout_user, login_required, current_user
from datetime import datetime
from urllib.parse import urlparse  # 修改这里：使用 urllib.parse
import logging
from app.models.users import User
from app import db
from app.utils.auth_helper import validate_password

# 设置日志
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

bp = Blueprint('web_auth', __name__, url_prefix='/web_auth')

@bp.route('/login', methods=['GET', 'POST'])
def web_login():
    """Web端登录"""
    # 如果用户已登录但token为空，强制重新登录
    if current_user.is_authenticated and not current_user.current_token:
        logout_user()
        flash('会话已过期，请重新登录')
        return redirect(url_for('web_auth.web_login'))
    
    # 如果用户已登录且token有效，直接跳转到首页
    if current_user.is_authenticated:
        response = redirect(url_for('alarms_view.index'))
        # 设置安全的HttpOnly cookie
        response.set_cookie('user_token', current_user.current_token, 
                           httponly=True, secure=request.is_secure, 
                           samesite='Lax', max_age=86400)  # 1天有效期
        return response
    
    logger.info(f"收到登录请求: 方法={request.method}, 内容类型={request.headers.get('Content-Type')}")
    
    # GET请求返回登录页面
    if request.method == 'GET':
        return render_template('web_auth/login.html')
    
    # 检查是否是AJAX请求
    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
    
    if is_ajax:
        try:
            data = request.get_json()
            username = data.get('username')
            password = data.get('password')
            
            user = User.query.filter_by(username=username).first()
            if not user or not user.check_password(password):
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
            
            return jsonify({
                'success': True,
                'data': {
                    'user_token': token,
                    'redirect_url': url_for('alarms_view.index')
                }
            })
        except Exception as e:
            logger.error(f"登录处理异常: {str(e)}", exc_info=True)
            return jsonify({
                'success': False,
                'error': f'服务器错误: {str(e)}'
            })
    
    # 处理常规表单登录
    username = request.form.get('username')
    password = request.form.get('password')
    remember = request.form.get('remember', False)
    
    user = User.query.filter_by(username=username).first()
    
    if user and user.check_password(password):
        # 生成新的token
        token = user.generate_token()
        user.current_token = token
        user.last_login_time = datetime.utcnow()
        user.login_count = (user.login_count or 0) + 1
        user.last_login_ip = request.remote_addr
        user.token_timestamp = datetime.utcnow()
        db.session.commit()
        
        login_user(user, remember=remember)
        
        next_page = request.args.get('next')
        if not next_page or urlparse(next_page).netloc != '':
            # 登录成功后重定向到首页，不再在URL中附带token
            next_page = url_for('alarms_view.index')
        
        flash('登录成功')
        response = redirect(next_page)
        # 设置安全的HttpOnly cookie
        response.set_cookie('user_token', token, 
                           httponly=True, secure=request.is_secure, 
                           samesite='Lax', max_age=86400)  # 1天有效期
        return response
    
    flash('用户名或密码错误')
    return render_template('web_auth/login.html')

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
    """退出登录"""
    try:
        # 清除用户的token
        if current_user.is_authenticated:
            current_user.current_token = None
            current_user.token_timestamp = None
            db.session.commit()
            logger.info(f"用户 {current_user.username} 的token已清除")
        
        # 清理用户会话
        logout_user()
        
        response = redirect(url_for('web_auth.web_login'))
        # 清除cookie中的token
        response.delete_cookie('user_token')
        flash('您已成功退出登录')
        return response
        
    except Exception as e:
        logger.error(f"退出登录时出错: {str(e)}")
        response = redirect(url_for('web_auth.web_login'))
        response.delete_cookie('user_token')  # 确保即使出错也清除cookie
        flash('退出登录时发生错误')
        return response