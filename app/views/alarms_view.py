from flask import Blueprint, render_template, request, redirect, url_for, Response, flash, jsonify
from app.models.alarms import Alarm
from app.models.users import User
from app import db
from flask_login import current_user, login_required
from datetime import datetime, timedelta
import io, csv
import re
from app.utils.web_auth import web_auth_required
import logging

# 创建蓝图实例
bp = Blueprint('alarms_view', __name__)

logger = logging.getLogger(__name__)

@bp.route('/', methods=['GET'])
@login_required
def index():
    """告警列表页面"""
    # 获取筛选条件
    alarm_type = request.args.get('alarm_type', '')
    status = request.args.get('status', '')
    device_name = request.args.get('device_name', '')
    start_date = request.args.get('start_date', '')
    end_date = request.args.get('end_date', '')
    
    # 获取当前页码和每页条数
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 15, type=int)  # 默认每页显示15条
    user_token = request.args.get('user_token')
    
    # 强制刷新会话，确保获取最新数据
    db.session.expire_all()
    
    # 构建查询
    query = Alarm.query
    
    # 添加筛选条件
    if status:
        if status == '0':
            query = query.filter(Alarm.is_processed == False)
        elif status == '1':
            query = query.filter(Alarm.is_processed == True)
    if alarm_type:
        query = query.filter(Alarm.alarm_type == alarm_type)
    if device_name:
        query = query.filter(Alarm.device_name == device_name)
        
    # 添加时间筛选条件
    if start_date:
        query = query.filter(Alarm.alarm_time >= datetime.strptime(start_date, '%Y-%m-%d'))
    if end_date:
        query = query.filter(Alarm.alarm_time < datetime.strptime(end_date, '%Y-%m-%d') + timedelta(days=1))
    
    # 获取所有设备名称和告警类型（用于下拉列表）
    device_names = db.session.query(Alarm.device_name.distinct()).order_by(Alarm.device_name).all()
    device_names = [name[0] for name in device_names if name[0]]
    
    # 修改告警类型的获取方式，修复缩进问题
    alarm_types = db.session.query(Alarm.alarm_type.distinct()
        ).filter(Alarm.alarm_type.isnot(None)
        ).filter(Alarm.alarm_type != ''
        ).order_by(Alarm.alarm_type).all()
    alarm_types = [type[0].strip() for type in alarm_types if type[0] and len(type[0].strip()) > 0]
    
    # 分页 - 确保不使用缓存结果
    pagination = query.order_by(Alarm.alarm_time.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    # 获取所有结果，不使用缓存
    alarms = pagination.items
    
    # 添加调试代码，检查目标告警的状态
    test_alarms = []
    for alarm in alarms:
        # 确保所有告警对象都从数据库重新加载，避免使用缓存数据
        db.session.refresh(alarm)
        if alarm.alarm_code == "ALM202504191602239614":
            logger.info(f"视图中的告警对象(刷新后): alarm_code={alarm.alarm_code}, "
                      f"is_confirmed={alarm.is_confirmed}, confirmation_type={alarm.confirmation_type}, "
                      f"is_processed={alarm.is_processed}")
        test_alarms.append(alarm)

    # 使用刷新后的对象列表渲染模板
    return render_template('alarms/alarms_index.html',
                         alarms=test_alarms,
                         pagination=pagination,
                         alarm_types=alarm_types,
                         device_names=device_names,
                         current_status=status,
                         current_type=alarm_type,
                         current_device=device_name,
                         user_token=user_token)

@bp.route('/mark_as_handled', methods=['POST'])
@login_required
def mark_as_handled():
    try:
        data = request.get_json()
        alarm_ids = data.get('ids', [])
        user_token = request.args.get('user_token')
        
        alarms = Alarm.query.filter(Alarm.id.in_(alarm_ids)).all()
        for alarm in alarms:
            # 更新状态为已处理
            alarm.is_processed = True
            alarm.processed_time = datetime.now()
            # 注意：处理操作不会影响告警的确认状态(is_confirmed)和确认类型(confirmation_type)
        
        db.session.commit()
        return jsonify({'success': True, 'user_token': user_token})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@bp.route('/export')
@login_required
def export():
    try:
        # 获取筛选条件
        alarm_type = request.args.get('alarm_type')
        is_processed = request.args.get('is_processed')
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        user_token = request.args.get('user_token')
        
        # 构建查询
        query = Alarm.query
        
        if alarm_type:
            query = query.filter(Alarm.alarm_type == alarm_type)
        if is_processed:
            query = query.filter(Alarm.is_processed == (is_processed == '1'))
        if start_date:
            query = query.filter(Alarm.alarm_time >= datetime.strptime(start_date, '%Y-%m-%d'))
        if end_date:
            query = query.filter(Alarm.alarm_time < datetime.strptime(end_date, '%Y-%m-%d') + timedelta(days=1))
        
        alarms = query.all()
        
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(['告警编号', '告警状态', '确认状态', '告警类型', '设备名称', '摄像头IP', '告警时间', '上报次数', '最后上报时间'])
        
        for alarm in alarms:
            writer.writerow([
                alarm.alarm_code,
                '已处理' if alarm.is_processed else '待处理',
                '已确认' if alarm.is_confirmed else '未确认',
                alarm.alarm_type,
                alarm.device_name or '',
                alarm.camera_ip or '',
                alarm.alarm_time.strftime('%Y-%m-%d %H:%M:%S'),
                alarm.report_count,
                alarm.last_report_time.strftime('%Y-%m-%d %H:%M:%S') if alarm.last_report_time else ''
            ])
        
        output.seek(0)
        return Response(
            output,
            mimetype='text/csv',
            headers={
                'Content-Disposition': f'attachment; filename=alarms_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv',
                'X-User-Token': user_token
            }
        )
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/statistics')
@login_required
def statistics():
    try:
        # 基础查询
        base_query = Alarm.query
        
        # 总体统计
        total = base_query.count()
        processed = base_query.filter(Alarm.is_processed == True).count()
        unprocessed = base_query.filter(Alarm.is_processed == False).count()
        confirmed = base_query.filter(Alarm.is_confirmed == True).count()
        unconfirmed = base_query.filter(Alarm.is_confirmed == False).count()

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
        
        # 按日期统计
        daily_stats = []
        # 获取最近30天的数据
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
        
        # 格式化为前端需要的格式
        formatted_daily_stats = {
            'dates': [item['date'] for item in daily_stats],
            'counts': [item['count'] for item in daily_stats]
        }
        
        user_token = request.args.get('user_token')
        
        stats = {
            'total_alarms': total,
            'processed_alarms': processed,
            'unprocessed_alarms': unprocessed,
            'confirmed_alarms': confirmed,
            'unconfirmed_alarms': unconfirmed,
            'type_stats': type_stats,
            'device_stats': device_stats,
            'daily_stats': formatted_daily_stats
        }
        
        return render_template('alarms/alarm_statistics.html', stats=stats, user_token=user_token)

    except Exception as e:
        print(f"Error in statistics: {str(e)}")
        import traceback
        print(traceback.format_exc())
        return render_template('alarms/alarm_statistics.html', stats={
            'total_alarms': 0,
            'processed_alarms': 0,
            'unprocessed_alarms': 0,
            'confirmed_alarms': 0,
            'unconfirmed_alarms': 0,
            'type_stats': [],
            'device_stats': [],
            'daily_stats': {'dates': [], 'counts': []}
        })

@bp.route('/export_alarms')
@login_required
def export_alarms():
    try:
        # 获取筛选条件
        alarm_type = request.args.get('alarm_type')
        is_processed = request.args.get('is_processed')
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        user_token = request.args.get('user_token')
        
        # 构建查询
        query = Alarm.query
        
        if alarm_type:
            query = query.filter(Alarm.alarm_type == alarm_type)
        if is_processed:
            query = query.filter(Alarm.is_processed == (is_processed == '1'))
        if start_date:
            query = query.filter(Alarm.alarm_time >= datetime.strptime(start_date, '%Y-%m-%d'))
        if end_date:
            query = query.filter(Alarm.alarm_time < datetime.strptime(end_date, '%Y-%m-%d') + timedelta(days=1))
        
        alarms = query.all()
        
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(['告警编号', '告警状态', '确认状态', '告警类型', '设备名称', '摄像头IP', '告警时间', '上报次数', '最后上报时间'])
        
        for alarm in alarms:
            writer.writerow([
                alarm.alarm_code,
                '已处理' if alarm.is_processed else '待处理',
                '已确认' if alarm.is_confirmed else '未确认',
                alarm.alarm_type,
                alarm.device_name,
                alarm.camera_ip or '',
                alarm.alarm_time.strftime('%Y-%m-%d %H:%M:%S'),
                alarm.report_count,
                alarm.last_report_time.strftime('%Y-%m-%d %H:%M:%S') if alarm.last_report_time else ''
            ])
        
        output.seek(0)
        return Response(
            output,
            mimetype='text/csv',
            headers={
                'Content-Disposition': f'attachment; filename=alarms_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv',
                'X-User-Token': user_token
            }
        )
    except Exception as e:
        return jsonify({'error': str(e)}), 500


def check_password_strength(password):
    """检查密码复杂度"""
    if len(password) < 8:
        return False, "密码长度至少为8位"
    
    if not re.search(r"[A-Z]", password):
        return False, "密码必须包含大写字母"
    
    if not re.search(r"[a-z]", password):
        return False, "密码必须包含小写字母"
    
    if not re.search(r"\d", password):
        return False, "密码必须包含数字"
    
    if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", password):
        return False, "密码必须包含特殊字符"
    
    return True, "密码符合要求"

@bp.route('/change_password', methods=['POST'])
@login_required
def change_password():
    try:
        user_token = request.args.get('user_token')
        data = request.get_json()
        old_password = data.get('old_password')
        new_password = data.get('new_password')
        confirm_password = data.get('confirm_password')
        
        # 检查确认密码
        if new_password != confirm_password:
            return jsonify({
                'success': False,
                'message': '两次输入的新密码不一致',
                'user_token': user_token
            })
        
        if not current_user.check_password(old_password):
            return jsonify({
                'success': False, 
                'message': '原密码不正确',
                'user_token': user_token
            })
        
        # 检查新密码复杂度
        is_valid, message = check_password_strength(new_password)
        if not is_valid:
            return jsonify({
                'success': False,
                'message': message,
                'user_token': user_token
            })
        
        current_user.set_password(new_password)
        db.session.commit()
        
        return jsonify({
            'success': True, 
            'message': '密码修改成功',
            'user_token': user_token,
            'redirect_url': url_for('alarms_view.index', user_token=user_token)
        })
    except Exception as e:
        return jsonify({
            'success': False, 
            'message': str(e),
            'user_token': user_token
        })

@bp.route('/detail/<int:alarm_id>')
@web_auth_required
def alarm_detail(alarm_id):
    alarm = Alarm.query.get_or_404(alarm_id)
    user_token = request.args.get('user_token')
    return render_template('alarms/alarm_detail.html', alarm=alarm, user_token=user_token)

@bp.route('/confirm_type/<int:alarm_id>', methods=['GET', 'POST'])
@web_auth_required
def show_confirm_type(alarm_id):
    user_token = request.args.get('user_token')
    # 获取告警信息
    alarm = Alarm.query.get_or_404(alarm_id)
    
    # 如果是 POST 请求，处理表单提交
    if request.method == 'POST':
        confirmation_type = request.form.get('confirmation_type')
        if confirmation_type:
            alarm.confirmation_type = confirmation_type
            alarm.is_confirmed = True
            alarm.confirmed_at = datetime.now()
            # 不改变processed_status，只设置确认类型
            db.session.commit()
            return redirect(url_for('alarms_view.index', user_token=user_token))
    
    # 如果是 GET 请求，显示表单
    return render_template('alarms/alarms_confirm_type.html', alarm=alarm, user_token=user_token)

@bp.route('/process/<int:alarm_id>', methods=['POST'])
@web_auth_required
def process_alarm(alarm_id):
    """处理告警"""
    alarm = Alarm.query.get_or_404(alarm_id)
    description = request.form.get('description', '')
    
    # 更新告警状态
    alarm.is_processed = True
    alarm.processed_time = datetime.now()
    alarm.processed_by = current_user.username
    
    if description:
        alarm.description = description
    
    db.session.commit()
    flash('告警已成功处理', 'success')
    return redirect(url_for('alarms_view.index'))

