# HTTPS配置与使用指南

本文档说明如何配置和使用HTTPS安全连接来增强API服务器的安全性。

## 1. 安装必要的依赖

首先需要安装SSL相关的Python依赖：

```bash
pip install -r requirements-ssl.txt
```

这将安装`pyOpenSSL`和`cryptography`等必要的包。

## 2. 生成SSL证书

系统初始化脚本已包含自动生成SSL证书的功能。运行以下命令初始化系统并生成证书：

```bash
python scripts/init_pg_db.py
```

此命令将：
- 初始化数据库
- 在`ssl`目录下生成自签名SSL证书
- 创建测试数据

如果只想生成SSL证书而不执行其他初始化步骤，可以使用：

```bash
python scripts/init_pg_db.py --no-test-data
```

## 3. 启动HTTPS服务器

生成证书后，可以使用`--ssl`参数启动支持HTTPS的服务器：

```bash
# 只启动API服务器（HTTPS）
python run.py --api-only --ssl

# 只启动Web应用（HTTPS）
python run.py --web-only --ssl

# 同时启动Web应用和API服务器（均为HTTPS）
python run.py --ssl
```

## 4. 客户端连接到HTTPS服务器

### 使用测试脚本

测试脚本默认使用HTTPS连接，但不验证证书（因为是自签名证书）：

```bash
python scripts/test_edge_device_api.py
```

如果需要切换回HTTP，可以使用`--http`参数：

```bash
python scripts/test_edge_device_api.py --http
```

### 使用Python代码连接

在Python代码中连接HTTPS API时，对于自签名证书，需要设置`verify=False`：

```python
import requests

response = requests.post(
    "https://localhost:5566/api/devices/auth/token",
    json={
        "device_id": "your_device_id",
        "secret_key": "your_secret_key"
    },
    verify=False  # 自签名证书不验证
)
```

### 使用curl测试

使用curl命令测试HTTPS API：

```bash
# 使用-k参数忽略证书验证
curl -k -X POST -H "Content-Type: application/json" \
    -d '{"device_id":"6647dd44","secret_key":"SKzyvw5xwWOrPzWn3BkFQaKg1QvijNcCMbzZh8rwtd"}' \
    https://localhost:5566/api/devices/auth/token
```

## 5. 生产环境注意事项

对于生产环境，建议：

1. 使用正规CA签发的SSL证书，而不是自签名证书
2. 定期更新证书
3. 配置适当的密码套件和协议版本
4. 启用HSTS（HTTP严格传输安全）

## 6. 故障排除

### 无法连接到HTTPS服务器

- 确认服务器正在运行：`ps aux | grep run.py`
- 确认服务器监听在正确的端口：`netstat -tulpn | grep 5566`
- 检查SSL证书是否正确生成：`ls -la ssl/`

### 证书验证失败

因为使用的是自签名证书，大多数客户端会显示证书验证错误。在开发测试环境中，可以安全地忽略这些错误。 