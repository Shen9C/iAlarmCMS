from flask import Blueprint, render_template, request, flash, redirect, url_for, session, jsonify
from flask_login import login_required
from app.models.edge_devices import EdgeDevice
from app.utils.auth_helper import admin_required
from app.utils.machine_auth import get_ssl_context
from app import db
import logging
import traceback
from datetime import datetime

bp = Blueprint('edge_devices_mngt', __name__, url_prefix='/edge_devices_mngt')

@bp.route('/')
@login_required
def index():
    """边缘设备管理页面"""
    try:
        logging.debug("正在访问边缘设备管理页面(routes/edge_devices.py)")
        
        # 检查URL参数 - 如果没有edit参数，则清除会话中的编辑数据
        if 'edit' not in request.args and 'edit_device' in session:
            session.pop('edit_device')
        
        # 记录分页参数
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 15, type=int)
        logging.debug(f"分页参数: page={page}, per_page={per_page}")
        
        # 获取筛选参数
        device_name = request.args.get('device_name', '')
        ip_address = request.args.get('ip_address', '')
        status = request.args.get('status', '')
        
        # 构建查询
        query = EdgeDevice.query
        
        # 根据筛选参数进行过滤
        if device_name:
            query = query.filter(EdgeDevice.device_name.like(f'%{device_name}%'))
        if ip_address:
            query = query.filter(EdgeDevice.ip_address.like(f'%{ip_address}%'))
        if status in ['在线', '离线']:
            query = query.filter(EdgeDevice.status == status)
        
        # 记录查询结果数量
        devices_count = query.count()
        logging.debug(f"设备总数: {devices_count}")
        
        # 分页
        pagination = query.paginate(
            page=page, per_page=per_page, error_out=False
        )
        
        # 获取当前时间，用于计算设备状态
        current_time = datetime.now()
        logging.debug(f"当前时间: {current_time}")
        
        # 记录传递给模板的参数
        logging.debug(f"传递给模板的设备数量: {len(pagination.items)}")
        
        # 尝试渲染模板
        logging.debug("开始渲染模板...")
        result = render_template('edge_devices/edge_devices_index.html', 
                           devices=pagination.items,
                           pagination=pagination,
                           current_time=current_time,
                           filter_params={
                               'device_name': device_name,
                               'ip_address': ip_address,
                               'status': status
                           })
        logging.debug("模板渲染成功")
        return result
        
    except Exception as e:
        logging.error(f"访问边缘设备管理页面失败: {str(e)}")
        logging.error(traceback.format_exc())
        flash(f"加载边缘设备管理页面失败: {str(e)}", "error")
        return render_template('error.html', error_message=str(e), stack_trace=traceback.format_exc()), 500

@bp.route('/detail/<string:device_id>')
@login_required
def device_detail(device_id):
    """边缘设备详情页面，展示包括设备编号在内的完整信息"""
    try:
        device = EdgeDevice.query.filter_by(device_id=device_id).first_or_404()
        return render_template('edge_devices/device_detail.html', device=device)
    except Exception as e:
        flash(f'加载设备详情失败: {str(e)}', 'error')
        return redirect(url_for('edge_devices_mngt.index'))

@bp.route('/edit/<int:device_id>')
@login_required
def edit_device(device_id):
    """边缘设备编辑页面"""
    try:
        device = EdgeDevice.query.get_or_404(device_id)
        return render_template('edge_devices/edit_device.html', device=device)
    except Exception as e:
        flash(f'加载编辑页面失败: {str(e)}', 'error')
        return redirect(url_for('edge_devices_mngt.index'))

@bp.route('/delete_device/<int:device_id>', methods=['POST'])
@login_required
@admin_required
def delete_device(device_id):
    """删除边缘设备"""
    try:
        device = EdgeDevice.query.get_or_404(device_id)
        device_name = device.device_name
        
        db.session.delete(device)
        db.session.commit()
        
        flash(f'设备 {device_name} 已成功删除', 'success')
        return redirect(url_for('edge_devices_mngt.index'))
    except Exception as e:
        db.session.rollback()
        flash(f'删除设备失败: {str(e)}', 'error')
        return redirect(url_for('edge_devices_mngt.index'))

@bp.route('/update_device/<int:device_id>', methods=['POST'])
@login_required
@admin_required
def update_device(device_id):
    """更新边缘设备信息"""
    try:
        device = EdgeDevice.query.get_or_404(device_id)
        
        device_name = request.form.get('device_name')
        ip_address = request.form.get('ip_address')
        new_device_id = request.form.get('device_id')
        
        if not device_name or not ip_address:
            flash('设备名称和IP地址不能为空', 'error')
            return redirect(url_for('edge_devices_mngt.edit_device', device_id=device_id))
        
        # 检查设备名称是否已存在（排除当前设备）
        existing_device = EdgeDevice.query.filter(
            EdgeDevice.device_name == device_name, 
            EdgeDevice.id != device_id
        ).first()
        if existing_device:
            flash('设备名称已存在', 'error')
            return redirect(url_for('edge_devices_mngt.edit_device', device_id=device_id))
        
        # 检查IP地址是否已存在（排除当前设备）
        existing_ip = EdgeDevice.query.filter(
            EdgeDevice.ip_address == ip_address, 
            EdgeDevice.id != device_id
        ).first()
        if existing_ip:
            flash('IP地址已被使用', 'error')
            return redirect(url_for('edge_devices_mngt.edit_device', device_id=device_id))
        
        # 如果提供了device_id，检查是否已存在（排除当前设备）
        if new_device_id and new_device_id != device.device_id:
            existing_device_id = EdgeDevice.query.filter(
                EdgeDevice.device_id == new_device_id, 
                EdgeDevice.id != device_id
            ).first()
            if existing_device_id:
                flash('设备ID已存在', 'error')
                return redirect(url_for('edge_devices_mngt.edit_device', device_id=device_id))
            device.device_id = new_device_id
        
        # 更新设备信息
        device.device_name = device_name
        device.ip_address = ip_address
        
        db.session.commit()
        
        flash('设备信息已更新', 'success')
        return redirect(url_for('edge_devices_mngt.index'))
    except Exception as e:
        db.session.rollback()
        flash(f'更新设备失败: {str(e)}', 'error')
        return redirect(url_for('edge_devices_mngt.edit_device', device_id=device_id))

@bp.route('/add_device', methods=['POST'])
@login_required
@admin_required
def add_device():
    """添加新的边缘设备"""
    try:
        device_name = request.form.get('device_name')
        ip_address = request.form.get('ip_address')
        device_id = request.form.get('device_id')  # 可选参数
        
        if not device_name or not ip_address:
            flash('设备名称和IP地址不能为空', 'error')
            return redirect(url_for('edge_devices_mngt.index'))
        
        # 检查设备名称是否已存在
        existing_device = EdgeDevice.query.filter_by(device_name=device_name).first()
        if existing_device:
            flash('设备名称已存在', 'error')
            return redirect(url_for('edge_devices_mngt.index'))
        
        # 检查IP地址是否已存在
        existing_ip = EdgeDevice.query.filter_by(ip_address=ip_address).first()
        if existing_ip:
            flash('IP地址已被使用', 'error')
            return redirect(url_for('edge_devices_mngt.index'))
        
        # 如果提供了device_id，检查是否已存在
        if device_id:
            existing_device_id = EdgeDevice.query.filter_by(device_id=device_id).first()
            if existing_device_id:
                flash('设备ID已存在', 'error')
                return redirect(url_for('edge_devices_mngt.index'))
        
        # 创建新设备
        new_device = EdgeDevice(
            device_name=device_name,
            ip_address=ip_address,
            device_id=device_id
        )
        
        db.session.add(new_device)
        db.session.commit()
        
        flash('设备添加成功', 'success')
        return redirect(url_for('edge_devices_mngt.index'))
    except Exception as e:
        db.session.rollback()
        flash(f'添加设备失败: {str(e)}', 'error')
        return redirect(url_for('edge_devices_mngt.index'))

# 新增API接口，直接注册到原有bp蓝图下
@bp.route('/api/edge_devices/<int:device_id>/regenerate_keys', methods=['POST'])
@login_required
@admin_required
def regenerate_keys(device_id):
    try:
        device = EdgeDevice.query.get_or_404(device_id)
        device.secret_key = EdgeDevice.generate_secret_key()
        db.session.commit()
        return jsonify({'code': 200, 'message': '密钥已重新生成', 'secret_key': device.secret_key})
    except Exception as e:
        db.session.rollback()
        return jsonify({'code': 500, 'message': f'密钥重生成失败: {str(e)}'}), 500 