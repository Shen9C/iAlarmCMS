from flask import Blueprint, request, jsonify, redirect, url_for, flash, session
from flask_login import login_required
from app.models.edge_devices import EdgeDevice
from app.utils.decorators import admin_required  # 确保这个导入存在
# 添加 device_auth_required 装饰器的导入
from app.utils.decorators import device_auth_required  # 添加这行导入
from app import db
import secrets
import string

from datetime import datetime
import logging

logger = logging.getLogger(__name__)
# 创建API蓝图，URL前缀为 /api/edge_devices
bp = Blueprint('edge_devices_api', __name__, url_prefix='/api/edge_devices')

@bp.route('', methods=['GET'])
@login_required
def get_edge_devices():
    """获取所有边缘设备"""
    try:
        devices = EdgeDevice.query.all()
        return jsonify({
            'code': 200,
            'message': '获取成功',
            'data': [device.to_dict() for device in devices]
        })
    except Exception as e:
        logger.error(f"获取边缘设备列表失败: {str(e)}")
        return jsonify({
            'code': 500,
            'message': f'获取边缘设备列表失败: {str(e)}'
        }), 500

@bp.route('', methods=['POST'])
@login_required
# 移除 @admin_required 装饰器
def add_device():
    """添加新的边缘设备"""
    try:
        # 判断请求内容类型
        if request.content_type and 'application/json' in request.content_type:
            data = request.get_json()
        else:
            # 处理表单提交
            data = request.form.to_dict()
        
        if not data:
            return jsonify({"code": 400, "message": "无效的请求数据"}), 400
        
        device_name = data.get('device_name')  # 修改为与表单字段名一致
        ip_address = data.get('ip_address')
        device_id = data.get('device_id')  # 添加对设备编号的处理
        
        if not device_name or not ip_address:
            return jsonify({"code": 400, "message": "设备名称和IP地址不能为空"}), 400
        
        # 检查设备名称是否已存在
        existing_device = EdgeDevice.query.filter_by(device_name=device_name).first()
        if existing_device:
            return jsonify({"code": 400, "message": "设备名称已存在"}), 400
        
        # 检查IP地址是否已存在
        existing_ip = EdgeDevice.query.filter_by(ip_address=ip_address).first()
        if existing_ip:
            return jsonify({"code": 400, "message": "IP地址已被使用"}), 400
        
        # 创建新设备 - 使用模型自己的初始化方法
        new_device = EdgeDevice(
            device_name=device_name,
            ip_address=ip_address,
            device_id=device_id
        )
        
        db.session.add(new_device)
        db.session.commit()
        
        # 如果是表单提交，重定向回设备列表页面
        if not request.content_type or 'application/json' not in request.content_type:
            return redirect(url_for('edge_devices.index'))
            
        return jsonify({"code": 200, "message": "设备添加成功", "data": {"id": new_device.id}}), 200
    
    except Exception as e:
        db.session.rollback()
        logger.error(f"添加设备失败: {str(e)}")
        return jsonify({"code": 500, "message": f"添加设备失败: {str(e)}"}), 500

# 为现有表单添加一个重定向回边缘设备列表的路由
@bp.route('/create_device', methods=['POST'])
@login_required
def create_device():
    """处理添加设备表单提交"""
    return add_device()

@bp.route('/<int:device_id>', methods=['PUT'])
@login_required
def update_edge_device(device_id):
    """更新边缘设备"""
    try:
        device = EdgeDevice.query.get(device_id)
        if not device:
            return jsonify({
                'code': 404,
                'message': f'设备ID {device_id} 不存在'
            }), 404
        
        if request.content_type and 'application/json' in request.content_type:
            data = request.get_json()
        else:
            data = request.form.to_dict()
        
        device_name = data.get('device_name')
        ip_address = data.get('ip_address')
        new_device_id = data.get('device_id')
        
        # 验证必填字段
        if not device_name or not ip_address:
            return jsonify({
                'code': 400,
                'message': '设备名称和IP地址不能为空'
            }), 400
        
        # 检查设备名称是否已存在（排除当前设备）
        existing_device = EdgeDevice.query.filter_by(device_name=device_name).first()
        if existing_device and existing_device.id != device_id:
            return jsonify({
                'code': 400,
                'message': f'设备名称 {device_name} 已存在'
            }), 400
        
        # 如果修改了设备ID，检查是否已存在
        if new_device_id and new_device_id != device.device_id:
            existing_by_device_id = EdgeDevice.query.filter_by(device_id=new_device_id).first()
            if existing_by_device_id:
                return jsonify({
                    'code': 400,
                    'message': f'设备编号 {new_device_id} 已存在'
                }), 400
            device.device_id = new_device_id
        
        # 更新设备信息
        device.device_name = device_name
        device.ip_address = ip_address
        
        # 如果请求中包含了重新生成密钥的标志
        if data.get('regenerate_keys'):
            device.secret_key = EdgeDevice.generate_secret_key()
        
        db.session.commit()
        
        # 如果是表单提交，重定向回设备列表页面
        if not request.content_type or 'application/json' not in request.content_type:
            return redirect(url_for('edge_devices.index'))
        
        return jsonify({
            'code': 200,
            'message': '更新成功',
            'data': device.to_dict()
        })
    except Exception as e:
        db.session.rollback()
        logger.error(f"更新边缘设备失败: {str(e)}")
        return jsonify({
            'code': 500,
            'message': f'更新边缘设备失败: {str(e)}'
        }), 500

@bp.route('/<int:device_id>', methods=['DELETE'])
@login_required
def delete_edge_device(device_id):
    """删除边缘设备"""
    try:
        # 首先检查设备是否存在
        device = EdgeDevice.query.get(device_id)
        if not device:
            return jsonify({
                'code': 404,
                'message': f'设备ID {device_id} 不存在'
            }), 404
        
        # 检查该设备是否有关联的任务 - 需要检查更多可能的关联方式
        from app.models.tasks import Task
        from sqlalchemy import or_
        
        # 尝试多种可能的关联方式
        associated_tasks = Task.query.filter(
            or_(
                Task.device_id == str(device_id),
                Task.device_id == device_id,
                Task.device_id == device.device_id
            )
        ).all()
        
        if associated_tasks:
            task_count = len(associated_tasks)
            # 返回错误，阻止删除
            task_ids = [str(task.id) for task in associated_tasks[:5]]
            task_id_str = ", ".join(task_ids)
            if len(associated_tasks) > 5:
                task_id_str += "..."
                
            return jsonify({
                'code': 400,
                'message': f'删除失败：该设备关联了{task_count}个任务(任务ID: {task_id_str})，请先删除关联的任务。'
            }), 400
        
        # 删除设备前，先将关联的任务手动解除关联
        # 这是为了处理可能存在的外键约束
        all_tasks = Task.query.all()
        updated_tasks = []
        for task in all_tasks:
            try:
                # 检查各种可能的设备ID格式
                if (task.device_id == str(device_id) or 
                    task.device_id == device_id or 
                    (hasattr(task, 'edge_device_id') and task.edge_device_id == device_id) or
                    (device.device_id and task.device_id == device.device_id)):
                    
                    # 设置一个默认设备ID或者添加一个标记
                    task.device_id = "DELETED_DEVICE"
                    updated_tasks.append(task.id)
            except Exception as e:
                logger.warning(f"处理任务 {task.id} 与设备关联时出错: {str(e)}")
        
        if updated_tasks:
            logger.info(f"已解除 {len(updated_tasks)} 个任务与设备 {device_id} 的关联: {updated_tasks}")
            db.session.commit()
        
        # 删除设备
        db.session.delete(device)
        db.session.commit()
        
        return jsonify({
            'code': 200,
            'message': '删除成功'
        })
    except Exception as e:
        db.session.rollback()
        logger.error(f"删除边缘设备失败: {str(e)}")
        return jsonify({
            'code': 500,
            'message': f'删除边缘设备失败: {str(e)}'
        }), 500

@bp.route('/<int:device_id>/regenerate_keys', methods=['POST'])
@login_required
def regenerate_keys(device_id):
    """重新生成设备密钥"""
    try:
        device = EdgeDevice.query.get(device_id)
        if not device:
            return jsonify({
                'code': 404,
                'message': f'设备ID {device_id} 不存在'
            }), 404
        
        device.secret_key = EdgeDevice.generate_secret_key()
        db.session.commit()
        
        # 如果是表单提交，重定向回设备列表页面
        if not request.content_type or 'application/json' not in request.content_type:
            return redirect(url_for('edge_devices.index'))
        
        return jsonify({
            'code': 200,
            'message': '密钥重新生成成功',
            'data': {
                'secret_key': device.secret_key
            }
        })
    except Exception as e:
        db.session.rollback()
        logger.error(f"重新生成设备密钥失败: {str(e)}")
        return jsonify({
            'code': 500,
            'message': f'重新生成设备密钥失败: {str(e)}'
        }), 500

@bp.route('/auth/verify', methods=['POST'])
# 在文件的第196行附近，有一个使用了 device_auth_required 装饰器的函数
@device_auth_required  # 现在这个装饰器已经被正确导入
def some_function():
    """验证边缘设备认证"""
    try:
        device_id = request.headers.get('X-Device-ID')
        device = EdgeDevice.query.get(device_id)
        if not device:
            return jsonify({
                'code': 404,
                'message': '设备不存在'
            }), 404

        return jsonify({
            'code': 200,
            'message': '认证成功',
            'data': {
                'device_id': device_id,
                'device_name': device.device_name,
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
        })
    except Exception as e:
        logger.error(f"设备认证验证失败: {str(e)}")
        return jsonify({
            'code': 500,
            'message': f'认证验证失败: {str(e)}'
        }), 500

@bp.route('/auth/status/<int:device_id>', methods=['GET'])
@login_required
def get_device_auth_status(device_id):
    """获取边缘设备认证状态"""
    try:
        device = EdgeDevice.query.get(device_id)
        if not device:
            return jsonify({
                'code': 404,
                'message': '设备不存在'
            }), 404

        return jsonify({
            'code': 200,
            'message': '获取成功',
            'data': {
                'device_id': device.id,
                'device_name': device.device_name,
                'secret_key': device.secret_key,
                'auth_status': 'active',
                'last_auth_time': device.last_auth_time.strftime('%Y-%m-%d %H:%M:%S') if hasattr(device, 'last_auth_time') and device.last_auth_time else None
            }
        })
    except Exception as e:
        logger.error(f"获取设备认证状态失败: {str(e)}")
        return jsonify({
            'code': 500,
            'message': f'获取认证状态失败: {str(e)}'
        }), 500

# 增加一个通用的更新设备路由，用于表单提交
@bp.route('/update_device', methods=['POST', 'GET'])
@login_required
def update_device():
    """处理更新设备表单提交或显示编辑页面"""
    try:
        # 处理GET请求 - 显示编辑页面或打开编辑模态框
        if request.method == 'GET':
            device_id = request.args.get('id')
            if not device_id:
                flash('设备ID不能为空', 'error')
                return redirect(url_for('edge_devices.index'))
            
            # 查找设备信息
            device = EdgeDevice.query.get(int(device_id))
            if not device:
                flash(f'设备 ID {device_id} 不存在', 'error')
                return redirect(url_for('edge_devices.index'))
            
            # 将设备信息添加到会话中，以便在前端渲染时使用
            session['edit_device'] = {
                'id': device.id,
                'device_id': device.device_id,
                'device_name': device.device_name,
                'ip_address': device.ip_address
            }
            
            # 记录会话信息
            logger.info(f"设置会话数据: edit_device={session['edit_device']}")
            
            # 重定向回索引页，并附带打开编辑模态框的查询参数
            return redirect(url_for('edge_devices.index', edit=device_id))
        
        # 处理POST请求 - 更新设备信息
        device_id = request.form.get('id')
        if not device_id:
            return jsonify({"code": 400, "message": "设备ID不能为空"}), 400
        
        # 调用原有的更新函数
        return update_edge_device(int(device_id))
    except Exception as e:
        logger.error(f"更新设备失败: {str(e)}")
        flash(f"更新设备失败: {str(e)}", "error")
        return redirect(url_for('edge_devices.index'))

# 添加删除设备路由，用于表单提交
@bp.route('/delete_device', methods=['POST'])
@login_required
def delete_device():
    """处理删除设备表单提交"""
    try:
        from flask import flash, redirect, url_for
        device_id = request.form.get('device_id')
        logger.info(f"收到删除设备请求，设备ID: {device_id}")
        
        if not device_id:
            logger.error("设备ID为空")
            flash("设备ID不能为空", "error")
            return redirect(url_for('edge_devices.index'))
        
        # 首先检查设备是否存在
        device = EdgeDevice.query.get(int(device_id))
        if not device:
            logger.error(f"设备ID {device_id} 不存在")
            flash(f'设备ID {device_id} 不存在', "error")
            return redirect(url_for('edge_devices.index'))
        
        logger.info(f"找到设备: ID={device.id}, 名称={device.device_name}, 编号={device.device_id}")
        
        # 检查该设备是否有关联的任务 - 需要检查更多可能的关联方式
        from app.models.tasks import Task
        from sqlalchemy import or_
        
        # 尝试多种可能的关联方式
        tasks_query = Task.query.filter(
            or_(
                Task.device_id == str(device_id),
                Task.device_id == device_id,
                Task.device_id == device.device_id  # 可能使用设备编号而非ID
            )
        )
        
        # 先检查任务数量
        task_count = tasks_query.count()
        logger.info(f"设备关联的任务数量: {task_count}")
        
        if task_count > 0:
            # 我们有两个选择:
            # 1. 阻止删除并提示用户
            # 2. 级联删除相关任务
            
            # 选择方案2: 级联删除 - 如果需要阻止删除，取消注释下面的代码，注释掉级联删除代码
            # task_ids = [str(task.id) for task in tasks_query.limit(5).all()]
            # task_id_str = ", ".join(task_ids)
            # if task_count > 5:
            #     task_id_str += "..."
            # logger.warning(f"删除失败: 设备关联了{task_count}个任务(IDs: {task_id_str})")
            # flash(f'删除失败：设备"{device.device_name}"关联了{task_count}个任务(任务ID: {task_id_str})，请先删除关联的任务。', "error")
            # return redirect(url_for('edge_devices.index'))
            
            # 级联删除相关任务
            associated_tasks = tasks_query.all()
            task_ids = [task.id for task in associated_tasks]
            logger.info(f"将级联删除关联的任务: {task_ids}")
            
            # 开始删除任务
            for task in associated_tasks:
                try:
                    logger.info(f"删除任务: {task.id}")
                    db.session.delete(task)
                except Exception as task_error:
                    logger.error(f"删除任务 {task.id} 失败: {str(task_error)}")
            
            # 提交任务删除
            try:
                db.session.commit()
                logger.info(f"已成功删除 {len(task_ids)} 个关联任务")
            except Exception as commit_error:
                db.session.rollback()
                logger.error(f"提交任务删除失败: {str(commit_error)}")
                flash(f'删除关联任务失败: {str(commit_error)}', "error")
                return redirect(url_for('edge_devices.index'))
        
        # 删除设备
        device_name = device.device_name
        logger.info(f"开始删除设备: {device_name}")
        db.session.delete(device)
        
        try:
            db.session.commit()
            logger.info(f"设备 {device_name} 删除成功")
            flash(f'设备"{device_name}"删除成功', 'success')
        except Exception as device_error:
            db.session.rollback()
            logger.error(f"设备删除提交失败: {str(device_error)}")
            flash(f'设备删除失败: {str(device_error)}', 'error')
        
        return redirect(url_for('edge_devices.index'))
    except Exception as e:
        db.session.rollback()
        logger.error(f"删除设备失败: {str(e)}")
        
        # 重定向回设备列表页面，并显示错误消息
        flash(f'删除设备失败: {str(e)}', 'error')
        return redirect(url_for('edge_devices.index'))

# 添加重新生成密钥路由，用于表单提交
@bp.route('/regenerate_key', methods=['POST'])
@login_required
def regenerate_key():
    """处理重新生成密钥表单提交"""
    try:
        device_id = request.form.get('device_id')
        if not device_id:
            return jsonify({"code": 400, "message": "设备ID不能为空"}), 400
        
        # 调用原有的重新生成密钥函数
        return regenerate_keys(int(device_id))
    except Exception as e:
        logger.error(f"重新生成密钥失败: {str(e)}")
        return jsonify({"code": 500, "message": f"重新生成密钥失败: {str(e)}"}), 500