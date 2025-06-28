# Production PlayCanvas SOGS Compression Container
FROM nvidia/cuda:12.9.1-runtime-ubuntu22.04

# Prevent interactive prompts
ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1

# Install system dependencies needed for SOGS
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3-minimal \
    python3-pip \
    git \
    build-essential \
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

# Install SOGS dependencies
RUN pip3 install --no-cache-dir \
    cupy-cuda12x \
    torchpq \
    plyfile==0.7.4 \
    Pillow==10.0.0 \
    numpy==1.24.3 \
    boto3==1.34.69 \
    && pip3 cache purge \
    && rm -rf ~/.cache/pip \
    && rm -rf /tmp/*

# Install PLAS (Parallel Linear Assignment Sorting) from GitHub
RUN pip3 install --no-cache-dir git+https://github.com/fraunhoferhhi/PLAS.git \
    && pip3 cache purge \
    && rm -rf ~/.cache/pip \
    && rm -rf /tmp/*

# Copy files
COPY requirements.txt .
COPY compress.py .
RUN chmod +x compress.py

# Set CUDA environment
ENV NVIDIA_VISIBLE_DEVICES=all
ENV NVIDIA_DRIVER_CAPABILITIES=compute,utility

# Entry point for SageMaker
ENTRYPOINT ["python3", "/opt/ml/code/compress.py"] 