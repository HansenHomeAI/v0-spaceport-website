FROM public.ecr.aws/docker/library/node:20-bookworm-slim

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1
ENV SPLAT_TRANSFORM_BIN=splat-transform
ENV SOGS_DEVICE=cpu

RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 \
    python3-pip \
    python3-venv \
    ca-certificates \
    webp \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /opt/ml/code

COPY requirements.txt .
RUN pip3 install --no-cache-dir --upgrade pip && \
    pip3 install --no-cache-dir -r requirements.txt

RUN npm install -g @playcanvas/splat-transform@1.10.2

COPY compress.py .
COPY diagnostic_script.py .
COPY assets ./assets

RUN chmod +x compress.py diagnostic_script.py

RUN python3 -c "import boto3; print('boto3:', boto3.__version__)" && \
    splat-transform --version

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD splat-transform --version >/dev/null 2>&1 || exit 1

ENTRYPOINT ["python3", "/opt/ml/code/compress.py"]
