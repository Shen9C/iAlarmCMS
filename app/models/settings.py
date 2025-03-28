from app import db
from datetime import datetime

class SystemConfig(db.Model):
    """系统基本配置模型，存储预定义的系统配置项"""
    id = db.Column(db.Integer, primary_key=True)
    system_name_zh = db.Column(db.String(100), default="智能告警综合管理系统")
    system_name_en = db.Column(db.String(100), default="Intelligent Alarm Management System")
    company_name = db.Column(db.String(100), default="示例公司")
    logo_url = db.Column(db.String(255), default="/static/images/logo.png")
    theme_color = db.Column(db.String(20), default="#3498db")
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)
    
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
    """键值对形式的系统设置模型，用于存储动态配置项"""
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(50), unique=True, nullable=False)
    value = db.Column(db.String(500))
    description = db.Column(db.String(200))
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)
    
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