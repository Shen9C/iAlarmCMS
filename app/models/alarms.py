from datetime import datetime
from typing import Optional
from sqlalchemy import String, DateTime, Boolean, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column
from app import db

class Alarm(db.Model):
    __tablename__ = 'alarms'
    id = db.Column(db.Integer, primary_key=True)
    alarm_number = db.Column(db.String(50), index=True)
    alarm_type = db.Column(db.String(100))
    
    device_id = db.Column(db.String(64), db.ForeignKey('edge_devices.device_id'), nullable=False)
    device_name = db.Column(db.String(100))
    
    camera_ip = db.Column(db.String(50))
    # 修改为 TIMESTAMP WITH TIME ZONE
    alarm_time = db.Column(db.TIMESTAMP(timezone=True), default=lambda: datetime.now(datetime.timezone.utc))
    last_report_time = db.Column(db.TIMESTAMP(timezone=True), default=lambda: datetime.now(datetime.timezone.utc))
    report_count = db.Column(db.Integer, default=1)
    alarm_image = db.Column(db.String(255))
    is_processed = db.Column(db.Boolean, default=False)
    processed_time = db.Column(db.TIMESTAMP(timezone=True))
    is_confirmed = db.Column(db.Boolean, default=False)
    confirmed_time = db.Column(db.TIMESTAMP(timezone=True))
    status = db.Column(db.String(20), default='待确认')
    confirm_type = db.Column(db.String(20))
    
    def __repr__(self) -> str:
        return f'<Alarm {self.alarm_number}>'

    @classmethod
    def create_or_update(cls, alarm_data):
        """创建或更新告警"""
        # 检查是否存在未处理的相同类型告警，无论是否已确认
        existing_alarm = cls.query.filter(
            cls.device_name == alarm_data.get('device_name'),
            cls.alarm_type == alarm_data.get('alarm_type'),
            cls.is_processed == False  # 只要未处理，无论是否已确认
        ).first()

        if existing_alarm:
            # 更新最后上报时间
            existing_alarm.last_report_time = datetime.now()
            # 增加上报次数
            existing_alarm.report_count += 1
            
            # 如果提供了新的告警图片，则更新
            if 'alarm_image' in alarm_data and alarm_data['alarm_image']:
                existing_alarm.alarm_image = alarm_data['alarm_image']
                
            db.session.commit()
            return existing_alarm
        
        # 确保alarm_data中包含alarm_number
        if 'alarm_number' not in alarm_data or not alarm_data['alarm_number']:
            # 生成告警编号
            alarm_data['alarm_number'] = cls.generate_alarm_number()
            
        # 创建新告警
        new_alarm = cls(**alarm_data)
        db.session.add(new_alarm)
        db.session.commit()
        return new_alarm
        
    @staticmethod
    def generate_alarm_number():
        """生成唯一的告警编号"""
        prefix = "ALM"
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        random_suffix = str(hash(str(datetime.now().microsecond)))[-4:]
        return f"{prefix}{timestamp}{random_suffix}"
    
    # 添加关系属性
    device = db.relationship('EdgeDevice', backref=db.backref('alarms', lazy=True))