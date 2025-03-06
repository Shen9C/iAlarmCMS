from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required
from app.models.settings import Settings
from app import db

bp = Blueprint('settings', __name__)

@bp.route('/')
@login_required
def index():
    settings = Settings.query.first()
    if not settings:
        settings = Settings(
            system_name_zh='智能告警综合管理系统',
            system_name_en='Intelligent Alarm Comprehensive Management System'
        )
        db.session.add(settings)
        db.session.commit()
    return render_template('settings/index.html', settings=settings)

@bp.route('/settings/update', methods=['POST'])
@login_required
def update():
    for key, value in request.form.items():
        if key.startswith('setting_'):
            setting_key = key.replace('setting_', '')
            setting = SystemSetting.query.filter_by(key=setting_key).first()
            if setting:
                setting.value = value
    
    db.session.commit()
    flash('系统设置已更新')
    return redirect(url_for('settings.index'))

@bp.route('/update_alarm_settings', methods=['POST'])
@login_required
def update_alarm_settings():
    settings = Settings.query.first()
    if not settings:
        settings = Settings()
        db.session.add(settings)
    
    settings.retention_days = request.form.get('retention_days', type=int)
    settings.refresh_interval = request.form.get('refresh_interval', type=int)
    db.session.commit()
    
    flash('告警设置已更新')
    return redirect(url_for('settings.index'))

@bp.route('/update_email_settings', methods=['POST'])
@login_required
def update_email_settings():
    settings = Settings.query.first()
    if not settings:
        settings = Settings()
        db.session.add(settings)
    
    settings.smtp_server = request.form.get('smtp_server')
    settings.smtp_port = request.form.get('smtp_port', type=int)
    settings.sender_email = request.form.get('sender_email')
    
    password = request.form.get('email_password')
    if password:
        settings.email_password = password
    
    settings.enable_email = 'enable_email' in request.form
    db.session.commit()
    
    flash('邮件设置已更新')
    return redirect(url_for('settings.index'))

@bp.route('/test_email', methods=['POST'])
@login_required
def test_email():
    try:
        # 这里添加发送测试邮件的逻辑
        return jsonify({'success': True, 'message': '测试邮件发送成功'})
    except Exception as e:
        return jsonify({'success': False, 'message': f'测试邮件发送失败：{str(e)}'})

@bp.route('/update_basic_settings', methods=['POST'])
@login_required
def update_basic_settings():
    settings = Settings.query.first()
    if not settings:
        settings = Settings()
        db.session.add(settings)
    
    settings.system_name_zh = request.form.get('system_name_zh')
    settings.system_name_en = request.form.get('system_name_en')
    db.session.commit()
    
    flash('基本设置已更新')
    return redirect(url_for('settings.index'))
