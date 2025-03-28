import pytest
from app.models.alarms import Alarm
from app import db
from datetime import datetime

def test_index_page(client):
    # 先登录
    client.post('/login', data={
        'username': 'test_user',
        'password': 'test_password'
    })
    
    response = client.get('/')
    assert response.status_code == 200
    assert b'\xe5\x91\x8a\xe8\xad\xa6\xe4\xbf\xa1\xe6\x81\xaf\xe7\xae\xa1\xe7\x90\x86\xe7\xb3\xbb\xe7\xbb\x9f' in response.data

def test_add_alarm(client, app):
    # 先登录
    client.post('/login', data={
        'username': 'test_user',
        'password': 'test_password'
    })
    
    response = client.post('/add_alarm', data={
        'alarm_number': 'TEST001',
        'alarm_type': '测试告警'
    }, follow_redirects=True)
    
    assert response.status_code == 200
    
    with app.app_context():
        alarm = Alarm.query.filter_by(alarm_number='TEST001').first()
        assert alarm is not None
        assert alarm.alarm_type == '测试告警'

def test_export_alarms(client, app):
    # 先登录
    client.post('/login', data={
        'username': 'test_user',
        'password': 'test_password'
    })
    
    # 添加测试数据
    with app.app_context():
        alarm = Alarm(
            alarm_number='TEST002',
            alarm_type='导出测试',
            alarm_time=datetime.now()
        )
        db.session.add(alarm)
        db.session.commit()
    
    response = client.get('/export')
    assert response.status_code == 200
    assert response.headers['Content-Type'] == 'text/csv'
    assert 'attachment' in response.headers['Content-Disposition']