from app import db

class Settings(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    
    # 系统基本设置
    system_name_zh = db.Column(db.String(128), default='智能告警综合管理系统')
    system_name_en = db.Column(db.String(128), default='Intelligent Alarm Comprehensive Management System')
    
    # 告警设置
    retention_days = db.Column(db.Integer, default=30)
    refresh_interval = db.Column(db.Integer, default=30)
    
    # 邮件设置
    smtp_server = db.Column(db.String(128))
    smtp_port = db.Column(db.Integer, default=587)
    sender_email = db.Column(db.String(128))
    email_password = db.Column(db.String(128))
    enable_email = db.Column(db.Boolean, default=False)