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
    
    # # 添加调试打印
    # for alarm in alarms:
    #     print(f"告警ID: {alarm.id}")
    #     print(f"摄像头IP: {alarm.camera_ip}")
    #     print(f"设备名称: {alarm.device_name}")
    #     print(f"告警类型: {alarm.alarm_type}")
    #     print("原始数据:", vars(alarm))
    #     print("-" * 50)
    
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

# 修改 alarm_detail 路由
@bp.route('/detail/<string:alarm_number>')
@web_auth_required
def alarm_detail(alarm_number):
    alarm = Alarm.query.filter_by(alarm_number=alarm_number).first_or_404()
    return render_template('alarm_detail.html', alarm=alarm, user_token=request.args.get('user_token'))

# 修改 show_confirm_type 路由
@bp.route('/confirm_type/<string:alarm_number>', methods=['GET', 'POST'])
@web_auth_required
def show_confirm_type(alarm_number):
    try:
        user_token = request.args.get('user_token')
        alarm = Alarm.query.filter_by(alarm_number=alarm_number).first_or_404()
        
        # 处理POST请求（确认告警）
        if request.method == 'POST':
            confirm_type = request.form.get('confirm_type')
            
            if not confirm_type:
                flash('缺少确认类型', 'error')
                return render_template('confirm_type.html', alarm=alarm, user_token=user_token)
            
            alarm.is_confirmed = True
            alarm.confirm_type = confirm_type
            alarm.confirmed_time = datetime.now()
            db.session.commit()
            flash('告警确认成功', 'success')
            return redirect(url_for('alarm_view.index', user_token=user_token))
        
        # 处理GET请求（显示确认页面）
        return render_template('confirm_type.html', alarm=alarm, user_token=user_token)
    except Exception as e:
        print(f"Error in confirm_type: {str(e)}")
        db.session.rollback()
        flash('操作失败', 'error')
        return redirect(url_for('alarm_view.index', user_token=user_token))

# 修改 process_alarm 路由
@bp.route('/process/<string:alarm_number>', methods=['POST'])
@web_auth_required
def process_alarm(alarm_number):
    try:
        user_token = request.args.get('user_token')
        confirm_type = request.form.get('confirm_type')
        
        alarm = Alarm.query.filter_by(alarm_number=alarm_number).first_or_404()
        alarm.is_confirmed = True
        alarm.confirmed_time = datetime.now()
        alarm.confirm_type = confirm_type
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': '告警已确认',
            'redirect_url': url_for('alarm_view.index', user_token=user_token)
        })
    except Exception as e:
        print(f"Error processing alarm: {str(e)}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

