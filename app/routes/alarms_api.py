from flask import Blueprint, jsonify, request
from flask_login import login_required, current_user
from app.models.alarms import Alarm
from app import db
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)
bp = Blueprint('alarms_api', __name__, url_prefix='/api/alarms')

@bp.route('/list', methods=['GET'])
@login_required
def get_alarms():
    """获取告警列表"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 15, type=int)
        status = request.args.get('status', '')
        alarm_type = request.args.get('alarm_type', '')
        device_name = request.args.get('device_name', '')
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        
        query = Alarm.query
        
        # 应用过滤条件
        if status:
            if status == '0':
                query = query.filter(Alarm.is_processed == False)
            elif status == '1':
                query = query.filter(Alarm.is_processed == True)
        if alarm_type:
            query = query.filter(Alarm.alarm_type == alarm_type)
        if device_name:
            query = query.filter(Alarm.device_name == device_name)
        if start_date:
            query = query.filter(Alarm.alarm_time >= datetime.strptime(start_date, '%Y-%m-%d'))
        if end_date:
            query = query.filter(Alarm.alarm_time < datetime.strptime(end_date, '%Y-%m-%d') + timedelta(days=1))
        
        pagination = query.order_by(Alarm.alarm_time.desc()).paginate(
            page=page, per_page=per_page, error_out=False
        )
        
        return jsonify({
            'code': 200,
            'message': '获取成功',
            'data': {
                'items': [alarm.to_dict() for alarm in pagination.items],
                'total': pagination.total,
                'pages': pagination.pages,
                'current_page': page
            }
        })
    except Exception as e:
        logger.error(f"获取告警列表失败: {str(e)}")
        return jsonify({
            'code': 500,
            'message': f'获取告警列表失败: {str(e)}'
        }), 500

@bp.route('/confirm', methods=['POST'])
@login_required
def confirm_alarm():
    """确认告警"""
    try:
        data = request.get_json()
        alarm_number = data.get('alarm_number')
        confirm_type = data.get('confirm_type')
        
        if not alarm_number or not confirm_type:
            return jsonify({
                'code': 400,
                'message': '缺少必要参数'
            }), 400
        
        alarm = Alarm.query.filter_by(alarm_number=alarm_number).first()
        if not alarm:
            return jsonify({
                'code': 404,
                'message': '告警不存在'
            }), 404
        
        alarm.is_confirmed = True
        alarm.confirm_type = confirm_type
        alarm.confirmed_time = datetime.now()
        db.session.commit()
        
        return jsonify({
            'code': 200,
            'message': '告警确认成功'
        })
    except Exception as e:
        db.session.rollback()
        logger.error(f"确认告警失败: {str(e)}")
        return jsonify({
            'code': 500,
            'message': f'确认告警失败: {str(e)}'
        }), 500

@bp.route('/batch/confirm', methods=['POST'])
@login_required
def batch_confirm():
    """批量确认告警"""
    try:
        data = request.get_json()
        alarm_numbers = data.get('alarm_numbers', [])
        confirm_type = data.get('confirm_type')
        
        if not alarm_numbers or not confirm_type:
            return jsonify({
                'code': 400,
                'message': '缺少必要参数'
            }), 400
        
        Alarm.query.filter(Alarm.alarm_number.in_(alarm_numbers)).update({
            'is_confirmed': True,
            'confirm_type': confirm_type,
            'confirmed_time': datetime.now()
        }, synchronize_session=False)
        
        db.session.commit()
        return jsonify({
            'code': 200,
            'message': '批量确认成功'
        })
    except Exception as e:
        db.session.rollback()
        logger.error(f"批量确认告警失败: {str(e)}")
        return jsonify({
            'code': 500,
            'message': f'批量确认告警失败: {str(e)}'
        }), 500

@bp.route('/stats', methods=['GET'])
@login_required
def get_stats():
    """获取告警统计信息"""
    try:
        base_query = Alarm.query
        
        # 基础统计
        stats = {
            'total': base_query.count(),
            'processed': base_query.filter(Alarm.is_processed == True).count(),
            'unprocessed': base_query.filter(Alarm.is_processed == False).count(),
            'confirmed': base_query.filter(Alarm.is_confirmed == True).count(),
            'unconfirmed': base_query.filter(Alarm.is_confirmed == False).count()
        }
        
        # 按类型统计
        type_stats = []
        alarm_types = db.session.query(Alarm.alarm_type.distinct()).filter(Alarm.alarm_type.isnot(None)).all()
        for type_tuple in alarm_types:
            alarm_type = type_tuple[0]
            if alarm_type:
                count = base_query.filter(Alarm.alarm_type == alarm_type).count()
                type_stats.append({'type': alarm_type, 'count': count})
        
        # 按设备统计
        device_stats = []
        devices = db.session.query(Alarm.device_name.distinct()).filter(Alarm.device_name.isnot(None)).all()
        for device_tuple in devices:
            device_name = device_tuple[0]
            if device_name:
                count = base_query.filter(Alarm.device_name == device_name).count()
                device_stats.append({'device': device_name, 'count': count})
        
        # 按日期统计（最近30天）
        daily_stats = []
        end_date = datetime.now()
        start_date = end_date - timedelta(days=30)
        
        current_date = start_date
        while current_date <= end_date:
            next_date = current_date + timedelta(days=1)
            count = base_query.filter(
                Alarm.alarm_time >= current_date,
                Alarm.alarm_time < next_date
            ).count()
            
            daily_stats.append({
                'date': current_date.strftime('%Y-%m-%d'),
                'count': count
            })
            current_date = next_date
        
        return jsonify({
            'code': 200,
            'message': '获取成功',
            'data': {
                'basic_stats': stats,
                'type_stats': type_stats,
                'device_stats': device_stats,
                'daily_stats': daily_stats
            }
        })
    except Exception as e:
        logger.error(f"获取告警统计失败: {str(e)}")
        return jsonify({
            'code': 500,
            'message': f'获取告警统计失败: {str(e)}'
        }), 500