from flask import Blueprint, render_template, request, flash, redirect, url_for, jsonify, current_app
from flask_login import login_required, current_user  # 添加current_user导入
from app.models.edge_devices import EdgeDevice
from app.models.alarms import Alarm
from app.utils.decorators import admin_required
from app import db
import logging
import traceback
from datetime import datetime
import uuid

bp = Blueprint('edge_devices', __name__, url_prefix='/edge_devices')

@bp.route('/')
@login_required
def index():
    """边缘设备管理页面"""
    try:
        logging.debug("正在访问边缘设备管理页面(views/edge_devices_view.py)")
        
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 15, type=int)
        logging.debug(f"分页参数: page={page}, per_page={per_page}")
        
        # 获取筛选参数
        device_name = request.args.get('device_name', '')
        ip_address = request.args.get('ip_address', '')
        status = request.args.get('status', '')
        logging.debug(f"筛选参数: device_name={device_name}, ip_address={ip_address}, status={status}")
        
        # 构建查询
        query = EdgeDevice.query
        
        # 根据筛选参数进行过滤
        if device_name:
            query = query.filter(EdgeDevice.device_name.like(f'%{device_name}%'))
        if ip_address:
            query = query.filter(EdgeDevice.ip_address.like(f'%{ip_address}%'))
        if status in ['online', 'error', 'offline']:
            query = query.filter(EdgeDevice.status == status)
        
        # 添加默认排序（按ID升序）
        query = query.order_by(EdgeDevice.id.asc())
        
        # 记录查询结果数量
        devices_count = query.count()
        logging.debug(f"筛选后设备总数: {devices_count}")
        
        # 分页
        pagination = query.paginate(
            page=page, per_page=per_page, error_out=False
        )
        
        # 记录传递给模板的参数
        logging.debug(f"传递给模板的设备数量: {len(pagination.items)}")
        
        # 尝试渲染模板
        logging.debug("开始渲染模板...")
        try:
            render_params = {
                'devices': pagination.items,
                'pagination': pagination,
                'filter_params': {
                    'device_name': device_name,
                    'ip_address': ip_address,
                    'status': status
                }
            }
            logging.debug(f"模板参数: {render_params}")
            result = render_template('edge_devices/edge_devices_index.html', **render_params)
            logging.debug("模板渲染成功")
            return result
        except Exception as template_error:
            logging.error(f"模板渲染错误: {str(template_error)}")
            logging.error(traceback.format_exc())
            raise  # 重新抛出异常以便外层捕获
        
    except Exception as e:
        logging.error(f"访问边缘设备管理页面失败: {str(e)}")
        logging.error(traceback.format_exc())
        flash(f"加载边缘设备管理页面失败: {str(e)}", "error")
        return render_template('error.html', error_message=str(e), stack_trace=traceback.format_exc()), 500

@bp.route('/detail/<string:device_id>')
@login_required
def device_detail(device_id):
    """边缘设备详情页面，展示包括设备编号在内的完整信息"""
    try:
        device = EdgeDevice.query.filter_by(device_id=device_id).first_or_404()
        return render_template('edge_devices/device_detail.html', device=device)
    except Exception as e:
        flash(f'加载设备详情失败: {str(e)}', 'error')
        return redirect(url_for('edge_devices.index'))

@bp.route('/auth/<int:device_id>')
@login_required
@admin_required
def device_auth_detail(device_id):
    """边缘设备认证详情页面"""
    try:
        device = EdgeDevice.query.get_or_404(device_id)
        return render_template('edge_devices/auth_detail.html', device=device)
    except Exception as e:
        flash(f'加载设备认证信息失败: {str(e)}', 'error')
        return redirect(url_for('edge_devices.index'))

@bp.route('/auth/<int:device_id>/regenerate', methods=['POST'])
@login_required
@admin_required
def regenerate_device_auth(device_id):
    """重新生成设备认证密钥"""
    try:
        device = EdgeDevice.query.get_or_404(device_id)
        device.secret_key = EdgeDevice.generate_secret_key()
        db.session.commit()
        
        flash('设备认证密钥已更新', 'success')
        return redirect(url_for('edge_devices.device_auth_detail', device_id=device_id))
    except Exception as e:
        flash(f'更新认证密钥失败: {str(e)}', 'error')
        return redirect(url_for('edge_devices.device_auth_detail', device_id=device_id))

@bp.route('/edge_devices/add', methods=['POST'])
@login_required
@admin_required
def add_device():
    """添加新设备"""
    try:
        data = request.get_json()
        if not data or 'device_name' not in data or 'ip_address' not in data:
            return jsonify({"code": 400, "message": "缺少必要参数"}), 400

        device_name = data['device_name']
        ip_address = data['ip_address']

        # 检查设备名称是否已存在
        if EdgeDevice.query.filter_by(device_name=device_name).first():
            return jsonify({"code": 400, "message": "设备名称已存在"}), 400

        # 创建新设备
        device = EdgeDevice(
            device_name=device_name,
            ip_address=ip_address,
            device_id=f"DEV{uuid.uuid4().hex[:8]}",
            secret_key=EdgeDevice.generate_secret_key()
        )

        db.session.add(device)
        db.session.commit()

        return jsonify({
            "code": 200,
            "message": "设备添加成功",
            "data": device.to_dict()
        }), 200

    except Exception as e:
        current_app.logger.error(f"添加设备失败: {str(e)}")
        db.session.rollback()
        return jsonify({"code": 500, "message": "服务器内部错误"}), 500

@bp.route('/edge_devices/<int:device_id>/regenerate_key', methods=['POST'])
@login_required
@admin_required
def regenerate_key(device_id):
    """重新生成设备密钥"""
    try:
        device = EdgeDevice.query.get_or_404(device_id)
        device.secret_key = EdgeDevice.generate_secret_key()
        db.session.commit()

        return jsonify({
            "code": 200,
            "message": "密钥重新生成成功",
            "data": {"secret_key": device.secret_key}
        }), 200

    except Exception as e:
        current_app.logger.error(f"重新生成密钥失败: {str(e)}")
        db.session.rollback()
        return jsonify({"code": 500, "message": "服务器内部错误"}), 500

@bp.route('/edge_devices/<int:device_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_device(device_id):
    """删除设备"""
    try:
        device = EdgeDevice.query.get_or_404(device_id)
        
        # 检查设备是否有关联的告警
        if Alarm.query.filter_by(device_id=device.device_id).first():
            return jsonify({
                "code": 400,
                "message": "设备存在关联的告警记录，无法删除"
            }), 400

        db.session.delete(device)
        db.session.commit()

        return jsonify({
            "code": 200,
            "message": "设备删除成功"
        }), 200

    except Exception as e:
        current_app.logger.error(f"删除设备失败: {str(e)}")
        db.session.rollback()
        return jsonify({"code": 500, "message": "服务器内部错误"}), 500

# 创建API蓝图
api_bp = Blueprint('edge_devices_view', __name__, url_prefix='/api/edge_devices')

@api_bp.route('/', methods=['GET'])
@login_required
def get_devices():
    """获取所有边缘设备列表，包含设备编号"""
    try:
        devices = EdgeDevice.query.all()
        devices_list = []
        for device in devices:
            devices_list.append({
                'id': device.id,
                'device_id': device.device_id,  # 确保包含设备编号
                'device_name': device.device_name,
                'ip_address': device.ip_address,
                'status': device.status,
                'last_heartbeat': device.last_auth_time.strftime('%Y-%m-%d %H:%M:%S') if device.last_auth_time else None
            })
        return jsonify({"code": 200, "message": "获取设备列表成功", "data": devices_list}), 200
    except Exception as e:
        return jsonify({"code": 500, "message": f"获取设备列表失败: {str(e)}"}), 500

@api_bp.route('/<string:device_id>', methods=['GET'])
@login_required
def get_device(device_id):
    """根据设备编号获取设备详情"""
    try:
        device = EdgeDevice.query.filter_by(device_id=device_id).first()
        if not device:
            return jsonify({"code": 404, "message": "设备不存在"}), 404
            
        device_info = {
            'id': device.id,
            'device_id': device.device_id,
            'device_name': device.device_name,
            'ip_address': device.ip_address,
            'status': device.status,
            'last_heartbeat': device.last_auth_time.strftime('%Y-%m-%d %H:%M:%S') if device.last_auth_time else None,
            'secret_key': device.secret_key if current_user.is_admin else None  # 仅管理员可见密钥
        }
        return jsonify({"code": 200, "message": "获取设备详情成功", "data": device_info}), 200
    except Exception as e:
        return jsonify({"code": 500, "message": f"获取设备详情失败: {str(e)}"}), 500

@api_bp.route('/test', methods=['GET'])
def test_api():
    """测试API是否正常工作"""
    from datetime import datetime
    return jsonify({"code": 200, "message": "API工作正常", "time": str(datetime.now())}), 200

@api_bp.route('/<int:device_id>/regenerate_keys', methods=['POST'])
@login_required
@admin_required
def regenerate_keys(device_id):
    """重新生成设备密钥（作为regenerate_device_secret的别名）"""
    try:
        device = EdgeDevice.query.get_or_404(device_id)
        
        # 生成新的密钥
        device.secret_key = EdgeDevice.generate_secret_key()
        
        db.session.commit()
        
        return jsonify({"code": 200, "message": "密钥重新生成成功", "data": {"secret_key": device.secret_key}}), 200
    
    except Exception as e:
        db.session.rollback()
        return jsonify({"code": 500, "message": f"重新生成密钥失败: {str(e)}"}), 500