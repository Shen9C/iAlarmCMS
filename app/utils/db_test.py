#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
数据库连接测试工具
仅提供连接测试功能，不进行数据库初始化
"""

import os
import sys
import logging
import time
import psycopg2
from pathlib import Path

# 设置日志
logger = logging.getLogger(__name__)

# 获取项目根目录
project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root))

# 导入数据库配置
from app.utils.yaml_config_loader import config

# 从配置对象中获取数据库配置
DB_USER = config.DB_USER
DB_PASSWORD = config.DB_PASSWORD
DB_HOST = config.DB_HOST
DB_PORT = config.DB_PORT
DB_NAME = config.DB_NAME

# 修改成功/失败标记
SUCCESS_MARK = '[成功]'
ERROR_MARK = '[失败]'

def get_connection(database=None, max_retries=3, retry_delay=1):
    """
    获取数据库连接，带有重试机制
    
    Args:
        database (str): 要连接的数据库名，None表示使用配置中的数据库
        max_retries (int): 最大重试次数
        retry_delay (int): 初始重试延迟(秒)
    
    Returns:
        psycopg2.connection or None: 连接对象，失败则返回None
    """
    if database is None:
        database = DB_NAME
        
    retries = 0
    last_error = None
    
    while retries < max_retries:
        try:
            # 添加连接超时设置
            conn = psycopg2.connect(
                user=DB_USER,
                password=DB_PASSWORD,
                host=DB_HOST,
                port=DB_PORT,
                database=database,
                connect_timeout=3  # 减少超时时间
            )
            logger.info(f"{SUCCESS_MARK} 数据库连接成功: {database}")
            return conn
        except Exception as e:
            last_error = e
            retries += 1
            logger.warning(f"数据库连接失败 (尝试 {retries}/{max_retries}): {e}")
            
            if retries < max_retries:
                # 重试延迟增加（指数退避）
                current_delay = retry_delay * (2 ** (retries - 1))
                logger.info(f"等待 {current_delay} 秒后重试...")
                time.sleep(current_delay)
    
    # 所有重试都失败
    logger.error(f"{ERROR_MARK} 达到最大重试次数，数据库连接最终失败: {last_error}")
    return None


def test_server_connection():
    """测试PostgreSQL服务器连接是否正常（连接postgres默认数据库）"""
    try:
        # 尝试连接postgres数据库
        conn = get_connection(database="postgres")
        if conn:
            logger.info(f"{SUCCESS_MARK} 成功连接到PostgreSQL服务器")
            conn.close()
            return True
        else:
            logger.error(f"{ERROR_MARK} 无法连接到PostgreSQL服务器")
            return False
    except Exception as e:
        logger.error(f"{ERROR_MARK} 连接PostgreSQL服务器时发生错误: {e}")
        return False


def test_database_connection():
    """测试应用数据库连接是否正常"""
    try:
        conn = get_connection()
        if conn:
            logger.info(f"{SUCCESS_MARK} 成功连接到 {DB_NAME} 数据库")
            conn.close()
            return True
        else:
            logger.error(f"{ERROR_MARK} 无法连接到 {DB_NAME} 数据库")
            return False
    except Exception as e:
        logger.error(f"{ERROR_MARK} 连接数据库时发生错误: {e}")
        return False


def main():
    """主函数"""
    import argparse
    
    # 确保logs文件夹存在
    logs_dir = os.path.join(project_root, 'logs')
    os.makedirs(logs_dir, exist_ok=True)
    
    # 配置日志记录
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(os.path.join(logs_dir, 'db_test.log')),
            logging.StreamHandler()
        ]
    )
    
    # 打印启动信息
    logger.info("="*80)
    logger.info("数据库连接测试工具")
    logger.info("="*80)
    
    parser = argparse.ArgumentParser(description='数据库连接测试工具')
    parser.add_argument('--server-only', action='store_true', help='仅测试PostgreSQL服务器连接')
    parser.add_argument('--db-only', action='store_true', help='仅测试应用数据库连接')
    parser.add_argument('--verbose', action='store_true', help='显示详细信息')
    args = parser.parse_args()
    
    # 记录数据库配置信息
    logger.info(f"数据库配置: 主机={DB_HOST}, 端口={DB_PORT}, 数据库={DB_NAME}, 用户={DB_USER}")
    
    success = True
    
    # 测试服务器连接
    if args.db_only:
        logger.info("跳过PostgreSQL服务器连接测试")
    else:
        if not test_server_connection():
            logger.error(f"{ERROR_MARK} PostgreSQL服务器连接测试失败")
            logger.error("请检查PostgreSQL服务是否运行且网络可达")
            success = False
    
    # 测试数据库连接
    if args.server_only:
        logger.info("跳过应用数据库连接测试")
    else:
        if not test_database_connection():
            logger.error(f"{ERROR_MARK} 应用数据库连接测试失败")
            logger.error(f"请确认数据库 {DB_NAME} 已存在且用户 {DB_USER} 有访问权限")
            success = False
    
    # 打印总结
    if success:
        logger.info(f"{SUCCESS_MARK} 数据库连接测试全部通过")
        sys.exit(0)
    else:
        logger.error(f"{ERROR_MARK} 数据库连接测试存在失败项")
        sys.exit(1)


if __name__ == "__main__":
    main() 