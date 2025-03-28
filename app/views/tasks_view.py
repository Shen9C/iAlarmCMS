from flask import Blueprint, render_template, request
from flask_login import login_required
from app.models.tasks import Task

bp = Blueprint('tasks', __name__)

@bp.route('/tasks')
@login_required
def index():
    """作业任务列表页面"""
    try:
        tasks = Task.query.all()
        return render_template('tasks/tasks_index.html', 
                             tasks=tasks,
                             user_token=request.args.get('user_token'))
    except Exception as e:
        return render_template('tasks/tasks_index.html', 
                             tasks=[],
                             error=str(e),
                             user_token=request.args.get('user_token'))