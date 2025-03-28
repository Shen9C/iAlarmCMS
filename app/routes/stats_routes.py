from flask import Blueprint, render_template, jsonify
from flask_login import login_required
from app.models.alarms import Alarm
from sqlalchemy import func
from datetime import datetime, timedelta

bp = Blueprint('stats', __name__)

@bp.route('/stats')
@login_required
def index():
    return render_template('stats/index.html')

@bp.route('/stats/alarm_trend')
@login_required
def alarm_trend():
    # 获取最近7天的告警趋势
    end_date = datetime.now()
    start_date = end_date - timedelta(days=7)
    
    daily_stats = db.session.query(
        func.date(Alarm.alarm_time).label('date'),
        func.count(Alarm.id).label('count')
    ).filter(
        Alarm.alarm_time.between(start_date, end_date)
    ).group_by(
        func.date(Alarm.alarm_time)
    ).all()
    
    return jsonify({
        'dates': [stat.date.strftime('%Y-%m-%d') for stat in daily_stats],
        'counts': [stat.count for stat in daily_stats]
    })

@bp.route('/stats/alarm_types')
@login_required
def alarm_types():
    # 获取告警类型统计
    type_stats = db.session.query(
        Alarm.alarm_type,
        func.count(Alarm.id).label('count')
    ).group_by(Alarm.alarm_type).all()
    
    return jsonify({
        'types': [stat.alarm_type for stat in type_stats],
        'counts': [stat.count for stat in type_stats]
    })