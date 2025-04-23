from flask import Flask, redirect, url_for, request, jsonify, flash, render_template  # 添加 render_template 导入
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, current_user, logout_user
from flask_migrate import Migrate
from app.utils.yaml_config_loader import Config, config
import logging
import os
import importlib.util
from pathlib import Path
import sys
from datetime import datetime

# 设置日志
logger = logging.getLogger(__name__)

# 初始化Flask扩展
db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()

# 删除这行错误的导入
# from app.routes import tasks_view  # 删除这行

# 导入自定义SSL模块
try:
    from app.utils.custom_ssl import get_ssl_context, enable_ssl_for_app
except ImportError:
    logger.warning("无法导入自定义SSL模块，请确保app/utils/custom_ssl.py文件存在")
    # 系统将使用默认HTTP模式

def create_api_app(config_class=None):
    """创建边缘设备API服务器应用实例
    
    Args:
        config_class: 配置类，如果为None则使用默认配置
        
    Returns:
        Flask API服务器应用实例
    """
    # 导入Flask，以避免未定义的变量错误
    from flask import Flask, jsonify, Blueprint
    import importlib

    logger.info("创建API服务器应用实例 - 极简模式")
    try:
        # 创建一个纯净的API应用实例
        api_app = Flask("api_server", template_folder=None, static_folder=None)
        
        # 应用配置
        if config_class is None:
            api_app.config.from_object(config)
        else:
            api_app.config.from_object(Config(config_class))
        
        # 确保设置数据库URI
        if hasattr(config, 'SQLALCHEMY_DATABASE_URI'):
            api_app.config['SQLALCHEMY_DATABASE_URI'] = config.SQLALCHEMY_DATABASE_URI
        else:
            # 如果配置对象没有URI，则手动构建
            db_cfg = config.database
            api_app.config['SQLALCHEMY_DATABASE_URI'] = f"postgresql://{db_cfg.user}:{db_cfg.password}@{db_cfg.host}:{db_cfg.port}/{db_cfg.name}"
        
        # 禁用严格传输安全，避免HTTPS自签名证书问题
        api_app.config['PREFERRED_URL_SCHEME'] = 'https'
        # 数据库配置
        api_app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
        
        # 初始化数据库
        db.init_app(api_app)
        
        # 添加错误处理器，确保所有错误返回JSON而不是HTML
        @api_app.errorhandler(404)
        def api_not_found(error):
            return jsonify({
                'code': 404,
                'message': '请求的API端点不存在'
            }), 404
        
        @api_app.errorhandler(500)
        def api_server_error(error):
            return jsonify({
                'code': 500,
                'message': '服务器内部错误: ' + str(error)
            }), 500
        
        # 添加日志中间件
        @api_app.before_request
        def log_api_request():
            """记录API请求信息"""
            logger.debug(f"API请求: {request.method} {request.path}")
            logger.debug(f"请求数据: {request.get_json(silent=True)}")
        
        # 导入API路由 - 直接使用edge_device_api_server.py中的device_api_server蓝图
        # 而不是尝试从其他模块导入，避免命名冲突
        
        # 首先尝试直接导入边缘设备API蓝图
        try:
            from app.routes.edge_device_api_server import device_api_server
            api_app.register_blueprint(device_api_server)
            logger.info(f"成功注册边缘设备API蓝图: device_api_server ({device_api_server.name})")
        except ImportError as e:
            logger.error(f"导入edge_device_api_server模块失败: {str(e)}")
            # 创建一个全新名称的蓝图，避免与Web应用冲突
            empty_bp = Blueprint('api_device_server', __name__, url_prefix='/api/edge_devices')
            
            @empty_bp.route('/')
            def api_root():
                return jsonify({
                    'message': '边缘设备API服务器',
                    'status': 'error',
                    'error': '无法加载完整的API路由',
                    'detail': str(e)
                })
            
            api_app.register_blueprint(empty_bp)
            logger.warning("已注册临时API蓝图替代")
        except Exception as e:
            logger.error(f"注册API蓝图时发生未知错误: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            # 创建一个错误处理蓝图
            error_bp = Blueprint('api_error', __name__, url_prefix='/api')
            
            @error_bp.route('/')
            def api_error():
                return jsonify({
                    'message': '边缘设备API服务器',
                    'status': 'error',
                    'error': '服务器初始化失败',
                    'detail': str(e)
                })
            
            api_app.register_blueprint(error_bp)
        
        # 添加一个状态检查端点
        @api_app.route('/status')
        def api_status():
            """服务器状态检查端点"""
            from datetime import datetime
            return jsonify({
                'status': 'ok',
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'message': 'API服务器运行正常'
            })
        
        logger.info("API服务器应用实例创建成功")
        return api_app
    except Exception as e:
        logger.error(f"无法创建API应用实例: {str(e)}")
        logger.exception("详细错误信息:")
        raise

def create_web_app(config_class=None):
    """
    创建Web应用实例
    
    Args:
        config_class: 配置类，如果为None则使用默认配置
    
    Returns:
        Flask Web应用实例
    """
    # 导入Flask，以避免未定义的变量错误
    from flask import Flask, jsonify, Blueprint
    import importlib

    # 创建Web应用
    logger.info("创建Web应用实例")
    app = Flask(__name__)
    
    # 使用YAML配置加载器
    if config_class is None:
        # 加载配置
        cfg = config
    else:
        # 如果传入了具体的config_class，使用该配置
        cfg = Config(config_class)

    # 将配置应用到Flask应用
    app.config['SECRET_KEY'] = cfg.secret_key
    app.config['DEBUG'] = cfg.debug
    
    # 确保设置数据库URI
    if hasattr(cfg, 'SQLALCHEMY_DATABASE_URI'):
        app.config['SQLALCHEMY_DATABASE_URI'] = cfg.SQLALCHEMY_DATABASE_URI
    else:
        # 如果配置对象没有URI，则手动构建
        db_cfg = cfg.database
        app.config['SQLALCHEMY_DATABASE_URI'] = f"postgresql://{db_cfg.user}:{db_cfg.password}@{db_cfg.host}:{db_cfg.port}/{db_cfg.name}"
    
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    # 禁用严格传输安全，避免HTTPS自签名证书问题
    app.config['PREFERRED_URL_SCHEME'] = 'https'
    
    # 设置应用程序的安全相关配置
    # 在开发环境中，禁用一些可能导致问题的安全功能
    if app.debug:
        # 开发环境配置
        app.config['SESSION_COOKIE_SECURE'] = False  # 允许HTTP访问cookie
        app.config['REMEMBER_COOKIE_SECURE'] = False  # 允许HTTP访问记住我cookie
    else:
        # 生产环境配置
        app.config['SESSION_COOKIE_SECURE'] = True  # 只允许HTTPS访问cookie
        app.config['REMEMBER_COOKIE_SECURE'] = True  # 只允许HTTPS访问记住我cookie
    
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
    from app.models.users import User  # 添加这行，确保User模型被正确导入
    
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
    # 注册视图版本的边缘设备蓝图，提供API端点
    from app.views.edge_devices_view import bp as edge_devices_api_bp
    app.register_blueprint(edge_devices_api_bp)
    logger.info("成功注册edge_devices_view蓝图 (从views/edge_devices_view.py导入)")
    
    # 注册api_bp蓝图，该蓝图包含重新生成密钥等API功能
    from app.views.edge_devices_view import api_bp as edge_devices_view_api_bp
    app.register_blueprint(edge_devices_view_api_bp)
    logger.info("成功注册edge_devices_view中的api_bp蓝图 (从views/edge_devices_view.py导入)")
    
    # 注册路由版本的边缘设备管理蓝图，提供页面管理功能
    from app.routes.edge_devices import bp as edge_devices_mngt_bp
    app.register_blueprint(edge_devices_mngt_bp)
    logger.info("成功注册edge_devices_mngt蓝图 (从routes/edge_devices.py导入)")
    
    
    # ===================== 注册任务相关蓝图 =====================
    from app.views.tasks_view import bp as tasks_view_bp
    from app.routes.tasks_api import bp as tasks_api_bp
    # 修改这行，使用正确的蓝图变量
    app.register_blueprint(tasks_view_bp)  # 修改这行
    app.register_blueprint(tasks_api_bp)

    # ===================== 注册油井相关蓝图 =====================
    from app.views.oil_wells_view import bp as oil_wells_view_bp
    from app.routes.oil_wells_api import bp as oil_wells_api_bp
    app.register_blueprint(oil_wells_view_bp)
    app.register_blueprint(oil_wells_api_bp)
    
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
    
    @app.before_request
    def check_auth():
        """全局请求拦截器，验证用户登录状态和URL"""
        if app.config.get('DEBUG_LOG_ENABLED', False):
            logger.debug(f"请求信息: endpoint={request.endpoint}, path={request.path}, method={request.method}")
        
        # 检查用户认证状态和token
        if current_user.is_authenticated and not current_user.current_token:
            logout_user()  # 强制登出
            # 修改这里：使用 X-Requested-With 头判断是否是 AJAX 请求
            if request.headers.get('X-Requested-With') != 'XMLHttpRequest':
                flash('会话已过期，请重新登录')
                return redirect(url_for('web_auth.web_login'))
            return jsonify({
                'success': False,
                'error': '会话已过期，请重新登录'
            }), 401
        
        # 不需要验证的路由和静态资源
        public_endpoints = [
            'web_auth.web_login',
            'web_auth_api.web_login_api',
            'static',
            'test_https',
            'edge_device_api.create_alarm',
            'edge_device_api.create_batch_alarms',
            'edge_device_api.get_alarm_status'
            # 删除以下注释中的端点，因为它们不再是主应用的一部分
            # 'device_api.get_device_token',
            # 'device_api.create_alarm',
            # 'device_api.api_status'
        ]
        
        if request.endpoint and not any(request.endpoint.startswith(ep) for ep in public_endpoints):
            if not current_user.is_authenticated:
                if app.config.get('DEBUG_LOG_ENABLED', False):
                    logger.debug("用户未认证，重定向到登录页面")
                # 修改这里：使用 X-Requested-With 头判断是否是 AJAX 请求
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return jsonify({
                        'success': False,
                        'error': '未登录或会话已过期'
                    }), 401
                return redirect(url_for('web_auth.web_login'))
    
    @app.route('/test-https')
    def test_https():
        """用于测试HTTPS连接的路由"""
        is_https = request.headers.get('X-Forwarded-Proto', request.scheme) == 'https'
        scheme = request.scheme
        
        if app.config.get('DEBUG_LOG_ENABLED', False):
            logger.debug(f"访问/test-https: scheme={scheme}, is_https={is_https}, headers={dict(request.headers)}")
            
        # 获取到达服务器的协议方案信息
        protocol_info = {
            'scheme': request.scheme,
            'http_host': request.host,
            'url': request.url,
            'path': request.path,
            'is_secure': request.is_secure
        }
            
        return render_template('test_https.html', protocol_info=protocol_info)
    
    @app.route('/')
    def index():
        """应用程序主入口"""
        if app.config.get('DEBUG_LOG_ENABLED', False):
            logger.debug(f"访问根路径: authenticated={current_user.is_authenticated}")
        
        # 添加调试日志，帮助发现问题
        request_info = {
            'scheme': request.scheme,
            'host': request.host,
            'path': request.path,
            'is_secure': request.is_secure,
            'headers': dict(request.headers),
            'authenticated': current_user.is_authenticated if hasattr(current_user, 'is_authenticated') else False
        }
        logger.info(f"根路由请求信息: {request_info}")
        
        # 恢复原始的重定向逻辑
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
    
    # 注册自定义过滤器
    @app.template_filter('datetime')
    def format_datetime(value):
        if value is None:
            return ""
        # 确保不显示时区信息，只显示年月日时分秒
        return value.strftime('%Y-%m-%d %H:%M:%S')
    
    # 添加内置函数到Jinja2上下文
    app.jinja_env.globals.update(min=min, max=max)
    
    # 添加全局上下文处理器，确保所有模板都能访问系统配置
    from app.models.settings import SystemConfig
    @app.context_processor
    def inject_system_config():
        """向所有模板注入系统配置信息"""
        system_config = SystemConfig.get_instance()
        return {'system_config': system_config}
    
    with app.app_context():
        # 清理所有用户的登录状态
        try:
            # 不再检查命令行参数，每次应用启动时都清除所有用户的token
            from app.models.users import User
            users = User.query.all()
            for user in users:
                user.current_token = None
                user.token_timestamp = None
            db.session.commit()
            logger.info("所有用户会话已清理")
        except Exception as e:
            logger.error(f"清理用户会话时出错: {str(e)}")
            logger.exception("详细错误信息：")
    
    return app

@login_manager.user_loader
def load_user(id):
    """Flask-Login用户加载回调"""
    from app.models.users import User
    return User.query.get(int(id))
    