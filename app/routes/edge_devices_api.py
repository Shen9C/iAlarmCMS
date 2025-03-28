from flask import Blueprint, jsonify, request
from flask_login import login_required, current_user
from app.models.edge_devices import EdgeDevice
from app.utils.decorators import admin_required, device_auth_required
from app import db
from datetime import datetime
import logging

logger = logging.getLogger(__name__)
bp = Blueprint('edge_device_api', __name__, url_prefix='/api/edge_devices')

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
@admin_required
def add_edge_device():
    """添加边缘设备"""
    try:
        data = request.get_json()
        name = data.get('name')
        ip_address = data.get('ip_address')
        
        # 验证必填字段
        if not name or not ip_address:
            return jsonify({
                'code': 400,
                'message': '设备名称和IP地址不能为空'
            }), 400
        
        # 检查设备名称是否已存在
        if EdgeDevice.query.filter_by(name=name).first():
            return jsonify({
                'code': 400,
                'message': f'设备名称 {name} 已存在'
            }), 400
        
        # 创建新设备
        device = EdgeDevice(name=name, ip_address=ip_address)
        db.session.add(device)
        db.session.commit()
        
        return jsonify({
            'code': 200,
            'message': '添加成功',
            'data': device.to_dict()
        })
    except Exception as e:
        db.session.rollback()
        logger.error(f"添加边缘设备失败: {str(e)}")
        return jsonify({
            'code': 500,
            'message': f'添加边缘设备失败: {str(e)}'
        }), 500

@bp.route('/<int:device_id>', methods=['PUT'])
@login_required
@admin_required
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
@admin_required
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
@admin_required
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
@device_auth_required
def verify_device_auth():
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
@admin_required
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