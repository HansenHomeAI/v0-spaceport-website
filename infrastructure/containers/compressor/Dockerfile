# Production SOGS Compression Container - Optimized for GitHub Actions
FROM nvidia/cuda:12.1-runtime-ubuntu20.04

# Prevent interactive prompts during installation
ENV DEBIAN_FRONTEND=noninteractive

WORKDIR /opt/ml/code

# Install all system dependencies and Python in single optimized layer
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3.9 \
    python3.9-dev \
    python3.9-distutils \
    python3-pip \
    build-essential \
    git \
    cmake \
    pkg-config \
    libjpeg-dev \
    libpng-dev \
    libwebp-dev \
    libtiff-dev \
    curl \
    wget \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean \
    && update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.9 1 \
    && update-alternatives --install /usr/bin/python python /usr/bin/python3.9 1 \
    && python -m pip install --upgrade pip

# Copy requirements first for better Docker layer caching
COPY requirements.txt .

# Install all Python dependencies in single layer to minimize disk usage
RUN pip install --no-cache-dir \
    torch==2.0.1+cu118 torchvision==0.15.2+cu118 torchaudio==2.0.2+cu118 \
    --index-url https://download.pytorch.org/whl/cu118 \
    && pip install --no-cache-dir -r requirements.txt \
    && pip install --no-cache-dir cupy-cuda11x \
    && pip cache purge \
    && rm -rf ~/.cache/pip \
    && rm -rf /tmp/* /var/tmp/*

# Copy the production compression script
COPY compress.py .
RUN chmod +x compress.py

# Set environment variables for CUDA and Python
ENV PYTHONPATH="/opt/ml/code:${PYTHONPATH}"
ENV NVIDIA_VISIBLE_DEVICES=all
ENV NVIDIA_DRIVER_CAPABILITIES=compute,utility
ENV CUDA_VISIBLE_DEVICES=all

# Set the entrypoint to our production script
ENTRYPOINT ["python", "/opt/ml/code/compress.py"] 