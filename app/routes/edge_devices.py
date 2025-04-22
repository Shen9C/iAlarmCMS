from flask import Blueprint, render_template, request, flash, redirect, url_for, session
from flask_login import login_required
from app.models.edge_devices import EdgeDevice
from app.utils.decorators import admin_required
from app import db

bp = Blueprint('edge_devices', __name__, url_prefix='/edge_devices')

@bp.route('/')
@login_required
def index():
    """边缘设备管理页面"""
    # 检查URL参数 - 如果没有edit参数，则清除会话中的编辑数据
    if 'edit' not in request.args and 'edit_device' in session:
        session.pop('edit_device')
        
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)
    
    # 构建查询
    query = EdgeDevice.query
    
    # 分页
    pagination = query.paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    return render_template('edge_devices/edge_devices_index.html', 
                           devices=pagination.items,
                           pagination=pagination)

@bp.route('/detail/<string:device_id>')
@login_required
def device_detail(device_id):
    """边缘设备详情页面，展示包括设备编号在内的完整信息"""
    try:
        device = EdgeDevice.query.filter_by(device_id=device_id).first_or_404()
        return render_template('edge_devices/device_detail.html', device=device)
    except Exception as e:
        flash(f'加载设备详情失败: {str(e)}', 'error')
        return redirect(url_for('edge_devices.index'))

@bp.route('/edit/<int:device_id>')
@login_required
def edit_device(device_id):
    """边缘设备编辑页面"""
    try:
        device = EdgeDevice.query.get_or_404(device_id)
        return render_template('edge_devices/edit_device.html', device=device)
    except Exception as e:
        flash(f'加载编辑页面失败: {str(e)}', 'error')
        return redirect(url_for('edge_devices.index')) 