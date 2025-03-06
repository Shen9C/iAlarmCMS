from app import create_app, db
from app.models.user import User

app = create_app()

def init_db():
    with app.app_context():
        # 创建所有表
        db.create_all()
        
        # 检查是否已存在管理员用户
        if not User.query.filter_by(username='admin').first():
            # 创建管理员用户
            admin = User(username='admin')
            admin.set_password('admin123')
            db.session.add(admin)
            db.session.commit()
            print('\n初始化完成！')
            print('-' * 30)
            print('管理员账号：admin')
            print('初始密码：admin123')
            print('-' * 30)
        else:
            print('管理员用户已存在！')

if __name__ == '__main__':
    init_db()