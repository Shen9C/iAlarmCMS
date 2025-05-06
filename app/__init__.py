from flask import Flask, redirect, url_for, request, jsonify, flash, render_template
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, current_user, logout_user
from flask_migrate import Migrate
from flask_cors import CORS
from app.utils.yaml_config_loader import ConfigObject, load_yaml_config, merge_configs, create_config_object
from app.utils.web_auth import get_ssl_context, enable_ssl_for_app
import logging
import os
import importlib.util
from pathlib import Path
import sys
from datetime import datetime
import traceback

# 初始化日志配置
from app.utils.logger_config import setup_logger
setup_logger()

# 禁用所有数据库相关的日志输出
logging.getLogger('sqlalchemy.engine').setLevel(logging.WARNING)
logging.getLogger('sqlalchemy.pool').setLevel(logging.WARNING)
logging.getLogger('sqlalchemy.dialects').setLevel(logging.WARNING)
logging.getLogger('sqlalchemy.orm').setLevel(logging.WARNING)
logging.getLogger('base').setLevel(logging.WARNING)
logging.getLogger('sqlalchemy').setLevel(logging.WARNING)
logging.getLogger('alembic').setLevel(logging.WARNING)
logging.getLogger('app.models').setLevel(logging.WARNING)
logging.getLogger('app.utils.db_connection').setLevel(logging.WARNING)

# 设置日志
logger = logging.getLogger(__name__)

# 初始化Flask扩展
db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()
login_manager.login_view = 'web_auth.web_login'  # 设置登录视图
login_manager.login_message = '请先登录'  # 设置登录提示消息
login_manager.login_message_category = 'info'  # 设置消息类别

# 导入数据库连接管理器
try:
    from app.utils.db_connection import init_db_engine, check_db_connection, db_session
    HAS_DB_CONNECTION_MANAGER = True
    logger.info("成功导入数据库连接管理器")
except ImportError as e:
    logger.warning(f"无法导入数据库连接管理器，将使用默认SQLAlchemy连接: {e}")
    HAS_DB_CONNECTION_MANAGER = False

def configure_database(app):
    """配置数据库连接和日志级别"""
    with app.app_context():
        # 配置SQLAlchemy的日志级别
        db.engine.echo = False
        db.engine.logger.setLevel(logging.WARNING)
        
        # 如果使用自定义数据库连接管理器，初始化引擎
        if HAS_DB_CONNECTION_MANAGER:
            try:
                init_db_engine()
                logger.info(f"{app.name}: 数据库连接管理器初始化成功")
            except Exception as db_error:
                logger.error(f"{app.name}: 数据库连接管理器初始化失败: {db_error}")

def create_app(config=None):
    """
    创建Flask应用实例
    
    Args:
        config: 配置对象，如果为None则使用默认配置
    
    Returns:
        Flask: Flask应用实例
    """
    app = Flask(__name__)
    
    # 加载配置
    if config is None:
        import os
        config_path = os.environ.get('CONFIG_PATH', 'config/settings.yaml')
        config = load_yaml_config(config_path)

    # 将配置对象添加到模板上下文中
    app.config['system_config'] = config
    
    # 设置应用配置
    app.config.update(
        SECRET_KEY=config.get('secret_key', 'dev'),
        SQLALCHEMY_DATABASE_URI=f"postgresql://{config['database']['user']}:{config['database']['password']}@{config['database']['host']}/{config['database']['name']}",
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        SQLALCHEMY_ENGINE_OPTIONS={
            'pool_size': 10,
            'pool_recycle': 3600,
            'pool_pre_ping': True
        }
    )
    
    # 初始化扩展
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    CORS(app)
    
    # 配置数据库
    configure_database(app)
    
    # 注册蓝图
    from app.views.web_auth_view import bp as web_auth_bp
    from app.views.alarms_view import bp as alarms_bp
    from app.views.edge_devices_view import bp as devices_bp, api_bp as devices_api_bp
    from app.views.tasks_view import bp as tasks_bp
    from app.views.users_view import bp as users_bp
    from app.views.oil_wells_view import bp as oil_wells_bp
    from app.views.stats_view import bp as stats_bp
    from app.views.settings_view import bp as settings_bp
    from app.routes.settings_api import bp as settings_api_bp
    from app.routes.edge_devices import bp as edge_devices_mngt_bp
    
    app.register_blueprint(web_auth_bp)
    app.register_blueprint(alarms_bp, url_prefix='/alarms')
    app.register_blueprint(devices_bp, url_prefix='/edge_devices')
    app.register_blueprint(tasks_bp, url_prefix='/tasks')
    app.register_blueprint(users_bp, url_prefix='/users')
    app.register_blueprint(oil_wells_bp, url_prefix='/wells')
    app.register_blueprint(stats_bp, url_prefix='/stats')
    app.register_blueprint(settings_bp, url_prefix='/settings')
    app.register_blueprint(settings_api_bp)
    app.register_blueprint(edge_devices_mngt_bp)
    
    # 添加根路由重定向
    @app.route('/')
    def index():
        return redirect(url_for('alarms_view.index'))
    
    # 添加系统配置到模板上下文中
    @app.context_processor
    def inject_system_name():
        try:
            from app.models.settings import SystemConfig
            return {'system_name_zh': SystemConfig.get_system_name()}
        except Exception as e:
            logging.warning(f"系统名称获取失败: {e}")
            return {'system_name_zh': "智能告警综合管理系统"}
    
    # 添加 datetime 过滤器
    @app.template_filter('datetime')
    def format_datetime(value):
        if value is None:
            return ''
        return value.strftime('%Y-%m-%d %H:%M:%S')
    
    # 添加401错误处理器
    @app.errorhandler(401)
    def unauthorized(error):
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({
                'code': 401,
                'message': '请先登录',
                'success': False
            }), 401
        return redirect(url_for('web_auth.web_login'))
    
    return app

def create_web_app(config=None):
    """
    创建Web应用实例
    
    Args:
        config: 配置对象，如果为None则使用默认配置
        
    Returns:
        Flask: Web应用实例
    """
    return create_app(config)

def create_api_app(config=None):
    """
    创建API应用实例
    
    Args:
        config: 配置对象，如果为None则使用默认配置
        
    Returns:
        Flask: API应用实例
    """
    app = create_app(config)
    
    # API特定的配置
    app.config['JSON_AS_ASCII'] = False
    app.config['JSONIFY_MIMETYPE'] = 'application/json;charset=utf-8'
    
    return app

@login_manager.user_loader
def load_user(id):
    """Flask-Login用户加载回调"""
    from app.models.users import User
    return User.query.get(int(id))
    
# 在文件末尾添加导出
__all__ = ['create_web_app', 'create_api_app', 'db', 'migrate', 'login_manager']
    