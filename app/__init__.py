from flask import Flask, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, current_user
from flask_migrate import Migrate
from config import Config  # 添加配置类的导入

db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()

from app.models.settings import Settings

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    
    login_manager.login_view = 'auth.login'
    login_manager.login_message = '请先登录以访问此页面'
    login_manager.login_message_category = 'info'
    
    # 确保 auth 蓝图最先注册
    from app.routes import auth_routes
    print(f"[DEBUG] 注册 auth 蓝图: prefix={auth_routes.bp.url_prefix}")
    app.register_blueprint(auth_routes.bp, url_prefix='/auth')
    
    from app.views import alarms
    app.register_blueprint(alarms.bp, url_prefix='/alarms')
    
    # 确保只注册一次 settings 蓝图
    from app.routes import settings_routes
    app.register_blueprint(settings_routes.bp, url_prefix='/system/settings')  # 修改URL前缀避免冲突
    
    from app.routes import user_routes
    app.register_blueprint(user_routes.bp)
    
    @app.route('/')
    def index():
        if current_user.is_authenticated:
            return redirect(url_for('alarm_view.index'))
        return redirect(url_for('auth.login'))

    @app.context_processor
    def inject_settings():
        settings = Settings.query.first()
        return dict(settings=settings)

    return app  # 添加这行，返回 app 实例

@login_manager.user_loader
def load_user(id):
    from app.models.user import User
    return User.query.get(int(id))