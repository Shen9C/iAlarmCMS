from flask import Blueprint, render_template, request, redirect, url_for, flash
import re
from flask_login import login_required, current_user
from app.models.users import User
from app import db
from sqlalchemy import or_

bp = Blueprint('users', __name__)

@bp.route('/')
@login_required
def index():
    if current_user.role != 'admin':
        flash('您没有权限访问此页面')
        return redirect(url_for('alarms_view.index', user_token=request.args.get('user_token')))
    
    try:
        # 获取筛选参数
        username = request.args.get('username', '')
        role = request.args.get('role', '')
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 15, type=int)
        
        # 构建查询
        query = User.query
        
        # 应用筛选条件
        if username:
            query = query.filter(User.username.ilike(f'%{username}%'))
            
        if role:
            query = query.filter(User.role == role)
            
        # 按ID升序排序
        query = query.order_by(User.id.asc())
            
        # 获取分页数据
        pagination = query.paginate(
            page=page, per_page=per_page, error_out=False
        )
        
        return render_template('users/users_index.html',
                             users=pagination.items,
                             pagination=pagination)
    except Exception as e:
        flash(f'获取用户列表失败: {str(e)}', 'error')
        return render_template('users/users_index.html', users=[], pagination=None)

def validate_password(password):
    """
    验证密码复杂度
    要求：
    1. 最少8个字符
    2. 至少包含一个大写字母
    3. 至少包含一个小写字母
    4. 至少包含一个数字
    5. 至少包含一个特殊字符
    """
    if len(password) < 8:
        return False, "密码长度必须至少为8个字符"
    if not re.search(r'[A-Z]', password):
        return False, "密码必须包含至少一个大写字母"
    if not re.search(r'[a-z]', password):
        return False, "密码必须包含至少一个小写字母"
    if not re.search(r'\d', password):
        return False, "密码必须包含至少一个数字"
    if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
        return False, "密码必须包含至少一个特殊字符(!@#$%^&*(),.?\":{}|<>)"
    return True, "密码验证通过"

@bp.route('/create', methods=['GET', 'POST'])
@login_required
def create():
    if current_user.role != 'admin':
        flash('权限不足')
        return redirect(url_for('alarms_view.index', user_token=request.args.get('user_token')))
    
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        role = request.form.get('role')
        
        # 验证用户名
        if not username or len(username) < 3:
            flash('用户名必须至少3个字符')
            return redirect(url_for('users.create'))
        
        # 验证密码
        is_valid, message = validate_password(password)
        if not is_valid:
            flash(message)
            return redirect(url_for('users.create'))
        
        # 检查用户名是否已存在
        if User.query.filter_by(username=username).first():
            flash('用户名已存在')
            return redirect(url_for('users.create'))
            
        # 创建新用户
        user = User(username=username, role=role)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        
        flash('用户创建成功')
        return redirect(url_for('users.index'))
            
    return render_template('users/users_create.html')

@bp.route('/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit(id):
    if current_user.role != 'admin':
        flash('权限不足')
        return redirect(url_for('alarms_view.index', user_token=request.args.get('user_token')))
    
    user = User.query.get_or_404(id)
    
    if request.method == 'POST':
        username = request.form.get('username')
        role = request.form.get('role')
        password = request.form.get('password')
        
        # 验证用户名
        if not username or len(username) < 3:
            flash('用户名必须至少3个字符')
            return redirect(url_for('users.edit', id=id))
            
        # 如果提供了新密码，验证密码
        if password:
            is_valid, message = validate_password(password)
            if not is_valid:
                flash(message)
                return redirect(url_for('users.edit', id=id))
            user.set_password(password)
        
        # 检查用户名是否已存在（排除当前用户）
        existing_user = User.query.filter_by(username=username).first()
        if existing_user and existing_user.id != id:
            flash('用户名已存在')
            return redirect(url_for('users.edit', id=id))
            
        # 更新用户信息
        user.username = username
        user.role = role
        db.session.commit()
        
        flash('用户信息更新成功')
        return redirect(url_for('users.index'))
            
    return render_template('users/users_edit.html', user=user)

@bp.route('/delete/<int:id>', methods=['POST'])
@login_required
def delete(id):
    if current_user.role != 'admin':
        flash('权限不足')
        return redirect(url_for('alarms_view.index', user_token=request.args.get('user_token')))
    
    # 不允许删除自己
    if id == current_user.id:
        flash('不能删除当前登录的用户')
        return redirect(url_for('users.index'))
    
    user = User.query.get_or_404(id)
    username = user.username
    
    try:
        db.session.delete(user)
        db.session.commit()
        flash(f'用户 {username} 已成功删除')
    except Exception as e:
        db.session.rollback()
        flash('删除用户失败，请稍后重试')
    
    return redirect(url_for('users.index'))