# 将原user.py的内容复制到这里
# 例如：
from app import db
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy import TIMESTAMP
import time
import uuid
from datetime import datetime, timedelta

# 在User类中确保有以下字段
from datetime import datetime
from sqlalchemy import TIMESTAMP
from app import db

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True, comment='用户ID，自增主键')
    username = db.Column(db.String(64), unique=True, nullable=False, comment='用户名，唯一')
    password_hash = db.Column(db.String(512), nullable=False, comment='密码哈希值')
    role = db.Column(db.String(64), comment='用户角色')
    is_admin = db.Column(db.Boolean, default=False, comment='是否是管理员')
    current_token = db.Column(db.String(64), unique=True, comment='当前TOKEN，可用于API认证')
    token_timestamp = db.Column(TIMESTAMP, default=lambda: datetime.now(), comment='令牌创建时间')
    login_count = db.Column(db.Integer, default=0, comment='登录次数')
    last_login_time = db.Column(TIMESTAMP, default=lambda: datetime.now(), comment='最后登录时间')
    last_login_ip = db.Column(db.String(50), comment='最后登录IP')
    active = db.Column(db.Boolean, default=True, comment='账户是否激活')
    
    def __init__(self, username, role='user', is_admin=False, active=True):
        self.username = username
        self.role = role
        self.is_admin = is_admin
        self.active = active

    def update_token(self, token):
        self.current_token = token
        self.token_timestamp = datetime.now()
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def generate_token(self):
        """生成用户访问令牌，用于API请求认证"""
        self.current_token = str(uuid.uuid4())
        self.token_timestamp = datetime.now()
        return self.current_token
    
    def is_token_expired(self):
        """检查当前令牌是否过期，默认1小时过期"""
        if not self.current_token or not self.token_timestamp:
            return True
        
        # 检查时间戳是否超过1小时
        return datetime.now() > self.token_timestamp + timedelta(hours=1)
    
    def renew_token(self):
        """更新用户令牌"""
        new_token = str(uuid.uuid4())
        self.current_token = new_token
        self.token_timestamp = datetime.now()
        return new_token
    
    # 定义is_active属性的getter和setter
    @property
    def is_active(self):
        return self.active
    
    @is_active.setter
    def is_active(self, value):
        self.active = value
