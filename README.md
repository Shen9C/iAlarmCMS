# 智能告警综合管理系统

## 项目简介
智能告警综合管理系统（Intelligent Alarm Comprehensive Management System）是一个基于 Flask 框架开发的 Web 应用，用于集中管理和处理各类告警信息。

## 主要功能
- 告警管理
  - 告警信息展示
  - 告警状态更新
  - 告警处理记录
  - 告警自动清理

- 系统设置
  - 基本设置（系统名称等）
  - 告警设置（保留天数、刷新间隔）
  - 邮件通知设置

- 用户管理
  - 用户账号管理
  - 角色权限控制
  - 密码修改

- 边缘设备管理
  - 设备注册与认证
  - 设备状态监控
  - 远程设备管理
  - 设备告警上报接口

- 统计分析
  - 告警统计
  - 处理效率分析

## 技术栈
- 后端框架：Flask
- 数据库：PostgreSQL/SQLite
- 前端框架：Bootstrap 5
- 图标库：Bootstrap Icons

## 环境要求
- Python 3.8+
- Flask 2.0+
- SQLAlchemy
- Flask-Login
- Flask-Migrate

## 快速开始

1. 克隆项目
```bash
git clone https://github.com/Shen9C/iAlarmCMS.git
cd iAlarmCMS
```

## 边缘设备API服务器

系统集成了专用的边缘设备API服务器，用于处理边缘设备的认证和数据上报请求，不需要经过Web应用的用户认证机制。

### 功能特点

- **设备认证**：提供 `/auth/token` 接口，支持边缘设备获取访问令牌
- **告警上报**：提供 `/alarms` 接口，支持边缘设备上报告警数据
- **独立服务**：可与Web应用共同运行，也可独立启动
- **安全机制**：设备认证基于预设的设备密钥，保证数据安全性

### 启动方式

系统支持多种启动模式，可通过 `run.py` 脚本的命令行参数进行控制：

1. **默认模式**（同时启动Web应用和边缘设备API服务器）：
   ```bash
   python run.py
   ```

2. **仅启动边缘设备API服务器**：
   ```bash
   python run.py --api-only
   ```

3. **仅启动Web应用**：
   ```bash
   python run.py --web-only
   ```

4. **自定义服务配置**：
   ```bash
   python run.py --web-port 8000 --api-port 8080 --debug
   ```

### 命令行参数

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `--web-host` | Web应用监听地址 | 0.0.0.0 |
| `--web-port` | Web应用监听端口 | 5000 |
| `--api-host` | 边缘设备API监听地址 | 0.0.0.0 |
| `--api-port` | 边缘设备API监听端口 | 5566 |
| `--debug` | 启用调试模式 | False |
| `--api-only` | 仅启动边缘设备API服务 | False |
| `--web-only` | 仅启动Web应用服务 | False |

### 生产环境部署

在生产环境中，建议使用 Gunicorn 或 uWSGI 等 WSGI 服务器来部署应用。


让我先查看一下当前的run.py文件结构。

Read file: run.py
现在，我将修改run.py文件，将边缘设备API服务器和主Web应用一起启动：

```python:run.py
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
```
现在不再需要单独的批处理文件了，可以删除它：

Ran tool
我已经成功地将边缘设备API服务器的启动代码集成到`run.py`中。现在可以通过一个命令同时启动主Web应用和边缘设备API服务器。以下是新增功能的说明：

### 1. 多服务集成启动

现在`run.py`支持以下启动模式：
- **默认模式**：同时启动Web应用（端口5000）和边缘设备API服务器（端口5566）
- **仅Web模式**：通过`--web-only`参数只启动Web应用
- **仅API模式**：通过`--api-only`参数只启动边缘设备API服务器

### 2. 命令行参数支持

添加了完整的命令行参数支持：
- `--web-host`：设置Web应用监听地址（默认0.0.0.0）
- `--web-port`：设置Web应用监听端口（默认5000）
- `--api-host`：设置API服务器监听地址（默认0.0.0.0）
- `--api-port`：设置API服务器监听端口（默认5566）
- `--debug`：启用调试模式
- `--api-only`：仅启动API服务器
- `--web-only`：仅启动Web应用

### 3. 使用线程管理

使用Python的`threading`模块实现两个服务的并行运行：
- 边缘设备API服务器在独立线程中运行
- 主Web应用在主线程中运行
- 两个线程共享同一个Python进程，可以共享数据库连接池和应用配置

### 使用示例

1. **启动全部服务**（Web应用和设备API服务器）：
   ```bash
   python run.py
   ```

2. **仅启动边缘设备API服务器**：
   ```bash
   python run.py --api-only
   ```

3. **自定义端口启动**：
   ```bash
   python run.py --web-port 8000 --api-port 8080
   ```

4. **启用调试模式**：
   ```bash
   python run.py --debug
   ```

这个集成方案简化了部署，不再需要开发人员管理多个启动脚本，同时也方便了生产环境的维护和监控。
