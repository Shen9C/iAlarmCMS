import os
import json
from pathlib import Path

def load_machine_config():
    """加载机机认证配置"""
    config_path = Path(__file__).parent.parent / 'scripts' / 'config.json'
    if config_path.exists():
        with open(config_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {
        'api_url': 'http://localhost:5000/api/v1/machine/alarms/batch',
        'access_key': 'AKID123456789',
        'secret_key': 'SK987654321',
        'device_names': ['1号油井', '2号油井', '3号油井', '4号油井', '5号油井', '6号油井', '7号油井'],
        'alarm_types': ['异常停机', '毛辫子断', '皮带断裂', '发动机冒烟', '原油泄露', '压力表异常']
    }

class Config:
    SECRET_KEY = 'your-secret-key'
    SQLALCHEMY_DATABASE_URI = 'sqlite:///alarms.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'app', 'static', 'images')
