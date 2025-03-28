# 将原user.py的内容复制到这里
# 例如：
from app import db
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
import time
import uuid

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, index=True)
    password_hash = db.Column(db.String(128))
    role = db.Column(db.String(64), default='user')
    is_admin = db.Column(db.Boolean, default=False)
    last_login_time = db.Column(db.DateTime)
    current_token = db.Column(db.String(128))
    token_timestamp = db.Column(db.DateTime)
    active = db.Column(db.Boolean, default=True)
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def generate_token(self):
        self.current_token = str(uuid.uuid4())
        # 修改这里，使用token_timestamp而不是token_expiration
        from datetime import datetime, timedelta
        self.token_timestamp = datetime.now()
        return self.current_token
    
    def is_token_expired(self):
        # 修改这里，使用token_timestamp而不是token_expiration
        if not self.token_timestamp:
            return True
        from datetime import datetime, timedelta
        # 检查token是否超过1小时
        return datetime.now() > self.token_timestamp + timedelta(hours=1)
    
    # 定义is_active属性的getter和setter
    @property
    def is_active(self):
        return self.active
    
    @is_active.setter
    def is_active(self, value):
        self.active = value
