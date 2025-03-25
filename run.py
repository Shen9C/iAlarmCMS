from app import create_app, db
from flask_login import logout_user
from app.models.user import User
import os

def create_and_init_app():
    app = create_app()
    # 检查数据库文件是否存在，如果存在则删除
    db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'instance', 'app.db')
    if os.path.exists(db_path):
        try:
            os.remove(db_path)
            print("[INFO] 已删除旧的数据库文件")
        except Exception as e:
            print(f"[ERROR] 删除数据库文件失败: {str(e)}")
    
    # 创建数据库目录（如果不存在）
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    
    with app.app_context():
        db.create_all()  # 重新创建数据库表
        print("[INFO] 数据库初始化完成")
    return app

app = create_and_init_app()

def clear_all_sessions():
    """服务启动时清除所有用户的登录状态"""
    try:
        with app.app_context():
            users = User.query.all()
            for user in users:
                user.is_active = True
                user.current_token = None
                user.last_login_time = None
                user.token_timestamp = None
            db.session.commit()
            print("[INFO] 已清除所有用户的登录状态")
    except Exception as e:
        print(f"[ERROR] 清除会话时出错: {str(e)}")

if __name__ == '__main__':
    with app.app_context():
        clear_all_sessions()
    app.run(debug=True)