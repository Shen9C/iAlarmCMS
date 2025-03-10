from flask import Blueprint, render_template, redirect, url_for, flash, request, session
from flask_login import login_user, logout_user, login_required, current_user
from datetime import datetime  # 添加这行
import logging

# 设置日志
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

from werkzeug.security import check_password_hash, generate_password_hash
from app.models.user import User
from app import db
import re  # 添加 re 模块的导入

# 修改 Blueprint 的名称和 url_prefix
bp = Blueprint('auth', __name__, url_prefix='/auth')

def validate_password(password):
    """验证密码复杂度"""
    if len(password) < 8:
        return False, '密码长度必须至少8位'
    
    if not re.search(r'[A-Z]', password):
        return False, '密码必须包含大写字母'
    
    if not re.search(r'[a-z]', password):
        return False, '密码必须包含小写字母'
    
    if not re.search(r'\d', password):
        return False, '密码必须包含数字'
    
    if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
        return False, '密码必须包含特殊字符'
    
    return True, '密码符合要求'

# 在 login 函数中使用 urlparse
@bp.route('/login', methods=['GET', 'POST'])
def login():
    # 如果用户已登录，检查请求来源
    if current_user.is_authenticated:
        next_page = request.args.get('next')
        if next_page:
            return redirect(next_page)
        return redirect(url_for('alarm_view.index'))

    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        user = User.query.filter_by(username=username).first()
        if user is None or not user.check_password(password):
            flash('用户名或密码错误', 'danger')
            return render_template('auth/login.html')
        
        # 更新登录信息，添加空值检查
        user.last_login_time = datetime.utcnow()
        user.login_count = (user.login_count or 0) + 1  # 如果为 None 则设为 0
        user.last_login_ip = request.remote_addr
        db.session.commit()
        
        login_user(user, remember=True)
        next_page = request.args.get('next')
        if next_page:
            return redirect(next_page)
        return redirect(url_for('alarm_view.index'))
    
    return render_template('auth/login.html')

@bp.route('/change_password', methods=['GET', 'POST'])
@login_required
def change_password():
    # 进入修改密码页面时清除之前的消息
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
            # 验证密码复杂度
            is_valid, message = validate_password(new_password)
            if not is_valid:
                flash(message)
            else:
                current_user.set_password(new_password)
                db.session.commit()
                flash('密码修改成功', 'success')  # 添加消息类型
                return redirect(url_for('alarm_view.index'))

    return render_template('auth/change_password.html')

# 修改登出路由
@bp.route('/logout')  # 只使用 GET 方法，移除 methods 参数
@login_required
def logout():
    logger.debug(f"[DEBUG] 进入登出路由")
    logger.debug(f"[DEBUG] 请求方法: {request.method}")
    logger.debug(f"[DEBUG] 请求路径: {request.path}")
    
    try:
        logout_user()
        logger.debug("[DEBUG] 用户已登出")
        flash('您已成功退出系统', 'info')
        return redirect(url_for('auth.login'))
    except Exception as e:
        logger.error(f"[ERROR] 登出过程发生错误: {str(e)}")
        raise