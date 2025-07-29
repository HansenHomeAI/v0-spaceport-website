# Production PlayCanvas SOGS Compression Container
# Official implementation using PlayCanvas SOGS package from:
# https://github.com/playcanvas/sogs

# Use NVIDIA CUDA base image with Python 3.10+ (required by Kornia)
FROM nvidia/cuda:12.9.1-devel-ubuntu22.04

# Prevent interactive prompts
ENV DEBIAN_FRONTEND=noninteractive
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

# Install PyTorch with CUDA 12.1 support (as per SOGS documentation)
RUN pip3 install --no-cache-dir \
    torch torchvision torchaudio \
    --index-url https://download.pytorch.org/whl/cu121

# Install CUDA-specific dependencies (as per SOGS documentation)
RUN pip3 install --no-cache-dir cupy-cuda12x

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

# Verify installations
RUN python3 -c "import torch; print('PyTorch version:', torch.__version__); print('CUDA available:', torch.cuda.is_available())"
RUN python3 -c "import cupy; print('CuPy installed successfully')"
RUN python3 -c "import torchpq; print('TorchPQ installed successfully')"
RUN python3 -c "from plas import sort_with_plas; print('PLAS installed successfully')"
RUN sogs-compress --help

# Health check to verify SOGS CLI is working
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD sogs-compress --help > /dev/null || exit 1

# Entry point for SageMaker
ENTRYPOINT ["python3", "/opt/ml/code/compress.py"] 