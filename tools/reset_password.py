import sys
import os

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app, db
from app.models.user import User
from werkzeug.security import generate_password_hash

def reset_password(username, new_password):
    app = create_app()
    with app.app_context():
        user = User.query.filter_by(username=username).first()
        if not user:
            print(f"用户 {username} 不存在")
            return False
        
        user.password_hash = generate_password_hash(new_password)
        db.session.commit()
        print(f"用户 {username} 的密码已重置")
        return True

if __name__ == '__main__':
    if len(sys.argv) != 3:
        print("使用方法: python reset_password.py <用户名> <新密码>")
        sys.exit(1)
    
    username = sys.argv[1]
    new_password = sys.argv[2]
    reset_password(username, new_password)