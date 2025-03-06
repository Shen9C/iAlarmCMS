from app import create_app
from app.models.user import User
from app import db

app = create_app()

def reset_password():
    with app.app_context():
        user = User.query.filter_by(username='admin').first()
        if user:
            user.set_password('admin123')
            db.session.commit()
            print("\n密码已重置")
            print("-" * 30)
            print("用户名: admin")
            print("新密码: admin123")
            print("-" * 30)
        else:
            print("未找到管理员用户")

if __name__ == '__main__':
    reset_password()