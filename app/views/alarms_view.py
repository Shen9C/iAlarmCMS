from flask import Blueprint, render_template, request, redirect, url_for, Response, flash, jsonify, current_app
from app.models.alarms import Alarm
from app.models.users import User
from app import db
from flask_login import current_user, login_required
from datetime import datetime, timedelta
import io, csv
import re
from app.utils.web_auth import web_auth_required
import logging
import os

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
    
    # 按ID升序排序
    query = query.order_by(Alarm.id.asc())
    
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

    for alarm in alarms:
        filename = alarm.alarm_image.split('/')[-1] if alarm.alarm_image else None
        if filename:
            alarm.image_exists = os.path.isfile(os.path.join('/zhyn/alarm_images', filename))
        else:
            alarm.image_exists = False

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
        alarm_types = db.session.query(
            Alarm.alarm_type,
            db.func.count(Alarm.id).label('count')
        ).filter(
            Alarm.alarm_type.isnot(None)
        ).group_by(
            Alarm.alarm_type
        ).order_by(
            db.desc('count')
        ).all()

        # 处理告警类型统计
        for alarm_type, count in alarm_types:
            if alarm_type:
                # 从告警类型中提取分类
                alarm_category = None
                alarm_name = alarm_type
                
                # 如果告警类型包含 "-"，则分割为分类和名称
                if "-" in alarm_type:
                    parts = alarm_type.split("-", 1)
                    if len(parts) == 2:
                        alarm_category = parts[0].strip()
                        alarm_name = parts[1].strip()
                
                type_stats.append({
                    'alarm_type': alarm_type,
                    'alarm_category': alarm_category,
                    'alarm_name': alarm_name,
                    'count': count
                })
        
        # 按设备统计
        device_stats = []
        devices = db.session.query(
            Alarm.device_name,
            Alarm.alarm_type,
            db.func.count(Alarm.id).label('count')
        ).filter(
            Alarm.device_name.isnot(None)
        ).group_by(
            Alarm.device_name,
            Alarm.alarm_type
        ).order_by(
            db.desc('count')
        ).limit(10).all()

        for device_name, alarm_type, count in devices:
            if device_name:
                # 从告警类型中提取名称
                alarm_name = alarm_type
                if "-" in alarm_type:
                    alarm_name = alarm_type.split("-", 1)[1].strip()
                
                device_stats.append({
                    'device_name': device_name,
                    'alarm_type': alarm_type,
                    'alarm_name': alarm_name,
                    'count': count
                })
        
        # 按日期统计
        daily_stats = []
        end_date = datetime.now()
        start_date = end_date - timedelta(days=7)  # 改为只显示最近7天
        
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
        
        user_token = request.args.get('user_token')
        
        stats = {
            'total_alarms': total,
            'processed_alarms': processed,
            'unprocessed_alarms': unprocessed,
            'confirmed_alarms': confirmed,
            'unconfirmed_alarms': unconfirmed,
            'type_stats': type_stats,
            'device_stats': device_stats,
            'daily_stats': daily_stats
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

@bp.route('/detail/<int:alarm_id>', methods=['GET', 'POST'])
@login_required
def alarm_detail(alarm_id):
    # 从cookie或请求参数中获取user_token
    user_token = request.cookies.get('user_token') or request.args.get('user_token')
    
    logger.info(f"告警详情请求: alarm_id={alarm_id}, method={request.method}, user_token={user_token}")
    
    # 获取告警详情
    alarm = Alarm.query.get_or_404(alarm_id)
    
    return render_template('alarms/alarm_detail.html', alarm=alarm, user_token=user_token)

@bp.route('/confirm_alarm_type/<int:alarm_id>', methods=['GET', 'POST'])
@login_required
def confirm_alarm_type(alarm_id):
    """
    显示告警确认类型页面
    """
    logger.info(f'访问告警确认页面: alarm_id={alarm_id}, method={request.method}')
    
    # 优先用Flask-Login session认证
    from flask_login import current_user
    user_token = request.cookies.get('user_token') or request.args.get('user_token')
    logger.info(f'用户令牌: {user_token}, 当前用户: {getattr(current_user, "username", None)}, 已认证: {current_user.is_authenticated}')
    
    # 只要登录了就允许访问，不再强制user_token
    # if not user_token and not current_user.is_authenticated:
    #     flash('缺少用户认证信息', 'error')
    #     return redirect(url_for('alarms_view.index'))

    # 获取告警信息
    alarm = Alarm.query.get_or_404(alarm_id)
    logger.info(f'获取到的告警信息: {alarm.alarm_code}')
    
    if request.method == 'POST':
        logger.info('处理POST请求')
        logger.info(f'表单数据: {request.form}')
        
        confirmation_type = request.form.get('confirmation_type')
        notes = request.form.get('notes', '')
        
        logger.info(f'确认类型: {confirmation_type}')
        
        if not confirmation_type:
            flash('请选择确认类型', 'warning')
            return render_template('alarms/alarms_confirm_type.html', alarm=alarm, user_token=user_token)
        
        try:
            # 更新告警确认状态
            alarm.is_confirmed = True
            alarm.confirmation_type = confirmation_type
            alarm.confirmation_notes = notes
            alarm.confirmed_at = datetime.now()
            alarm.confirmed_by = current_user.username
            
            db.session.commit()
            logger.info('告警确认成功')
            flash('告警确认成功', 'success')
            return redirect(url_for('alarms_view.index', user_token=user_token))
            
        except Exception as e:
            db.session.rollback()
            logger.error(f'告警确认失败: {str(e)}')
            flash('告警确认失败，请重试', 'error')
    
    return render_template('alarms/alarms_confirm_type.html', alarm=alarm, user_token=user_token)

@bp.route('/process_alarm/<int:alarm_id>', methods=['GET', 'POST'])
@login_required
def process_alarm(alarm_id):
    """
    处理告警
    """
    logger.info(f'访问告警处理页面: alarm_id={alarm_id}, method={request.method}')
    
    from flask_login import current_user
    user_token = request.cookies.get('user_token') or request.args.get('user_token')
    logger.info(f'用户令牌: {user_token}, 当前用户: {getattr(current_user, "username", None)}, 已认证: {current_user.is_authenticated}')
    
    # 只要登录了就允许访问，不再强制user_token
    # if not user_token and not current_user.is_authenticated:
    #     if request.is_json:
    #         return jsonify({'success': False, 'message': '缺少用户认证信息'})
    #     flash('缺少用户认证信息', 'error')
    #     return redirect(url_for('alarms_view.index'))

    # 获取告警信息
    alarm = Alarm.query.get_or_404(alarm_id)
    logger.info(f'获取到的告警信息: {alarm.alarm_code}')
    
    if request.method == 'POST':
        logger.info('处理POST请求')
        
        # 检查是否是AJAX请求
        if request.is_json:
            data = request.get_json()
            notes = data.get('notes', '')
        else:
            notes = request.form.get('notes', '')
        
        logger.info(f'处理数据: notes={notes}')
        
        if not notes:
            if request.is_json:
                return jsonify({'error': '备注不能为空'}), 400
            else:
                flash('备注不能为空', 'error')
                return redirect(url_for('alarms_view.process_alarm', alarm_id=alarm_id))
        
        try:
            # 更新告警处理状态
            alarm.is_processed = True
            alarm.process_notes = notes
            alarm.processed_time = datetime.now()
            alarm.processed_by = current_user.username
            
            db.session.commit()
            logger.info('告警处理成功')
            
            if request.is_json:
                return jsonify({'success': True, 'message': '告警处理成功'})
            
            flash('告警处理成功', 'success')
            return redirect(url_for('alarms_view.index', user_token=user_token))
            
        except Exception as e:
            db.session.rollback()
            logger.error(f'告警处理失败: {str(e)}')
            if request.is_json:
                return jsonify({'success': False, 'message': f'告警处理失败: {str(e)}'})
            flash('告警处理失败，请重试', 'error')
    
    return render_template('alarms/alarms_process.html', alarm=alarm, user_token=user_token)

