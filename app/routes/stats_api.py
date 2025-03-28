from flask import Blueprint, jsonify, request
from flask_login import login_required, current_user
from app.models.alarms import Alarm
from app import db
from datetime import datetime, timedelta

bp = Blueprint('stats_api', __name__, url_prefix='/api/stats')

@bp.route('/summary', methods=['GET'])
@login_required
def get_summary():
    """获取统计摘要数据"""
    try:
        # 获取基础统计数据
        total_alarms = Alarm.query.count()
        processed_alarms = Alarm.query.filter_by(is_processed=True).count()
        unprocessed_alarms = total_alarms - processed_alarms
        
        return jsonify({
            'code': 200,
            'data': {
                'total_alarms': total_alarms,
                'processed_alarms': processed_alarms,
                'unprocessed_alarms': unprocessed_alarms
            }
        })
    except Exception as e:
        return jsonify({
            'code': 500,
            'message': f'获取统计数据失败: {str(e)}'
        }), 500

@bp.route('/trend', methods=['GET'])
@login_required
def get_trend():
    """获取趋势统计数据"""
    try:
        days = request.args.get('days', 7, type=int)
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        # 获取时间段内的告警趋势
        trend_data = []
        current_date = start_date
        
        while current_date <= end_date:
            next_date = current_date + timedelta(days=1)
            count = Alarm.query.filter(
                Alarm.alarm_time >= current_date,
                Alarm.alarm_time < next_date
            ).count()
            
            trend_data.append({
                'date': current_date.strftime('%Y-%m-%d'),
                'count': count
            })
            current_date = next_date
            
        return jsonify({
            'code': 200,
            'data': trend_data
        })
    except Exception as e:
        return jsonify({
            'code': 500,
            'message': f'获取趋势数据失败: {str(e)}'
        }), 500