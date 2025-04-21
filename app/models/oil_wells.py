from datetime import datetime
from sqlalchemy import TIMESTAMP
from app import db

class OilWell(db.Model):
    __tablename__ = 'oil_wells'
    
    id = db.Column(db.Integer, primary_key=True, comment='油井ID，自增主键')
    well_code = db.Column(db.String(50), unique=True, nullable=False, index=True, comment='油井编号，唯一标识')
    well_name = db.Column(db.String(128), nullable=False, comment='油井名称')
    location = db.Column(db.String(100), comment='位置')
    status = db.Column(db.String(20), default='正常', comment='状态：正常、维护中、停机')
    description = db.Column(db.String(500), comment='描述')
    created_at = db.Column(TIMESTAMP, default=lambda: datetime.now(), comment='创建时间')
    updated_at = db.Column(TIMESTAMP, default=lambda: datetime.now(), onupdate=lambda: datetime.now(), comment='更新时间')
    
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