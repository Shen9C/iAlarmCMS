from app import create_app, db
from app.models.user import User

app = create_app()

with app.app_context():
    # 确保数据库表存在
    db.create_all()
    
    # 创建管理员用户
    admin = User(username='admin', role='admin')
    admin.set_password('admin123')
    db.session.add(admin)
    db.session.commit()
    
    print('管理员用户创建成功')