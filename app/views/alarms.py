from flask import Blueprint, render_template, request, redirect, url_for, Response, flash
from app.models.alarm import Alarm
from app.models.user import User  # 添加 User 模型的导入
from app import db
from flask_login import current_user, login_required  # 添加 login_required 导入
from datetime import datetime, timedelta
from app import db
from app.models.alarm import Alarm
import io, csv
from flask import jsonify
import re

# 创建蓝图实例 - 确保在任何路由之前定义
# 修改蓝图名称
# 创建蓝图实例
bp = Blueprint('alarm_view', __name__)

@bp.route('/')  # 保持为根路由，因为已经有 /alarms 前缀
def index():
    page = request.args.get('page', 1, type=int)
    page_size = request.args.get('page_size', 10, type=int)
    user_token = request.args.get('user_token')
    
    # 构建查询
    query = Alarm.query
    
    # 筛选条件
    alarm_type = request.args.get('alarm_type')
    is_processed = request.args.get('is_processed')
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    
    if alarm_type:
        query = query.filter(Alarm.alarm_type == alarm_type)
    if is_processed:
        query = query.filter(Alarm.is_processed == (is_processed == '1'))
    if start_date:
        query = query.filter(Alarm.alarm_time >= datetime.strptime(start_date, '%Y-%m-%d'))
    if end_date:
        query = query.filter(Alarm.alarm_time < datetime.strptime(end_date, '%Y-%m-%d') + timedelta(days=1))
    
    # 分页
    pagination = query.order_by(Alarm.alarm_time.desc()).paginate(
        page=page, per_page=page_size, error_out=False
    )
    
    return render_template('alarm_list.html',
                         alarms=pagination.items,
                         pagination=pagination,
                         page_size=page_size,
                         user_token=user_token,
                         alarm_types=db.session.query(Alarm.alarm_type).distinct().all())

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
        writer.writerow(['告警编号', '处理状态', '告警类型', '设备名称', 'IP地址', '告警时间'])
        
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
    user_token = request.args.get('user_token')
    try:
        # 基础查询
        base_query = Alarm.query
        
        # 总体统计 - 添加 .scalar() 确保返回具体数值
        total = base_query.count()
        processed = base_query.filter(Alarm.is_processed == True).count()
        unprocessed = base_query.filter(Alarm.is_processed == False).count()

        # 按类型统计
        type_stats = []
        type_query = db.session.query(
            Alarm.alarm_type,
            db.func.count(Alarm.id).label('count')
        ).group_by(Alarm.alarm_type).all()
        
        for alarm_type, count in type_query:
            type_stats.append({
                'alarm_type': alarm_type or '未知类型',
                'count': count
            })
        
        # print("Debug - Type query:", type_query)  # 调试输出
        # print("Debug - Formatted type_stats:", type_stats)

        # 按设备统计
        device_stats = []
        device_query = db.session.query(
            Alarm.device_name,
            db.func.count(Alarm.id).label('count')
        ).group_by(Alarm.device_name
        ).order_by(db.func.count(Alarm.id).desc()
        ).limit(10).all()
        
        for device_name, count in device_query:
            device_stats.append({
                'device_name': device_name or '未知设备',
                'count': count
            })
        
        # print("Debug - Device query:", device_query)  # 调试输出
        # print("Debug - Formatted device_stats:", device_stats)

        # 最近7天趋势
        today = datetime.now()
        seven_days_ago = today - timedelta(days=6)

        # 查询最近7天的数据
        daily_stats = db.session.query(
            db.func.date(Alarm.alarm_time).label('date'),
            db.func.count(Alarm.id).label('count')
        ).filter(
            Alarm.alarm_time.between(
                seven_days_ago.replace(hour=0, minute=0, second=0),
                today.replace(hour=23, minute=59, second=59)
            )
        ).group_by(
            db.func.date(Alarm.alarm_time)
        ).order_by(
            db.func.date(Alarm.alarm_time)
        ).all()

        # 将查询结果转换为字典格式，使用实际的告警日期
        formatted_daily_stats = []
        date_counts = {stat.date: stat.count for stat in daily_stats}
        print(date_counts)
        print("-------------------------------------------------")
        # 遍历最近7天
        for i in range(7):
            current_date = (seven_days_ago + timedelta(days=i)).date().strftime('%Y-%m-%d')
            print(current_date)
            count = date_counts.get(current_date, 0)
            formatted_daily_stats.append({
                'date': current_date,  # 使用完整日期格式
                'count': count
            })

        stats = {
            'total_alarms': total,
            'processed_alarms': processed,
            'unprocessed_alarms': unprocessed,
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

@bp.route('/')
@bp.route('/detail/<int:alarm_id>')
def alarm_detail(alarm_id):
    alarm = Alarm.query.get_or_404(alarm_id)
    return render_template('alarm_detail.html', alarm=alarm)

@bp.route('/process/<int:alarm_id>', methods=['POST'])
def process_alarm(alarm_id):
    user_token = request.args.get('user_token')
    alarm = Alarm.query.get_or_404(alarm_id)
    alarm.is_processed = True
    db.session.commit()
    
    # 获取所有当前的 URL 参数
    args = request.args.copy()
    # 确保包含 user_token
    args['user_token'] = user_token
    
    # 重定向回原页面，保留所有查询参数
    return redirect(url_for('alarm_view.index', **args))

def root():
    return redirect(url_for('alarm_view.index'))


# 添加用户管理页面的路由
@bp.route('/users')
@login_required
def user_management():
    if not current_user.is_admin:
        flash('您没有权限访问此页面')
        return redirect(url_for('alarm_view.index'))
        
    users = User.query.all()
    return render_template('user_management.html', users=users)

@bp.route('/users/add', methods=['POST'])
@login_required
def add_user():
    if not current_user.is_admin:
        flash('您没有权限执行此操作')
        return redirect(url_for('alarm_view.index'))
    
    username = request.form.get('username')
    password = request.form.get('password')
    role = request.form.get('role', User.ROLE_USER)
    
    if User.query.filter_by(username=username).first():
        flash('用户名已存在')
        return redirect(url_for('alarm_view.user_management'))
    
    user = User(username=username, role=role)
    user.set_password(password)
    db.session.add(user)
    db.session.commit()
    
    flash('用户添加成功')
    return redirect(url_for('alarm_view.user_management'))


# 删除或注释掉旧的 mark_as_handled 路由
# @bp.route('/mark_as_handled', methods=['POST'])
# @login_required
# def mark_as_handled():
#     try:
#         data = request.get_json()
#         alarm_ids = data.get('ids', [])
#         
#         alarms = Alarm.query.filter(Alarm.id.in_(alarm_ids)).all()
#         for alarm in alarms:
#             alarm.status = 'handled'
#             alarm.handled_by = current_user.username
#             alarm.handled_time = datetime.now()
#         
#         db.session.commit()
#         return jsonify({'success': True})
#     except Exception as e:
#         return jsonify({'success': False, 'message': str(e)})

@bp.route('/batch_handle', methods=['POST'])
@login_required
def batch_handle_alarms():
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

# 删除或注释掉旧的 export 路由
# @bp.route('/export')
# @login_required
# def export():
#     ...

# 修改为新的导出路由
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
        writer.writerow(['告警编号', '处理状态', '告警类型', '设备名称', 'IP地址', '告警时间'])
        
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