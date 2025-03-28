from app import create_app, db
from flask_login import logout_user
from app.models.users import User
import os
import logging
from logging.handlers import RotatingFileHandler
from config import Config

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

if __name__ == '__main__':
    with app.app_context():
        # 列出所有用户，帮助调试
        users = User.query.all()
        logger.info(f"数据库中的用户数量: {len(users)}")
        for user in users:
            logger.info(f"用户: {user.username}, 角色: {user.role}, 是否管理员: {user.is_admin}")
        
        clear_all_sessions()
    app.run(
        host=Config.HOST if hasattr(Config, 'HOST') else '0.0.0.0',
        port=Config.PORT if hasattr(Config, 'PORT') else 5000
    )