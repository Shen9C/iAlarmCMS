from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from urllib.parse import urlparse  # 使用 Python 标准库
from app.models.user import User
from app import db  # 添加这行导入
import re

bp = Blueprint('auth', __name__)

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
    if current_user.is_authenticated:
        return redirect(url_for('alarm_view.index'))

    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        print(f"Debug - 尝试登录: username={username}")  # 调试输出
        
        user = User.query.filter_by(username=username).first()
        if user is None:
            print("Debug - 用户不存在")  # 调试输出
            flash('用户名或密码错误')
            return render_template('auth/login.html')
            
        if not user.check_password(password):
            print("Debug - 密码错误")  # 调试输出
            flash('用户名或密码错误')
            return render_template('auth/login.html')
        
        print("Debug - 登录成功")  # 调试输出
        login_user(user, remember=True)
        next_page = request.args.get('next')
        if next_page:
            return redirect(next_page)
        return redirect(url_for('alarm_view.index'))

    return render_template('auth/login.html')

@bp.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('auth.login'))

@bp.route('/change_password', methods=['GET', 'POST'])
@login_required
def change_password():
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
                flash('密码修改成功', 'success')
                return redirect(url_for('alarms.index'))
            
    return render_template('auth/change_password.html')