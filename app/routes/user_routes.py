from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from app.models.user import User
from app import db

bp = Blueprint('users', __name__, url_prefix='/users')

@bp.route('/')
@login_required
def user_list():
    if not current_user.is_admin:
        flash('您没有权限访问此页面')
        return redirect(url_for('alarm_view.index'))
    
    users = User.query.all()
    return render_template('users/user_list.html', users=users)

@bp.route('/users/create', methods=['GET', 'POST'])
@login_required
def create():
    if current_user.role != 'admin':
        flash('权限不足')
        return redirect(url_for('alarms.index'))
    
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        role = request.form['role']
        
        if User.query.filter_by(username=username).first():
            flash('用户名已存在')
        else:
            user = User(username=username, role=role)
            user.set_password(password)
            db.session.add(user)
            db.session.commit()
            flash('用户创建成功')
            return redirect(url_for('users.index'))
            
    return render_template('users/create.html')