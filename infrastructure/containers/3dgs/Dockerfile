# Use SageMaker PyTorch training container
FROM 763104351884.dkr.ecr.us-west-2.amazonaws.com/pytorch-training:2.0.1-gpu-py310-cu118-ubuntu20.04-sagemaker

# Set environment variables for CUDA compilation
ENV CUDA_HOME=/usr/local/cuda
ENV PATH=${CUDA_HOME}/bin:${PATH}
ENV LD_LIBRARY_PATH=${CUDA_HOME}/lib64:${LD_LIBRARY_PATH}
# T4 GPU architecture (sm_75)
ENV TORCH_CUDA_ARCH_LIST="7.5"
ENV FORCE_CUDA=1

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

# Install gsplat from PyPI (JIT compilation approach - industry standard)
RUN pip install --no-cache-dir gsplat

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

# Set the default command
CMD ["python", "train_gaussian_production.py", "--config", "progressive_config.yaml"] 