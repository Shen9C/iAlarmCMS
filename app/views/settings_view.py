from flask import Blueprint, render_template, request
from flask_login import login_required
from app.models.settings import SystemConfig, Settings

bp = Blueprint('settings', __name__)

@bp.route('/settings')
@login_required
def index():
    """设置页面视图"""
    try:
        settings = Settings.query.first()
        if not settings:
            settings = Settings()
        
        system_config = SystemConfig.get_instance()
        
        return render_template('settings/settings_index.html',
                             settings=settings,
                             system_config=system_config,
                             user_token=request.args.get('user_token'))
    except Exception as e:
        return render_template('settings/settings_index.html',
                             error=str(e),
                             user_token=request.args.get('user_token'))