from datetime import datetime
from sqlalchemy import TIMESTAMP
from app import db

class SystemConfig(db.Model):
    __tablename__ = 'system_config'
    """系统基本配置模型，存储预定义的系统配置项"""
    id = db.Column(db.Integer, primary_key=True, comment='配置ID，自增主键')
    system_name_zh = db.Column(db.String(100), default="智能告警综合管理系统", comment='系统中文名称')
    system_name_en = db.Column(db.String(100), default="Intelligent Alarm Management System", comment='系统英文名称')
    company_name = db.Column(db.String(100), default="示例公司", comment='公司名称')
    logo_url = db.Column(db.String(255), default="/static/images/logo.png", comment='系统logo URL')
    theme_color = db.Column(db.String(20), default="#3498db", comment='系统主题颜色')
    updated_at = db.Column(TIMESTAMP(timezone=True), default=lambda: datetime.now().astimezone(), onupdate=lambda: datetime.now().astimezone(), comment='更新时间')
    
    @classmethod
    def get_instance(cls):
        """获取系统配置实例，如果不存在则创建"""
        config = cls.query.first()
        if not config:
            config = cls()
            db.session.add(config)
            db.session.commit()
        return config

class KeyValueSetting(db.Model):
    __tablename__ = 'key_value_settings'
    """键值对形式的系统设置模型，用于存储动态配置项"""
    id = db.Column(db.Integer, primary_key=True, comment='设置ID，自增主键')
    key = db.Column(db.String(50), unique=True, nullable=False, comment='设置键名，唯一')
    value = db.Column(db.String(500), comment='设置值')
    description = db.Column(db.String(200), comment='设置描述')
    updated_at = db.Column(TIMESTAMP(timezone=True), default=lambda: datetime.now().astimezone(), onupdate=lambda: datetime.now().astimezone(), comment='更新时间')
    
    @classmethod
    def get_setting(cls, key, default=None):
        """获取系统设置值"""
        setting = cls.query.filter_by(key=key).first()
        return setting.value if setting else default
    
    @classmethod
    def set_setting(cls, key, value, description=None):
        """设置系统设置值"""
        setting = cls.query.filter_by(key=key).first()
        if setting:
            setting.value = value
            if description:
                setting.description = description
        else:
            setting = cls(key=key, value=value, description=description)
            db.session.add(setting)
        db.session.commit()
        return setting
    
    @classmethod
    def get_all_settings(cls):
        """获取所有系统设置"""
        return {setting.key: setting.value for setting in cls.query.all()}