#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
系统初始化脚本
用于首次部署时生成必要的配置和密钥
"""

import os
import sys
import secrets
import yaml
from pathlib import Path
import logging
import argparse
from datetime import datetime

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def generate_secret_key(length=32):
    """生成安全的密钥"""
    return secrets.token_hex(length)

def update_config(secret_key, is_production=False):
    """更新配置文件"""
    config_path = Path("config/settings.yaml")
    if not config_path.exists():
        logger.error("配置文件不存在")
        return False
    
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        
        # 更新密钥配置
        config['secret_key'] = secret_key
        logger.info("密钥已写入配置文件")
        
        # 更新其他配置
        config['debug'] = not is_production
        config['debug_log_enabled'] = not is_production
        
        # 创建配置备份
        backup_dir = Path("backup")
        backup_dir.mkdir(exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_file = backup_dir / f"settings_{timestamp}.yaml"
        
        with open(backup_file, 'w', encoding='utf-8') as f:
            yaml.dump(config, f, default_flow_style=False, allow_unicode=True)
        
        with open(config_path, 'w', encoding='utf-8') as f:
            yaml.dump(config, f, default_flow_style=False, allow_unicode=True)
        
        logger.info(f"配置文件已更新: {config_path}")
        logger.info(f"配置备份已创建: {backup_file}")
        return True
    except Exception as e:
        logger.error(f"更新配置文件失败: {e}")
        return False

def create_key_backup(secret_key, is_production=False):
    """创建密钥备份"""
    try:
        # 创建备份目录
        backup_dir = Path("backup")
        backup_dir.mkdir(exist_ok=True)
        
        # 生成备份文件名（使用时间戳）
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_file = backup_dir / f"secret_key_{timestamp}.txt"
        
        # 创建密钥备份
        with open(backup_file, 'w') as f:
            f.write(f"SECRET_KEY={secret_key}\n")
            f.write(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"环境: {'生产环境' if is_production else '开发环境'}\n")
            f.write(f"存储位置: config/settings.yaml\n")
        
        logger.info(f"密钥备份已创建: {backup_file}")
        return True
    except Exception as e:
        logger.error(f"创建密钥备份失败: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(description='系统初始化脚本')
    parser.add_argument('--production', action='store_true', help='生产环境模式')
    args = parser.parse_args()
    
    # 生成密钥
    secret_key = generate_secret_key()
    logger.info(f"已生成密钥: {secret_key[:8]}...")
    
    # 更新配置文件
    if not update_config(secret_key, args.production):
        sys.exit(1)
    
    # 创建密钥备份
    if not create_key_backup(secret_key, args.production):
        sys.exit(1)
    
    logger.info("系统初始化完成")
    
    if args.production:
        logger.info("""
生产环境部署说明：
1. 请妥善保管生成的密钥（已备份到 backup 目录）
2. 密钥已存储在 config/settings.yaml 中
3. 如需生成SSL证书，请运行 scripts/generate_web_cert.py
4. 确保配置文件中的其他设置符合生产环境要求
""")

if __name__ == '__main__':
    main() 