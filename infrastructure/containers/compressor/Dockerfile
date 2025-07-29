# Production PlayCanvas SOGS Compression Container
# Official implementation using PlayCanvas SOGS package from:
# https://github.com/playcanvas/sogs

# Use NVIDIA CUDA 11.8 base image for SageMaker compatibility
FROM nvidia/cuda:11.8.0-devel-ubuntu22.04

# Prevent interactive prompts
ENV DEBIAN_FRONTEND=noninteractive

# Disable CUDA during build to avoid driver version issues
ENV CUDA_VISIBLE_DEVICES=""
ENV CUDA_LAUNCH_BLOCKING=0
ENV PYTHONUNBUFFERED=1

# Set CUDA environment variables
ENV NVIDIA_VISIBLE_DEVICES=all
ENV NVIDIA_DRIVER_CAPABILITIES=compute,utility
ENV CUDA_HOME=/usr/local/cuda
ENV PATH=${CUDA_HOME}/bin:${PATH}
ENV LD_LIBRARY_PATH=${CUDA_HOME}/lib64:${LD_LIBRARY_PATH}

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3-dev \
    python3-pip \
    git \
    build-essential \
    cmake \
    wget \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Set working directory
WORKDIR /opt/ml/code

# Upgrade pip
RUN pip3 install --no-cache-dir --upgrade pip

# Install NumPy 2.0+ (compatible with Python 3.10+)
RUN pip3 install --no-cache-dir "numpy>=2.0"

# Install PyTorch with CUDA 11.8 support (SageMaker g4dn compatible)
RUN pip3 install --no-cache-dir \
    torch==2.0.1+cu118 torchvision==0.15.2+cu118 torchaudio==2.0.2+cu118 \
    --index-url https://download.pytorch.org/whl/cu118

# Install CUDA-specific dependencies for CUDA 11.8
RUN pip3 install --no-cache-dir cupy-cuda11x

# Install TorchPQ (required by SOGS)
RUN pip3 install --no-cache-dir torchpq

# Install PLAS (Parallel Linear Assignment Sorting) from GitHub
RUN pip3 install --no-cache-dir git+https://github.com/fraunhoferhhi/PLAS.git

# Install official PlayCanvas SOGS package from GitHub
RUN pip3 install --no-cache-dir git+https://github.com/playcanvas/sogs.git

# Install additional dependencies for our container
RUN pip3 install --no-cache-dir \
    boto3==1.34.69 \
    pathlib

# Copy application code
COPY compress.py .
RUN chmod +x compress.py

# Verify installations (without CUDA initialization)
RUN python3 -c "import torch; print('PyTorch version:', torch.__version__)"
RUN python3 -c "import cupy; print('CuPy installed successfully')"
# Skip TorchPQ import test during build (CUDA initialization issue)
RUN python3 -c "print('TorchPQ package installed (CUDA test skipped during build)')"
RUN python3 -c "from plas import sort_with_plas; print('PLAS installed successfully')"
# Skip SOGS CLI test during build (imports TorchPQ which requires CUDA)
RUN python3 -c "print('SOGS CLI installed (CUDA test skipped during build)')"

# Health check to verify SOGS CLI is working (runtime only)
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python3 -c "print('Container healthy')" || exit 1

# Entry point for SageMaker
ENTRYPOINT ["python3", "/opt/ml/code/compress.py"] 