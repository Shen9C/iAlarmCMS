from flask import Blueprint, render_template, request, flash, redirect, url_for, jsonify
from flask_login import login_required
from app.models.edge_devices import EdgeDevice
from app.utils.decorators import admin_required
from app import db
import secrets
import string

bp = Blueprint('edge_devices', __name__, url_prefix='/edge_devices')

@bp.route('/')
@login_required
def index():
    """边缘设备管理页面"""
    devices = EdgeDevice.query.all()
    return render_template('edge_devices/edge_devices_index.html', devices=devices)

@bp.route('/auth/<int:device_id>')
@login_required
@admin_required
def device_auth_detail(device_id):
    """边缘设备认证详情页面"""
    try:
        device = EdgeDevice.query.get_or_404(device_id)
        return render_template('edge_devices/auth_detail.html', device=device)
    except Exception as e:
        flash(f'加载设备认证信息失败: {str(e)}', 'error')
        return redirect(url_for('edge_devices.index'))

@bp.route('/auth/<int:device_id>/regenerate', methods=['POST'])
@login_required
@admin_required
def regenerate_device_auth(device_id):
    """重新生成设备认证密钥"""
    try:
        device = EdgeDevice.query.get_or_404(device_id)
        device.regenerate_auth_keys()
        db.session.commit()
        
        flash('设备认证密钥已更新', 'success')
        return redirect(url_for('edge_devices.device_auth_detail', device_id=device_id))
    except Exception as e:
        flash(f'更新认证密钥失败: {str(e)}', 'error')
        return redirect(url_for('edge_devices.device_auth_detail', device_id=device_id))

# 添加API路由处理添加、编辑和删除设备的功能
from flask import Blueprint, render_template, request, flash, redirect, url_for, jsonify
from flask_login import login_required
from app.models.edge_devices import EdgeDevice
from app.utils.decorators import admin_required
from app import db
import secrets
import string

# 创建API蓝图
api_bp = Blueprint('edge_devices_api', __name__, url_prefix='/api/edge_devices')

@api_bp.route('/api', methods=['POST'])
@login_required
@admin_required
def add_device():
    """添加新的边缘设备"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"code": 400, "message": "无效的请求数据"}), 400
        
        name = data.get('name')
        ip_address = data.get('ip_address')
        
        if not name or not ip_address:
            return jsonify({"code": 400, "message": "设备名称和IP地址不能为空"}), 400
        
        # 检查设备名称是否已存在
        existing_device = EdgeDevice.query.filter_by(name=name).first()
        if existing_device:
            return jsonify({"code": 400, "message": "设备名称已存在"}), 400
        
        # 检查IP地址是否已存在
        existing_ip = EdgeDevice.query.filter_by(ip_address=ip_address).first()
        if existing_ip:
            return jsonify({"code": 400, "message": "IP地址已被使用"}), 400
        
        # 生成访问密钥和密钥
        access_key = ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(20))
        secret_key = ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(40))
        
        # 创建新设备
        new_device = EdgeDevice(
            name=name,
            ip_address=ip_address,
            access_key=access_key,
            secret_key=secret_key
        )
        
        db.session.add(new_device)
        db.session.commit()
        
        return jsonify({"code": 200, "message": "设备添加成功", "data": {"id": new_device.id}}), 200
    
    except Exception as e:
        db.session.rollback()
        return jsonify({"code": 500, "message": f"添加设备失败: {str(e)}"}), 500

@bp.route('/api/edge_devices/<int:device_id>', methods=['PUT'])
@login_required
@admin_required
def update_device(device_id):
    """更新边缘设备信息"""
    try:
        device = EdgeDevice.query.get_or_404(device_id)
        data = request.get_json()
        
        if not data:
            return jsonify({"code": 400, "message": "无效的请求数据"}), 400
        
        name = data.get('name')
        ip_address = data.get('ip_address')
        
        if not name or not ip_address:
            return jsonify({"code": 400, "message": "设备名称和IP地址不能为空"}), 400
        
        # 检查设备名称是否已存在（排除当前设备）
        existing_device = EdgeDevice.query.filter(EdgeDevice.name == name, EdgeDevice.id != device_id).first()
        if existing_device:
            return jsonify({"code": 400, "message": "设备名称已存在"}), 400
        
        # 检查IP地址是否已存在（排除当前设备）
        existing_ip = EdgeDevice.query.filter(EdgeDevice.ip_address == ip_address, EdgeDevice.id != device_id).first()
        if existing_ip:
            return jsonify({"code": 400, "message": "IP地址已被使用"}), 400
        
        # 更新设备信息
        device.name = name
        device.ip_address = ip_address
        
        db.session.commit()
        
        return jsonify({"code": 200, "message": "设备更新成功"}), 200
    
    except Exception as e:
        db.session.rollback()
        return jsonify({"code": 500, "message": f"更新设备失败: {str(e)}"}), 500

@bp.route('/api/edge_devices/<int:device_id>', methods=['DELETE'])
@login_required
@admin_required
def delete_device(device_id):
    """删除边缘设备"""
    try:
        device = EdgeDevice.query.get_or_404(device_id)
        
        db.session.delete(device)
        db.session.commit()
        
        return jsonify({"code": 200, "message": "设备删除成功"}), 200
    
    except Exception as e:
        db.session.rollback()
        return jsonify({"code": 500, "message": f"删除设备失败: {str(e)}"}), 500

@bp.route('/api/edge_devices/<int:device_id>/regenerate_keys', methods=['POST'])
@login_required
@admin_required
def regenerate_device_keys(device_id):
    """重新生成设备访问密钥和密钥"""
    try:
        device = EdgeDevice.query.get_or_404(device_id)
        
        # 生成新的访问密钥和密钥
        device.access_key = ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(20))
        device.secret_key = ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(40))
        
        db.session.commit()
        
        return jsonify({"code": 200, "message": "密钥重新生成成功"}), 200
    
    except Exception as e:
        db.session.rollback()
        return jsonify({"code": 500, "message": f"重新生成密钥失败: {str(e)}"}), 500