# SafetyVision AI — container image for the Streamlit dashboard and FastAPI service (CPU inference)
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    YOLO_CONFIG_DIR=/tmp/Ultralytics

# OpenCV runtime libraries
RUN apt-get update \
    && apt-get install -y --no-install-recommends libgl1 libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# CPU-only PyTorch keeps the image small; the rest comes from requirements.txt
ARG TORCH_INDEX_URL=https://download.pytorch.org/whl/cpu
COPY requirements.txt .
RUN pip install --upgrade pip \
    && pip install torch torchvision --index-url ${TORCH_INDEX_URL} \
    && pip install -r requirements.txt

COPY . .

# Platforms such as Render / Railway / Cloud Run inject $PORT; default to Streamlit's 8501
ENV PORT=8501
EXPOSE 8501 8080

HEALTHCHECK --interval=30s --timeout=5s --start-period=60s \
    CMD python -c "import os, urllib.request; urllib.request.urlopen(f'http://localhost:{os.environ.get(\"PORT\", \"8501\")}/_stcore/health')" || exit 1

CMD ["sh", "-c", "streamlit run app/main.py --server.port ${PORT} --server.address 0.0.0.0"]
