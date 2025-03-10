from app import create_app, db
from flask_login import logout_user
from app.models.user import User

def create_and_init_app():
    app = create_app()
    with app.app_context():
        db.create_all()  # 确保数据库表已创建
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