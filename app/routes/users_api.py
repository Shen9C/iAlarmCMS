from flask import Blueprint, jsonify, request
from flask_login import login_required, current_user
from app.models.users import User
from app import db

bp = Blueprint('users_api', __name__, url_prefix='/api/users')

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