from flask import Blueprint, render_template, request, flash, redirect, url_for, jsonify
from flask_login import login_required, current_user  # 添加current_user导入
from app.models.edge_devices import EdgeDevice
from app.utils.decorators import admin_required
from app import db
from datetime import datetime

bp = Blueprint('edge_devices', __name__, url_prefix='/edge_devices')

@bp.route('/')
@login_required
def index():
    """边缘设备管理页面"""
    devices = EdgeDevice.query.all()
    # 确保设备列表包含设备编号信息
    return render_template('edge_devices/edge_devices_index.html', devices=devices)

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
        device.secret_key = EdgeDevice.generate_secret_key()
        db.session.commit()
        
        flash('设备认证密钥已更新', 'success')
        return redirect(url_for('edge_devices.device_auth_detail', device_id=device_id))
    except Exception as e:
        flash(f'更新认证密钥失败: {str(e)}', 'error')
        return redirect(url_for('edge_devices.device_auth_detail', device_id=device_id))

# 创建API蓝图
api_bp = Blueprint('edge_devices_api', __name__, url_prefix='/api/edge_devices')

@api_bp.route('/', methods=['POST'])
@login_required
@admin_required
def add_device():
    """添加新的边缘设备"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"code": 400, "message": "无效的请求数据"}), 400
        
        device_name = data.get('device_name')
        ip_address = data.get('ip_address')
        device_id = data.get('device_id')  # 可选参数
        
        if not device_name or not ip_address:
            return jsonify({"code": 400, "message": "设备名称和IP地址不能为空"}), 400
        
        # 检查设备名称是否已存在
        existing_device = EdgeDevice.query.filter_by(device_name=device_name).first()
        if existing_device:
            return jsonify({"code": 400, "message": "设备名称已存在"}), 400
        
        # 检查IP地址是否已存在
        existing_ip = EdgeDevice.query.filter_by(ip_address=ip_address).first()
        if existing_ip:
            return jsonify({"code": 400, "message": "IP地址已被使用"}), 400
        
        # 如果提供了device_id，检查是否已存在
        if device_id:
            existing_device_id = EdgeDevice.query.filter_by(device_id=device_id).first()
            if existing_device_id:
                return jsonify({"code": 400, "message": "设备ID已存在"}), 400
        
        # 创建新设备
        new_device = EdgeDevice(
            device_name=device_name,
            ip_address=ip_address,
            device_id=device_id
        )
        
        db.session.add(new_device)
        db.session.commit()
        
        return jsonify({"code": 200, "message": "设备添加成功", "data": {"id": new_device.id, "device_id": new_device.device_id}}), 200
    
    except Exception as e:
        db.session.rollback()
        return jsonify({"code": 500, "message": f"添加设备失败: {str(e)}"}), 500

@api_bp.route('/<int:device_id>', methods=['PUT'])
@login_required
@admin_required
def update_device(device_id):
    """更新边缘设备信息"""
    try:
        device = EdgeDevice.query.get_or_404(device_id)
        data = request.get_json()
        
        if not data:
            return jsonify({"code": 400, "message": "无效的请求数据"}), 400
        
        device_name = data.get('device_name')
        ip_address = data.get('ip_address')
        new_device_id = data.get('device_id')
        
        if not device_name or not ip_address:
            return jsonify({"code": 400, "message": "设备名称和IP地址不能为空"}), 400
        
        # 检查设备名称是否已存在（排除当前设备）
        existing_device = EdgeDevice.query.filter(
            EdgeDevice.device_name == device_name, 
            EdgeDevice.id != device_id
        ).first()
        if existing_device:
            return jsonify({"code": 400, "message": "设备名称已存在"}), 400
        
        # 检查IP地址是否已存在（排除当前设备）
        existing_ip = EdgeDevice.query.filter(
            EdgeDevice.ip_address == ip_address, 
            EdgeDevice.id != device_id
        ).first()
        if existing_ip:
            return jsonify({"code": 400, "message": "IP地址已被使用"}), 400
        
        # 如果提供了device_id，检查是否已存在（排除当前设备）
        if new_device_id and new_device_id != device.device_id:
            existing_device_id = EdgeDevice.query.filter(
                EdgeDevice.device_id == new_device_id, 
                EdgeDevice.id != device_id
            ).first()
            if existing_device_id:
                return jsonify({"code": 400, "message": "设备ID已存在"}), 400
            device.device_id = new_device_id
        
        # 更新设备信息
        device.device_name = device_name
        device.ip_address = ip_address
        
        db.session.commit()
        
        return jsonify({"code": 200, "message": "设备更新成功"}), 200
    
    except Exception as e:
        db.session.rollback()
        return jsonify({"code": 500, "message": f"更新设备失败: {str(e)}"}), 500

@api_bp.route('/<int:device_id>', methods=['DELETE'])
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

@api_bp.route('/<int:device_id>/regenerate_secret', methods=['POST'])
@login_required
@admin_required
def regenerate_device_secret(device_id):
    """重新生成设备密钥"""
    try:
        device = EdgeDevice.query.get_or_404(device_id)
        
        # 生成新的密钥
        device.secret_key = EdgeDevice.generate_secret_key()
        
        db.session.commit()
        
        return jsonify({"code": 200, "message": "密钥重新生成成功", "data": {"secret_key": device.secret_key}}), 200
    
    except Exception as e:
        db.session.rollback()
        return jsonify({"code": 500, "message": f"重新生成密钥失败: {str(e)}"}), 500

@api_bp.route('/', methods=['GET'])
@login_required
def get_devices():
    """获取所有边缘设备列表，包含设备编号"""
    try:
        devices = EdgeDevice.query.all()
        devices_list = []
        for device in devices:
            devices_list.append({
                'id': device.id,
                'device_id': device.device_id,  # 确保包含设备编号
                'device_name': device.device_name,
                'ip_address': device.ip_address,
                'status': device.status,
                'last_heartbeat': device.last_heartbeat.strftime('%Y-%m-%d %H:%M:%S') if device.last_heartbeat else None
            })
        return jsonify({"code": 200, "message": "获取设备列表成功", "data": devices_list}), 200
    except Exception as e:
        return jsonify({"code": 500, "message": f"获取设备列表失败: {str(e)}"}), 500

@api_bp.route('/<string:device_id>', methods=['GET'])
@login_required
def get_device(device_id):
    """根据设备编号获取设备详情"""
    try:
        device = EdgeDevice.query.filter_by(device_id=device_id).first()
        if not device:
            return jsonify({"code": 404, "message": "设备不存在"}), 404
            
        device_info = {
            'id': device.id,
            'device_id': device.device_id,
            'device_name': device.device_name,
            'ip_address': device.ip_address,
            'status': device.status,
            'last_heartbeat': device.last_heartbeat.strftime('%Y-%m-%d %H:%M:%S') if device.last_heartbeat else None,
            'secret_key': device.secret_key if current_user.is_admin else None  # 仅管理员可见密钥
        }
        return jsonify({"code": 200, "message": "获取设备详情成功", "data": device_info}), 200
    except Exception as e:
        return jsonify({"code": 500, "message": f"获取设备详情失败: {str(e)}"}), 500

@api_bp.route('/test', methods=['GET'])
def test_api():
    """测试API是否正常工作"""
    from datetime import datetime
    return jsonify({"code": 200, "message": "API工作正常", "time": str(datetime.now())}), 200