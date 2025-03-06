from datetime import datetime
from typing import Optional
from sqlalchemy import String, DateTime, Boolean
from sqlalchemy.orm import Mapped, mapped_column
from app import db

class Alarm(db.Model):
    __tablename__ = 'alarm'
    
    id: Mapped[int] = mapped_column(primary_key=True)
    alarm_number: Mapped[str] = mapped_column(String(50), unique=True)
    alarm_type: Mapped[str] = mapped_column(String(100))
    alarm_time: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    alarm_image: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    is_processed: Mapped[bool] = mapped_column(Boolean, default=False)
    device_name = db.Column(db.String(100), nullable=True, comment='设备名称')
    device_ip = db.Column(db.String(50), nullable=True, comment='设备IP地址')
    
    def __repr__(self) -> str:
        return f'<Alarm {self.alarm_number}>'