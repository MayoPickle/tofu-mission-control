# 使用官方 Python 运行时作为基础镜像
FROM python:3.10-slim

# 设置工作目录
WORKDIR /app

# 复制当前目录内容到容器内的 /app 目录
COPY . /app

# 安装 Python 依赖
RUN pip install --upgrade pip
RUN pip install scrapy sqlalchemy psycopg2-binary python-dotenv alembic requests
RUN if [ -f requirements.txt ]; then pip install -r requirements.txt; fi


# 设置环境变量（可选）
ENV PYTHONUNBUFFERED=1
# 设置时区为UTC
ENV TZ=UTC
# 配置时区
RUN ln -snf /usr/share/zoneinfo/UTC /etc/localtime && echo UTC > /etc/timezone

# 暴露容器端口（如果需要）
EXPOSE 8081

# 运行主程序
CMD ["gunicorn", "-w", "1", "-b", "0.0.0.0:8081", "app:app"]
