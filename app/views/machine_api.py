from flask import Blueprint, request, jsonify
from app.models.alarm import Alarm
from app.utils.machine_auth import machine_auth_required
from datetime import datetime
from app import db

bp = Blueprint('machine_api', __name__, url_prefix='/api/v1/machine')

@bp.route('/alarms', methods=['POST'])
@machine_auth_required
def create_alarm():
    """创建单个告警的接口"""
    try:
        data = request.get_json()
        
        # 验证必要字段
        required_fields = ['alarm_type', 'device_name', 'camera_ip']
        for field in required_fields:
            if field not in data:
                return jsonify({
                    'success': False,
                    'error': f'缺少必要字段: {field}'
                }), 400
        
        # 准备告警数据
        alarm_data = {
            'alarm_number': f"AL{datetime.now().strftime('%Y%m%d%H%M%S%f')}",
            'alarm_type': data['alarm_type'],
            'device_name': data['device_name'],
            'camera_ip': data['camera_ip'],
            'alarm_time': datetime.now(),
            'is_processed': False
        }
        
        # 创建或更新告警
        alarm = Alarm.create_or_update(alarm_data)
        
        return jsonify({
            'success': True,
            'message': '告警已记录',
            'alarm_number': alarm.alarm_number
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'处理告警时发生错误: {str(e)}'
        }), 500

@bp.route('/alarms/batch', methods=['POST'])
@machine_auth_required
def create_batch_alarms():
    """批量创建告警的接口"""
    try:
        data = request.get_json()
        if not isinstance(data, list):
            return jsonify({
                'success': False,
                'error': '请求数据必须是告警列表'
            }), 400
            
        results = []
        for alarm_data in data:
            try:
                # 验证每个告警的必要字段
                if not all(field in alarm_data for field in ['alarm_type', 'device_name', 'camera_ip']):
                    results.append({
                        'success': False,
                        'error': '缺少必要字段'
                    })
                    continue
                
                # 准备告警数据
                processed_data = {
                    'alarm_number': f"AL{datetime.now().strftime('%Y%m%d%H%M%S%f')}",
                    'alarm_type': alarm_data['alarm_type'],
                    'device_name': alarm_data['device_name'],
                    'camera_ip': alarm_data['camera_ip'],
                    'alarm_time': datetime.now(),
                    'is_processed': False
                }
                
                # 创建或更新告警
                alarm = Alarm.create_or_update(processed_data)
                results.append({
                    'success': True,
                    'alarm_number': alarm.alarm_number
                })
                
            except Exception as e:
                results.append({
                    'success': False,
                    'error': str(e)
                })
        
        return jsonify({
            'success': True,
            'results': results
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'处理批量告警时发生错误: {str(e)}'
        }), 500

@bp.route('/alarms/status', methods=['GET'])
@machine_auth_required
def get_alarm_status():
    """获取告警状态统计"""
    try:
        total_count = Alarm.query.count()
        unprocessed_count = Alarm.query.filter_by(is_processed=False).count()  # 修改为 is_processed
        processed_count = Alarm.query.filter_by(is_processed=True).count()     # 修改为 is_processed
        
        return jsonify({
            'success': True,
            'data': {
                'total': total_count,
                'alarm_generated': unprocessed_count,    # 告警产生数量
                'alarm_cleared': processed_count         # 告警清除数量
            }
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'获取告警状态统计失败: {str(e)}'
        }), 500