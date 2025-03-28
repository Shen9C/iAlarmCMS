from app import create_app, db
from flask_login import logout_user
from app.models.users import User
import os
import logging
from logging.handlers import RotatingFileHandler

# 确保logs文件夹存在
logs_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'logs')
os.makedirs(logs_dir, exist_ok=True)

# 配置日志
log_file_path = os.path.join(logs_dir, 'oilfield_gateway.log')
rotating_handler = RotatingFileHandler(
    log_file_path,
    maxBytes=50 * 1024 * 1024,  # 50MB
    backupCount=20  # 最多保留20个文件
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

# 直接创建应用实例
app = create_app()

# 添加请求前后的日志记录
@app.before_request
def log_request_info():
    from flask import request
    logger.debug(f'请求: {request.method} {request.url} - 参数: {dict(request.args)}')

@app.after_request
def log_response_info(response):
    from flask import request
    logger.debug(f'响应: {request.method} {request.url} - 状态码: {response.status_code}')
    
    # 对于登录失败的情况，记录更详细的信息
    if request.path == '/api/v1/web/login' and response.status_code == 401:
        try:
            response_data = response.get_json()
            logger.error(f"登录失败详情: {response_data}")
        except Exception as e:
            logger.error(f"无法解析登录失败响应: {str(e)}")
            # 尝试获取响应文本
            try:
                logger.error(f"登录失败响应文本: {response.get_data(as_text=True)}")
            except:
                pass
    
    if response.status_code == 302:
        logger.warning(f'重定向: {request.url} -> {response.location}')
    return response

# 添加登录验证的调试钩子
@app.before_request
def log_login_attempts():
    from flask import request
    if request.path == '/api/v1/web/login' and request.method == 'POST':
        # 尝试从JSON和表单数据中获取用户名和密码
        try:
            json_data = request.get_json(silent=True) or {}
            form_data = request.form.to_dict() or {}
            
            # 合并数据源
            data = {**form_data, **json_data}
            
            username = data.get('username')
            password = data.get('password')
            
            logger.debug(f"登录尝试: 用户名={username}, 密码长度={len(password) if password else 0}")
            logger.debug(f"请求内容类型: {request.content_type}")
            # logger.debug(f"请求数据: JSON={json_data}, 表单={form_data}")
            
            # 查询用户并验证密码
            user = User.query.filter_by(username=username).first()
            if user:
                logger.debug(f"找到用户: {user.username}, 角色={user.role}, 是否管理员={user.is_admin}")
                logger.debug(f"密码哈希值: {user.password_hash[:15] if user.password_hash else 'None'}...")
                
                # 手动验证密码
                if hasattr(user, 'password_hash') and user.password_hash:
                    from werkzeug.security import check_password_hash
                    is_valid = check_password_hash(user.password_hash, password)
                    logger.debug(f"密码验证结果: {'成功' if is_valid else '失败'}")
                    
                    # 如果验证失败，记录更多信息
                    if not is_valid:
                        logger.error(f"密码验证失败: 输入密码='{password}', 用户={username}")
                else:
                    logger.warning(f"用户 {username} 没有设置密码哈希")
            else:
                logger.warning(f"用户 {username} 不存在")
        except Exception as e:
            logger.error(f"处理登录请求时出错: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())

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
            logger.info("已清除所有用户的登录状态")
    except Exception as e:
        logger.error(f"清除会话时出错: {str(e)}")

if __name__ == '__main__':
    with app.app_context():
        # 列出所有用户，帮助调试
        users = User.query.all()
        logger.info(f"数据库中的用户数量: {len(users)}")
        for user in users:
            logger.info(f"用户: {user.username}, 角色: {user.role}, 是否管理员: {user.is_admin}, 密码哈希: {user.password_hash[:15] if user.password_hash else 'None'}...")
        
        clear_all_sessions()
    app.run(debug=True)