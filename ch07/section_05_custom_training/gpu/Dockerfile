# ビルド時に、利用可能性を確認済みのAgent Platform PyTorch GPUイメージを注入する。
# 例: docker build --build-arg BASE_IMAGE='<verified image URI>' .
ARG BASE_IMAGE
FROM ${BASE_IMAGE}

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY dl_task.py .
ENTRYPOINT ["python", "dl_task.py"]
