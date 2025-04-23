#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
数据库初始化脚本，负责：
1. 创建数据库表结构
2. 生成SSL证书（用于HTTPS支持）
"""

import os
import sys
import logging
from logging.handlers import RotatingFileHandler
from datetime import datetime
import click
import psycopg2
from psycopg2 import sql
import codecs
import traceback
from sqlalchemy import text, inspect
from pathlib import Path
import argparse
from OpenSSL import crypto
import importlib

# 将项目根目录添加到系统路径
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

# 确保logs文件夹存在
logs_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'logs')
os.makedirs(logs_dir, exist_ok=True)

# 创建logger实例
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# 清除现有的处理器，避免重复
if logger.handlers:
    logger.handlers.clear()

# 配置日志文件处理器
log_file_path = os.path.join(logs_dir, 'pg_db_init.log')
rotating_handler = RotatingFileHandler(
    log_file_path,
    maxBytes=50 * 1024 * 1024,
    backupCount=20,
    encoding='utf-8'
)

# 配置控制台处理器
if sys.stdout.encoding != 'utf-8':
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
console_handler = logging.StreamHandler(sys.stdout)

# 设置日志格式
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
rotating_handler.setFormatter(formatter)
console_handler.setFormatter(formatter)

# 添加处理器到logger
logger.addHandler(rotating_handler)
logger.addHandler(console_handler)

# 导入应用相关模块
from app import create_app, db
from app.models.users import User
from app.models.alarms import Alarm
from app.models.edge_devices import EdgeDevice
from app.models.tasks import Task
from app.models.oil_wells import OilWell
from app.models.settings import SystemConfig, KeyValueSetting
from app.utils.yaml_config_loader import Config, config

# 修改成功/失败标记
SUCCESS_MARK = '[成功]'
ERROR_MARK = '[失败]'

# 禁用应用日志处理器，避免日志重复
app = create_app()
app_logger = logging.getLogger('app')
app_logger.handlers.clear()
app_logger.addHandler(logging.NullHandler())

# 从配置对象中获取数据库配置
DB_USER = config.DB_USER
DB_PASSWORD = config.DB_PASSWORD
DB_HOST = config.DB_HOST
DB_PORT = config.DB_PORT
DB_NAME = config.DB_NAME

# 记录数据库配置信息
logger.info(f"数据库配置: 主机={DB_HOST}, 端口={DB_PORT}, 数据库名={DB_NAME}, 用户={DB_USER}")

def init_database(reset=False):
    """初始化数据库"""
    logger.info("正在初始化数据库...")
    
    # 检查数据库是否存在
    if not create_database_if_not_exists():
        logger.error("创建数据库失败")
        return False
    
    with app.app_context():
        try:
            # 如果需要重置数据库
            if reset:
                logger.info("重置数据库...")
                db.drop_all()
            
            # 创建数据库表
            logger.info("创建数据库表...")
            db.create_all()
            logger.info(f"{SUCCESS_MARK} 数据库表创建成功")
            
            # 创建管理员账户
            try:
                # 检查是否已有管理员账户
                admin = User.query.filter_by(username='管理员').first()
                if not admin:
                    admin = User(
                        username='管理员',
                        role='admin',
                        is_admin=True,
                        active=True
                    )
                    admin.set_password('admin123@Youtian')
                    db.session.add(admin)
                    db.session.commit()
                    logger.info(f"{SUCCESS_MARK} 管理员账户创建成功")
                else:
                    logger.info(f"管理员账户已存在，跳过创建")
            except Exception as e:
                logger.error(f"{ERROR_MARK} 创建管理员账户失败: {str(e)}")
            
            return True
        except Exception as e:
            logger.error(f"数据库初始化失败: {str(e)}")
            logger.error(traceback.format_exc())
            return False

@click.group()
def cli():
    """PostgreSQL数据库管理工具"""
    pass

def get_connection_string():
    """获取PostgreSQL连接字符串"""
    return f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

def get_connection():
    """获取PostgreSQL连接"""
    try:
        # 添加连接超时设置
        conn = psycopg2.connect(
            user=DB_USER,
            password=DB_PASSWORD,
            host=DB_HOST,
            port=DB_PORT,
            database=DB_NAME,
            connect_timeout=10  # 设置连接超时为10秒
        )
        return conn
    except Exception as e:
        logger.error(f"连接数据库失败: {str(e)}")
        return None

def create_database_if_not_exists():
    """如果数据库不存在，则创建数据库"""
    try:
        # 添加连接超时设置
        conn = psycopg2.connect(
            user=DB_USER,
            password=DB_PASSWORD,
            host=DB_HOST,
            port=DB_PORT,
            database="postgres",
            connect_timeout=10
        )
        conn.autocommit = True
        cursor = conn.cursor()
        
        # 使用更高效的查询
        cursor.execute("SELECT 1 FROM pg_database WHERE datname = %s", (DB_NAME,))
        exists = cursor.fetchone()
        
        if not exists:
            logger.info(f"数据库 {DB_NAME} 不存在，正在创建...")
            cursor.execute(sql.SQL("CREATE DATABASE {} WITH ENCODING 'UTF8'").format(
                sql.Identifier(DB_NAME)))
            logger.info(f"数据库 {DB_NAME} 创建成功")
        else:
            logger.info(f"数据库 {DB_NAME} 已存在")
        
        cursor.close()
        conn.close()
        return True
    except Exception as e:
        logger.error(f"创建数据库失败: {str(e)}")
        return False

@cli.command()
def init():
    """初始化PostgreSQL数据库"""
    init_database()

def clear_user_sessions():
    """清理所有用户会话"""
    try:
        logger.info("正在清理所有用户会话...")
        from app.models.users import User
        users = User.query.all()
        for user in users:
            user.current_token = None
            user.token_timestamp = None
        db.session.commit()
        logger.info(f"{SUCCESS_MARK} 所有用户会话已清理")
    except Exception as e:
        logger.error(f"清理用户会话失败: {str(e)}")

def generate_ssl_cert(cert_dir, cert_file, key_file, 
                     country="CN", state="Beijing", locality="Beijing", 
                     org="DevTest", org_unit="Testing", cn="localhost", force=False):
    """
    生成自签名的SSL证书和私钥
    """
    # 确保目录存在
    os.makedirs(cert_dir, exist_ok=True)
    
    cert_path = os.path.join(cert_dir, cert_file)
    key_path = os.path.join(cert_dir, key_file)
    
    # 检查证书是否已存在，如果不存在或force=True则生成新证书
    if not force and os.path.exists(cert_path) and os.path.exists(key_path):
        logger.info(f"证书已存在：{cert_path} 和 {key_path}")
        return cert_path, key_path
    
    # 创建密钥对
    k = crypto.PKey()
    k.generate_key(crypto.TYPE_RSA, 2048)
    
    # 创建自签名证书
    cert = crypto.X509()
    cert.get_subject().C = country
    cert.get_subject().ST = state
    cert.get_subject().L = locality
    cert.get_subject().O = org
    cert.get_subject().OU = org_unit
    cert.get_subject().CN = cn
    cert.set_serial_number(1000)
    cert.gmtime_adj_notBefore(0)
    cert.gmtime_adj_notAfter(10*365*24*60*60)  # 10年有效期
    cert.set_issuer(cert.get_subject())
    cert.set_pubkey(k)
    cert.sign(k, 'sha256')
    
    # 写入证书和私钥文件
    with open(cert_path, "wb") as cert_file_obj:
        cert_file_obj.write(crypto.dump_certificate(crypto.FILETYPE_PEM, cert))
    
    with open(key_path, "wb") as key_file_obj:
        key_file_obj.write(crypto.dump_privatekey(crypto.FILETYPE_PEM, k))
    
    logger.info(f"成功生成SSL证书：{cert_path}")
    logger.info(f"成功生成SSL私钥：{key_path}")
    
    return cert_path, key_path

def create_ssl_certs(force=False):
    """创建SSL证书"""
    logger.info("正在生成SSL证书...")
    
    # 定义SSL目录和文件名
    ssl_dir = os.path.join(project_root, "ssl")
    # 确保目录存在
    os.makedirs(ssl_dir, exist_ok=True)
    
    # 定义SSL证书和密钥文件名
    # Web服务器使用的证书文件
    web_cert_file = "web_cert.pem"
    web_key_file = "web_key.pem"
    # API服务器使用的证书文件
    api_cert_file = "api_cert.pem"
    api_key_file = "api_key.pem"
    
    # 完整路径
    web_cert_path = os.path.join(ssl_dir, web_cert_file)
    web_key_path = os.path.join(ssl_dir, web_key_file)
    api_cert_path = os.path.join(ssl_dir, api_cert_file)
    api_key_path = os.path.join(ssl_dir, api_key_file)
    
    # 存储证书路径的字典
    cert_paths = {}
    
    try:
        # 1. 首先生成Web证书（使用Chrome兼容证书生成脚本）
        web_cert_script = os.path.join(project_root, "scripts", "generate_web_cert.py")
        if os.path.exists(web_cert_script):
            logger.info("正在为Web登录生成Chrome兼容证书...")
            spec = importlib.util.spec_from_file_location("generate_web_cert", web_cert_script)
            web_cert_module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(web_cert_module)
            
            if hasattr(web_cert_module, "generate_chrome_compatible_cert"):
                try:
                    # 尝试使用新的参数调用
                    web_cert_path, web_key_path = web_cert_module.generate_chrome_compatible_cert(
                        ssl_dir, web_cert_file, web_key_file)
                except TypeError:
                    # 如果新参数调用失败，使用旧的调用方式
                    logger.warning("使用旧版证书生成器接口，将手动重命名证书文件")
                    temp_cert_path, temp_key_path = web_cert_module.generate_chrome_compatible_cert(ssl_dir)
                    
                    # 如果生成的证书不是我们想要的名称，则重命名
                    if os.path.basename(temp_cert_path) != web_cert_file:
                        os.rename(temp_cert_path, web_cert_path)
                    if os.path.basename(temp_key_path) != web_key_file:
                        os.rename(temp_key_path, web_key_path)
                
                logger.info(f"Web登录Chrome兼容证书生成成功: {web_cert_path}")
                cert_paths['web'] = (web_cert_path, web_key_path)
            else:
                logger.warning("Web证书生成模块缺少必要的函数，使用内置方法生成")
                web_cert_path, web_key_path = generate_ssl_cert(
                    cert_dir=ssl_dir,
                    cert_file=web_cert_file,
                    key_file=web_key_file,
                    cn="localhost",
                    force=force
                )
                cert_paths['web'] = (web_cert_path, web_key_path)
        else:
            logger.warning(f"未找到Web证书生成脚本，使用内置方法生成")
            
            # 使用内置方法生成Web证书
            web_cert_path, web_key_path = generate_ssl_cert(
                cert_dir=ssl_dir,
                cert_file=web_cert_file,
                key_file=web_key_file,
                cn="localhost",
                force=force
            )
            cert_paths['web'] = (web_cert_path, web_key_path)
        
        # 2. 然后生成API证书
        api_cert_script = os.path.join(project_root, "scripts", "generate_api_cert.py")
        if os.path.exists(api_cert_script):
            logger.info("正在为边缘设备API生成专用证书...")
            spec = importlib.util.spec_from_file_location("generate_api_cert", api_cert_script)
            api_cert_module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(api_cert_module)
            
            if hasattr(api_cert_module, "generate_api_cert"):
                try:
                    # 尝试使用新的参数调用
                    api_cert_path, api_key_path = api_cert_module.generate_api_cert(
                        ssl_dir, api_cert_file, api_key_file)
                except TypeError:
                    # 如果新参数调用失败，使用旧的调用方式
                    logger.warning("使用旧版API证书生成器接口，将手动重命名证书文件")
                    temp_cert_path, temp_key_path = api_cert_module.generate_api_cert(ssl_dir)
                    
                    # 如果生成的证书不是我们想要的名称，则重命名
                    if os.path.basename(temp_cert_path) != api_cert_file:
                        os.rename(temp_cert_path, api_cert_path)
                    if os.path.basename(temp_key_path) != api_key_file:
                        os.rename(temp_key_path, api_key_path)
                
                logger.info(f"API专用证书生成成功: {api_cert_path}")
                cert_paths['api'] = (api_cert_path, api_key_path)
            else:
                logger.warning("API证书生成模块缺少必要的函数，使用内置方法生成")
                api_cert_path, api_key_path = generate_ssl_cert(
                    cert_dir=ssl_dir,
                    cert_file=api_cert_file,
                    key_file=api_key_file,
                    cn="api.localhost",
                    force=force
                )
                cert_paths['api'] = (api_cert_path, api_key_path)
        else:
            logger.warning(f"未找到API证书生成脚本，使用内置方法生成")
            
            # 使用内置方法生成API证书
            api_cert_path, api_key_path = generate_ssl_cert(
                cert_dir=ssl_dir,
                cert_file=api_cert_file,
                key_file=api_key_file,
                cn="api.localhost",
                force=force
            )
            cert_paths['api'] = (api_cert_path, api_key_path)
        
        # 3. 生成兼容配置文件的软链接或副本
        # 根据配置文件中的设置，创建对应的证书链接
        config_cert_file = config.ssl.cert_file if hasattr(config.ssl, 'cert_file') else "cert.pem"
        config_key_file = config.ssl.key_file if hasattr(config.ssl, 'key_file') else "key.pem"
        
        # 如果配置文件中的证书名与web证书不同，则创建软链接或副本
        if config_cert_file != web_cert_file:
            config_cert_path = os.path.join(ssl_dir, config_cert_file)
            try:
                # 尝试创建软链接
                if os.path.exists(config_cert_path):
                    os.remove(config_cert_path)
                
                try:
                    # 在Windows上可能不支持软链接，所以使用副本
                    import shutil
                    shutil.copy2(web_cert_path, config_cert_path)
                    logger.info(f"为兼容配置文件，创建证书副本: {config_cert_path}")
                except:
                    os.symlink(web_cert_path, config_cert_path)
                    logger.info(f"为兼容配置文件，创建证书软链接: {config_cert_path}")
            except Exception as e:
                logger.warning(f"创建证书兼容文件失败: {str(e)}")
        
        if config_key_file != web_key_file:
            config_key_path = os.path.join(ssl_dir, config_key_file)
            try:
                # 尝试创建软链接
                if os.path.exists(config_key_path):
                    os.remove(config_key_path)
                
                try:
                    # 在Windows上可能不支持软链接，所以使用副本
                    import shutil
                    shutil.copy2(web_key_path, config_key_path)
                    logger.info(f"为兼容配置文件，创建密钥副本: {config_key_path}")
                except:
                    os.symlink(web_key_path, config_key_path)
                    logger.info(f"为兼容配置文件，创建密钥软链接: {config_key_path}")
            except Exception as e:
                logger.warning(f"创建密钥兼容文件失败: {str(e)}")
        
        # 证书生成总结
        logger.info("\nSSL证书生成完成:")
        if 'web' in cert_paths:
            logger.info(f"Web登录证书: {cert_paths['web'][0]}")
            logger.info(f"Web登录密钥: {cert_paths['web'][1]}")
        if 'api' in cert_paths:
            logger.info(f"API证书: {cert_paths['api'][0]}")
            logger.info(f"API密钥: {cert_paths['api'][1]}")
        
        # 返回Web证书路径作为默认证书
        return cert_paths.get('web', (None, None))
            
        except Exception as e:
        logger.error(f"生成SSL证书时出错: {str(e)}")
        logger.error(traceback.format_exc())
        logger.error("请确保已安装相关依赖库: pip install pyOpenSSL cryptography")
        return None, None

def run_test_data_script():
    """
    该函数已废弃，测试数据生成已移至tests/test_generate_data.py
    此处仅保留提示信息，建议用户使用专门的测试工具
    """
    logger.info("测试数据生成已移至独立测试工具")
    logger.info("如需生成测试数据，请运行: python tests/test_generate_data.py")
    logger.info("这样可以更好地分离应用初始化和测试功能")

def main():
    parser = argparse.ArgumentParser(description="数据库初始化和系统准备脚本")
    parser.add_argument("action", nargs='?', default=None, help="执行的操作: reset(重置所有), ssl(仅生成SSL证书)")
    parser.add_argument("--reset", action="store_true", help="重置数据库（删除所有现有表并重建）")
    parser.add_argument("--no-ssl", action="store_true", help="不生成SSL证书")
    parser.add_argument("--ssl-only", action="store_true", help="只生成SSL证书")
    parser.add_argument("--regenerate-ssl", action="store_true", help="强制重新生成SSL证书（即使已存在）")
    
    args = parser.parse_args()
    
    # 处理位置参数
    if args.action == 'reset':
        args.reset = True
    elif args.action == 'ssl':
        args.ssl_only = True
    elif args.action == 'regenerate-ssl':
        args.regenerate_ssl = True
    elif args.action == 'rebuild':  # 兼容旧命令
        args.reset = True
    
    # 如果指定只重新生成SSL证书
    if args.regenerate_ssl:
        logger.info("正在强制重新生成SSL证书...")
        # 移除现有的Web证书文件
        ssl_dir = os.path.join(project_root, "ssl")
        web_cert_file = "web_cert.pem"
        web_key_file = "web_key.pem"
        api_cert_file = "api_cert.pem"
        api_key_file = "api_key.pem"
        # 以及旧的证书名称
        old_cert_file = "cert.pem"
        old_key_file = "key.pem"
        
        cert_files = [
            os.path.join(ssl_dir, web_cert_file),
            os.path.join(ssl_dir, web_key_file),
            os.path.join(ssl_dir, api_cert_file),
            os.path.join(ssl_dir, api_key_file),
            os.path.join(ssl_dir, old_cert_file),
            os.path.join(ssl_dir, old_key_file)
        ]
        
        # 尝试删除所有证书文件
        for cert_path in cert_files:
            try:
                if os.path.exists(cert_path):
                    logger.info(f"删除现有证书文件: {cert_path}")
                    os.remove(cert_path)
            except Exception as e:
                logger.warning(f"删除证书文件失败: {str(e)}")
        
        # 创建新的SSL证书
        cert_path, key_path = create_ssl_certs(force=True)
        if cert_path and key_path:
            logger.info("\nSSL证书重新生成完成！")
            logger.info("您可以通过以下命令启动HTTPS服务器:")
            logger.info("python run.py --web-only --ssl  # 启动HTTPS Web服务器")
            logger.info("python run.py --api-only --ssl  # 启动HTTPS API服务器")
        return
    
    # 如果只生成SSL证书
    if args.ssl_only:
        cert_path, key_path = create_ssl_certs()
        if cert_path and key_path:
            logger.info("\nSSL证书生成完成！")
            logger.info("您可以通过以下命令启动HTTPS服务器:")
            logger.info("python run.py --api-only --ssl")
        return
    
    # reset命令包含所有功能：重建数据库、生成证书
    if args.reset:
        logger.info("执行全面重置操作...")
        # 重建数据库
        init_database(reset=True)
        
        # 生成SSL证书（除非明确指定不生成）
        if not args.no_ssl:
            # 移除现有的Web证书文件
            ssl_dir = os.path.join(project_root, "ssl")
            web_cert_file = "web_cert.pem"
            web_key_file = "web_key.pem"
            api_cert_file = "api_cert.pem"
            api_key_file = "api_key.pem"
            # 以及旧的证书名称
            old_cert_file = "cert.pem"
            old_key_file = "key.pem"
            
            cert_files = [
                os.path.join(ssl_dir, web_cert_file),
                os.path.join(ssl_dir, web_key_file),
                os.path.join(ssl_dir, api_cert_file),
                os.path.join(ssl_dir, api_key_file),
                os.path.join(ssl_dir, old_cert_file),
                os.path.join(ssl_dir, old_key_file)
            ]
            
            # 尝试删除所有证书文件
            for cert_path in cert_files:
                try:
                    if os.path.exists(cert_path):
                        logger.info(f"删除现有证书文件: {cert_path}")
                        os.remove(cert_path)
                except Exception as e:
                    logger.warning(f"删除证书文件失败: {str(e)}")
            
            # 创建新的SSL证书
            create_ssl_certs(force=True)
        
        # 提示用户测试数据生成方法已改变
        run_test_data_script()
        
        logger.info("\n系统重置完成!")
        logger.info("您可以通过以下命令启动服务器:")
        logger.info("python run.py --api-only --ssl  # 启动HTTPS API服务器")
        logger.info("python run.py --api-only        # 启动HTTP API服务器")
        return
    
    # 普通初始化流程
    # 初始化数据库
    init_database(reset=False)
    
    # 生成SSL证书（除非明确指定不生成）
    if not args.no_ssl:
        create_ssl_certs()
    
    # 提示用户测试数据生成方法已改变
    run_test_data_script()
    
    logger.info("\n系统初始化和准备工作已完成!")
    logger.info("您可以通过以下命令启动服务器:")
    logger.info("python run.py --api-only --ssl  # 启动HTTPS API服务器")
    logger.info("python run.py --api-only        # 启动HTTP API服务器")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        cmd_map = {
            'rebuild': '--reset',
            'regenerate-ssl': '--regenerate-ssl',
            'ssl': '--ssl-only',
            'init': 'init'
        }
        if sys.argv[1] in cmd_map:
            sys.argv[1] = cmd_map[sys.argv[1]]
            # 对于click命令的兼容
            if sys.argv[1] == 'init':
    cli()
                sys.exit(0)
        # 其他情况继续执行main()
        main()
    else:
        main()

