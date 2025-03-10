from flask import Flask, redirect, url_for, request
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, current_user, logout_user  # 添加 logout_user
from flask_migrate import Migrate
from config import Config  # 添加配置类的导入

db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()

from app.models.settings import Settings

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # 初始化扩展
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    
    # 注册蓝图
    from app.routes import auth_routes
    app.register_blueprint(auth_routes.bp)
    
    from app.views import alarms
    app.register_blueprint(alarms.bp, url_prefix='/alarms')
    
    from app.routes import settings_routes
    app.register_blueprint(settings_routes.bp, url_prefix='/system/settings')
    
    # 添加用户管理蓝图
    from app.routes import user_routes
    app.register_blueprint(user_routes.bp, url_prefix='/users', name='users')
    
    @app.before_request
    def check_auth():
        """全局请求拦截器，验证用户登录状态和URL"""
        # 不需要验证的路由和静态资源
        public_endpoints = ['auth.login', 'static']
        
        # 检查当前请求是否需要验证
        if request.endpoint and not any(request.endpoint.startswith(ep) for ep in public_endpoints):
            # 检查用户是否已登录
            if not current_user.is_authenticated:
                return redirect(url_for('auth.login'))
            
            # 检查用户令牌
            user_token = request.args.get('user_token')
            if not user_token:
                # 如果是 AJAX 请求，不重定向
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return jsonify({'status': 'error', 'message': '会话已过期'}), 401
                # 如果是普通请求，重定向到登录页面
                logout_user()
                return redirect(url_for('auth.login'))
            
            # 检查令牌是否过期
            if current_user.is_token_expired():
                # 自动刷新令牌
                new_token = current_user.generate_token()
                db.session.commit()
                # 如果是 AJAX 请求，返回新令牌
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return jsonify({'status': 'refresh', 'new_token': new_token}), 200
            
            # 验证令牌是否匹配
            if current_user.current_token != user_token:
                logout_user()
                return redirect(url_for('auth.login', token=''))
            
            # 检查令牌是否过期
            if current_user.is_token_expired():
                logout_user()
                return redirect(url_for('auth.login', token=''))

    @app.route('/')
    def index():
        if current_user.is_authenticated and current_user.current_token:
            return redirect(url_for('alarm_view.index', user_token=current_user.current_token))
        return redirect(url_for('auth.login', token=''))

    @app.context_processor
    def inject_settings():
        settings = Settings.query.first()
        return dict(settings=settings)

    return app  # 添加这行，返回 app 实例

@login_manager.user_loader
def load_user(id):
    from app.models.user import User
    return User.query.get(int(id))
    