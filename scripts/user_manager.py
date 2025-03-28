from app import create_app
from app.models.users import User
from app import db
import sys
import getpass

app = create_app()

def list_users():
    with app.app_context():
        users = User.query.all()
        print("\n当前系统用户列表：")
        print("-" * 30)
        for user in users:
            print(f"用户名: {user.username}")
        print("-" * 30)

def reset_password(username, new_password):
    """重置指定用户的密码"""
    with app.app_context():
        user = User.query.filter_by(username=username).first()
        if user:
            user.set_password(new_password)
            db.session.commit()
            print(f"\n用户 {username} 的密码已重置")
            print("-" * 30)
            print(f"新密码: {new_password}")
            print("-" * 30)
        else:
            print(f"未找到用户: {username}")

def add_user(username, password):
    """添加新用户"""
    with app.app_context():
        if User.query.filter_by(username=username).first():
            print(f"用户 {username} 已存在！")
            return
        
        user = User(username=username)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        print(f"\n已成功添加用户：{username}")

if __name__ == '__main__':
    import sys
    
    if len(sys.argv) < 2:
        print("使用方法：")
        print("列出用户：python user_manager.py list")
        print("重置密码：python user_manager.py reset <username> <new_password>")
        print("添加用户：python user_manager.py add <username> <password>")
        sys.exit(1)
    
    # 现有的命令行处理代码
    
    # 添加列出用户的选项
    if len(sys.argv) > 1 and sys.argv[1] == 'list':
        list_users()
        sys.exit(0)
        
    command = sys.argv[1]
    
    if command == 'list':
        list_users()
    elif command == 'reset' and len(sys.argv) == 4:
        reset_password(sys.argv[2], sys.argv[3])
    elif command == 'add' and len(sys.argv) == 4:
        add_user(sys.argv[2], sys.argv[3])
    else:
        print("无效的命令！")