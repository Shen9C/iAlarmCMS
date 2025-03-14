from flask import Blueprint, render_template, request, redirect, url_for, Response, flash, jsonify
from app.models.alarm import Alarm
from app.models.user import User
from app import db
from flask_login import current_user, login_required
from datetime import datetime, timedelta
import io, csv
import re
from app.utils.web_auth import web_auth_required

# 创建蓝图实例
bp = Blueprint('alarm_view', __name__)

@bp.route('/')
@web_auth_required
def index():
    page = request.args.get('page', 1, type=int)
    page_size = request.args.get('page_size', 10, type=int)
    user_token = request.args.get('user_token')
    status = request.args.get('status', '')
    alarm_type = request.args.get('alarm_type', '')
    device_name = request.args.get('device_name', '')
    
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
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
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
    
    # 分页
    pagination = query.order_by(Alarm.alarm_time.desc()).paginate(
        page=page, per_page=page_size, error_out=False
    )
    alarms = pagination.items
    
    # 添加调试打印
    for alarm in alarms:
        print(f"告警ID: {alarm.id}")
        print(f"摄像头IP: {alarm.camera_ip}")
        print(f"设备名称: {alarm.device_name}")
        print(f"告警类型: {alarm.alarm_type}")
        print("原始数据:", vars(alarm))
        print("-" * 50)
    
    return render_template('alarm_list.html',
                         alarms=alarms,
                         pagination=pagination,
                         alarm_types=alarm_types,  # 确保传递告警类型列表
                         device_names=device_names,
                         current_status=status,
                         current_type=alarm_type,  # 确保传递当前选中的类型
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
            alarm.status = 'handled'
            alarm.handled_by = current_user.username
            alarm.handled_time = datetime.now()
        
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
        writer.writerow(['告警编号', '告警状态', '告警类型', '油井名称', '摄像头IP', '告警时间'])
        
        for alarm in alarms:
            writer.writerow([
                alarm.alarm_number,
                '已处理' if alarm.is_processed else '未处理',
                alarm.alarm_type,
                alarm.device_name or '',
                alarm.device_ip or '',
                alarm.alarm_time.strftime('%Y-%m-%d %H:%M:%S')
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
        
        # 总体统计 - 添加 .scalar() 确保返回具体数值
        total = base_query.count()
        processed = base_query.filter(Alarm.is_processed == True).count()  # 告警清除数量
        unprocessed = base_query.filter(Alarm.is_processed == False).count()  # 告警产生数量
        confirmed = base_query.filter(Alarm.is_confirmed == True).count()  # 已确认数量
        unconfirmed = base_query.filter(Alarm.is_confirmed == False).count()  # 未确认数量

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

        # 打印最终的统计数据
        print("Debug - Final stats:", stats['daily_stats'])
        
        return render_template('alarm_statistics.html', stats=stats, user_token=user_token)

    except Exception as e:
        print(f"Error in statistics: {str(e)}")
        import traceback
        print(traceback.format_exc())
        return render_template('alarm_statistics.html', stats={
            'total_alarms': 0,
            'processed_alarms': 0,
            'unprocessed_alarms': 0,
            'type_stats': [],
            'device_stats': [],
            'daily_stats': []
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
        writer.writerow(['告警编号', '告警状态', '告警类型', '油井名称', '摄像头IP', '告警时间'])
        
        for alarm in alarms:
            writer.writerow([
                alarm.alarm_number,
                '告警清除' if alarm.is_processed else '告警产生',
                '已确认' if alarm.is_confirmed else '未确认',
                alarm.alarm_type,
                alarm.device_name,
                alarm.camera_ip or '',  # 确保使用 camera_ip
                alarm.alarm_time.strftime('%Y-%m-%d %H:%M:%S')
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
    return send_file(
        excel_file,
        as_attachment=True,
        download_name=f'alarms_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx'
    )


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
            'redirect_url': url_for('alarm_view.index', user_token=user_token)
        })
    except Exception as e:
        return jsonify({
            'success': False, 
            'message': str(e),
            'user_token': user_token
        })

@bp.route('/detail/<int:alarm_id>')
@web_auth_required  # 添加认证装饰器
def alarm_detail(alarm_id):
    alarm = Alarm.query.get_or_404(alarm_id)
    return render_template('alarm_detail.html', alarm=alarm, user_token=request.args.get('user_token'))

@bp.route('/process/<int:alarm_id>', methods=['POST'])
@web_auth_required
def process_alarm(alarm_id):
    try:
        user_token = request.args.get('user_token')
        alarm = Alarm.query.get_or_404(alarm_id)
        
        # 修改确认状态和时间
        alarm.is_confirmed = True
        alarm.confirmed_time = datetime.now()
        db.session.commit()
        
        # 获取所有当前的 URL 参数
        args = request.args.copy()
        args['user_token'] = user_token
        
        return redirect(url_for('alarm_view.index', **args))
    except Exception as e:
        print(f"Error processing alarm: {str(e)}")
        flash('处理告警时发生错误')
        return redirect(url_for('alarm_view.index', user_token=user_token))