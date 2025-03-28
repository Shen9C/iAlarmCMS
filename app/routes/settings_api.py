from flask import Blueprint, jsonify, request
from flask_login import login_required, current_user
from app.models.settings import SystemConfig, KeyValueSetting
from app import db
import logging

logger = logging.getLogger(__name__)
bp = Blueprint('settings_api', __name__, url_prefix='/api/settings')

@bp.route('', methods=['GET'])
@login_required
def get_settings():
    """获取系统设置"""
    try:
        system_config = SystemConfig.get_instance()
        settings = KeyValueSetting.get_all_settings()
        return jsonify({
            'status': 'success',
            'data': {
                'system_config': {
                    'system_name_zh': system_config.system_name_zh,
                    'system_name_en': system_config.system_name_en,
                    'company_name': system_config.company_name,
                    'logo_url': system_config.logo_url,
                    'theme_color': system_config.theme_color
                },
                'settings': settings
            }
        })
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@bp.route('', methods=['PUT'])
@login_required
def update_settings():
    """更新系统设置"""
    try:
        data = request.get_json()
        
        # 更新系统配置
        system_config = SystemConfig.get_instance()
        for key, value in data.get('system_config', {}).items():
            if hasattr(system_config, key):
                setattr(system_config, key, value)
        
        # 更新键值对设置
        for key, value in data.get('settings', {}).items():
            KeyValueSetting.set_setting(key, value)
        
        return jsonify({'status': 'success'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@bp.route('/email/test', methods=['POST'])
@login_required
def test_email():
    """测试邮件发送"""
    try:
        # 这里添加发送测试邮件的逻辑
        return jsonify({
            'code': 200,
            'message': '测试邮件发送成功'
        })
    except Exception as e:
        return jsonify({
            'code': 500,
            'message': f'测试邮件发送失败：{str(e)}'
        }), 500

@bp.route('/basic', methods=['POST'])
@login_required
def update_basic_settings():
    """更新基本设置"""
    try:
        # 获取系统配置实例
        system_config = SystemConfig.get_instance()
        
        # 更新基本设置
        system_config.system_name_zh = request.json.get('system_name_zh')
        system_config.system_name_en = request.json.get('system_name_en')
        db.session.commit()
        
        return jsonify({
            'code': 200,
            'message': '基本设置更新成功'
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'code': 500,
            'message': f'更新基本设置失败: {str(e)}'
        }), 500

@bp.route('/alarm', methods=['POST'])
@login_required
def update_alarm_settings():
    """更新告警设置"""
    try:
        # 更新告警设置
        retention_days = request.json.get('retention_days', type=int)
        refresh_interval = request.json.get('refresh_interval', type=int)
        
        KeyValueSetting.set_setting('retention_days', str(retention_days))
        KeyValueSetting.set_setting('refresh_interval', str(refresh_interval))
        
        return jsonify({
            'code': 200,
            'message': '告警设置更新成功'
        })
    except Exception as e:
        return jsonify({
            'code': 500,
            'message': f'更新告警设置失败: {str(e)}'
        }), 500

@bp.route('/email', methods=['POST'])
@login_required
def update_email_settings():
    """更新邮件设置"""
    try:
        # 更新邮件设置
        email_settings = {
            'smtp_server': request.json.get('smtp_server'),
            'smtp_port': str(request.json.get('smtp_port', 587)),
            'sender_email': request.json.get('sender_email'),
            'enable_email': str(request.json.get('enable_email', False)).lower()
        }
        
        # 如果提供了新密码，则更新密码
        password = request.json.get('email_password')
        if password:
            email_settings['email_password'] = password
            
        # 保存所有邮件设置
        for key, value in email_settings.items():
            KeyValueSetting.set_setting(key, value)
        
        return jsonify({
            'code': 200,
            'message': '邮件设置更新成功'
        })
    except Exception as e:
        return jsonify({
            'code': 500,
            'message': f'更新邮件设置失败: {str(e)}'
        }), 500

@bp.route('/config/<key>')
@login_required
def get_config(key):
    """获取指定配置项"""
    try:
        value = KeyValueSetting.get_setting(key)
        return jsonify({
            'code': 200,
            'data': {
                'key': key,
                'value': value
            }
        })
    except Exception as e:
        return jsonify({
            'code': 500,
            'message': f'获取配置失败: {str(e)}'
        }), 500