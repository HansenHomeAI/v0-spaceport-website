# Production PlayCanvas SOGS Compression Container
# Official implementation using PlayCanvas SOGS package from:
# https://github.com/playcanvas/sogs
# 
# CRITICAL FIX: Aligned with working 3DGS container CUDA 11.8 setup
# Both containers should use A10G GPU (ml.g5.xlarge) for consistency

# Use SageMaker PyTorch training container with CUDA 11.8 (PROVEN TO WORK)
FROM 763104351884.dkr.ecr.us-west-2.amazonaws.com/pytorch-training:2.0.1-gpu-py310-cu118-ubuntu20.04-sagemaker

# Set environment variables for CUDA (same as 3DGS container)
ENV CUDA_HOME=/usr/local/cuda
ENV PATH=${CUDA_HOME}/bin:${PATH}
ENV LD_LIBRARY_PATH=${CUDA_HOME}/lib64:${LD_LIBRARY_PATH}

# Set CUDA architecture for A10G GPU (SAME AS 3DGS - Compute Capability 8.6)
ENV TORCH_CUDA_ARCH_LIST="8.6"
ENV CUDA_ARCH_FLAGS="-arch=sm_86"

# Set C++ standard for CUDA compilation (SAME AS 3DGS)
ENV CXXFLAGS="-std=c++17"
ENV NVCC_FLAGS="-std=c++17 --expt-relaxed-constexpr --use_fast_math -diag-suppress 20012,186 -arch=sm_86"

# Prevent interactive prompts
ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1

# Set working directory
WORKDIR /opt/ml/code

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    wget \
    build-essential \
    cmake \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Upgrade pip
RUN pip3 install --no-cache-dir --upgrade pip

# Install PyTorch with CUDA 11.8 support (SAME AS 3DGS CONTAINER)
RUN pip3 install --no-cache-dir \
    torch==2.0.1+cu118 \
    torchvision==0.15.2+cu118 \
    torchaudio==2.0.2+cu118 \
    --index-url https://download.pytorch.org/whl/cu118

# Install CUDA-specific dependencies for CUDA 11.8
RUN pip3 install --no-cache-dir cupy-cuda11x

# Install TorchPQ (required by SOGS) - CUDA 11.8 compatible
RUN pip3 install --no-cache-dir torchpq

# Install PLAS (Parallel Linear Assignment Sorting) from GitHub
RUN pip3 install --no-cache-dir git+https://github.com/fraunhoferhhi/PLAS.git

# Install official PlayCanvas SOGS package from GitHub
RUN pip3 install --no-cache-dir git+https://github.com/playcanvas/sogs.git

# Install additional dependencies for our container
RUN pip3 install --no-cache-dir \
    boto3==1.34.69 \
    numpy==1.24.3 \
    pathlib

# Copy application code
COPY compress.py .
RUN chmod +x compress.py

# Verify installations (with CUDA 11.8 compatibility)
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