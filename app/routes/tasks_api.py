from flask import Blueprint, jsonify, request
from flask_login import login_required, current_user
from app.models.tasks import Task
from app import db
import logging

logger = logging.getLogger(__name__)
bp = Blueprint('tasks_api', __name__, url_prefix='/api/tasks')

@bp.route('', methods=['GET'])
@login_required
def get_tasks():
    """获取任务列表"""
    try:
        tasks = Task.query.all()
        return jsonify({
            'code': 200,
            'data': [task.to_dict() for task in tasks]
        })
    except Exception as e:
        return jsonify({
            'code': 500,
            'message': f'获取任务列表失败: {str(e)}'
        }), 500

@bp.route('', methods=['POST'])
@login_required
def create_task():
    """创建新任务"""
    try:
        data = request.get_json()
        task = Task(
            name=data['name'],
            device_id=data['device_id'],
            schedule_time=data['schedule_time']
        )
        db.session.add(task)
        db.session.commit()
        
        return jsonify({
            'code': 200,
            'message': '任务创建成功',
            'data': task.to_dict()
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'code': 500,
            'message': f'创建任务失败: {str(e)}'
        }), 500

@bp.route('/<int:task_id>', methods=['PUT'])
@login_required
def update_task(task_id):
    """更新任务"""
    try:
        data = request.get_json()
        task = Task.query.get(task_id)
        task.name = data['name']
        task.device_id = data['device_id']
        task.schedule_time = data['schedule_time']
        db.session.commit()
        
        return jsonify({
            'code': 200,
            'message': '任务更新成功',
            'data': task.to_dict()
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'code': 500,
            'message': f'更新任务失败: {str(e)}'
        }), 500

@bp.route('/<int:task_id>', methods=['DELETE'])
@login_required
def delete_task(task_id):
    """删除任务"""
    try:
        task = Task.query.get(task_id)
        db.session.delete(task)
        db.session.commit()
        
        return jsonify({
            'code': 200,
            'message': '任务删除成功'
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'code': 500,
            'message': f'删除任务失败: {str(e)}'
        }), 500

@bp.route('/edit/<int:task_id>', methods=['POST'])
@login_required
def edit_task(task_id):
    """编辑任务"""
    try:
        data = request.get_json()
        task = Task.query.get_or_404(task_id)
        
        # 更新任务信息
        if 'name' in data:
            task.name = data['name']
        if 'device_id' in data:
            task.device_id = data['device_id']
        if 'schedule_time' in data:
            task.schedule_time = data['schedule_time']
            
        db.session.commit()
        
        return jsonify({
            'code': 200,
            'message': '任务编辑成功',
            'data': task.to_dict()
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'code': 500,
            'message': f'编辑任务失败: {str(e)}'
        }), 500