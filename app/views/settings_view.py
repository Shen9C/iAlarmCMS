from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from app.models.settings import SystemConfig, KeyValueSetting

bp = Blueprint('settings', __name__, url_prefix='/settings')  # 添加 url_prefix

@bp.route('/')
@login_required
def index():
    """设置页面视图"""
    # 检查权限
    if current_user.role != 'admin':
        flash('您没有权限访问此页面')
        return redirect(url_for('alarms_view.index', user_token=request.args.get('user_token')))
    
    try:
        # 获取系统配置
        system_config = SystemConfig.get_instance()
        # 获取键值对设置，如果获取失败则返回空字典
        settings = KeyValueSetting.get_all_settings() or {}
        
        return render_template('settings/settings_index.html',
                             system_config=system_config,
                             settings=settings,
                             user_token=request.args.get('user_token'))
    except Exception as e:
        flash(f'加载设置失败: {str(e)}')
        return render_template('settings/settings_index.html',
                             system_config=None,
                             settings={},
                             user_token=request.args.get('user_token'))