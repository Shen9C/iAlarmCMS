from datetime import datetime
from sqlalchemy import TIMESTAMP
from app import db

class Task(db.Model):
    __tablename__ = 'tasks'
    
    id = db.Column(db.Integer, primary_key=True)
    task_name = db.Column(db.String(128), nullable=False, comment='任务名称')
    well_name = db.Column(db.String(128), nullable=False, comment='油井名称')
    task_type = db.Column(db.String(50), nullable=False, comment='任务类型')
    camera_ip = db.Column(db.String(50), nullable=False, comment='摄像头IP')
    camera_preset = db.Column(db.Integer, nullable=False, comment='摄像头预置点')
    pressure_range = db.Column(db.Float, nullable=False, comment='压力表量程')
    created_at = db.Column(TIMESTAMP(timezone=True), default=lambda: datetime.now().astimezone(), comment='创建时间')
    updated_at = db.Column(TIMESTAMP(timezone=True), default=lambda: datetime.now().astimezone(), onupdate=lambda: datetime.now().astimezone(), comment='修改时间')
    
    # 添加与 EdgeDevice 的关系
    device_id = db.Column(db.String(64), db.ForeignKey('edge_devices.device_id'), nullable=False)
    device = db.relationship('EdgeDevice', backref=db.backref('tasks', lazy=True))
    
    def __repr__(self):
        return f'<Task {self.task_name} - {self.well_name}>'
    
    def to_dict(self):
        """将任务对象转换为字典"""
        return {
            'id': self.id,
            'task_name': self.task_name,
            'well_name': self.well_name,
            'task_type': self.task_type,
            'camera_ip': self.camera_ip,
            'camera_preset': self.camera_preset,
            'pressure_range': self.pressure_range,
            'device_id': self.device_id,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S') if self.created_at else None,
            'updated_at': self.updated_at.strftime('%Y-%m-%d %H:%M:%S') if self.updated_at else None
        }
    
    @classmethod
    def get_by_device_id(cls, device_id):
        """根据设备ID获取任务列表"""
        return cls.query.filter_by(device_id=device_id).all()
    
    @classmethod
    def get_by_task_type(cls, task_type):
        """根据任务类型获取任务列表"""
        return cls.query.filter_by(task_type=task_type).all()
    
    @classmethod
    def get_active_tasks(cls):
        """获取所有活动任务"""
        return cls.query.all()