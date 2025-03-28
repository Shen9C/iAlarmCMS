from flask import Blueprint, render_template, request
from flask_login import login_required
from app.models.alarms import Alarm
from app import db

bp = Blueprint('stats', __name__)

@bp.route('/stats')
@login_required
def index():
    """统计页面视图"""
    try:
        # 基础统计数据
        total_alarms = Alarm.query.count()
        processed_alarms = Alarm.query.filter_by(is_processed=True).count()
        unprocessed_alarms = total_alarms - processed_alarms
        
        stats = {
            'total_alarms': total_alarms,
            'processed_alarms': processed_alarms,
            'unprocessed_alarms': unprocessed_alarms
        }
        
        return render_template('stats/stats_index.html', 
                             stats=stats,
                             user_token=request.args.get('user_token'))
                             
    except Exception as e:
        return render_template('stats/stats_index.html', 
                             stats={},
                             error=str(e),
                             user_token=request.args.get('user_token'))