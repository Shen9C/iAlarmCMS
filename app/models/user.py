from app import db
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
import uuid

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    password_hash = db.Column(db.String(128))
    role = db.Column(db.String(20), default='user')  # 添加角色字段
    is_active = db.Column(db.Boolean, default=True)
    last_login_time = db.Column(db.DateTime)
    login_count = db.Column(db.Integer, default=0)
    last_login_ip = db.Column(db.String(40))
    current_token = db.Column(db.String(128))
    token_timestamp = db.Column(db.DateTime)  # 添加令牌时间戳字段

    def set_password(self, password):
        """设置密码"""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        """验证密码"""
        return check_password_hash(self.password_hash, password)

    def generate_token(self):
        """生成用户令牌并更新时间戳"""
        self.current_token = str(uuid.uuid4())
        self.token_timestamp = datetime.utcnow()
        return self.current_token

    def is_token_expired(self):
        """检查令牌是否过期（30分钟）"""
        if not self.token_timestamp:
            return True
        return datetime.utcnow() - self.token_timestamp > timedelta(minutes=30)