from app import create_app
from app.models.user import User

app = create_app()

def list_users():
    with app.app_context():
        users = User.query.all()
        print("\n当前系统用户列表：")
        print("-" * 30)
        for user in users:
            print(f"用户名: {user.username}")
        print("-" * 30)

if __name__ == '__main__':
    list_users()