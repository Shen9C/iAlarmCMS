from flask import Blueprint, jsonify, request
from flask_login import login_required, current_user
from app.models.tasks import Task
from app import db

bp = Blueprint('task_api', __name__, url_prefix='/api/tasks')

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