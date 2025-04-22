#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
边缘设备API服务器
独立运行在不同端口(默认5566)，专门用于处理边缘设备的认证和告警上报请求
避免被Web应用的身份验证中间件拦截
"""

from flask import Flask, Blueprint, jsonify, request, current_app
from app import create_app, db
from app.models.edge_devices import EdgeDevice
from app.models.alarms import Alarm
import jwt
import uuid
import logging
from datetime import datetime, timedelta
from functools import wraps

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 创建一个新的Flask应用实例，使用相同的应用配置
app = create_app()

# 创建一个仅包含设备API路由的Blueprint
device_api_server = Blueprint('device_api_server', __name__, url_prefix='/api/devices')

# 设备认证装饰器
def device_auth_required(f):
    """验证设备认证的装饰器"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # 从请求中获取访问密钥和密钥
        device_id = request.json.get('device_id')
        secret_key = request.json.get('secret_key')
        
        if not device_id or not secret_key:
            return jsonify({"code": 401, "message": "缺少认证信息"}), 401
        
        # 查找设备
        device = EdgeDevice.query.filter_by(device_id=device_id).first()
        if not device:
            logger.warning(f"设备认证失败: 无效的设备ID {device_id}")
            return jsonify({"code": 401, "message": "无效的设备ID"}), 401
        
        # 验证密钥
        if device.secret_key != secret_key:
            logger.warning(f"设备认证失败: 无效的密钥 (设备ID: {device_id})")
            return jsonify({"code": 401, "message": "无效的密钥"}), 401
            
        # 将设备信息添加到请求上下文
        request.current_device = device
        
        return f(*args, **kwargs)
    return decorated_function

# 设备token认证装饰器
def device_token_auth_required(f):
    """验证设备token认证的装饰器"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # 从请求头中获取访问令牌
        auth_header = request.headers.get('Authorization')
        
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({"code": 401, "message": "缺少认证信息"}), 401
        
        token = auth_header.split(' ')[1]
        
        try:
            # 解码JWT令牌
            payload = jwt.decode(token, current_app.config['SECRET_KEY'], algorithms=['HS256'])
            device_id = payload.get('device_id')
            
            # 查找设备
            device = EdgeDevice.query.filter_by(device_id=device_id).first()
            if not device:
                return jsonify({"code": 401, "message": "无效的设备ID"}), 401
            
            # 检查令牌是否过期
            if datetime.fromtimestamp(payload.get('exp')) < datetime.now():
                return jsonify({"code": 401, "message": "令牌已过期"}), 401
            
            # 将设备信息添加到请求上下文
            request.current_device = device
            
            return f(*args, **kwargs)
        except jwt.ExpiredSignatureError:
            return jsonify({"code": 401, "message": "令牌已过期"}), 401
        except jwt.InvalidTokenError:
            return jsonify({"code": 401, "message": "无效的令牌"}), 401
        except Exception as e:
            logger.error(f"设备令牌认证失败: {str(e)}")
            return jsonify({"code": 500, "message": f"认证失败: {str(e)}"}), 500
            
    return decorated_function

# 设备认证获取Token API
@device_api_server.route('/auth/token', methods=['POST'])
def get_device_token():
    """边缘设备通过设备ID和密钥获取访问令牌"""
    try:
        # 从请求中获取设备ID和密钥
        data = request.get_json()
        if not data:
            return jsonify({"code": 400, "message": "无效的请求数据"}), 400
        
        device_id = data.get('device_id')
        secret_key = data.get('secret_key')
        
        if not device_id or not secret_key:
            return jsonify({"code": 400, "message": "设备ID和密钥不能为空"}), 400
        
        # 查找设备
        device = EdgeDevice.query.filter_by(device_id=device_id).first()
        if not device:
            logger.warning(f"设备认证失败: 无效的设备ID {device_id}")
            return jsonify({"code": 401, "message": "无效的设备ID"}), 401
        
        # 验证密钥
        if device.secret_key != secret_key:
            logger.warning(f"设备认证失败: 无效的密钥 (设备ID: {device_id})")
            return jsonify({"code": 401, "message": "无效的密钥"}), 401
        
        # 更新设备最后一次登录时间和状态
        device.last_auth_time = datetime.now()
        device.status = '在线'
        db.session.commit()
        logger.info(f"设备 {device.device_name} (ID: {device.id}) 认证成功，已更新最后登录时间: {device.last_auth_time}")
        
        # 生成JWT令牌，有效期为24小时
        payload = {
            'device_id': device.device_id,
            'exp': datetime.now() + timedelta(hours=24),
            'iat': datetime.now(),
            'jti': str(uuid.uuid4())
        }
        
        token = jwt.encode(payload, current_app.config['SECRET_KEY'], algorithm='HS256')
        
        return jsonify({
            'code': 200,
            'message': '认证成功',
            'data': {
                'token': token,
                'expires_in': 86400,  # 24小时的秒数
                'device_id': device.device_id,
                'device_name': device.device_name
            }
        })
    except Exception as e:
        logger.error(f"获取设备令牌失败: {str(e)}")
        return jsonify({
            'code': 500,
            'message': f'获取令牌失败: {str(e)}'
        }), 500

# 上传告警API
@device_api_server.route('/alarms', methods=['POST'])
@device_token_auth_required
def create_alarm():
    """边缘设备上传告警信息"""
    try:
        # 从请求中获取告警数据
        data = request.get_json()
        if not data:
            return jsonify({"code": 400, "message": "无效的请求数据"}), 400
        
        device = request.current_device
        
        # 准备告警数据
        alarm_data = {
            'device_id': device.device_id,
            'device_name': device.device_name,
            'alarm_time': datetime.now()
        }
        
        # 从请求中提取必要的字段
        required_fields = ['alarm_type', 'alarm_code']
        for field in required_fields:
            if field not in data:
                return jsonify({"code": 400, "message": f"缺少必要的字段: {field}"}), 400
            alarm_data[field] = data[field]
        
        # 提取可选字段
        optional_fields = ['well_code', 'well_name', 'camera_ip', 'alarm_image', 'description', 'alarm_suffix_code']
        for field in optional_fields:
            if field in data:
                alarm_data[field] = data[field]
        
        # 创建或更新告警
        alarm = Alarm.create_or_update(alarm_data)
        
        logger.info(f"设备 {device.device_name} (ID: {device.device_id}) 上传告警成功: {alarm.alarm_code}")
        
        return jsonify({
            'code': 200,
            'message': '告警上报成功',
            'data': {
                'alarm_id': alarm.id,
                'alarm_code': alarm.alarm_code
            }
        })
    except ValueError as ve:
        # 处理特定的验证错误
        logger.error(f"告警上传失败 (验证错误): {str(ve)}")
        return jsonify({
            'code': 400,
            'message': str(ve)
        }), 400
    except Exception as e:
        logger.error(f"告警上报失败: {str(e)}")
        return jsonify({
            'code': 500,
            'message': f'告警上报失败: {str(e)}'
        }), 500

# 设备状态检查API
@device_api_server.route('/status', methods=['GET'])
def api_status():
    """API服务器状态检查"""
    return jsonify({
        'code': 200,
        'message': '边缘设备API服务器正常运行',
        'time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    })

# 注册Blueprint
app.register_blueprint(device_api_server)

# 删除全局请求拦截器，让设备API可以直接访问
if hasattr(app, 'before_request_funcs') and app.before_request_funcs and None in app.before_request_funcs:
    # 尝试移除全局请求拦截器
    for i, func in enumerate(app.before_request_funcs[None]):
        if func.__name__ == 'check_auth':
            app.before_request_funcs[None].pop(i)
            logger.info("已移除全局认证中间件")
            break

if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='边缘设备API服务器')
    parser.add_argument('--host', default='0.0.0.0', help='监听地址')
    parser.add_argument('--port', type=int, default=5566, help='监听端口')
    parser.add_argument('--debug', action='store_true', help='是否启用调试模式')
    
    args = parser.parse_args()
    
    logger.info(f"边缘设备API服务器正在启动，监听 {args.host}:{args.port}")
    app.run(host=args.host, port=args.port, debug=args.debug) 