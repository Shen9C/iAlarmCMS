from flask import Blueprint, jsonify, request
from flask_login import login_required, current_user
from app.models.settings import SystemConfig, KeyValueSetting
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import logging

logger = logging.getLogger(__name__)

bp = Blueprint('settings_api', __name__, url_prefix='/api/settings')

def send_test_email(to_email):
    """发送测试邮件
    
    Args:
        to_email (str): 收件人邮箱地址
    """
    try:
        # 获取邮件配置
        config = current_app.config['system_config']
        smtp_config = config.get('smtp', {})
        
        # 创建邮件内容
        msg = MIMEMultipart()
        msg['From'] = smtp_config.get('sender', 'noreply@example.com')
        msg['To'] = to_email
        msg['Subject'] = '测试邮件'
        
        # 邮件正文
        body = """
        <html>
            <body>
                <h2>测试邮件</h2>
                <p>这是一封测试邮件，用于验证邮件系统是否正常工作。</p>
                <p>如果您收到这封邮件，说明邮件系统配置正确。</p>
            </body>
        </html>
        """
        msg.attach(MIMEText(body, 'html'))
        
        # 连接SMTP服务器并发送邮件
        with smtplib.SMTP(smtp_config.get('host', 'localhost'), 
                         smtp_config.get('port', 25)) as server:
            if smtp_config.get('use_tls', False):
                server.starttls()
            
            if smtp_config.get('username') and smtp_config.get('password'):
                server.login(smtp_config['username'], smtp_config['password'])
            
            server.send_message(msg)
            logger.info(f'测试邮件已发送到 {to_email}')
            
    except Exception as e:
        logger.error(f'发送测试邮件失败: {str(e)}')
        raise

@bp.route('/test_email', methods=['POST'])
@login_required
def test_email():
    """发送测试邮件"""
    if current_user.role != 'admin':
        return jsonify({'code': 403, 'message': '没有权限'}), 403
    
    try:
        # 获取收件人邮箱
        email = request.json.get('email')
        if not email:
            return jsonify({'code': 400, 'message': '请提供邮箱地址'}), 400
        
        # 发送测试邮件
        send_test_email(email)
        return jsonify({'code': 200, 'message': '测试邮件发送成功'})
    except Exception as e:
        return jsonify({'code': 500, 'message': str(e)}), 500 