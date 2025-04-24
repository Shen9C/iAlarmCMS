from datetime import datetime
from typing import Optional
from sqlalchemy import String, DateTime, Boolean, Integer, Text, TIMESTAMP
from app import db

class Alarm(db.Model):
    __tablename__ = 'alarms'
    id = db.Column(db.Integer, primary_key=True, comment='告警ID，自增主键')
    alarm_code = db.Column(db.String(50), nullable=False, comment='告警编号，如WELL001_QT001')
    alarm_type = db.Column(db.String(100), nullable=False, comment='告警类型，如异常停止、毛辫子断裂等')
    
    device_id = db.Column(db.String(64), nullable=False, comment='设备ID，关联设备表')
    device_name = db.Column(db.String(100), comment='设备名称，冗余存储便于查询')
    well_name = db.Column(db.String(128), comment='油井名称，冗余存储便于查询')
    well_code = db.Column(db.String(50), index=True, comment='油井编号，关联oil_wells表')
    alarm_suffix_code = db.Column(db.String(10), comment='告警后缀码，用于标识具体故障类型，如QT001')
    camera_ip = db.Column(db.String(50), comment='摄像头IP地址')
    alarm_time = db.Column(TIMESTAMP, default=lambda: datetime.now(), comment='告警发生时间')
    last_report_time = db.Column(TIMESTAMP, default=lambda: datetime.now(), comment='最后一次上报时间')
    report_count = db.Column(db.Integer, default=1, comment='上报次数')
    alarm_image = db.Column(db.String(255), comment='告警图片URL')
    is_processed = db.Column(db.Boolean, default=False, comment='是否已处理,False表示待处理，True表示已处理')
    processed_time = db.Column(db.TIMESTAMP, comment='处理完成时间')
    processed_by = db.Column(db.String(100), comment='处理人')
    is_confirmed = db.Column(db.Boolean, default=False, comment='是否已确认,False表示未确认，True表示已确认')
    confirmed_at = db.Column(db.TIMESTAMP, comment='确认时间')
    confirmed_by = db.Column(db.String(100), comment='确认人')
    confirmation_type = db.Column(db.String(20), comment='确认类型，如故障、误报、测试等')
    confirmation_notes = db.Column(db.Text, comment='确认备注')
    description = db.Column(db.String(255), comment='告警描述')
    process_notes = db.Column(db.Text, comment='处理备注')
    
    created_at = db.Column(TIMESTAMP, default=lambda: datetime.now(), comment='创建时间')
    updated_at = db.Column(TIMESTAMP, default=lambda: datetime.now(), onupdate=lambda: datetime.now(), comment='更新时间')
    
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
            'well_code': self.well_code,
            'well_name': self.well_name,
            'camera_ip': self.camera_ip,
            'alarm_time': self.alarm_time.strftime('%Y-%m-%d %H:%M:%S') if self.alarm_time else None,
            'last_report_time': self.last_report_time.strftime('%Y-%m-%d %H:%M:%S') if self.last_report_time else None,
            'report_count': self.report_count,
            'alarm_image': self.alarm_image,
            'is_processed': self.is_processed,
            'processed_time': self.processed_time.strftime('%Y-%m-%d %H:%M:%S') if self.processed_time else None,
            'processed_by': self.processed_by,
            'is_confirmed': self.is_confirmed,
            'confirmed_at': self.confirmed_at.strftime('%Y-%m-%d %H:%M:%S') if self.confirmed_at else None,
            'confirmed_by': self.confirmed_by,
            'confirmation_type': self.confirmation_type,
            'confirmation_notes': self.confirmation_notes,
            'description': self.description,
            'process_notes': self.process_notes,
            'alarm_suffix_code': self.alarm_suffix_code,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S') if self.created_at else None,
            'updated_at': self.updated_at.strftime('%Y-%m-%d %H:%M:%S') if self.updated_at else None
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
            existing_alarm.last_report_time = datetime.now()
            # 增加上报次数
            existing_alarm.report_count += 1
            
            # 如果提供了新的告警图片，则更新
            if 'alarm_image' in alarm_data and alarm_data['alarm_image']:
                existing_alarm.alarm_image = alarm_data['alarm_image']
                
            db.session.commit()
            return existing_alarm
        
        # 确保alarm_data中包含alarm_code
        if 'alarm_code' not in alarm_data or not alarm_data['alarm_code']:
            raise ValueError("alarm_code是必传入字段，不能为空")
            
        # 创建新告警
        new_alarm = cls(**alarm_data)
        db.session.add(new_alarm)
        db.session.commit()
        return new_alarm
    
    @staticmethod
    def extract_well_code(alarm_code):
        """从告警编号中提取油井编号"""
        if not alarm_code or '_' not in alarm_code:
            return None
        
        # 跳过ALM前缀，提取中间的油井编号部分
        parts = alarm_code.split('_')
        if len(parts) >= 2:
            return parts[0]  # 第一部分应该是油井编号
        return None
    
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
        if status == "已处理":
            return cls.query.filter_by(is_processed=True).all()
        else:
            return cls.query.filter_by(is_processed=False).all()
    
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
            (~cls.is_processed) | (~cls.is_confirmed)
        ).all()
    