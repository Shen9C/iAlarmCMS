from flask import Blueprint, jsonify, request
from flask_login import login_required
from app.models.settings import SystemConfig, KeyValueSetting, Settings
from app import db

bp = Blueprint('settings_api', __name__, url_prefix='/api/settings')

@bp.route('', methods=['POST'])
@login_required
def update_settings():
    """更新通用设置"""
    try:
        data = request.json
        for key, value in data.items():
            KeyValueSetting.set_setting(key, value)
        return jsonify({
            'code': 200,
            'message': '设置更新成功'
        })
    except Exception as e:
        return jsonify({
            'code': 500,
            'message': f'更新设置失败: {str(e)}'
        }), 500

@bp.route('/alarm', methods=['POST'])
@login_required
def update_alarm_settings():
    """更新告警设置"""
    try:
        settings = Settings.query.first()
        if not settings:
            settings = Settings()
            db.session.add(settings)
        
        settings.retention_days = request.json.get('retention_days', type=int)
        settings.refresh_interval = request.json.get('refresh_interval', type=int)
        db.session.commit()
        
        return jsonify({
            'code': 200,
            'message': '告警设置更新成功'
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'code': 500,
            'message': f'更新告警设置失败: {str(e)}'
        }), 500

@bp.route('/email', methods=['POST'])
@login_required
def update_email_settings():
    """更新邮件设置"""
    try:
        settings = Settings.query.first()
        if not settings:
            settings = Settings()
            db.session.add(settings)
        
        settings.smtp_server = request.json.get('smtp_server')
        settings.smtp_port = request.json.get('smtp_port', type=int)
        settings.sender_email = request.json.get('sender_email')
        
        password = request.json.get('email_password')
        if password:
            settings.email_password = password
        
        settings.enable_email = request.json.get('enable_email', False)
        db.session.commit()
        
        return jsonify({
            'code': 200,
            'message': '邮件设置更新成功'
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'code': 500,
            'message': f'更新邮件设置失败: {str(e)}'
        }), 500

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
        settings = Settings.query.first()
        if not settings:
            settings = Settings()
            db.session.add(settings)
        
        settings.system_name_zh = request.json.get('system_name_zh')
        settings.system_name_en = request.json.get('system_name_en')
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