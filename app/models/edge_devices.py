from app import db
import datetime
import secrets
import string
import uuid

class EdgeDevice(db.Model):
    __tablename__ = 'edge_devices'
    
    id = db.Column(db.Integer, primary_key=True)
    device_id = db.Column(db.String(64), nullable=False, unique=True, comment='设备唯一ID')
    device_name = db.Column(db.String(100), nullable=False, comment='设备名称')
    ip_address = db.Column(db.String(50), nullable=False, comment='设备IP地址')
    secret_key = db.Column(db.String(128), nullable=False, comment='设备密钥')
    created_at = db.Column(db.DateTime, default=datetime.datetime.now)
    updated_at = db.Column(db.DateTime, default=datetime.datetime.now, onupdate=datetime.datetime.now)
    
    # 移除联合主键设置
    # __table_args__ = (
    #     db.PrimaryKeyConstraint('id', 'device_id'),
    # )
    
    def __init__(self, device_name, ip_address, device_id=None, secret_key=None):
        self.device_name = device_name
        self.ip_address = ip_address
        
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
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            'updated_at': self.updated_at.strftime('%Y-%m-%d %H:%M:%S')
        }
    
    def __repr__(self):
        return f'<EdgeDevice {self.device_name}>'