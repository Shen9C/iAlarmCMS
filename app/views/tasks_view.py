from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from app.models.tasks import Task
from app.models.settings import SystemConfig  # 添加这行
from app import db

bp = Blueprint('tasks_view', __name__, url_prefix='/tasks')

@bp.route('/')
@login_required
def index():
    """作业任务列表页面"""
    try:
        # 获取筛选参数
        task_type = request.args.get('task_type', '')
        status = request.args.get('status', '')
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 15, type=int)
        
        # 构建查询
        query = Task.query
        
        # 应用筛选条件
        if task_type:
            query = query.filter(Task.task_type == task_type)
        if status:
            query = query.filter(Task.status == status)
            
        # 获取分页数据
        pagination = query.paginate(
            page=page, per_page=per_page, error_out=False
        )
        
        # 获取筛选选项
        task_types = Task.query.with_entities(Task.task_type).distinct().all()
        task_types = [t[0] for t in task_types if t[0]]
        
        statuses = Task.query.with_entities(Task.status).distinct().all()
        statuses = [s[0] for s in statuses if s[0]]
        
        # 获取系统配置
        system_config = SystemConfig.query.first()
        
        return render_template('tasks/tasks_index.html',
                             tasks=pagination.items,
                             pagination=pagination,
                             task_types=task_types,
                             statuses=statuses,
                             current_type=task_type,
                             current_status=status,
                             system_config=system_config)  # 添加这个参数
    except Exception as e:
        return render_template('tasks/tasks_index.html',
                             tasks=[],
                             error=str(e))

@bp.route('/create', methods=['GET', 'POST'])
@login_required
def create():
    """创建任务页面"""
    if request.method == 'POST':
        try:
            task = Task(
                name=request.form['name'],
                device_id=request.form['device_id'],
                schedule_time=request.form['schedule_time']
            )
            db.session.add(task)
            db.session.commit()
            flash('任务创建成功', 'success')
            return redirect(url_for('tasks_view.index'))
        except Exception as e:
            db.session.rollback()
            flash(f'创建任务失败: {str(e)}', 'error')
    
    return render_template('tasks/task_form.html', task=None)

@bp.route('/edit/<int:task_id>', methods=['GET', 'POST'])
@login_required
def edit(task_id):
    """编辑任务页面"""
    task = Task.query.get_or_404(task_id)
    
    if request.method == 'POST':
        try:
            task.name = request.form['name']
            task.device_id = request.form['device_id']
            task.schedule_time = request.form['schedule_time']
            db.session.commit()
            flash('任务更新成功', 'success')
            return redirect(url_for('tasks_view.index'))
        except Exception as e:
            db.session.rollback()
            flash(f'更新任务失败: {str(e)}', 'error')
    
    return render_template('tasks/task_form.html', task=task)

@bp.route('/delete/<int:task_id>', methods=['POST'])
@login_required
def delete(task_id):
    """删除任务"""
    try:
        task = Task.query.get_or_404(task_id)
        db.session.delete(task)
        db.session.commit()
        flash('任务删除成功', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'删除任务失败: {str(e)}', 'error')
    
    return redirect(url_for('tasks_view.index'))

@bp.route('/<int:task_id>')
@login_required
def detail(task_id):
    """任务详情页面"""
    try:
        task = Task.query.get_or_404(task_id)
        return render_template('tasks/task_detail.html', task=task)
    except Exception as e:
        flash(f'获取任务详情失败: {str(e)}', 'error')
        return redirect(url_for('tasks_view.index'))