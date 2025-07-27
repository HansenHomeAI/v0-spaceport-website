# Use SageMaker PyTorch training container with CUDA 11.8
FROM 763104351884.dkr.ecr.us-west-2.amazonaws.com/pytorch-training:2.0.1-gpu-py310-cu118-ubuntu20.04-sagemaker

# Set environment variables for CUDA
ENV CUDA_HOME=/usr/local/cuda
ENV PATH=${CUDA_HOME}/bin:${PATH}
ENV LD_LIBRARY_PATH=${CUDA_HOME}/lib64:${LD_LIBRARY_PATH}

# Set C++ standard for CUDA compilation (required for gsplat JIT build)
ENV CXXFLAGS="-std=c++17"
ENV NVCC_FLAGS="-std=c++17"

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
# 3. Install gsplat using pre-compiled wheel (FAST & RELIABLE)
# ----------------------------------------------------------------------------
# Install CUDA compiler (nvcc) for gsplat JIT build – Ubuntu 20.04
RUN apt-get update && apt-get install -y wget gnupg2 \
 && wget https://developer.download.nvidia.com/compute/cuda/repos/ubuntu2004/x86_64/cuda-keyring_1.1-1_all.deb \
 && dpkg -i cuda-keyring_1.1-1_all.deb \
 && apt-get update \
 && apt-get install -y cuda-toolkit-11-8 \
 && rm -f cuda-keyring_1.1-1_all.deb \
 && rm -rf /var/lib/apt/lists/*

# Install gsplat dependencies first
RUN pip install ninja numpy jaxtyping rich

# Install gsplat from pre-compiled wheels (requires JIT compilation on first run)
RUN pip install gsplat --index-url https://docs.gsplat.studio/whl/pt20cu118

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