import os
import json
import logging
import time
from datetime import datetime, timedelta
from functools import wraps
from flask import Blueprint, jsonify, request, current_app, g, send_from_directory, send_file
from flask_login import login_required, current_user
from sqlalchemy import and_, or_, desc
from app import db
from app.models.alarms import Alarm
from app.models.users import User
from PIL import Image
from io import BytesIO

# 设置日志记录器
logger = logging.getLogger(__name__)

# 创建Blueprint
bp = Blueprint('alarms_api', __name__, url_prefix='/api/alarms')

# 创建缩略图缓存
thumbnail_cache = {}
CACHE_MAX_SIZE = 100  # 缓存最多保存100个缩略图
CACHE_EXPIRY = 3600   # 缓存有效期1小时（秒）

# 新增路由：提供告警图片访问
@bp.route('/images/<filename>')
def get_alarm_image(filename):
    """提供告警图片文件，添加速度优化"""
    # 安全检查：防止路径穿越
    if '..' in filename or filename.startswith('/'):
        return jsonify({'error': '无效的文件名'}), 400
    
    start_time = time.time()
    logger.info(f"开始处理图片请求: {filename}, 时间: {start_time}")
    
    # 优先尝试固定路径，避免多次检查不同路径
    cwd = os.getcwd()
    primary_path = os.path.join(cwd, 'app', 'static', 'alarm_images')
    file_path = os.path.join(primary_path, filename)
    
    # 检查是否要下载图片
    download_mode = request.args.get('download', 'false').lower() == 'true'
    
    # 直接检查主要路径
    if os.path.isfile(file_path):
        logger.info(f"找到图片文件: {file_path}, 用时: {time.time() - start_time:.4f}秒")
        
        # 根据请求模式决定如何发送文件
        if download_mode:
            logger.info(f"下载模式: {filename}")
            return send_file(
                file_path,
                mimetype='application/octet-stream',  # 使用通用二进制流类型
                as_attachment=True,                   # 强制作为附件下载
                download_name=filename                # 设置下载文件名
            )
        else:
            # 查看模式添加缓存头
            logger.info(f"查看模式: {filename}, 总用时: {time.time() - start_time:.4f}秒")
            response = send_file(file_path, mimetype='image/jpeg')
            response.headers['Cache-Control'] = 'public, max-age=86400'  # 缓存1天
            return response
    
    # 如果在首选路径找不到，尝试其他可能的位置
    backup_paths = [
        os.path.join(cwd, 'static', 'alarm_images'),
        os.path.join(cwd, 'app/static', 'alarm_images')
    ]
    
    for path in backup_paths:
        file_path = os.path.join(path, filename)
        if os.path.isfile(file_path):
            logger.info(f"备用路径找到图片: {file_path}, 用时: {time.time() - start_time:.4f}秒")
            
            if download_mode:
                return send_file(
                    file_path,
                    mimetype='application/octet-stream',
                    as_attachment=True,
                    download_name=filename
                )
            else:
                response = send_file(file_path, mimetype='image/jpeg')
                response.headers['Cache-Control'] = 'public, max-age=86400'
                return response
    
    # 如果所有路径都找不到文件
    logger.error(f"未找到图片文件: {filename}, 用时: {time.time() - start_time:.4f}秒")
    return jsonify({'error': '图片文件不存在'}), 404

@bp.route('/thumbnails/<filename>')
def get_alarm_thumbnail(filename):
    """提供告警图片缩略图，添加性能优化和缓存"""
    start_time = time.time()
    logger.info(f"开始处理缩略图请求: {filename}, 时间: {start_time}")
    
    # 检查缓存中是否已存在此缩略图
    cache_key = f"thumb_{filename}"
    if cache_key in thumbnail_cache:
        cache_entry = thumbnail_cache[cache_key]
        # 检查缓存是否过期
        if time.time() - cache_entry['timestamp'] < CACHE_EXPIRY:
            logger.info(f"缩略图缓存命中: {filename}, 用时: {time.time() - start_time:.4f}秒")
            # 从内存中返回缩略图
            output = BytesIO(cache_entry['data'])
            output.seek(0)
            response = send_file(output, mimetype='image/jpeg')
            response.headers['Cache-Control'] = 'public, max-age=86400'  # 缓存1天
            return response
    
    # 优先尝试固定路径，减少多路径检查
    cwd = os.getcwd()
    primary_path = os.path.join(cwd, 'app', 'static', 'alarm_images')
    file_path = os.path.join(primary_path, filename)
    
    # 如果主路径不存在，再尝试备用路径
    if not os.path.isfile(file_path):
        backup_paths = [
            os.path.join(cwd, 'static', 'alarm_images'),
            os.path.join(cwd, 'app/static', 'alarm_images')
        ]
        
        for path in backup_paths:
            test_path = os.path.join(path, filename)
            if os.path.isfile(test_path):
                file_path = test_path
                logger.info(f"在备用路径找到原始图片: {file_path}, 用时: {time.time() - start_time:.4f}秒")
                break
    else:
        logger.info(f"在主路径找到原始图片: {file_path}, 用时: {time.time() - start_time:.4f}秒")
            
    if not os.path.isfile(file_path):
        logger.error(f"未找到原始图片文件: {filename}, 用时: {time.time() - start_time:.4f}秒")
        return jsonify({'error': '图片文件不存在'}), 404
    
    # 找到图片后，生成缩略图
    try:
        thumb_start = time.time()
        img = Image.open(file_path)
        img.thumbnail((100, 100))  # 缩小到100x100
        
        # 保存到内存
        output = BytesIO()
        img.save(output, format='JPEG', quality=75, optimize=True)
        
        # 缓存生成的缩略图
        output_data = output.getvalue()
        thumbnail_cache[cache_key] = {
            'data': output_data,
            'timestamp': time.time()
        }
        
        # 如果缓存太大，移除最旧的条目
        if len(thumbnail_cache) > CACHE_MAX_SIZE:
            oldest_key = min(thumbnail_cache.keys(), key=lambda k: thumbnail_cache[k]['timestamp'])
            del thumbnail_cache[oldest_key]
            
        logger.info(f"缩略图生成完成: {filename}, 生成用时: {time.time() - thumb_start:.4f}秒, 总用时: {time.time() - start_time:.4f}秒")
        
        # 返回生成的缩略图
        output.seek(0)
        response = send_file(output, mimetype='image/jpeg')
        response.headers['Cache-Control'] = 'public, max-age=86400'  # 缓存1天
        return response
    except Exception as e:
        logger.error(f"生成缩略图失败: {str(e)}, 用时: {time.time() - start_time:.4f}秒")
        # 降级到原始图片
        response = send_file(file_path, mimetype='image/jpeg')
        response.headers['Cache-Control'] = 'public, max-age=86400'
        return response

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
        confirmation_type = data.get('confirmation_type')
        
        # 记录请求信息
        logger.info(f"接收到告警确认请求: alarm_id={alarm_id}, confirmation_type={confirmation_type}")
        
        # 获取告警前先记录是否存在 - 不使用缓存
        db.session.expire_all()  # 清除会话缓存
        alarm = Alarm.query.get_or_404(alarm_id)
        logger.info(f"告警对象获取成功: id={alarm.id}, alarm_code={alarm.alarm_code}")
        
        # 详细记录告警确认前的完整状态
        logger.info(f"告警确认前状态: id={alarm.id}, alarm_code={alarm.alarm_code}, confirmation_type={alarm.confirmation_type}, "
                   f"is_confirmed={alarm.is_confirmed}, is_processed={alarm.is_processed}, "
                   f"confirmed_at={alarm.confirmed_at}")
        
        # 更新所有相关字段 - 注意保持状态不变
        alarm.confirmation_type = confirmation_type
        alarm.is_confirmed = True
        alarm.confirmed_at = datetime.now()
        # 只修改confirmation_type和is_confirmed，不改变is_processed
        # 业务逻辑：确认操作只设置告警确认类型，不会改变告警的处理状态
        
        # 提交前记录字段
        logger.info(f"提交前检查字段: confirmation_type={alarm.confirmation_type}, is_confirmed={alarm.is_confirmed}")
        
        # 确保提交
        db.session.commit()
        logger.info("数据库事务已提交")
        
        # 重新查询以验证写入成功
        alarm_after = Alarm.query.get(alarm_id)
        logger.info(f"提交后重新查询: id={alarm_after.id}, alarm_code={alarm_after.alarm_code}, confirmation_type={alarm_after.confirmation_type}, "
                   f"is_confirmed={alarm_after.is_confirmed}, is_processed={alarm_after.is_processed}, "
                   f"confirmed_at={alarm_after.confirmed_at}")
        
        return jsonify({
            'code': 200,
            'success': True, 
            'message': '告警确认成功',
            'data': {
                'id': alarm_id,
                'alarm_code': alarm_after.alarm_code,
                'confirmation_type': alarm_after.confirmation_type,
                'is_confirmed': alarm_after.is_confirmed,
                'confirmed_at': alarm_after.confirmed_at.strftime('%Y-%m-%d %H:%M:%S') if alarm_after.confirmed_at else None
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
        confirmation_type = data.get('confirmation_type')
        
        if not alarm_ids or not confirmation_type:
            return jsonify({
                'success': False,
                'message': '缺少必要参数'
            }), 400
        
        alarms = Alarm.query.filter(Alarm.id.in_(alarm_ids)).all()
        for alarm in alarms:
            alarm.is_confirmed = True
            alarm.confirmation_type = confirmation_type
            alarm.confirmed_at = datetime.now()
            # 不修改is_processed，只设置确认类型
        
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
            alarm.processed_time = datetime.now()
            alarm.processed_by = current_user.username if hasattr(current_user, 'username') else '系统'
            alarm.process_notes = notes  # 现在数据库模型中已有process_notes字段
        
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
                   f"processed_time={alarm.processed_time}")
        
        # 更新告警状态为已处理
        alarm.is_processed = True
        alarm.processed_time = datetime.now()
        alarm.processed_by = user.username if hasattr(user, 'username') else '系统'
        
        # 如果有备注，添加到告警处理记录中
        if notes:
            alarm.process_notes = notes
        
        # 提交前记录字段
        logger.info(f"提交前检查字段: is_processed={alarm.is_processed}")
        
        # 确保提交
        db.session.commit()
        logger.info("数据库事务已提交")
        
        # 重新查询以验证写入成功
        alarm_after = Alarm.query.get(alarm_id)
        logger.info(f"提交后重新查询: id={alarm_after.id}, alarm_code={alarm_after.alarm_code}, "
                   f"is_processed={alarm_after.is_processed}, processed_time={alarm_after.processed_time}")
        
        return jsonify({
            'code': 200,
            'success': True, 
            'message': '告警处理成功',
            'data': {
                'id': alarm_id,
                'alarm_code': alarm_after.alarm_code,
                'is_processed': alarm_after.is_processed,
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

def optimize_images(directory, quality=85):
    """压缩目录中的所有JPG图片"""
    for filename in os.listdir(directory):
        if filename.lower().endswith('.jpg'):
            filepath = os.path.join(directory, filename)
            try:
                img = Image.open(filepath)
                # 保存为WebP格式或优化的JPG
                img.save(filepath, quality=quality, optimize=True)
                print(f"已优化: {filepath}")
            except Exception as e:
                print(f"处理{filepath}时出错: {e}")