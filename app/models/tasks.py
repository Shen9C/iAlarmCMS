from datetime import datetime
from app import db
import random
import string

class Task(db.Model):
    __tablename__ = 'tasks'
    
    id = db.Column(db.Integer, primary_key=True, comment='任务ID，自增主键')
    task_code = db.Column(db.String(50), unique=True, nullable=False, comment='任务编号，唯一标识')
    task_name = db.Column(db.String(128), nullable=False, comment='任务名称')
    well_name = db.Column(db.String(128), nullable=False, comment='油井名称')
    well_code = db.Column(db.String(50), db.ForeignKey('oil_wells.well_code'), nullable=True, index=True, comment='油井编号，关联oil_wells表')
    task_type = db.Column(db.String(50), nullable=False, comment='任务类型')
    camera_ip = db.Column(db.String(50), nullable=False, comment='摄像头IP')
    camera_preset = db.Column(db.Integer, nullable=False, comment='摄像头预置点')
    pressure_range = db.Column(db.Float, nullable=False, comment='压力表量程')
    task_description = db.Column(db.String(500), nullable=True, comment='任务描述')
    created_at = db.Column(db.DateTime, default=datetime.now, comment='创建时间')
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now, comment='修改时间')
    
    # 添加与 EdgeDevice 的关系
    device_id = db.Column(db.String(64), db.ForeignKey('edge_devices.device_id'), nullable=False, index=True, comment='设备ID，关联edge_devices表')
    device = db.relationship('EdgeDevice', backref=db.backref('tasks', lazy=True))
    
    # 关系在OilWell模型中通过backref定义
    
    def __repr__(self):
        return f'<Task {self.task_name} - {self.well_name}>'
    
    def to_dict(self):
        """将任务对象转换为字典"""
        return {
            'id': self.id,
            'task_code': self.task_code,
            'task_name': self.task_name,
            'well_name': self.well_name,
            'well_code': self.well_code,
            'task_type': self.task_type,
            'camera_ip': self.camera_ip,
            'camera_preset': self.camera_preset,
            'pressure_range': self.pressure_range,
            'task_description': self.task_description,
            'device_id': self.device_id,
            'device_name': self.device.device_name if self.device else None,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S') if self.created_at else None,
            'updated_at': self.updated_at.strftime('%Y-%m-%d %H:%M:%S') if self.updated_at else None
        }
    
    @staticmethod
    def generate_task_code(well_code=None):
        """生成任务编号，包含油井编号前缀"""
        prefix = "TASK"
        well_part = f"{well_code}_" if well_code else ""
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        random_suffix = ''.join(random.choices(string.digits, k=4))
        return f"{prefix}_{well_part}{timestamp}_{random_suffix}"
    
    @classmethod
    def get_by_device_id(cls, device_id):
        """根据设备ID获取任务列表"""
        return cls.query.filter_by(device_id=device_id).all()
    
    @classmethod
    def get_by_task_type(cls, task_type):
        """根据任务类型获取任务列表"""
        return cls.query.filter_by(task_type=task_type).all()
    
    @classmethod
    def get_by_well_name(cls, well_name):
        """根据油井名称获取任务列表"""
        return cls.query.filter_by(well_name=well_name).all()
    
    @classmethod
    def get_by_well_code(cls, well_code):
        """根据油井编号获取任务列表"""
        return cls.query.filter_by(well_code=well_code).all()
    
    @classmethod
    def get_active_tasks(cls):
        """获取所有活动任务"""
        return cls.query.all()
    
    @classmethod
    def get_by_task_code(cls, task_code):
        """根据任务编号获取任务"""
        return cls.query.filter_by(task_code=task_code).first()