from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from app.models.tasks import Task
from app.models.settings import SystemConfig
from app.models.edge_devices import EdgeDevice
from app.models.oil_wells import OilWell
from app import db
from sqlalchemy import or_

bp = Blueprint('tasks_view', __name__, url_prefix='/tasks')

@bp.route('/')
@login_required
def index():
    """作业任务列表页面"""
    try:
        # 获取筛选参数
        task_type = request.args.get('task_type', '')
        well_name = request.args.get('well_name', '')
        well_code = request.args.get('well_code', '')
        device_name = request.args.get('device_name', '')
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 15, type=int)
        
        # 构建查询
        query = Task.query
        
        # 应用筛选条件
        if task_type:
            query = query.filter(Task.task_type == task_type)
        
        if well_name:
            query = query.filter(Task.well_name.ilike(f'%{well_name}%'))
            
        if well_code:
            query = query.filter(Task.well_code == well_code)
            
        if device_name:
            query = query.join(Task.device).filter(EdgeDevice.device_name.ilike(f'%{device_name}%'))
            
        # 按创建时间降序排序
        query = query.order_by(Task.created_at.desc())
            
        # 获取分页数据
        pagination = query.paginate(
            page=page, per_page=per_page, error_out=False
        )
        
        # 获取筛选选项
        task_types = Task.query.with_entities(Task.task_type).distinct().all()
        task_types = [t[0] for t in task_types if t[0]]
        
        well_names = Task.query.with_entities(Task.well_name).distinct().all()
        well_names = [w[0] for w in well_names if w[0]]
        
        well_codes = Task.query.with_entities(Task.well_code).distinct().all()
        well_codes = [w[0] for w in well_codes if w[0]]
        
        device_names = EdgeDevice.query.with_entities(EdgeDevice.device_name).distinct().all()
        device_names = [d[0] for d in device_names if d[0]]
        
        # 获取系统配置
        system_config = SystemConfig.query.first()
        
        return render_template('tasks/tasks_index.html',
                             tasks=pagination.items,
                             pagination=pagination,
                             task_types=task_types,
                             well_names=well_names,
                             well_codes=well_codes,
                             device_names=device_names,
                             current_type=task_type,
                             current_well=well_name,
                             current_well_code=well_code,
                             current_device=device_name,
                             system_config=system_config)
    except Exception as e:
        flash(f'获取任务列表失败: {str(e)}', 'error')
        return render_template('tasks/tasks_index.html', tasks=[], pagination=None)

@bp.route('/create', methods=['GET', 'POST'])
@login_required
def create():
    """创建任务页面"""
    if request.method == 'POST':
        try:
            well_code = request.form.get('well_code', '')
            # 生成任务编号
            task_code = Task.generate_task_code(well_code)
            
            # 获取油井名称
            well_name = request.form.get('well_name', '')
            if not well_name and well_code:
                oil_well = OilWell.query.filter_by(well_code=well_code).first()
                if oil_well:
                    well_name = oil_well.well_name
            
            # 创建任务描述
            task_type = request.form.get('task_type', '')
            device_id = request.form.get('device_id', '')
            device = EdgeDevice.query.get(device_id)
            device_name = device.device_name if device else ""
            task_description = f"{task_type}任务：{well_name or ''}（{well_code or ''}）- {device_name or ''}"
            
            task = Task(
                task_code=task_code,
                task_name=request.form['task_name'],
                well_name=well_name,
                well_code=well_code,
                task_type=task_type,
                camera_ip=request.form['camera_ip'],
                camera_preset=int(request.form['camera_preset']),
                pressure_range=float(request.form['pressure_range']),
                device_id=device_id,
                task_description=task_description
            )
            db.session.add(task)
            db.session.commit()
            flash('任务创建成功', 'success')
            return redirect(url_for('tasks_view.index'))
        except Exception as e:
            db.session.rollback()
            flash(f'创建任务失败: {str(e)}', 'error')
    
    # 获取设备列表供选择
    devices = EdgeDevice.query.all()
    # 获取油井列表
    oil_wells = OilWell.query.all()
    return render_template('tasks/task_form.html', task=None, devices=devices, oil_wells=oil_wells)

@bp.route('/edit/<int:task_id>', methods=['GET', 'POST'])
@login_required
def edit(task_id):
    """编辑任务页面"""
    task = Task.query.get_or_404(task_id)
    
    if request.method == 'POST':
        try:
            well_code = request.form.get('well_code', '')
            
            # 获取油井名称
            well_name = request.form.get('well_name', '')
            if not well_name and well_code:
                oil_well = OilWell.query.filter_by(well_code=well_code).first()
                if oil_well:
                    well_name = oil_well.well_name
            
            # 更新任务描述
            task_type = request.form.get('task_type', '')
            device_id = request.form.get('device_id', '')
            device = EdgeDevice.query.get(device_id)
            device_name = device.device_name if device else ""
            task_description = f"{task_type}任务：{well_name or ''}（{well_code or ''}）- {device_name or ''}"
            
            task.task_name = request.form['task_name']
            task.well_name = well_name
            task.well_code = well_code
            task.task_type = task_type
            task.camera_ip = request.form['camera_ip']
            task.camera_preset = int(request.form['camera_preset'])
            task.pressure_range = float(request.form['pressure_range'])
            task.device_id = device_id
            task.task_description = task_description
            db.session.commit()
            flash('任务更新成功', 'success')
            return redirect(url_for('tasks_view.index'))
        except Exception as e:
            db.session.rollback()
            flash(f'更新任务失败: {str(e)}', 'error')
    
    # 获取设备列表供选择
    devices = EdgeDevice.query.all()
    # 获取油井列表
    oil_wells = OilWell.query.all()
    return render_template('tasks/task_form.html', task=task, devices=devices, oil_wells=oil_wells)

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