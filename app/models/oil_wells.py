from datetime import datetime
from sqlalchemy import TIMESTAMP
from app import db

class OilWell(db.Model):
    __tablename__ = 'oil_wells'
    
    id = db.Column(db.Integer, primary_key=True, comment='油井ID，自增主键')
    well_code = db.Column(db.String(50), unique=True, nullable=False, index=True, comment='油井编号，唯一标识')
    well_name = db.Column(db.String(128), nullable=False, comment='油井名称')
    location = db.Column(db.String(255), comment='地理位置')
    status = db.Column(db.String(50), default='正常', comment='油井状态')
    description = db.Column(db.Text, comment='油井描述')
    created_at = db.Column(TIMESTAMP(timezone=True), default=lambda: datetime.now().astimezone(), comment='创建时间')
    updated_at = db.Column(TIMESTAMP(timezone=True), default=lambda: datetime.now().astimezone(), onupdate=lambda: datetime.now().astimezone(), comment='更新时间')
    
    # 反向关系，一个油井有多个任务
    tasks = db.relationship('Task', backref='oil_well', lazy='dynamic')
    
    def __repr__(self):
        return f'<OilWell {self.well_code} - {self.well_name}>'
    
    def to_dict(self):
        """将油井对象转换为字典"""
        return {
            'id': self.id,
            'well_code': self.well_code,
            'well_name': self.well_name,
            'location': self.location,
            'status': self.status,
            'description': self.description,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S') if self.created_at else None,
            'updated_at': self.updated_at.strftime('%Y-%m-%d %H:%M:%S') if self.updated_at else None
        }
    
    @classmethod
    def get_by_well_code(cls, well_code):
        """根据油井编号获取油井"""
        return cls.query.filter_by(well_code=well_code).first()
    
    @classmethod
    def get_all_wells(cls):
        """获取所有油井"""
        return cls.query.order_by(cls.well_code).all() 