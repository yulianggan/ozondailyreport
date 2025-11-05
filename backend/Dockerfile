FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# 安装依赖
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

# 拷贝应用
COPY app /app/app

EXPOSE 8009

# 通过环境变量传入 Mongo 连接串（compose中覆盖）
ENV MONGODB_URI="mongodb://host.docker.internal:27017"

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8009"]

