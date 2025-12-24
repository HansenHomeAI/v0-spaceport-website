# =================================================================
# AWS SageMaker 3D Gaussian Splatting Training Container
# Vincent Woo's Sutro Tower Methodology - JIT Compilation Approach
# =================================================================
# Branch-specific build verification marker - safe to remove or update during tests
# Test: New branch container build verification - OOM fix validated
# Second change to trigger container build workflow

FROM 763104351884.dkr.ecr.us-west-2.amazonaws.com/pytorch-training:2.0.1-gpu-py310-cu118-ubuntu20.04-sagemaker

LABEL maintainer="Spaceport ML Team"
LABEL version="3.0"
LABEL description="3D Gaussian Splatting training with gsplat JIT compilation for AWS ml.g5.xlarge"

# Set working directory
WORKDIR /opt/ml/code

# ---------------------------------------------------------------
# 1. Install System Dependencies
# ---------------------------------------------------------------

# Install COLMAP, CUDA developer toolchain, and build dependencies
# CUDA packages are needed so gsplat's JIT compilation can link libcudart
# Build tools (cmake, g++, etc.) are needed for fpsample and other compiled dependencies
# Ninja is required by scikit-build-core when building pybind11 extensions
RUN apt-get update && apt-get install -y --no-install-recommends wget gnupg && \
    wget https://developer.download.nvidia.com/compute/cuda/repos/ubuntu2004/x86_64/cuda-keyring_1.1-1_all.deb && \
    dpkg -i cuda-keyring_1.1-1_all.deb && rm cuda-keyring_1.1-1_all.deb && \
    apt-get update && apt-get install -y --no-install-recommends \
        colmap \
        cuda-nvcc-11-8 \
        cuda-cudart-dev-11-8 \
        build-essential \
        cmake \
        ninja-build \
        git \
    && rm -rf /var/lib/apt/lists/*

ENV CUDA_HOME=/usr/local/cuda
ENV LD_LIBRARY_PATH=/usr/local/cuda/lib64:/usr/local/cuda/lib
ENV LIBRARY_PATH=/usr/local/cuda/lib64:/usr/local/cuda/lib
ENV PATH=/usr/local/cuda/bin:/opt/conda/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin

# CRITICAL: Limit build parallelism globally to prevent OOM during pip installs
# BUILD_GENERAL1_LARGE has 15GB RAM, parallel builds (cmake/ninja) need ~8-12GB each
# Set globally so all build systems respect these limits
ENV MAX_JOBS=1
ENV CMAKE_BUILD_PARALLEL_LEVEL=1

# ---------------------------------------------------------------
# 2. Install NerfStudio with gsplat JIT Compilation (Vincent Woo's Approach)
# ---------------------------------------------------------------

# Ensure latest pybind11 to satisfy fpsample build requirements
RUN pip install --no-cache-dir "pybind11>=2.13.0"

# Install NerfStudio - this automatically includes gsplat as a dependency
# gsplat will use JIT (Just-In-Time) compilation on first execution
# Build parallelism is limited globally via MAX_JOBS and CMAKE_BUILD_PARALLEL_LEVEL env vars
# This matches the past fix for gsplat compilation (commit 5c864e1a)
RUN pip install --no-cache-dir "nerfstudio[all]>=1.0.0"

# Verify installations
RUN python -c "import nerfstudio; print('✅ NerfStudio installed successfully')"
RUN python -c "import gsplat; print('✅ gsplat backend available (will JIT compile on first use)')"
RUN ns-install-cli --help > /dev/null && echo "✅ NerfStudio CLI available"

# ---------------------------------------------------------------
# 2. AWS and Production Dependencies
# ---------------------------------------------------------------

RUN pip install --no-cache-dir \
    boto3>=1.26.0 \
    psutil>=5.9.0 \
    plyfile>=0.7.4

# ---------------------------------------------------------------
# 3. Copy Training Code and Configuration
# ---------------------------------------------------------------

COPY train_nerfstudio_production.py /opt/ml/code/
COPY nerfstudio_config.yaml /opt/ml/code/
COPY utils/ /opt/ml/code/utils/

# Set Python path
ENV PYTHONPATH="/opt/ml/code:${PYTHONPATH}"

# CRITICAL: Disable PyTorch Triton compilation to prevent CUDA development header errors
# PyTorch 2.0+ tries to use Triton/Inductor backends which need cuda.h at runtime
# SageMaker containers only have CUDA runtime, not development environment
ENV TORCH_COMPILE_DISABLE=1
ENV TORCH_CUDA_ARCH_LIST="8.0 8.6"

# Create necessary directories
RUN mkdir -p /opt/ml/model /opt/ml/input /opt/ml/output

# Set the SageMaker entry point (Vincent Woo's methodology)
ENTRYPOINT ["python", "/opt/ml/code/train_nerfstudio_production.py"]
