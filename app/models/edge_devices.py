from app import db
import datetime
import secrets
import string

class EdgeDevice(db.Model):
    __tablename__ = 'edge_devices'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True, comment='设备名称')
    ip_address = db.Column(db.String(50), nullable=False, comment='设备IP地址')
    access_key = db.Column(db.String(64), nullable=False, unique=True, comment='设备访问密钥')
    secret_key = db.Column(db.String(128), nullable=False, comment='设备密钥')
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    
    def __init__(self, name, ip_address, access_key=None, secret_key=None):
        self.name = name
        self.ip_address = ip_address
        
        # 如果未提供access_key，则自动生成
        if not access_key:
            self.access_key = self.generate_access_key()
        else:
            self.access_key = access_key
            
        # 如果未提供secret_key，则自动生成
        if not secret_key:
            self.secret_key = self.generate_secret_key()
        else:
            self.secret_key = secret_key
    
    @staticmethod
    def generate_access_key():
        """生成随机的访问密钥"""
        return f"AK-{''.join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(20))}"
    
    @staticmethod
    def generate_secret_key():
        """生成随机的密钥"""
        return f"SK-{''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(40))}"
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'ip_address': self.ip_address,
            'access_key': self.access_key,
            'secret_key': self.secret_key,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            'updated_at': self.updated_at.strftime('%Y-%m-%d %H:%M:%S')
        }
    
    def __repr__(self):
        return f'<EdgeDevice {self.name}>'