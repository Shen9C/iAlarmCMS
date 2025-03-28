from datetime import datetime
from app import db

class Task(db.Model):
    __tablename__ = 'tasks'
    
    id = db.Column(db.Integer, primary_key=True)
    task_name = db.Column(db.String(128), nullable=False, comment='任务名称')
    well_name = db.Column(db.String(128), nullable=False, comment='油井名称')
    detection_type = db.Column(db.String(50), nullable=False, comment='检测类型')
    camera_ip = db.Column(db.String(50), nullable=False, comment='摄像头IP')
    camera_preset = db.Column(db.Integer, nullable=False, comment='摄像头预置点')
    pressure_range = db.Column(db.Float, nullable=False, comment='压力表量程')
    created_at = db.Column(db.DateTime, default=datetime.utcnow, comment='创建时间')
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, comment='修改时间')
    
    def __repr__(self):
        return f'<Task {self.task_name} - {self.well_name}>'