# 将原user.py的内容复制到这里
# 例如：
from app import db
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy import TIMESTAMP
import time
import uuid
from datetime import datetime

# 在User类中确保有以下字段
from datetime import datetime
from sqlalchemy import TIMESTAMP
from app import db

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    password_hash = db.Column(db.String(512), nullable=False)
    role = db.Column(db.String(64))
    is_admin = db.Column(db.Boolean, default=False)
    current_token = db.Column(db.String(512))
    token_timestamp = db.Column(TIMESTAMP(timezone=True), default=lambda: datetime.now().astimezone())
    login_count = db.Column(db.Integer, default=0)
    last_login_time = db.Column(TIMESTAMP(timezone=True), default=lambda: datetime.now().astimezone())
    last_login_ip = db.Column(db.String(64))
    active = db.Column(db.Boolean, default=True)
    
    def update_token(self, token):
        self.current_token = token
        self.token_timestamp = datetime.now().astimezone()
    active = db.Column(db.Boolean, default=True)
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def generate_token(self):
        self.current_token = str(uuid.uuid4())
        # 修改这里，使用token_timestamp而不是token_expiration
        from datetime import datetime, timedelta
        self.token_timestamp = datetime.now().astimezone()
        return self.current_token
    
    def is_token_expired(self):
        # 修改这里，使用token_timestamp而不是token_expiration
        if not self.token_timestamp:
            return True
        from datetime import datetime, timedelta
        # 检查token是否超过1小时，并确保时区一致
        return datetime.now().astimezone() > self.token_timestamp + timedelta(hours=1)
    
    # 定义is_active属性的getter和setter
    @property
    def is_active(self):
        return self.active
    
    @is_active.setter
    def is_active(self, value):
        self.active = value
