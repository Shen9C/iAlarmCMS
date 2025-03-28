from datetime import datetime
from typing import Optional
from sqlalchemy import String, DateTime, Boolean
from sqlalchemy.orm import Mapped, mapped_column
from app import db

class Alarm(db.Model):
    __tablename__ = 'alarms'  # 表名为'alarms'
    id = db.Column(db.Integer, primary_key=True)
    alarm_number = db.Column(db.String(50))
    alarm_type = db.Column(db.String(100))
    device_name = db.Column(db.String(100))
    camera_ip = db.Column(db.String(50))
    alarm_time = db.Column(db.DateTime, default=datetime.utcnow)
    alarm_image = db.Column(db.String(255))
    is_processed = db.Column(db.Boolean, default=False)
    processed_time = db.Column(db.DateTime)
    is_confirmed = db.Column(db.Boolean, default=False)
    confirmed_time = db.Column(db.DateTime)
    status = db.Column(db.String(20), default='待确认')
    confirm_type = db.Column(db.String(20))  # 添加确认类型字段：'fault'(故障) 或 'false_alarm'(误报)
    
    def __repr__(self) -> str:
        return f'<Alarm {self.alarm_number}>'

    @classmethod
    def create_or_update(cls, alarm_data):
        """创建或更新告警"""
        # 检查是否存在未处理的相同类型告警
        existing_alarm = cls.query.filter(
            cls.device_name == alarm_data['device_name'],
            cls.alarm_type == alarm_data['alarm_type'],
            cls.status != '已处理'
        ).first()

        if existing_alarm:
            # 更新最后上报时间
            existing_alarm.last_report_time = datetime.now()
            db.session.commit()
            return existing_alarm
        
        # 创建新告警
        new_alarm = cls(**alarm_data)
        db.session.add(new_alarm)
        db.session.commit()
        return new_alarm