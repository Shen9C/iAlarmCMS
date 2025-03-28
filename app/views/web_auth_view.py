from flask import Blueprint, render_template, redirect, url_for, flash, request, session
from flask_login import login_user, logout_user, login_required, current_user
from datetime import datetime
import logging
from app.models.users import User
from app import db
from app.utils.auth_helper import validate_password

# 设置日志
logger = logging.getLogger(__name__)

bp = Blueprint('web_auth', __name__)

@bp.route('/web/login', methods=['GET', 'POST'])
def web_login():
    """Web端登录页面"""
    if current_user.is_authenticated:
        if current_user.is_token_expired():
            new_token = current_user.generate_token()
            db.session.commit()
            return redirect(url_for('alarm_view.index', user_token=new_token))
        return redirect(url_for('alarm_view.index', user_token=current_user.current_token))

    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        user = User.query.filter_by(username=username).first()
        if user is None or not user.check_password(password):
            flash('用户名或密码错误', 'danger')
            return render_template('auth/web_login.html')
        
        token = user.generate_token()
        user.current_token = token
        user.last_login_time = datetime.utcnow()
        user.login_count = (user.login_count or 0) + 1
        user.last_login_ip = request.remote_addr
        user.token_timestamp = datetime.utcnow()
        db.session.commit()
        
        login_user(user, remember=True)
        next_page = request.args.get('next')
        if next_page:
            return redirect(next_page)
        return redirect(url_for('alarm_view.index', user_token=token))
    
    return render_template('auth/web_login.html')

@bp.route('/web/change_password', methods=['GET', 'POST'])
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
                return redirect(url_for('alarm_view.index'))

    return render_template('auth/web_change_password.html')

@bp.route('/web/logout')
@login_required
def web_logout():
    """Web端登出页面"""
    token = request.args.get('user_token')
    if not token or current_user.current_token != token:
        flash('无效的会话', 'error')
        return redirect(url_for('web_auth.web_login'))
        
    try:
        current_user.current_token = None
        db.session.commit()
        logout_user()
        flash('您已成功退出系统', 'info')
        return redirect(url_for('web_auth.web_login'))
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