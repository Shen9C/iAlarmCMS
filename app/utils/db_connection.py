#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
数据库连接管理工具
提供数据库连接和连接状态检查功能
"""

import time
import logging
import threading
from contextlib import contextmanager
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError, OperationalError, DisconnectionError
from sqlalchemy.orm import sessionmaker, scoped_session
from flask import current_app
import psycopg2

# 获取日志记录器
logger = logging.getLogger(__name__)

# 数据库连接配置
MAX_RETRIES = 3  # 连接重试次数
RETRY_DELAY = 1  # 重试延迟（秒）
CONNECTION_POOL_SIZE = 10  # 连接池大小
CONNECTION_MAX_OVERFLOW = 20  # 最大溢出连接数
CONNECTION_TIMEOUT = 5  # 连接超时（秒）
POOL_RECYCLE = 3600  # 连接回收时间（秒）
POOL_PRE_PING = True  # 是否在使用前检查连接
CONNECTION_CHECK_CACHE_TIME = 30  # 连接检查缓存时间（秒）

# 连接状态追踪
_engine = None
_Session = None
_lock = threading.RLock()
_last_connection_attempt = 0
_connection_health_status = True  # 连接健康状态


def get_db_url():
    """获取数据库连接URL，优先从Flask应用配置获取"""
    try:
        # 尝试从Flask应用配置获取
        if current_app and 'SQLALCHEMY_DATABASE_URI' in current_app.config:
            return current_app.config['SQLALCHEMY_DATABASE_URI']
    except Exception:
        pass
    
    # 作为后备方案，从配置中构建
    try:
        from app.utils.yaml_config_loader import config
        db_cfg = config.database
        return f"postgresql://{db_cfg.user}:{db_cfg.password}@{db_cfg.host}:{db_cfg.port}/{db_cfg.name}"
    except Exception as e:
        logger.error(f"无法构建数据库URL: {e}")
        raise


def init_db_engine(force=False):
    """初始化数据库引擎"""
    global _engine, _Session
    
    # 如果引擎已存在且不强制重新创建，则直接返回
    if _engine is not None and not force:
        return _engine
    
    with _lock:
        # 双重检查锁定模式，避免竞态条件
        if _engine is not None and not force:
            return _engine
        
        try:
            # 获取数据库URL
            db_url = get_db_url()
            
            # 创建引擎，添加连接池配置
            _engine = create_engine(
                db_url,
                pool_size=CONNECTION_POOL_SIZE,
                max_overflow=CONNECTION_MAX_OVERFLOW,
                pool_timeout=CONNECTION_TIMEOUT,
                pool_recycle=POOL_RECYCLE,
                pool_pre_ping=POOL_PRE_PING,
                connect_args={'connect_timeout': 3}  # 减少连接超时时间
            )
            
            # 创建会话工厂
            _Session = scoped_session(sessionmaker(bind=_engine))
            
            # 测试连接 - 使用 SQLAlchemy 2.0 API
            with _engine.connect() as conn:
                conn.execute(text("SELECT 1"))
                conn.commit()
            
            logger.info("数据库引擎初始化成功")
            
            # 更新连接状态
            global _connection_health_status, _last_connection_attempt
            _connection_health_status = True
            _last_connection_attempt = time.time()
            
            logger.debug(f"连接池状态: 大小={_engine.pool.size()}, 溢出={_engine.pool.overflow()}, 检出={_engine.pool.checkedout()}")
            
            return _engine
        except Exception as e:
            logger.error(f"数据库引擎初始化失败: {e}")
            _engine = None
            _Session = None
            _connection_health_status = False
            _last_connection_attempt = time.time()
            raise


def get_engine():
    """获取数据库引擎，如果不存在则初始化"""
    global _engine
    if _engine is None:
        init_db_engine()
    return _engine


def get_session():
    """获取数据库会话"""
    global _Session
    if _Session is None:
        init_db_engine()
    return _Session()


@contextmanager
def db_session():
    """数据库会话上下文管理器，提供自动重试和错误处理"""
    session = get_session()
    
    retries = 0
    success = False
    
    while not success and retries < MAX_RETRIES:
        try:
            yield session
            session.commit()
            success = True
        except (OperationalError, DisconnectionError) as e:
            session.rollback()
            retries += 1
            
            # 更新连接状态
            global _connection_health_status, _last_connection_attempt
            _connection_health_status = False
            _last_connection_attempt = time.time()
            
            logger.warning(f"数据库连接错误 (尝试 {retries}/{MAX_RETRIES}): {e}")
            
            if retries < MAX_RETRIES:
                # 重试延迟增加（指数退避）
                time.sleep(RETRY_DELAY * (2 ** (retries - 1)))
                
                # 尝试重新初始化连接
                try:
                    init_db_engine(force=True)
                    # 获取新会话
                    session.close()
                    session = get_session()
                except Exception as init_error:
                    logger.error(f"重新初始化数据库连接失败: {init_error}")
            else:
                logger.error(f"达到最大重试次数，数据库操作失败: {e}")
                raise
        except Exception as e:
            session.rollback()
            logger.error(f"数据库操作错误: {e}")
            raise
        finally:
            if not success:
                session.close()
    
    # 确保会话关闭
    session.close()


def check_db_connection():
    """检查数据库连接状态"""
    global _connection_health_status, _last_connection_attempt
    
    # 如果上次检查后不久，直接返回上次结果（避免频繁检查）
    if time.time() - _last_connection_attempt < CONNECTION_CHECK_CACHE_TIME:
        return _connection_health_status
    
    retries = 0
    while retries < MAX_RETRIES:
        try:
            engine = get_engine()
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            
            _connection_health_status = True
            _last_connection_attempt = time.time()
            return True
        except Exception as e:
            retries += 1
            logger.warning(f"数据库连接检查失败 (尝试 {retries}/{MAX_RETRIES}): {e}")
            
            if retries < MAX_RETRIES:
                time.sleep(RETRY_DELAY * (2 ** (retries - 1)))
            else:
                _connection_health_status = False
                _last_connection_attempt = time.time()
                return False


def quick_db_check():
    """快速检查数据库连接（不依赖SQLAlchemy，直接使用psycopg2）"""
    try:
        # 导入配置
        from app.utils.yaml_config_loader import config
        
        # 直接使用psycopg2连接数据库
        conn = psycopg2.connect(
            user=config.DB_USER,
            password=config.DB_PASSWORD,
            host=config.DB_HOST,
            port=config.DB_PORT,
            database=config.DB_NAME,
            connect_timeout=3  # 较短的超时时间
        )
        conn.close()
        logger.info("数据库连接检查成功")
        return True
    except Exception as e:
        logger.error(f"数据库连接检查失败: {e}")
        # 尝试获取配置信息
        try:
            from app.utils.yaml_config_loader import config
            logger.error(f"数据库配置: 主机={config.DB_HOST}, 端口={config.DB_PORT}, 数据库={config.DB_NAME}, 用户={config.DB_USER}")
        except:
            pass
        return False 