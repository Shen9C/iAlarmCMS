# 数据库连接故障处理指南

## 问题描述

当前系统在运行过程中可能会出现数据库连接异常，导致所有请求返回500错误。这通常表现为以下日志消息：

```
[2025-04-24 10:01:36,381] INFO in _internal: Press CTRL+C to quit
[2025-04-24 10:02:12,062] INFO in _internal: 127.0.0.1 - - [24/Apr/2025 10:02:12] "GET /favicon.ico HTTP/1.1" 500 -
[2025-04-24 10:02:15,656] INFO in _internal: 127.0.0.1 - - [24/Apr/2025 10:02:15] "GET /alarms/?user_token=7fdb3f93-943b-4fde-a038-1348c2e1278d HTTP/1.1" 500 -
```

## 解决方案

为了解决数据库连接问题，我们实现了以下改进措施：

1. 创建了高可靠的数据库连接管理工具 `app/utils/db_connection.py`
2. 修改了应用初始化流程，集成数据库连接管理工具
3. 添加了数据库连接状态检查和故障处理机制
4. 创建了友好的错误页面，提供自动重试功能

## 使用方法

### 1. 初始化数据库

使用新的数据库初始化工具初始化或重置数据库：

```bash
# 初始化数据库
python app/utils/db_init.py

# 重置数据库（删除所有数据并重新创建）
python app/utils/db_init.py --reset
```

### 2. 启动应用

正常启动应用：

```bash
# 启动Web应用
python start_web_app.py

# 启动API服务器
python start_api_server.py

# 或同时启动两者
python run.py
```

## 数据库连接配置

数据库连接配置位于 `config/settings.yaml` 和环境特定配置文件中：

```yaml
# 数据库配置
database:
  user: shen9c
  password: 123456
  host: localhost
  port: 25432
  name: oilfield_web
```

请确保这些配置正确无误并且PostgreSQL服务器正在运行。

## 连接池配置

数据库连接池配置位于 `app/utils/db_connection.py`：

```python
# 数据库连接配置
MAX_RETRIES = 3                # 连接重试次数
RETRY_DELAY = 1                # 重试延迟（秒）
CONNECTION_POOL_SIZE = 10      # 连接池大小
CONNECTION_MAX_OVERFLOW = 20   # 最大溢出连接数
CONNECTION_TIMEOUT = 10        # 连接超时（秒）
POOL_RECYCLE = 3600            # 连接回收时间（秒）
POOL_PRE_PING = True           # 是否在使用前检查连接
```

您可以根据实际需求调整这些参数。

## 常见问题

### 问题1：应用启动后立即返回数据库连接错误

可能原因：
- PostgreSQL服务器未启动
- 配置中的数据库端口/主机不正确
- 用户名或密码错误

解决方法：
1. 检查PostgreSQL服务器是否正在运行：`pg_ctl status`
2. 验证配置文件中的连接信息是否正确
3. 尝试手动连接数据库：`psql -U username -h host -p port database`

### 问题2：应用运行一段时间后连接断开

可能原因：
- 数据库连接超时设置太短
- 防火墙或网络设备断开了空闲连接
- 数据库服务器有最大连接数限制

解决方法：
1. 增加 `POOL_RECYCLE` 值，减少连接被数据库服务器断开的概率
2. 增加 `CONNECTION_POOL_SIZE` 和 `CONNECTION_MAX_OVERFLOW` 值，增加可用连接数
3. 检查PostgreSQL的 `max_connections` 设置，确保足够大

### 问题3：负载高峰期连接失败

可能原因：
- 连接池大小不足
- 数据库服务器资源不足
- 数据库查询效率低下

解决方法：
1. 增加 `CONNECTION_POOL_SIZE` 和 `CONNECTION_MAX_OVERFLOW` 值
2. 优化数据库查询
3. 考虑升级数据库服务器或进行水平扩展

## 故障排查

如果仍然遇到数据库连接问题，请检查以下日志文件获取详细信息：

- `logs/oilfield_gateway.log` - 应用主日志
- `logs/db_init.log` - 数据库初始化日志

您也可以临时启用调试模式获取更详细的日志：

```bash
# 使用调试模式启动应用
python start_web_app.py --debug
``` 