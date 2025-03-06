from flask import Blueprint, render_template, request, redirect, url_for, Response, flash
from app.models.alarm import Alarm
from app.models.user import User  # 添加 User 模型的导入
from app import db
from flask_login import current_user, login_required  # 添加 login_required 导入
from datetime import datetime, timedelta
from app import db
from app.models.alarm import Alarm
import io, csv

# 创建蓝图实例 - 确保在任何路由之前定义
# 修改蓝图名称
# 创建蓝图实例
bp = Blueprint('alarm_view', __name__)

@bp.route('/')  # 保持为根路由，因为已经有 /alarms 前缀
def index():
    page = request.args.get('page', 1, type=int)
    page_size = request.args.get('page_size', 10, type=int)
    
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
                         alarm_types=db.session.query(Alarm.alarm_type).distinct().all())

# 导出功能也需要更新
@bp.route('/export')
def export_alarms():
    alarms = Alarm.query.all()
    
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
        headers={'Content-Disposition': 'attachment; filename=alarms.csv'}
    )


def create_alarm(alarm_data):
    alarm = Alarm(
        alarm_number=generate_alarm_number(),
        alarm_type=alarm_data['type'],
        device_name=alarm_data.get('device_name'),
        device_ip=alarm_data.get('device_ip'),
        alarm_time=datetime.now(),
        alarm_image=save_alarm_image(alarm_data.get('image'))
    )
    db.session.add(alarm)
    db.session.commit()
    return alarm


# 统计页面
@bp.route('/statistics')
def statistics():
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
        
        return render_template('alarm_statistics.html', stats=stats)

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
    alarm = Alarm.query.get_or_404(alarm_id)
    alarm.is_processed = True
    db.session.commit()
    return redirect(url_for('alarm_view.index'))

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