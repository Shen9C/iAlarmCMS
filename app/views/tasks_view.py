from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from app.models.tasks import Task
from app.models.edge_devices import EdgeDevice
from app.models.oil_wells import OilWell
from app import db
from sqlalchemy import or_
from flask import current_app

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
            
        # 按ID升序排序
        query = query.order_by(Task.id.asc())
            
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
                             current_device=device_name)
    except Exception as e:
        flash(f'获取任务列表失败: {str(e)}', 'error')
        return render_template('tasks/tasks_index.html', tasks=[], pagination=None)

@bp.route('/create', methods=['GET', 'POST'])
@login_required
def create():
    """创建任务页面"""
    if request.method == 'POST':
        try:
            # 检查是否是AJAX请求
            is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
            
            # 获取表单数据
            if is_ajax:
                data = request.get_json()
                well_code = data.get('well_code', '')
                well_name = data.get('well_name', '')
                task_type = data.get('task_type', '')
                device_id = data.get('device_id', '')
                camera_ip = data.get('camera_ip', '')
                camera_preset = data.get('camera_preset', '1')
                pressure_range = data.get('pressure_range', '0')
            else:
                well_code = request.form.get('well_code', '')
                well_name = request.form.get('well_name', '')
                task_type = request.form.get('task_type', '')
                device_id = request.form.get('device_id', '')
                camera_ip = request.form.get('camera_ip', '')
                camera_preset = request.form.get('camera_preset', '1')
                pressure_range = request.form.get('pressure_range', '0')
            
            # 验证必填字段
            required_fields = {
                'task_name': '任务名称',
                'task_type': '任务类型',
                'well_name': '油井名称',
                'well_code': '油井编号',
                'device_id': '设备',
                'camera_ip': '摄像头IP',
                'camera_preset': '摄像头预置点',
                'pressure_range': '压力表量程'
            }
            
            missing_fields = []
            for field, label in required_fields.items():
                if not (data if is_ajax else request.form).get(field):
                    missing_fields.append(label)
            
            if missing_fields:
                if is_ajax:
                    return jsonify({
                        'code': 400,
                        'message': f'请填写以下必填字段: {", ".join(missing_fields)}'
                    }), 400
                else:
                    flash(f'请填写以下必填字段: {", ".join(missing_fields)}', 'error')
                    return render_template('tasks/task_form.html', task=None)
            
            # 验证设备是否存在
            device = EdgeDevice.query.filter_by(device_id=device_id).first()
            if not device:
                if is_ajax:
                    return jsonify({
                        'code': 400,
                        'message': '选择的设备不存在，请重新选择'
                    }), 400
                else:
                    flash('选择的设备不存在，请重新选择', 'error')
                    return render_template('tasks/task_form.html', task=None)
            
            # 验证摄像头预置点
            try:
                camera_preset = int(camera_preset)
                if camera_preset < 1 or camera_preset > 255:
                    raise ValueError('摄像头预置点必须在1-255之间')
            except ValueError as e:
                if is_ajax:
                    return jsonify({
                        'code': 400,
                        'message': str(e)
                    }), 400
                else:
                    flash(str(e), 'error')
                    return render_template('tasks/task_form.html', task=None)
            
            # 验证压力表量程
            try:
                pressure_range = float(pressure_range)
                if pressure_range < 0:
                    raise ValueError('压力表量程不能为负数')
            except ValueError as e:
                if is_ajax:
                    return jsonify({
                        'code': 400,
                        'message': str(e)
                    }), 400
                else:
                    flash(str(e), 'error')
                    return render_template('tasks/task_form.html', task=None)
            
            # 生成任务编号
            task_code = Task.generate_task_code(well_code)
            
            # 创建任务描述
            device_name = device.device_name
            task_description = f"{task_type}任务：{well_name}（{well_code}）- {device_name}"
            
            # 创建任务
            task = Task(
                task_code=task_code,
                task_name=(data if is_ajax else request.form)['task_name'],
                well_name=well_name,
                well_code=well_code,
                task_type=task_type,
                camera_ip=camera_ip,
                camera_preset=camera_preset,
                camera_username=(data if is_ajax else request.form).get('camera_username', ''),
                camera_password=(data if is_ajax else request.form).get('camera_password', ''),
                pressure_range=pressure_range,
                device_id=device_id,
                task_description=task_description
            )
            
            # 保存到数据库
            db.session.add(task)
            db.session.commit()
            
            if is_ajax:
                return jsonify({
                    'code': 200,
                    'message': '任务创建成功'
                })
            else:
                flash('任务创建成功', 'success')
                return redirect(url_for('tasks_view.index'))
            
        except Exception as e:
            db.session.rollback()
            # 记录错误日志
            current_app.logger.error(f'创建任务失败: {str(e)}')
            if is_ajax:
                return jsonify({
                    'code': 500,
                    'message': '创建任务失败，请检查输入数据是否正确'
                }), 500
            else:
                flash('创建任务失败，请检查输入数据是否正确', 'error')
    
    # GET请求，显示创建页面
    devices = EdgeDevice.query.all()
    oil_wells = OilWell.query.all()
    return render_template('tasks/task_form.html', task=None, devices=devices, oil_wells=oil_wells)

@bp.route('/edit/<int:task_id>', methods=['GET', 'POST'])
@login_required
def edit(task_id):
    """编辑任务页面"""
    task = Task.query.get_or_404(task_id)
    
    if request.method == 'POST':
        try:
            print(request.form)  # 打印表单内容，便于调试
            print(f"正在处理任务编辑表单提交，任务ID: {task_id}")
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
            device = EdgeDevice.query.filter_by(device_id=device_id).first()
            device_name = device.device_name if device else ""
            task_description = f"{task_type}任务：{well_name or ''}（{well_code or ''}）- {device_name or ''}"
            
            # 验证压力表量程
            try:
                pressure_range = float(request.form.get('pressure_range', '0'))
                if pressure_range < 0:
                    raise ValueError('压力表量程不能为负数')
            except ValueError as e:
                flash(str(e), 'error')
                return render_template('tasks/task_form.html', task=task)
            
            task.task_name = request.form.get('task_name', '')
            task.well_name = well_name
            task.well_code = well_code
            task.task_type = task_type
            task.camera_ip = request.form.get('camera_ip', '')
            task.camera_preset = int(request.form.get('camera_preset', '1'))
            task.camera_username = request.form.get('camera_username', '')
            task.camera_password = request.form.get('camera_password', '')
            task.pressure_range = pressure_range
            task.device_id = device_id
            task.task_description = task_description
            
            print(f"更新的任务信息: 名称={task.task_name}, 类型={task.task_type}, 设备ID={task.device_id}")
            
            db.session.commit()
            print(f"任务更新成功，ID: {task_id}")
            flash('任务更新成功', 'success')
            # 使用完整路径进行重定向
            return redirect(url_for('tasks_view.index', _external=True))
        except Exception as e:
            db.session.rollback()
            print(f"任务更新失败，错误: {str(e)}")
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
        # 直接删除任务
        task = Task.query.get_or_404(task_id)
        
        print(f"尝试删除任务ID: {task_id}, 名称: {task.task_name}")
        
        db.session.delete(task)
        db.session.commit()
        
        print(f"任务删除成功")
        flash(f"任务 '{task.task_name}' 已成功删除", 'success')
    except Exception as e:
        db.session.rollback()
        print(f"任务删除失败，错误: {str(e)}")
        flash(f"删除任务失败: {str(e)}", 'danger')
    
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