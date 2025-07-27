# Use SageMaker PyTorch training container with CUDA 12.1 (supports A10G natively)
FROM 763104351884.dkr.ecr.us-west-2.amazonaws.com/pytorch-training:2.1.0-gpu-py310-cu121-ubuntu20.04-sagemaker

# Set environment variables for CUDA
ENV CUDA_HOME=/usr/local/cuda
ENV PATH=${CUDA_HOME}/bin:${PATH}
ENV LD_LIBRARY_PATH=${CUDA_HOME}/lib64:${LD_LIBRARY_PATH}

# Set CUDA architecture for A10G GPU (Compute Capability 8.6)
# This forces PyTorch to include A10G architecture in compilation
ENV TORCH_CUDA_ARCH_LIST="7.0;7.5;8.0;8.6"
ENV CUDA_ARCH_FLAGS="-arch=sm_86"

# Set C++ standard for CUDA compilation (required for gsplat source build)
ENV CXXFLAGS="-std=c++17"
ENV NVCC_FLAGS="-std=c++17 --expt-relaxed-constexpr --use_fast_math -diag-suppress 20012,186"

# Set working directory
WORKDIR /opt/ml/code

# ----------------------------------------------------------------------------
# 1. Install System Dependencies
# ----------------------------------------------------------------------------
RUN apt-get update && apt-get install -y \
    git \
    wget \
    build-essential \
    cmake \
    && rm -rf /var/lib/apt/lists/*

# ----------------------------------------------------------------------------
# 2. Install Python Dependencies
# ----------------------------------------------------------------------------
# Copy requirements files
COPY requirements_optimized.txt /opt/ml/

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
# 3. Install gsplat FROM SOURCE for A10G compatibility
# ----------------------------------------------------------------------------
# Install gsplat dependencies required for source compilation
RUN pip install ninja numpy jaxtyping rich

# CRITICAL: Install gsplat from source with A10G architecture support
# This ensures it compiles with compute_86 support for labeled_partition
RUN TORCH_CUDA_ARCH_LIST="7.0;7.5;8.0;8.6" pip install git+https://github.com/nerfstudio-project/gsplat.git --no-cache-dir --force-reinstall

# Install remaining requirements (excluding gsplat which is already installed)
RUN grep -v "gsplat" /opt/ml/requirements_optimized.txt > /tmp/requirements_no_gsplat.txt && \
    pip install --no-cache-dir -r /tmp/requirements_no_gsplat.txt && \
    rm /tmp/requirements_no_gsplat.txt

# ----------------------------------------------------------------------------
# 4. Copy training code
# ----------------------------------------------------------------------------
COPY train_gaussian_production.py /opt/ml/code/
COPY utils/ /opt/ml/code/utils/
COPY progressive_config.yaml /opt/ml/code/

# Set Python path
ENV PYTHONPATH="/opt/ml/code:${PYTHONPATH}"

# Set the SageMaker entry point
ENTRYPOINT ["python", "/opt/ml/code/train_gaussian_production.py", "--config", "/opt/ml/code/progressive_config.yaml"] 