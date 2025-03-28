from flask import Flask, redirect, url_for, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, current_user, logout_user
from flask_migrate import Migrate
from config import Config, load_machine_config  # 修改导入路径，使用根目录的config.py

db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    
    # 从配置文件加载机机认证配置
    machine_config = load_machine_config()
    app.config['MACHINE_AUTH'] = {
        'default': {
            'access_key': machine_config['access_key'],
            'secret_key': machine_config['secret_key']
        }
    }
    
    # 初始化扩展
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    
    # 注册蓝图
    from app.routes import auth_routes
    app.register_blueprint(auth_routes.bp)
    
    # 注册告警相关路由
    from app.views import alarms_view  # 修改这里，从alarms改为alarms_view
    app.register_blueprint(alarms_view.bp, url_prefix='/alarms')
    
    # 添加导入
    from app.routes.settings_routes import bp as settings_bp
    
    # 在注册其他Blueprint的地方添加
    app.register_blueprint(settings_bp)
    
    from app.routes import user_routes
    app.register_blueprint(user_routes.bp, url_prefix='/users', name='users')
    
    # 注册 Web API 蓝图
    from .views import web_api
    app.register_blueprint(web_api.bp)
    
    # 注册机机接口蓝图
    from .views import machine_api
    app.register_blueprint(machine_api.bp)
    
    # 注册边缘设备管理蓝图
    from app.views import edge_devices
    app.register_blueprint(edge_devices.bp)
    
    # 注册任务管理蓝图
    from app.views import tasks
    app.register_blueprint(tasks.bp)
    
    @app.before_request
    def check_auth():
        """全局请求拦截器，验证用户登录状态和URL"""
        # 不需要验证的路由和静态资源
        public_endpoints = ['web_api.login', 'static', 'machine_api.create_alarm', 
                          'machine_api.create_batch_alarms', 'machine_api.get_alarm_status']
        
        # 检查当前请求是否需要验证
        if request.endpoint and not any(request.endpoint.startswith(ep) for ep in public_endpoints):
            # 检查用户是否已登录
            if not current_user.is_authenticated:
                return redirect(url_for('web_api.login'))
            
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
            # 修改路由名称，使用 alarms.index 替代 alarm_view.index
            return redirect(url_for('alarm_view.index', user_token=current_user.current_token))
        return redirect(url_for('web_api.login'))

    # 修改上下文处理器
    @app.context_processor
    def inject_settings():
        from app.models.settings import SystemConfig
        return {'system_config': SystemConfig.get_instance()}

    return app

@login_manager.user_loader
def load_user(id):
    from app.models.users import User
    return User.query.get(int(id))
    