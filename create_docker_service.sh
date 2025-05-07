#!/bin/bash

# 设置颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 检查是否以root权限运行
if [ "$EUID" -ne 0 ]; then 
    echo -e "${RED}请使用root权限运行此脚本${NC}"
    exit 1
fi

# 检查docker是否安装
if ! command -v docker &> /dev/null; then
    echo -e "${RED}未检测到docker，请先安装docker${NC}"
    exit 1
fi

# 创建必要的目录
echo -e "${YELLOW}创建必要的目录...${NC}"
# mkdir -p logs alarm_images backups config ssl pg_data

# 创建docker网络
echo -e "${YELLOW}创建docker网络...${NC}"
docker network create oilfield_network 2>/dev/null || true

# 停止并删除已存在的容器
echo -e "${YELLOW}清理已存在的容器...${NC}"
docker stop oilfield_web_app oilfield_web_db 2>/dev/null || true
docker rm oilfield_web_app oilfield_web_db 2>/dev/null || true

# 启动PostgreSQL容器
echo -e "${YELLOW}启动PostgreSQL容器...${NC}"
docker run -d \
    --name oilfield_web_db \
    --network=host \
    -e POSTGRES_USER=guanliyuan \
    -e POSTGRES_PASSWORD=admin123_Youtian \
    -e POSTGRES_DB=oilfield_web_db \
    -e TZ=Asia/Shanghai \
    -v /opt/cms_web/oilfield-web_db:/var/lib/postgresql/data \
    --memory=1g \
    --memory-reservation=512m \
    --restart=unless-stopped \
    postgres:latest


# 等待数据库容器完全启动
echo -e "${YELLOW}等待数据库启动...${NC}"
sleep 30

# 启动Flask应用容器
echo -e "${YELLOW}启动Flask应用容器...${NC}"
docker run -d \
    --name oilfield_web_app \
    --network=host \
    -v /opt/cms_web/oilfield-web_app/logs:/zhyn/logs \
    -v /opt/cms_web/oilfield-web_app/alarm_images:/zhyn/alarm_images \
    -v /opt/cms_web/oilfield-web_app/backups:/zhyn/backups \
    -v /opt/cms_web/oilfield-web_app/config:/zhyn/config \
    -v /opt/cms_web/oilfield-web_app/ssl:/zhyn/ssl \
    -e PYTHONPATH=/zhyn \
    -e FLASK_APP=run.py \
    -e FLASK_ENV=production \
    -e TZ=Asia/Shanghai \
    --memory=2g \
    --memory-reservation=1g \
    --restart=unless-stopped \
    oilfield-web:v1.0.0


# 检查容器状态
echo -e "${YELLOW}检查容器状态...${NC}"
sleep 5
docker ps

# 显示帮助信息
echo -e "\n${GREEN}服务已启动！${NC}"
echo -e "${YELLOW}常用命令：${NC}"
echo -e "查看容器状态: docker ps"
echo -e "查看应用日志: docker logs oilfield_web_app"
echo -e "查看数据库日志: docker logs oilfield_web_db"
echo -e "停止服务: docker stop oilfield_web_app oilfield_web_db"
echo -e "启动服务: docker start oilfield_web_app oilfield_web_db"
echo -e "重启服务: docker restart oilfield_web_app oilfield_web_db"
echo -e "删除服务: docker rm -f oilfield_web_app oilfield_web_db"

  