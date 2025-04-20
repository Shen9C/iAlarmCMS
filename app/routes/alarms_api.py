import os
import json
import logging
from datetime import datetime, timedelta
from functools import wraps
from flask import Blueprint, jsonify, request, current_app, g
from flask_login import login_required, current_user
from sqlalchemy import and_, or_, desc
from app import db
from app.models.alarms import Alarm
from app.models.users import User

# 设置日志记录器
logger = logging.getLogger(__name__)

# 创建Blueprint
bp = Blueprint('alarms_api', __name__, url_prefix='/api/alarms')

# 辅助函数：通过token获取用户
def get_user_by_token(token):
    if not token:
        return None
    return User.query.filter_by(current_token=token).first()

# 自定义装饰器：支持token验证或会话验证
def token_or_login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # 检查是否有user_token
        user_token = request.args.get('user_token')
        if user_token:
            user = get_user_by_token(user_token)
            if user:
                # 保存用户到g对象，以便在视图函数中使用
                g.user = user
                logger.info(f"通过API token验证用户: {user.username}")
                return f(*args, **kwargs)
            else:
                logger.warning(f"无效的user_token: {user_token}")
                return jsonify({
                    'code': 401,
                    'success': False,
                    'message': '无效的用户令牌'
                }), 401
        # 如果没有token，则使用login_required
        return login_required(f)(*args, **kwargs)
    return decorated_function

@bp.route('/list', methods=['GET'])
@token_or_login_required
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
@token_or_login_required
def confirm_alarm():
    """确认告警"""
    try:
        data = request.get_json()
        alarm_id = data.get('alarm_id')
        confirm_type = data.get('confirm_type')
        
        # 记录请求信息
        logger.info(f"接收到告警确认请求: alarm_id={alarm_id}, confirm_type={confirm_type}")
        
        # 获取告警前先记录是否存在 - 不使用缓存
        db.session.expire_all()  # 清除会话缓存
        alarm = Alarm.query.get_or_404(alarm_id)
        logger.info(f"告警对象获取成功: id={alarm.id}, alarm_code={alarm.alarm_code}")
        
        # 详细记录告警确认前的完整状态
        logger.info(f"告警确认前状态: id={alarm.id}, alarm_code={alarm.alarm_code}, confirm_type={alarm.confirm_type}, "
                   f"is_confirmed={alarm.is_confirmed}, status={alarm.status}, "
                   f"confirmed_time={alarm.confirmed_time}")
        
        # 更新所有相关字段 - 注意保持状态不变
        alarm.confirm_type = confirm_type
        alarm.is_confirmed = True
        alarm.confirmed_time = datetime.now().astimezone()
        # 只修改confirm_type和is_confirmed，不改变status和is_processed
        # 业务逻辑：确认操作只设置告警确认类型，不会改变告警的处理状态
        
        # 提交前记录字段
        logger.info(f"提交前检查字段: confirm_type={alarm.confirm_type}, is_confirmed={alarm.is_confirmed}")
        
        # 确保提交
        db.session.commit()
        logger.info("数据库事务已提交")
        
        # 重新查询以验证写入成功
        alarm_after = Alarm.query.get(alarm_id)
        logger.info(f"提交后重新查询: id={alarm_after.id}, alarm_code={alarm_after.alarm_code}, confirm_type={alarm_after.confirm_type}, "
                   f"is_confirmed={alarm_after.is_confirmed}, status={alarm_after.status}, "
                   f"confirmed_time={alarm_after.confirmed_time}")
        
        return jsonify({
            'code': 200,
            'success': True, 
            'message': '告警确认成功',
            'data': {
                'id': alarm_id,
                'alarm_code': alarm_after.alarm_code,
                'confirm_type': alarm_after.confirm_type,
                'is_confirmed': alarm_after.is_confirmed,
                'confirmed_time': alarm_after.confirmed_time.strftime('%Y-%m-%d %H:%M:%S') if alarm_after.confirmed_time else None
            }
        })
    except Exception as e:
        logger.error(f"告警确认失败: {str(e)}")
        logger.exception("详细异常堆栈")
        db.session.rollback()
        return jsonify({
            'code': 500,
            'success': False, 
            'message': f'告警确认失败: {str(e)}'
        })

@bp.route('/batch-confirm', methods=['POST'])
@token_or_login_required
def batch_confirm_alarms():
    """批量确认告警"""
    try:
        data = request.get_json()
        alarm_ids = data.get('alarm_ids', [])
        confirm_type = data.get('confirm_type')
        
        if not alarm_ids or not confirm_type:
            return jsonify({
                'success': False,
                'message': '缺少必要参数'
            }), 400
        
        alarms = Alarm.query.filter(Alarm.id.in_(alarm_ids)).all()
        for alarm in alarms:
            alarm.is_confirmed = True
            alarm.confirm_type = confirm_type
            alarm.confirmed_time = datetime.now().astimezone()
            # 不修改status，只设置确认类型
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'成功确认 {len(alarms)} 个告警'
        })
    except Exception as e:
        db.session.rollback()
        logger.error(f"批量确认告警失败: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'确认告警失败: {str(e)}'
        }), 500

@bp.route('/batch-process', methods=['POST'])
@token_or_login_required
def batch_process_alarms():
    """批量处理告警"""
    try:
        data = request.get_json()
        alarm_ids = data.get('alarm_ids', [])
        notes = data.get('notes', '')
        
        if not alarm_ids:
            return jsonify({
                'success': False,
                'message': '缺少必要参数'
            }), 400
        
        alarms = Alarm.query.filter(Alarm.id.in_(alarm_ids)).all()
        for alarm in alarms:
            alarm.is_processed = True
            alarm.processed_time = datetime.now().astimezone()
            alarm.status = '已处理'
            # 如果有备注，可以在这里添加到告警处理记录中
            # alarm.process_notes = notes  # 需要先在数据库模型中添加相应字段
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'成功处理 {len(alarms)} 个告警'
        })
    except Exception as e:
        db.session.rollback()
        logger.error(f"批量处理告警失败: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'处理告警失败: {str(e)}'
        }), 500

@bp.route('/<int:alarm_id>/process', methods=['POST', 'GET'])
@token_or_login_required
def process_alarm(alarm_id):
    """处理单个告警"""
    try:
        # 确定请求的用户 - 可能是通过token验证的用户或通过会话验证的用户
        user = g.get('user') or current_user
        logger.info(f"处理告警操作由用户执行: {user.username}")
        
        # 区分GET和POST请求
        if request.method == 'GET':
            notes = request.args.get('notes', '')
            logger.info(f"接收到GET告警处理请求: alarm_id={alarm_id}, notes={notes}")
        else:  # POST请求
            try:
                data = request.get_json()
                notes = data.get('notes', '')
            except Exception as e:
                # 处理无法解析JSON的情况
                notes = ''
                logger.warning(f"POST请求未包含有效的JSON数据: {str(e)}")
            
            logger.info(f"接收到POST告警处理请求: alarm_id={alarm_id}, notes={notes}")
        
        # 获取告警前先记录是否存在 - 不使用缓存
        db.session.expire_all()  # 清除会话缓存
        alarm = Alarm.query.get_or_404(alarm_id)
        logger.info(f"告警对象获取成功: id={alarm.id}, alarm_code={alarm.alarm_code}")
        
        # 详细记录告警处理前的完整状态
        logger.info(f"告警处理前状态: id={alarm.id}, alarm_code={alarm.alarm_code}, is_processed={alarm.is_processed}, "
                   f"status={alarm.status}, processed_time={alarm.processed_time}")
        
        # 更新告警状态为已处理
        alarm.is_processed = True
        alarm.processed_time = datetime.now().astimezone()
        alarm.status = '已处理'
        # 注意：处理操作不会影响告警的确认状态(is_confirmed)和确认类型(confirm_type)
        
        # 如果有备注，可以在这里添加到告警处理记录中
        # alarm.process_notes = notes  # 需要先在数据库模型中添加相应字段
        
        # 提交前记录字段
        logger.info(f"提交前检查字段: is_processed={alarm.is_processed}, status={alarm.status}")
        
        # 确保提交
        db.session.commit()
        logger.info("数据库事务已提交")
        
        # 重新查询以验证写入成功
        alarm_after = Alarm.query.get(alarm_id)
        logger.info(f"提交后重新查询: id={alarm_after.id}, alarm_code={alarm_after.alarm_code}, "
                   f"is_processed={alarm_after.is_processed}, status={alarm_after.status}, "
                   f"processed_time={alarm_after.processed_time}")
        
        return jsonify({
            'code': 200,
            'success': True, 
            'message': '告警处理成功',
            'data': {
                'id': alarm_id,
                'alarm_code': alarm_after.alarm_code,
                'is_processed': alarm_after.is_processed,
                'status': alarm_after.status,
                'processed_time': alarm_after.processed_time.strftime('%Y-%m-%d %H:%M:%S') if alarm_after.processed_time else None
            }
        })
    except Exception as e:
        logger.error(f"告警处理失败: {str(e)}")
        logger.exception("详细异常堆栈")
        db.session.rollback()
        return jsonify({
            'code': 500,
            'success': False, 
            'message': f'告警处理失败: {str(e)}'
        })

@bp.route('/stats', methods=['GET'])
@token_or_login_required
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