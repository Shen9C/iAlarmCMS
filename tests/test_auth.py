import pytest
from flask import session
from app.models.users import User

def test_login(client):
    response = client.post('/login', data={
        'username': 'test_user',
        'password': 'test_password'
    }, follow_redirects=True)
    assert response.status_code == 200
    
def test_login_invalid_password(client):
    response = client.post('/login', data={
        'username': 'test_user',
        'password': 'wrong_password'
    }, follow_redirects=True)
    assert b'\xe6\x97\xa0\xe6\x95\x88\xe7\x9a\x84\xe7\x94\xa8\xe6\x88\xb7\xe5\x90\x8d\xe6\x88\x96\xe5\xaf\x86\xe7\xa0\x81' in response.data

def test_logout(client):
    # 先登录
    client.post('/login', data={
        'username': 'test_user',
        'password': 'test_password'
    })
    # 然后登出
    response = client.get('/logout', follow_redirects=True)
    assert response.status_code == 200