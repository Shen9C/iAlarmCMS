from flask import Flask, redirect, url_for, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, current_user, logout_user
from flask_migrate import Migrate
from config import Config  
import logging

# 设置日志
logger = logging.getLogger(__name__)

# 初始化Flask扩展
db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    
    # 配置日志级别
    if app.config.get('DEBUG_LOG_ENABLED', False):
        # 修改这里，确保日志配置正确
        logging.basicConfig(
            level=logging.DEBUG,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.StreamHandler()  # 添加控制台处理器
            ]
        )
        logger.debug("应用启动，调试日志已启用")
    
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
    from app.routes.alarms_api import bp as alarms_api_bp
    app.register_blueprint(alarms_view_bp, url_prefix='/alarms')
    app.register_blueprint(alarms_api_bp)
    
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
    
    # 删除这部分，因为已经不需要了
    # ===================== 注册机机接口蓝图 =====================
    # from app.routes.machine_api import bp as machine_api_bp
    # app.register_blueprint(machine_api_bp)
    
    @app.before_request
    def check_auth():
        """全局请求拦截器，验证用户登录状态和URL"""
        if app.config.get('DEBUG_LOG_ENABLED', False):
            logger.debug(f"请求信息: endpoint={request.endpoint}, path={request.path}, method={request.method}")
            
            # 如果是登录请求，记录用户名和密码信息（仅用于调试）
            if request.endpoint == 'web_auth.web_login' and request.method == 'POST':
                if request.is_json:
                    data = request.get_json()
                    logger.debug(f"登录尝试 - 用户名: {data.get('username')}, 密码: {data.get('password')}")
                elif request.form:
                    logger.debug(f"登录尝试 - 用户名: {request.form.get('username')}, 密码: {request.form.get('password')}")
            
            logger.debug(f"用户认证状态: authenticated={current_user.is_authenticated}")
            if current_user.is_authenticated:
                logger.debug(f"当前登录用户: {current_user.username}, Token: {current_user.current_token}")
        
        # 不需要验证的路由和静态资源
        public_endpoints = [
            'web_auth.web_login',
            'web_auth_api.web_login_api',
            'static',
            'edge_device_api.create_alarm',
            'edge_device_api.create_batch_alarms',
            'edge_device_api.get_alarm_status'
        ]
        
        if request.endpoint and not any(request.endpoint.startswith(ep) for ep in public_endpoints):
            if not current_user.is_authenticated:
                if app.config.get('DEBUG_LOG_ENABLED', False):
                    logger.debug("用户未认证，重定向到登录页面")
                if request.is_xhr:
                    return jsonify({
                        'success': False,
                        'error': '未登录或会话已过期'
                    }), 401
                return redirect(url_for('web_auth.web_login'))
    
    @app.route('/')
    def index():
        """应用程序主入口"""
        if app.config.get('DEBUG_LOG_ENABLED', False):
            logger.debug(f"访问根路径: authenticated={current_user.is_authenticated}")
        
        if current_user.is_authenticated:
            if current_user.current_token:
                if app.config.get('DEBUG_LOG_ENABLED', False):
                    logger.debug(f"用户已登录，重定向到告警页面: token={current_user.current_token}")
                return redirect(url_for('alarms_view.index', user_token=current_user.current_token))
            
            token = current_user.generate_token()
            current_user.current_token = token
            db.session.commit()
            if app.config.get('DEBUG_LOG_ENABLED', False):
                logger.debug(f"生成新token并重定向: token={token}")
            return redirect(url_for('alarms_view.index', user_token=token))
        
        if app.config.get('DEBUG_LOG_ENABLED', False):
            logger.debug("用户未登录，重定向到登录页面")
        return redirect(url_for('web_auth.web_login'))

    return app

@login_manager.user_loader
def load_user(id):
    """Flask-Login用户加载回调"""
    from app.models.users import User
    return User.query.get(int(id))
    