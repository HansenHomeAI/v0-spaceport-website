# Production SOGS Compression Container - Split Installation Strategy
FROM nvidia/cuda:12.9.1-runtime-ubuntu22.04

# Prevent interactive prompts
ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1

# Install minimal system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3-minimal \
    python3-pip \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean \
    && rm -rf /var/cache/apt/*

WORKDIR /opt/ml/code

# Install pip and PyTorch first (largest package)
RUN pip3 install --no-cache-dir --upgrade pip \
    && pip3 install --no-cache-dir \
    torch==2.0.1+cu118 \
    --index-url https://download.pytorch.org/whl/cu118 \
    && pip3 cache purge \
    && rm -rf ~/.cache/pip \
    && rm -rf /tmp/*

# Install remaining dependencies
RUN pip3 install --no-cache-dir \
    torchpq==0.2.1 \
    plyfile==0.7.4 \
    trimesh==3.21.7 \
    boto3==1.34.69 \
    numpy==1.24.3 \
    && pip3 cache purge \
    && rm -rf ~/.cache/pip \
    && rm -rf /tmp/* \
    && find /usr/local/lib/python3.*/dist-packages -name "*.pyc" -delete \
    && find /usr/local/lib/python3.*/dist-packages -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true

# Copy files
COPY requirements.txt .
COPY compress.py .
RUN chmod +x compress.py

# Set CUDA environment
ENV NVIDIA_VISIBLE_DEVICES=all
ENV NVIDIA_DRIVER_CAPABILITIES=compute,utility

# Entry point for SageMaker
ENTRYPOINT ["python3", "/opt/ml/code/compress.py"] 