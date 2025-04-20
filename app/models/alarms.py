from datetime import datetime
from typing import Optional
from sqlalchemy import String, DateTime, Boolean, Integer, Text, TIMESTAMP
from app import db

class Alarm(db.Model):
    __tablename__ = 'alarms'
    id = db.Column(db.Integer, primary_key=True)
    alarm_code = db.Column(db.String(50), index=True, comment='告警编号，标识一类告警，如ALM202404190001')
    alarm_type = db.Column(db.String(100), nullable=False, comment='告警类型，如压力异常、液位异常等')
    
    device_id = db.Column(db.String(64), nullable=False)
    device_name = db.Column(db.String(100))
    camera_ip = db.Column(db.String(50))
    alarm_time = db.Column(TIMESTAMP(timezone=True), default=lambda: datetime.now().astimezone())
    last_report_time = db.Column(TIMESTAMP(timezone=True), default=lambda: datetime.now().astimezone())
    report_count = db.Column(db.Integer, default=1)
    alarm_image = db.Column(db.String(255))
    is_processed = db.Column(db.Boolean, default=False)
    processed_time = db.Column(db.TIMESTAMP(timezone=True))
    is_confirmed = db.Column(db.Boolean, default=False)
    confirmed_time = db.Column(db.TIMESTAMP(timezone=True))
    status = db.Column(db.String(20), default='待确认')
    confirm_type = db.Column(db.String(20))
    
    
    def __repr__(self) -> str:
        return f'<Alarm {self.alarm_code} - {self.alarm_type}>'
    
    def to_dict(self):
        """将告警对象转换为字典"""
        return {
            'id': self.id,
            'alarm_code': self.alarm_code,
            'alarm_type': self.alarm_type,
            'device_id': self.device_id,
            'device_name': self.device_name,
            'camera_ip': self.camera_ip,
            'alarm_time': self.alarm_time.strftime('%Y-%m-%d %H:%M:%S') if self.alarm_time else None,
            'last_report_time': self.last_report_time.strftime('%Y-%m-%d %H:%M:%S') if self.last_report_time else None,
            'report_count': self.report_count,
            'alarm_image': self.alarm_image,
            'is_processed': self.is_processed,
            'processed_time': self.processed_time.strftime('%Y-%m-%d %H:%M:%S') if self.processed_time else None,
            'is_confirmed': self.is_confirmed,
            'confirmed_time': self.confirmed_time.strftime('%Y-%m-%d %H:%M:%S') if self.confirmed_time else None,
            'status': self.status,
            'confirm_type': self.confirm_type
        }

    @classmethod
    def create_or_update(cls, alarm_data):
        """创建或更新告警"""
        # 检查是否存在未处理的相同类型告警
        existing_alarm = cls.query.filter(
            cls.device_id == alarm_data.get('device_id'),
            cls.alarm_type == alarm_data.get('alarm_type'),
            cls.is_processed == False
        ).first()

        if existing_alarm:
            # 更新最后上报时间
            existing_alarm.last_report_time = datetime.now().astimezone()
            # 增加上报次数
            existing_alarm.report_count += 1
            
            # 如果提供了新的告警图片，则更新
            if 'alarm_image' in alarm_data and alarm_data['alarm_image']:
                existing_alarm.alarm_image = alarm_data['alarm_image']
                
            db.session.commit()
            return existing_alarm
        
        # 确保alarm_data中包含alarm_code
        if 'alarm_code' not in alarm_data or not alarm_data['alarm_code']:
            alarm_data['alarm_code'] = cls.generate_alarm_code()
            
        # 创建新告警
        new_alarm = cls(**alarm_data)
        db.session.add(new_alarm)
        db.session.commit()
        return new_alarm
        
    @staticmethod
    def generate_alarm_code():
        """生成告警编号"""
        prefix = "ALM"
        timestamp = datetime.now().astimezone().strftime("%Y%m%d%H%M%S")
        random_suffix = str(hash(str(datetime.now().microsecond)))[-4:]
        return f"{prefix}{timestamp}{random_suffix}"
    
    @classmethod
    def get_by_device_id(cls, device_id):
        """根据设备ID获取告警列表"""
        return cls.query.filter_by(device_id=device_id).all()
    
    @classmethod
    def get_by_alarm_type(cls, alarm_type):
        """根据告警类型获取告警列表"""
        return cls.query.filter_by(alarm_type=alarm_type).all()
    
    @classmethod
    def get_by_status(cls, status):
        """根据状态获取告警列表"""
        return cls.query.filter_by(status=status).all()
    
    @classmethod
    def get_unprocessed(cls):
        """获取所有未处理的告警"""
        return cls.query.filter_by(is_processed=False).all()
    
    @classmethod
    def get_unconfirmed(cls):
        """获取所有未确认的告警"""
        return cls.query.filter_by(is_confirmed=False).all()
    
    @classmethod
    def get_active_alarms(cls):
        """获取所有活动告警（未处理或未确认）"""
        return cls.query.filter(
            (cls.is_processed == False) | (cls.is_confirmed == False)
        ).all()
    