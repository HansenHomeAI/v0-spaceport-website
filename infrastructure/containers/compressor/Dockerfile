# Production PlayCanvas SOGS Compression Container - Multi-Stage Build
# Optimized for layer caching and build efficiency

# Stage 1: Base CUDA environment
FROM nvidia/cuda:12.9.1-runtime-ubuntu22.04 AS base

# Prevent interactive prompts
ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1

# Install system dependencies (cached layer)
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3-minimal=3.10.6-1~22.04 \
    python3-pip=22.0.2+dfsg-1ubuntu0.4 \
    git=1:2.34.1-1ubuntu1.10 \
    build-essential=12.9ubuntu3 \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean \
    && rm -rf /var/cache/apt/*

# Stage 2: Python dependencies
FROM base AS python-deps

WORKDIR /opt/ml/code

# Copy requirements first for better caching
COPY requirements.txt .

# Install pip and PyTorch first (largest packages)
RUN pip3 install --no-cache-dir --upgrade pip \
    && pip3 install --no-cache-dir \
    torch==2.0.1+cu118 \
    --index-url https://download.pytorch.org/whl/cu118 \
    && pip3 cache purge \
    && rm -rf ~/.cache/pip \
    && rm -rf /tmp/*

# Install SOGS dependencies in order of size/complexity
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

# Stage 3: Application code
FROM python-deps AS app-build

# Copy application files (most frequently changed)
COPY compress.py .
RUN chmod +x compress.py

# Stage 4: Final runtime image
FROM app-build AS runtime

# Create non-root user for security
RUN useradd --create-home --shell /bin/bash sagemaker \
    && chown -R sagemaker:sagemaker /opt/ml

# Set CUDA environment
ENV NVIDIA_VISIBLE_DEVICES=all
ENV NVIDIA_DRIVER_CAPABILITIES=compute,utility

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python3 -c "import torch; print('CUDA available:', torch.cuda.is_available())" || exit 1

# Switch to non-root user
USER sagemaker

# Entry point for SageMaker
ENTRYPOINT ["python3", "/opt/ml/code/compress.py"] 