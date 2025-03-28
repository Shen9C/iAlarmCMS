from flask import Blueprint, render_template, request
from flask_login import login_required

bp = Blueprint('edge_devices', __name__, url_prefix='/edge_devices')

@bp.route('/device_list')
@login_required
def device_list():
    """边缘设备列表页面"""
    return render_template('edge_devices/list.html', user_token=request.args.get('user_token'))