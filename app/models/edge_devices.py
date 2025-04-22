from app import db
from sqlalchemy import TIMESTAMP
from datetime import datetime
import secrets
import string
import uuid

class EdgeDevice(db.Model):
    __tablename__ = 'edge_devices'
    
    id = db.Column(db.Integer, primary_key=True, comment='设备ID，自增主键')
    device_id = db.Column(db.String(64), nullable=False, unique=True, comment='设备唯一ID')
    device_name = db.Column(db.String(100), nullable=False, comment='设备名称')
    ip_address = db.Column(db.String(50), nullable=False, comment='设备IP地址')
    secret_key = db.Column(db.String(128), nullable=False, comment='设备密钥')
    created_at = db.Column(db.DateTime, default=datetime.now, comment='创建时间')
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now, comment='更新时间')
    last_auth_time = db.Column(db.DateTime, nullable=True, comment='最后一次登录时间')
    status = db.Column(db.String(20), default='离线', nullable=False, comment='设备状态：在线, 离线')
    
    def __init__(self, device_name, ip_address, device_id=None, secret_key=None, status='离线'):
        self.device_name = device_name
        self.ip_address = ip_address
        self.status = status
        
        # 如果未提供device_id，则自动生成
        if not device_id:
            self.device_id = self.generate_device_id()
        else:
            self.device_id = device_id
            
        # 如果未提供secret_key，则自动生成
        if not secret_key:
            self.secret_key = self.generate_secret_key()
        else:
            self.secret_key = secret_key
    
    def update_auth_time(self):
        """更新最后一次登录时间"""
        self.last_auth_time = datetime.now()
        self.status = '在线'  # 更新设备状态为在线
    
    def update_status(self):
        """
        根据最后登录时间更新设备状态
        如果最后登录时间在1小时内，则设为在线(online)
        否则设为离线(offline)
        如果没有登录记录，则也设为离线
        """
        now = datetime.now()
        
        # 如果没有最后登录记录，设为离线
        if not self.last_auth_time:
            self.status = '离线'
            return
        
        # 计算最后登录时间与当前时间的差值（小时）
        time_diff = (now - self.last_auth_time).total_seconds() / 3600
        
        # 如果在1小时内有登录记录，则设为在线，否则设为离线
        if time_diff < 1:
            self.status = '在线'
        else:
            self.status = '离线'
    
    @staticmethod
    def generate_device_id():
        """生成随机的设备唯一ID，使用uuid1"""
        return str(uuid.uuid1())
    
    @staticmethod
    def generate_secret_key():
        """生成随机的密钥"""
        return f"SK{''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(40))}"
    
    def to_dict(self):
        return {
            'id': self.id,
            'device_id': self.device_id,
            'device_name': self.device_name,
            'ip_address': self.ip_address,
            'secret_key': self.secret_key,
            'status': self.status,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            'updated_at': self.updated_at.strftime('%Y-%m-%d %H:%M:%S'),
            'last_auth_time': self.last_auth_time.strftime('%Y-%m-%d %H:%M:%S') if self.last_auth_time else None
        }
    
    def __repr__(self):
        return f'<EdgeDevice {self.device_name}>'