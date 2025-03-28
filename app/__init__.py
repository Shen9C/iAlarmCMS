from flask import Flask, redirect, url_for, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, current_user, logout_user
from flask_migrate import Migrate
from config import Config  

# 初始化Flask扩展
db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    
    # 初始化扩展
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    
    # 确保所有模型都被导入
    from app.models import settings, tasks, users
    
    # 注册认证相关蓝图 =====================
    from app.routes.web_auth_api import bp as web_auth_api_bp
    from app.views.web_auth_view import bp as web_auth_view_bp
    app.register_blueprint(web_auth_api_bp)
    app.register_blueprint(web_auth_view_bp)
    
    # ===================== 注册告警相关蓝图 =====================
    from app.views.alarms_view import bp as alarms_view_bp
    app.register_blueprint(alarms_view_bp, url_prefix='/alarms')
    
    # ===================== 注册用户相关蓝图 =====================
    from app.views.users_view import bp as users_view_bp
    from app.routes.users_api import bp as users_api_bp
    app.register_blueprint(users_view_bp, url_prefix='/users')
    app.register_blueprint(users_api_bp)
    
    # ===================== 注册边缘设备相关蓝图 =====================
    from app.views.edge_devices_view import bp as edge_devices_view_bp
    from app.routes.edge_devices_api import bp as edge_devices_api_bp
    app.register_blueprint(edge_devices_view_bp)
    app.register_blueprint(edge_devices_api_bp)
    
    # ===================== 注册任务相关蓝图 =====================
    from app.views.tasks_view import bp as tasks_view_bp
    from app.routes.tasks_api import bp as tasks_api_bp
    app.register_blueprint(tasks_view_bp)
    app.register_blueprint(tasks_api_bp)
    
    # ===================== 注册统计相关蓝图 =====================
    from app.views.stats_view import bp as stats_view_bp
    from app.routes.stats_api import bp as stats_api_bp
    app.register_blueprint(stats_view_bp)
    app.register_blueprint(stats_api_bp)
    
    # ===================== 注册设置相关蓝图 =====================
    from app.views.settings_view import bp as settings_view_bp
    from app.routes.settings_api import bp as settings_api_bp
    app.register_blueprint(settings_view_bp)
    app.register_blueprint(settings_api_bp)
    
    # ===================== 注册机机接口蓝图 =====================
    from app.routes.machine_api import bp as machine_api_bp
    app.register_blueprint(machine_api_bp)
    
    @app.before_request
    def check_auth():
        """全局请求拦截器，验证用户登录状态和URL"""
        # 不需要验证的路由和静态资源
        public_endpoints = [
            'web_auth_view.login',
            'web_auth_api.login',
            'static',
            'machine_api.create_alarm',
            'machine_api.create_batch_alarms',
            'machine_api.get_alarm_status'
        ]
        
        # 检查当前请求是否需要验证
        if request.endpoint and not any(request.endpoint.startswith(ep) for ep in public_endpoints):
            # 检查用户是否已登录
            if not current_user.is_authenticated:
                return redirect(url_for('web_auth_view.login'))
            
            # 检查用户令牌
            user_token = request.args.get('user_token')
            if not user_token:
                # 如果是 AJAX 请求，返回401状态码
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return jsonify({'status': 'error', 'message': '会话已过期'}), 401
                # 如果是普通请求，重定向到登录页面
                logout_user()
                return redirect(url_for('web_auth_view.login'))
            
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
                return redirect(url_for('web_auth_view.login'))
            
            # 检查令牌是否过期
            if current_user.is_token_expired():
                logout_user()
                return redirect(url_for('web_auth_view.login'))

    @app.route('/')
    def index():
        """应用程序主入口"""
        if current_user.is_authenticated and current_user.current_token:
            return redirect(url_for('alarms_view.index', user_token=current_user.current_token))
        return redirect(url_for('web_auth_view.login'))

    @app.context_processor
    def inject_settings():
        """注入系统配置到模板上下文"""
        from app.models.settings import SystemConfig
        return {'system_config': SystemConfig.get_instance()}

    return app

@login_manager.user_loader
def load_user(id):
    """Flask-Login用户加载回调"""
    from app.models.users import User
    return User.query.get(int(id))
    