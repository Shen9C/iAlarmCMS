from flask import Blueprint, render_template, request
from flask_login import login_required

bp = Blueprint('tasks', __name__, url_prefix='/tasks')

@bp.route('/task_list')
@login_required
def task_list():
    """作业任务列表页面"""
    return render_template('tasks/list.html', user_token=request.args.get('user_token'))