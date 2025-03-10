from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify  # 添加 jsonify
from flask_login import login_required, current_user
from app.models.user import User
from app import db

bp = Blueprint('users', __name__)

@bp.route('/')
@login_required
def index():
    if current_user.role != 'admin':
        flash('您没有权限访问此页面')
        return redirect(url_for('alarm_view.index', user_token=request.args.get('user_token')))
    
    users = User.query.all()
    return render_template('users/user_list.html', users=users)

@bp.route('/create', methods=['GET', 'POST'])
@login_required
def create():
    if current_user.role != 'admin':
        flash('权限不足')
        return redirect(url_for('alarm_view.index', user_token=request.args.get('user_token')))
    
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
            return redirect(url_for('users.index', user_token=request.args.get('user_token')))
            
    return render_template('users/create.html')

@bp.route('/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit(id):
    if current_user.role != 'admin':
        flash('权限不足')
        return redirect(url_for('alarm_view.index', user_token=request.args.get('user_token')))
    
    user = User.query.get_or_404(id)
    
    if request.method == 'POST':
        username = request.form['username']
        role = request.form['role']
        password = request.form.get('password')
        
        # 检查用户名是否已存在（排除当前用户）
        existing_user = User.query.filter(User.username == username, User.id != id).first()
        if existing_user:
            flash('用户名已存在')
        else:
            user.username = username
            user.role = role
            if password:
                user.set_password(password)
            db.session.commit()
            flash('用户信息更新成功')
            return redirect(url_for('users.index', user_token=request.args.get('user_token')))
            
    return render_template('users/edit.html', user=user)

@bp.route('/delete/<int:id>', methods=['POST'])
@login_required
def delete_user(id):
    if current_user.role != 'admin':
        return jsonify({'error': '权限不足'}), 403
    
    user = User.query.get_or_404(id)
    if user.username == 'admin':
        return jsonify({'error': '不能删除管理员账号'}), 403
    
    if user.id == current_user.id:
        return jsonify({'error': '不能删除当前登录用户'}), 403
        
    try:
        db.session.delete(user)
        db.session.commit()
        return jsonify({'message': '删除成功'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': '删除用户失败，请稍后重试'}), 500