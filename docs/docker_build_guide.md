# Docker构建指南

## 目录
- [环境要求](#环境要求)
- [构建步骤](#构建步骤)
- [运行容器](#运行容器)
- [常用命令](#常用命令)
- [故障排除](#故障排除)
- [最佳实践](#最佳实践)

## 环境要求

- Docker 20.10.0 或更高版本
- 至少 2GB 可用内存
- 至少 5GB 可用磁盘空间
- 稳定的网络连接

## 构建步骤

### 1. 克隆代码库
```bash
git clone <repository-url>
cd oilfield-web
```

### 2. 构建Docker镜像
```bash
# # 基本构建命令
# docker build -t oilfield-web:latest .

# 带缓存的构建（适用于依赖更新）
docker build --no-cache -t oilfield-web:v1.0.0 .
docker build --no-cache -t flask_base:v1.0.0 .

# # 使用代理构建（如果需要）
# docker build \
#   --build-arg http_proxy=http://your-proxy:port \
#   --build-arg https_proxy=http://your-proxy:port \
#   -t oilfield-web:v1.0.0 .
```

### 3. 验证镜像
```bash
# 查看构建的镜像
docker images | grep oilfield-web

# 检查镜像详情
# docker inspect oilfield-web:latest
docker inspect oilfield-web:v1.0.0
```

## 运行容器

### 1. 基本运行
```bash
docker run -d \
  -p 5000:5000 \
  -p 5566:5566 \
  --name oilfield-web \
  oilfield-web:latest
```

### 2. 带数据卷的运行
```bash
docker run -d \
   --network host \  # 使用主机网络
  -p 5000:5000 \
  -p 5566:5566 \
  -v $(pwd)/logs:/zhyn/logs \
  -v $(pwd)/alarm_images:/zhyn/alarm_images \
  -v $(pwd)/backups:/zhyn/backups \
  -v $(pwd)/config:/zhyn/config \
  -v $(pwd)/ssl:/zhyn/ssl \
  --name oilfield-web \
  oilfield-web:v1.0.0
```
```
docker run -d --network host -p 8000:5000 -p 15566:5566 -v ./logs:/zhyn/logs -v ./alarm_images:/zhyn/alarm_images -v ./backups:/zhyn/backups -v ./config:/zhyn/config -v ./ssl:/zhyn/ssl --name oilfield-web oilfield-web:v1.0.0
```
### 3. 带环境变量的运行
```bash
docker run -d \
  -p 5000:5000 \
  -p 5566:5566 \
  -e FLASK_ENV=production \
  -e DATABASE_URL=postgresql://user:password@host:port/db \
  --name oilfield-web \
  oilfield-web:latest
```

# 指定健康检查
```bash
docker run -d \
  --name oilfield-web \
  --health-cmd="curl -f http://localhost:5000/ || exit 1" \
  --health-interval=30s \
  --health-timeout=30s \
  --health-start-period=5s \
  --health-retries=3 \
  oilfield-web:v1.0.0
```

## 常用命令

### 容器管理
```bash
# 查看运行中的容器
docker ps

# 查看所有容器（包括停止的）
docker ps -a

# 启动容器
docker start oilfield-web

# 停止容器
docker stop oilfield-web

# 重启容器
docker restart oilfield-web

# 删除容器
docker rm oilfield-web
```

### 日志查看
```bash
# 查看实时日志
docker logs -f oilfield-web

# 查看最近100行日志
docker logs --tail 100 oilfield-web

# 查看特定时间段的日志
docker logs --since "2024-01-01" oilfield-web
```

### 健康检查
```bash
# 查看容器健康状态
docker inspect --format='{{.State.Health.Status}}' oilfield-web

# 查看健康检查详情
docker inspect --format='{{json .State.Health}}' oilfield-web
```

## 故障排除

### 1. 构建失败
- 检查网络连接
- 确保Dockerfile语法正确
- 检查依赖文件是否完整

### 2. 容器启动失败
- 检查端口是否被占用
- 检查数据卷权限
- 查看容器日志

### 3. 应用无法访问
- 检查防火墙设置
- 验证端口映射
- 检查应用日志

## 最佳实践

1. **版本控制**
   - 为镜像使用有意义的标签
   - 保持Dockerfile的版本控制

2. **安全性**
   - 使用非root用户运行容器
   - 定期更新基础镜像
   - 限制容器资源使用

3. **性能优化**
   - 使用多阶段构建
   - 优化Dockerfile指令顺序
   - 合理使用缓存

4. **监控**
   - 配置健康检查
   - 设置资源限制
   - 启用日志收集

5. **维护**
   - 定期清理未使用的镜像
   - 更新依赖包
   - 备份重要数据

## 注意事项

1. 生产环境部署前请进行充分测试
2. 确保数据卷的备份策略
3. 定期检查容器日志
4. 监控容器资源使用情况
5. 遵循最小权限原则