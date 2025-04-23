#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
边缘设备API服务器
独立运行在不同端口(默认5566)，专门用于处理边缘设备的认证和告警上报请求
避免被Web应用的身份验证中间件拦截
"""

from flask import Flask, Blueprint, jsonify, request
import os
import sys
from pathlib import Path
import importlib

# 将项目根目录添加到系统路径
project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root))

from app import db
from app.models.edge_devices import EdgeDevice
from app.models.alarms import Alarm
from app.utils.yaml_config_loader import Config, config
import jwt
import uuid
import logging
from datetime import datetime, timedelta
from functools import wraps

# 配置日志
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 创建一个仅包含设备API路由的Blueprint，避免命名冲突
device_api_server = Blueprint('device_api_server', __name__, url_prefix='/api/edge_devices')

# 全局Flask应用实例仅在直接运行此文件时创建
# 当此模块被导入时不创建应用实例，避免与create_api_app冲突
standalone_app = None

# 设备认证装饰器
def device_auth_required(f):
    """验证设备认证的装饰器"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # 从请求中获取访问密钥和密钥
        device_id = request.json.get('device_id')
        secret_key = request.json.get('secret_key')
        
        if not device_id or not secret_key:
            logger.warning("缺少认证信息: 未提供设备ID或密钥")
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
        
        # 更新设备最后一次登录时间和状态
        device.last_auth_time = datetime.now()
        device.status = '在线'
        db.session.commit()
        logger.info(f"设备 {device.device_name} (ID: {device.id}) 认证成功，已更新最后登录时间")
            
        # 将设备信息添加到请求上下文
        request.current_device = device
        
        return f(*args, **kwargs)
    return decorated_function

# 设备token认证装饰器 - 仅用于Token认证方式
def device_token_auth_required(f):
    """验证设备token认证的装饰器"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # 从请求头中获取访问令牌
        auth_header = request.headers.get('Authorization')
        
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({"code": 401, "message": "缺少认证信息"}), 401
        
        token = auth_header.split(' ')[1]
        logger.debug(f"收到的令牌: {token}")
        
        try:
            # 尝试解码令牌 - 简化为直接调用jwt库解码
            try:
                # 获取密钥 - 这里不应该使用request.app
                # 可以从当前应用或全局配置获取secret_key
                from flask import current_app
                try:
                    # 尝试从当前应用获取密钥
                    secret_key = current_app.config.get('SECRET_KEY')
                except RuntimeError:
                    # 如果不在应用上下文中，使用配置中的密钥
                    secret_key = config.secret_key
                
                payload = jwt.decode(
                    token, 
                    secret_key, 
                    algorithms=['HS256'],
                    options={
                        "verify_signature": True,
                        "verify_exp": True,
                    }
                )
                logger.debug(f"令牌解码成功: {payload}")
                
                # 从载荷中提取设备ID
                device_id = payload.get('device_id')
                
                if not device_id:
                    logger.warning("令牌中缺少device_id字段")
                    return jsonify({"code": 401, "message": "无效的令牌格式：缺少device_id字段"}), 401
            except jwt.ExpiredSignatureError:
                logger.warning("令牌已过期")
                return jsonify({"code": 401, "message": "令牌已过期"}), 401
            except jwt.InvalidTokenError as e:
                logger.warning(f"无效的令牌: {str(e)}")
                return jsonify({"code": 401, "message": f"无效的令牌: {str(e)}"}), 401
                    
            # 查找设备
            device = EdgeDevice.query.filter_by(device_id=device_id).first()
            if not device:
                logger.warning(f"无效的设备ID: {device_id}")
                return jsonify({"code": 401, "message": "无效的设备ID"}), 401
            
            # 更新设备最后一次登录时间和状态
            device.last_auth_time = datetime.now()
            device.status = '在线'
            db.session.commit()
            
            # 将设备信息添加到请求上下文
            request.current_device = device
            logger.debug(f"令牌验证成功，设备ID: {device_id}")
            
            return f(*args, **kwargs)
                
        except Exception as e:
            logger.error(f"设备令牌认证失败: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
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
        logger.info(f"设备 {device.device_name} (ID: {device.device_id}) 认证成功，已更新最后登录时间")
        
        # 生成JWT令牌，有效期为24小时
        current_time = datetime.now()
        exp_time = current_time + timedelta(hours=24)
        
        # 使用简单的payload格式
        payload = {
            'device_id': device.device_id,
            'exp': int(exp_time.timestamp()),
            'iat': int(current_time.timestamp()),
            'jti': str(uuid.uuid4())
        }
        
        # 记录用于调试的信息
        logger.debug(f"生成令牌的payload: {payload}")
        
        # 获取密钥 - 这里不应该使用request.app
        # 可以从当前应用或全局配置获取secret_key
        from flask import current_app
        try:
            # 尝试从当前应用获取密钥
            secret_key = current_app.config.get('SECRET_KEY')
        except RuntimeError:
            # 如果不在应用上下文中，使用配置中的密钥
            secret_key = config.secret_key
        
        # 生成令牌
        token = jwt.encode(
            payload, 
            secret_key, 
            algorithm='HS256'
        )
        
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

# 上传告警API - 支持Token认证
@device_api_server.route('/alarms', methods=['POST'])
@device_token_auth_required
def create_alarm_with_token():
    """边缘设备上传告警信息 - 使用Token认证方式"""
    try:
        # 从请求中获取告警数据
        data = request.get_json()
        if not data:
            logger.error("请求中未提供JSON数据")
            return jsonify({"code": 400, "message": "无效的请求数据"}), 400
        
        device = request.current_device  # 从装饰器获取已验证的设备
        logger.info(f"设备 {device.device_name} (ID: {device.device_id}) 使用Token认证方式成功")
            
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
                logger.error(f"缺少必要字段: {field}")
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
        import traceback
        logger.error(traceback.format_exc())
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

# 专门用于直接认证的测试端点
@device_api_server.route('/direct_test', methods=['POST'])
@device_auth_required
def direct_test():
    """直接认证测试API - 专门用于测试设备ID和密钥认证方式"""
    logger.info("收到直接认证测试请求")
    
    try:
        # 从请求中获取数据
        data = request.get_json()
        if not data:
            logger.error("请求中未提供JSON数据")
            return jsonify({"code": 400, "message": "无效的请求数据"}), 400
        
        # 设备信息已由装饰器验证
        device = request.current_device
        logger.info(f"设备 {device.device_name} (ID: {device.device_id}) 直接认证成功")
        
        # 处理告警数据
        alarm_type = data.get('alarm_type')
        alarm_code = data.get('alarm_code')
        
        if not alarm_type or not alarm_code:
            logger.error("缺少告警类型或告警编号")
            return jsonify({"code": 400, "message": "缺少告警类型或告警编号"}), 400
        
        # 准备告警数据
        alarm_data = {
            'device_id': device.device_id,
            'device_name': device.device_name,
            'alarm_time': datetime.now(),
            'alarm_type': alarm_type,
            'alarm_code': alarm_code
        }
        
        # 提取其他字段
        optional_fields = ['well_code', 'well_name', 'camera_ip', 'alarm_image', 'description', 'alarm_suffix_code']
        for field in optional_fields:
            if field in data:
                alarm_data[field] = data[field]
        
        # 创建告警
        alarm = Alarm.create_or_update(alarm_data)
        
        logger.info(f"设备 {device.device_name} (ID: {device.device_id}) 直接认证告警上报成功: {alarm.alarm_code}")
        
        return jsonify({
            'code': 200,
            'message': '直接认证告警上报成功',
            'data': {
                'alarm_id': alarm.id,
                'alarm_code': alarm.alarm_code,
                'device_name': device.device_name,
                'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
        })
        
    except Exception as e:
        logger.error(f"直接认证测试失败: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return jsonify({
            'code': 500,
            'message': f'直接认证测试失败: {str(e)}'
        }), 500

# 仅当作为独立脚本运行时才创建Flask应用
if __name__ == '__main__':
    import argparse
    
    # 创建独立的Flask应用实例
    standalone_app = Flask(__name__, template_folder=None, static_folder=None)
    standalone_app.config.from_object(Config)
    
    # 初始化数据库
    db.init_app(standalone_app)
    
    # 添加日志记录中间件
    @standalone_app.before_request
    def log_request_info():
        """记录所有接收到的请求信息，用于调试"""
        logger.debug('请求头: %s', dict(request.headers))
        logger.debug('请求URL: %s %s', request.method, request.url)
        logger.debug('请求数据: %s', request.get_json(silent=True))
    
    # 添加错误处理器，确保所有错误返回JSON而不是HTML
    @standalone_app.errorhandler(404)
    def not_found(error):
        return jsonify({
            'code': 404,
            'message': '请求的API端点不存在'
        }), 404
    
    @standalone_app.errorhandler(500)
    def server_error(error):
        return jsonify({
            'code': 500,
            'message': '服务器内部错误: ' + str(error)
        }), 500
    
    # 注册Blueprint
    standalone_app.register_blueprint(device_api_server)
    
    # 命令行参数
    parser = argparse.ArgumentParser(description='边缘设备API服务器')
    parser.add_argument('--host', default='0.0.0.0', help='监听地址')
    parser.add_argument('--port', type=int, default=5566, help='监听端口')
    parser.add_argument('--debug', action='store_true', help='是否启用调试模式')
    
    args = parser.parse_args()
    
    logger.info(f"边缘设备API服务器正在启动，监听 {args.host}:{args.port}")
    standalone_app.run(host=args.host, port=args.port, debug=args.debug) 