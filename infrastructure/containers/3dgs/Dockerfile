# Use SageMaker PyTorch training container with CUDA 11.8
FROM 763104351884.dkr.ecr.us-west-2.amazonaws.com/pytorch-training:2.0.1-gpu-py310-cu118-ubuntu20.04-sagemaker

# Set environment variables for CUDA
ENV CUDA_HOME=/usr/local/cuda
ENV PATH=${CUDA_HOME}/bin:${PATH}
ENV LD_LIBRARY_PATH=${CUDA_HOME}/lib64:${LD_LIBRARY_PATH}

# Set CUDA architecture for A10G GPU (Compute Capability 8.6)
ENV TORCH_CUDA_ARCH_LIST="8.6"
ENV CUDA_ARCH_FLAGS="-arch=sm_86"

# Set C++ standard for CUDA compilation
ENV CXXFLAGS="-std=c++17"
ENV NVCC_FLAGS="-std=c++17 --expt-relaxed-constexpr --use_fast_math -diag-suppress 20012,186 -arch=sm_86"

# Set working directory
WORKDIR /opt/ml/code

# ----------------------------------------------------------------------------
# 1. Install System Dependencies (CACHED LAYER)
# ----------------------------------------------------------------------------
RUN apt-get update && apt-get install -y \
    git \
    wget \
    build-essential \
    cmake \
    && rm -rf /var/lib/apt/lists/*

# ----------------------------------------------------------------------------
# 2. Install Core Python Dependencies (CACHED LAYER)
# ----------------------------------------------------------------------------
# Fix NumPy compatibility and install core dependencies
RUN pip install --no-cache-dir "numpy<2.0" && \
    pip install --no-cache-dir \
        ninja \
        jaxtyping \
        rich \
        pyyaml \
        scipy \
        matplotlib \
        tqdm \
        opencv-python \
        scikit-image

# ----------------------------------------------------------------------------
# 3. Install gsplat using pre-compiled wheel (FAST & CACHED)
# ----------------------------------------------------------------------------
# Copy requirements file first for better caching
COPY requirements_optimized.txt /opt/ml/

# Install gsplat dependencies
RUN pip install ninja numpy jaxtyping rich

# Use pre-compiled wheels for gsplat (much faster than source compilation)
# This avoids the 10+ minute source compilation every time
RUN pip install gsplat --index-url https://docs.gsplat.studio/whl/pt20cu118 --no-cache-dir

# Install remaining requirements (excluding gsplat which is already installed)
RUN grep -v "gsplat" /opt/ml/requirements_optimized.txt > /tmp/requirements_no_gsplat.txt && \
    pip install --no-cache-dir -r /tmp/requirements_no_gsplat.txt && \
    rm /tmp/requirements_no_gsplat.txt

# ----------------------------------------------------------------------------
# 4. Copy training code (LAST LAYER - changes most frequently)
# ----------------------------------------------------------------------------
COPY train_gaussian_production.py /opt/ml/code/
COPY utils/ /opt/ml/code/utils/
COPY progressive_config.yaml /opt/ml/code/

# Set Python path
ENV PYTHONPATH="/opt/ml/code:${PYTHONPATH}"

# Set the SageMaker entry point
ENTRYPOINT ["python", "/opt/ml/code/train_gaussian_production.py", "--config", "/opt/ml/code/progressive_config.yaml"] 