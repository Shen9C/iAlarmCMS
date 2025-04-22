from app import create_app, db
from flask_login import logout_user
from app.models.users import User
import os
import logging
from logging.handlers import RotatingFileHandler
from config import Config
import threading
import argparse

# 确保logs文件夹存在
os.makedirs(Config.LOG_PATH, exist_ok=True)

# 配置日志
log_file_path = os.path.join(Config.LOG_PATH, Config.LOG_FILENAME)
rotating_handler = RotatingFileHandler(
    log_file_path,
    maxBytes=Config.LOG_MAX_BYTES,
    backupCount=Config.LOG_BACKUP_COUNT
)

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        rotating_handler
    ]
)
logger = logging.getLogger(__name__)

# 创建应用实例
app = create_app()

def clear_all_sessions():
    """清理所有用户会话"""
    try:
        # 更新所有用户的令牌为空
        User.query.update({User.current_token: None})
        db.session.commit()
        logger.info("所有用户会话已清理")
    except Exception as e:
        logger.error(f"清理会话时发生错误: {str(e)}")
        db.session.rollback()

def run_web_app(host, port, debug):
    """运行主Web应用"""
    logger.info(f"启动主Web应用服务器，监听 {host}:{port}")
    app.run(host=host, port=port, debug=debug, use_reloader=False)

def run_device_api(host, port, debug):
    """运行边缘设备API服务器"""
    try:
        from app.routes.edge_device_api_server import app as device_api_app
        logger.info(f"启动边缘设备API服务器，监听 {host}:{port}")
        device_api_app.run(host=host, port=port, debug=debug, use_reloader=False)
    except Exception as e:
        logger.error(f"启动边缘设备API服务器失败: {str(e)}")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='油田数据管理系统服务器')
    
    # Web应用参数
    parser.add_argument('--web-host', default='0.0.0.0', help='Web应用监听地址')
    parser.add_argument('--web-port', type=int, default=5000, help='Web应用监听端口')
    
    # 设备API参数
    parser.add_argument('--api-host', default='0.0.0.0', help='设备API监听地址')
    parser.add_argument('--api-port', type=int, default=5566, help='设备API监听端口')
    
    # 共享参数
    parser.add_argument('--debug', action='store_true', help='是否启用调试模式')
    parser.add_argument('--api-only', action='store_true', help='仅启动边缘设备API服务')
    parser.add_argument('--web-only', action='store_true', help='仅启动Web应用服务')
    
    args = parser.parse_args()
    
    with app.app_context():
        # 列出所有用户，帮助调试
        users = User.query.all()
        logger.info(f"数据库中的用户数量: {len(users)}")
        for user in users:
            logger.info(f"用户: {user.username}, 角色: {user.role}, 是否管理员: {user.is_admin}")
        
        clear_all_sessions()
    
    # 根据参数决定启动哪些服务
    if args.api_only:
        # 仅启动边缘设备API服务
        run_device_api(args.api_host, args.api_port, args.debug)
    elif args.web_only:
        # 仅启动Web应用
        run_web_app(args.web_host, args.web_port, args.debug)
    else:
        # 同时启动两个服务
        logger.info("同时启动Web应用和边缘设备API服务器")
        
        # 使用线程启动设备API服务器
        device_api_thread = threading.Thread(
            target=run_device_api,
            args=(args.api_host, args.api_port, args.debug),
            daemon=True
        )
        device_api_thread.start()
        
        # 主线程运行Web应用
        run_web_app(args.web_host, args.web_port, args.debug)