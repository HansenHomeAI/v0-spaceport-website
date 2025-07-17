# 3D Gaussian Splatting Training Container - Multi-Stage Production Build
# Optimized for layer caching and build efficiency

# Stage 1: Base environment with system dependencies
FROM nvidia/cuda:11.8.0-devel-ubuntu22.04 AS base

# Prevent interactive prompts during package installation
ENV DEBIAN_FRONTEND=noninteractive

# Set CUDA environment variables early
ENV CUDA_HOME=/usr/local/cuda
ENV PATH=${CUDA_HOME}/bin:${PATH}
ENV LD_LIBRARY_PATH=${CUDA_HOME}/lib64:${LD_LIBRARY_PATH}
ENV CUDA_VISIBLE_DEVICES=all
ENV NVIDIA_VISIBLE_DEVICES=all
ENV NVIDIA_DRIVER_CAPABILITIES=compute,utility

# Install system dependencies (cached layer)
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    git \
    wget \
    curl \
    build-essential \
    cmake \
    nvidia-cuda-toolkit \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Stage 2: Python dependencies
FROM base AS python-deps

# Set working directory
WORKDIR /opt/ml

# Copy requirements first for better caching
COPY requirements.txt /opt/ml/
COPY requirements_optimized.txt /opt/ml/

# Install PyTorch with CUDA support using official PyTorch index
RUN pip3 install --no-cache-dir \
    torch==2.0.1+cu118 \
    torchvision==0.15.2+cu118 \
    torchaudio==2.0.2+cu118 \
    --index-url https://download.pytorch.org/whl/cu118

# Install other Python dependencies using default PyPI (PyTorch already installed above)
RUN pip3 install --no-cache-dir -r requirements_optimized.txt

# Initialize NVIDIA runtime for SageMaker (CRITICAL FOR GPU DETECTION)
RUN nvidia-smi || echo "nvidia-smi not available in build context (expected)"

# Verify CUDA installation and force PyTorch to detect GPU
RUN python3 -c "import torch; print('PyTorch version:', torch.__version__); print('CUDA available:', torch.cuda.is_available()); print('CUDA version:', torch.version.cuda if torch.cuda.is_available() else 'None'); print('GPU count:', torch.cuda.device_count())"

# Stage 3: Application code
FROM python-deps AS app-build

# Set working directory
WORKDIR /opt/ml/code

# Copy source code (most frequently changed)
COPY . /opt/ml/code/

# Make scripts executable
RUN chmod +x train_gaussian_production.py \
    && chmod +x test_production.py

# Add the code directory to python path
ENV PYTHONPATH="/opt/ml/code:${PYTHONPATH}"

# Stage 4: Final runtime image
FROM app-build AS runtime

# CRITICAL: Add ECS GPU capability label for SageMaker
LABEL com.amazonaws.ecs.capability.gpu="true"

# Reinforce CUDA environment variables for runtime
ENV NVIDIA_VISIBLE_DEVICES=all
ENV NVIDIA_DRIVER_CAPABILITIES=compute,utility
ENV CUDA_VISIBLE_DEVICES=all
ENV CUDA_HOME=/usr/local/cuda
ENV PATH=${CUDA_HOME}/bin:${PATH}
ENV LD_LIBRARY_PATH=${CUDA_HOME}/lib64:${LD_LIBRARY_PATH}

# SageMaker specific environment variables for GPU detection
ENV SM_MODEL_DIR=/opt/ml/model
ENV SM_CHANNEL_TRAINING=/opt/ml/input/data/training
ENV SM_OUTPUT_DATA_DIR=/opt/ml/output
ENV SM_NUM_GPUS=1

# Health check with comprehensive GPU detection
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python3 -c "import torch; import gsplat; print('PyTorch CUDA:', torch.cuda.is_available()); print('GPU Count:', torch.cuda.device_count() if torch.cuda.is_available() else 0); print('gsplat loaded:', True)" || exit 1

# Ensure all SageMaker directories have proper permissions
RUN mkdir -p /opt/ml/model /opt/ml/output /opt/ml/input \
    && chmod -R 755 /opt/ml

# Run as root user for SageMaker Training Jobs (eliminates permission issues)
USER root

# Set the correct entrypoint for SageMaker Training Jobs
ENTRYPOINT ["python3", "train_gaussian_production.py"] 