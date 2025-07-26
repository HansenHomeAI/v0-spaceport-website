# Use SageMaker PyTorch training container with CUDA 11.8 (add compiler for gsplat)
FROM 763104351884.dkr.ecr.us-west-2.amazonaws.com/pytorch-training:2.0.1-gpu-py310-cu118-ubuntu20.04-sagemaker

# Set environment variables for CUDA compilation
ENV CUDA_HOME=/usr/local/cuda
ENV PATH=${CUDA_HOME}/bin:${PATH}
ENV LD_LIBRARY_PATH=${CUDA_HOME}/lib64:${LD_LIBRARY_PATH}
# T4 GPU architecture (sm_75) - for compilation if needed
ENV TORCH_CUDA_ARCH_LIST="7.5"
# Remove FORCE_CUDA=1 to allow pre-compiled wheels

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

# Install CUDA compiler for gsplat compilation (will compile on GPU at runtime)
RUN apt-get update && apt-get install -y cuda-nvcc-11-8 && rm -rf /var/lib/apt/lists/*

# Install gsplat (will compile CUDA extensions when first imported on GPU)
RUN pip install --no-cache-dir gsplat==1.5.3

# Install remaining requirements (excluding gsplat which is already installed)
RUN grep -v "gsplat" /opt/ml/requirements_optimized.txt > /tmp/requirements_no_gsplat.txt && \
    pip install --no-cache-dir -r /tmp/requirements_no_gsplat.txt && \
    rm /tmp/requirements_no_gsplat.txt

# ----------------------------------------------------------------------------
# 3. Copy training code
# ----------------------------------------------------------------------------
COPY train_gaussian_production.py /opt/ml/code/
COPY utils/ /opt/ml/code/utils/
COPY progressive_config.yaml /opt/ml/code/

# Set Python path
ENV PYTHONPATH="/opt/ml/code:${PYTHONPATH}"

# Set the SageMaker entry point (this is the proper way for SageMaker containers)
ENTRYPOINT ["python", "/opt/ml/code/train_gaussian_production.py", "--config", "/opt/ml/code/progressive_config.yaml"] 