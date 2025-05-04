from flask import Blueprint, jsonify
from flask_login import login_required
from app.models.edge_devices import EdgeDevice
from app.utils.auth_helper import admin_required
from app import db

bp = Blueprint('edge_devices_api', __name__)

@bp.route('/<int:device_id>/regenerate_keys', methods=['POST'])
@login_required
@admin_required
def regenerate_keys(device_id):
    try:
        device = EdgeDevice.query.get_or_404(device_id)
        device.secret_key = EdgeDevice.generate_secret_key()
        db.session.commit()
        return jsonify({'code': 200, 'message': '密钥已重新生成', 'secret_key': device.secret_key})
    except Exception as e:
        db.session.rollback()
        return jsonify({'code': 500, 'message': f'密钥重生成失败: {str(e)}'}), 500 