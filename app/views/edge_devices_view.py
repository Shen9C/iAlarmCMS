from flask import Blueprint, render_template, request, flash, redirect, url_for
from flask_login import login_required
from app.models.edge_devices import EdgeDevice
from app.utils.decorators import admin_required
from app import db

bp = Blueprint('edge_devices', __name__)

@bp.route('/edge_devices')
@login_required
def index():
    """边缘设备管理页面"""
    devices = EdgeDevice.query.all()
    return render_template('edge_devices/edge_devices_index.html', devices=devices)

@bp.route('/edge_devices/auth/<int:device_id>')
@login_required
@admin_required
def device_auth_detail(device_id):
    """边缘设备认证详情页面"""
    try:
        device = EdgeDevice.query.get_or_404(device_id)
        return render_template('edge_devices/auth_detail.html',
                             device=device,
                             user_token=request.args.get('user_token'))
    except Exception as e:
        flash(f'加载设备认证信息失败: {str(e)}', 'error')
        return redirect(url_for('edge_device.index',
                              user_token=request.args.get('user_token')))

@bp.route('/edge_devices/auth/<int:device_id>/regenerate', methods=['POST'])
@login_required
@admin_required
def regenerate_device_auth(device_id):
    """重新生成设备认证密钥"""
    try:
        device = EdgeDevice.query.get_or_404(device_id)
        device.regenerate_auth_keys()
        db.session.commit()
        
        flash('设备认证密钥已更新', 'success')
        return redirect(url_for('edge_device.device_auth_detail',
                              device_id=device_id,
                              user_token=request.args.get('user_token')))
    except Exception as e:
        flash(f'更新认证密钥失败: {str(e)}', 'error')
        return redirect(url_for('edge_device.device_auth_detail',
                              device_id=device_id,
                              user_token=request.args.get('user_token')))