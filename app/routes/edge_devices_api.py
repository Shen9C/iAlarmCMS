from flask import Blueprint, request, jsonify
from flask_login import login_required
from app.models.edge_devices import EdgeDevice
from app.utils.decorators import admin_required  # 确保这个导入存在
# 添加 device_auth_required 装饰器的导入
from app.utils.decorators import device_auth_required  # 添加这行导入
from app import db
import secrets
import string

from datetime import datetime
import logging

logger = logging.getLogger(__name__)
# 创建API蓝图，URL前缀为 /api/edge_devices
bp = Blueprint('edge_devices_api', __name__, url_prefix='/api/edge_devices')

@bp.route('', methods=['GET'])
@login_required
def get_edge_devices():
    """获取所有边缘设备"""
    try:
        devices = EdgeDevice.query.all()
        return jsonify({
            'code': 200,
            'message': '获取成功',
            'data': [device.to_dict() for device in devices]
        })
    except Exception as e:
        logger.error(f"获取边缘设备列表失败: {str(e)}")
        return jsonify({
            'code': 500,
            'message': f'获取边缘设备列表失败: {str(e)}'
        }), 500

@bp.route('', methods=['POST'])
@login_required
# 移除 @admin_required 装饰器
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

@bp.route('/<int:device_id>', methods=['PUT'])
@login_required
def update_edge_device(device_id):
    """更新边缘设备"""
    try:
        device = EdgeDevice.query.get(device_id)
        if not device:
            return jsonify({
                'code': 404,
                'message': f'设备ID {device_id} 不存在'
            }), 404
        
        data = request.get_json()
        name = data.get('name')
        ip_address = data.get('ip_address')
        
        # 验证必填字段
        if not name or not ip_address:
            return jsonify({
                'code': 400,
                'message': '设备名称和IP地址不能为空'
            }), 400
        
        # 检查设备名称是否已存在（排除当前设备）
        existing_device = EdgeDevice.query.filter_by(name=name).first()
        if existing_device and existing_device.id != device_id:
            return jsonify({
                'code': 400,
                'message': f'设备名称 {name} 已存在'
            }), 400
        
        # 更新设备信息
        device.name = name
        device.ip_address = ip_address
        
        # 如果请求中包含了重新生成密钥的标志
        if data.get('regenerate_keys'):
            device.access_key = EdgeDevice.generate_access_key()
            device.secret_key = EdgeDevice.generate_secret_key()
        
        db.session.commit()
        
        return jsonify({
            'code': 200,
            'message': '更新成功',
            'data': device.to_dict()
        })
    except Exception as e:
        db.session.rollback()
        logger.error(f"更新边缘设备失败: {str(e)}")
        return jsonify({
            'code': 500,
            'message': f'更新边缘设备失败: {str(e)}'
        }), 500

@bp.route('/<int:device_id>', methods=['DELETE'])
@login_required
def delete_edge_device(device_id):
    """删除边缘设备"""
    try:
        device = EdgeDevice.query.get(device_id)
        if not device:
            return jsonify({
                'code': 404,
                'message': f'设备ID {device_id} 不存在'
            }), 404
        
        db.session.delete(device)
        db.session.commit()
        
        return jsonify({
            'code': 200,
            'message': '删除成功'
        })
    except Exception as e:
        db.session.rollback()
        logger.error(f"删除边缘设备失败: {str(e)}")
        return jsonify({
            'code': 500,
            'message': f'删除边缘设备失败: {str(e)}'
        }), 500

@bp.route('/<int:device_id>/regenerate_keys', methods=['POST'])
@login_required
def regenerate_keys(device_id):
    """重新生成设备密钥"""
    try:
        device = EdgeDevice.query.get(device_id)
        if not device:
            return jsonify({
                'code': 404,
                'message': f'设备ID {device_id} 不存在'
            }), 404
        
        device.access_key = EdgeDevice.generate_access_key()
        device.secret_key = EdgeDevice.generate_secret_key()
        db.session.commit()
        
        return jsonify({
            'code': 200,
            'message': '密钥重新生成成功',
            'data': {
                'access_key': device.access_key,
                'secret_key': device.secret_key
            }
        })
    except Exception as e:
        db.session.rollback()
        logger.error(f"重新生成设备密钥失败: {str(e)}")
        return jsonify({
            'code': 500,
            'message': f'重新生成设备密钥失败: {str(e)}'
        }), 500

@bp.route('/auth/verify', methods=['POST'])
# 在文件的第196行附近，有一个使用了 device_auth_required 装饰器的函数
@device_auth_required  # 现在这个装饰器已经被正确导入
def some_function():
    """验证边缘设备认证"""
    try:
        device_id = request.headers.get('X-Device-ID')
        device = EdgeDevice.query.get(device_id)
        if not device:
            return jsonify({
                'code': 404,
                'message': '设备不存在'
            }), 404

        return jsonify({
            'code': 200,
            'message': '认证成功',
            'data': {
                'device_id': device_id,
                'device_name': device.name,
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
        })
    except Exception as e:
        logger.error(f"设备认证验证失败: {str(e)}")
        return jsonify({
            'code': 500,
            'message': f'认证验证失败: {str(e)}'
        }), 500

@bp.route('/auth/status/<int:device_id>', methods=['GET'])
@login_required
def get_device_auth_status(device_id):
    """获取边缘设备认证状态"""
    try:
        device = EdgeDevice.query.get(device_id)
        if not device:
            return jsonify({
                'code': 404,
                'message': '设备不存在'
            }), 404

        return jsonify({
            'code': 200,
            'message': '获取成功',
            'data': {
                'device_id': device.id,
                'device_name': device.name,
                'access_key': device.access_key,
                'auth_status': 'active',
                'last_auth_time': device.last_auth_time.strftime('%Y-%m-%d %H:%M:%S') if device.last_auth_time else None
            }
        })
    except Exception as e:
        logger.error(f"获取设备认证状态失败: {str(e)}")
        return jsonify({
            'code': 500,
            'message': f'获取认证状态失败: {str(e)}'
        }), 500