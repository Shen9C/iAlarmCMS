# 使用Python 3.11作为基础镜像
FROM python:3.12-slim

# 设置工作目录
WORKDIR /zhyn

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 创建必要的目录
RUN mkdir -p \
    /zhyn/alarm_images \
    /zhyn/app \
    /zhyn/backups \
    /zhyn/config \
    /zhyn/logs \
    /zhyn/migrations \
    /zhyn/scripts \
    /zhyn/ssl \
    /zhyn/tests

# 复制项目文件
COPY requirements.txt .
COPY app/ /zhyn/app/
COPY scripts/ /zhyn/scripts/
COPY migrations/ /zhyn/migrations/
COPY run.py .
COPY start_api_server.py .
COPY start_web_app.py .
COPY wsgi.py .

# 安装Python依赖
RUN pip install --no-cache-dir -r requirements.txt

# 设置环境变量
ENV PYTHONPATH=/zhyn
ENV FLASK_APP=run.py
ENV FLASK_ENV=production

# 暴露端口
EXPOSE 5000 5566

# # 启动命令
# CMD ["python", "run.py"] 
# 启动命令
CMD ["python", "run.py", "--no-ssl"] 