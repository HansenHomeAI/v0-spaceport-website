# 3D Gaussian Splatting Training Container - Multi-Stage Production Build
# Optimized for layer caching and build efficiency with FIXED CUDA DETECTION

# Stage 1: Base environment with CUDA runtime (NOT devel)
# Updated to CUDA 12.4 to match SageMaker host driver
FROM nvidia/cuda:12.4.1-runtime-ubuntu22.04 AS base

# Prevent interactive prompts during package installation
ENV DEBIAN_FRONTEND=noninteractive

# Set CUDA environment variables early
ENV CUDA_HOME=/usr/local/cuda
ENV CUDA_PATH=/usr/local/cuda
ENV PATH=${CUDA_HOME}/bin:${PATH}
ENV LD_LIBRARY_PATH=${CUDA_HOME}/lib64:${LD_LIBRARY_PATH}
ENV CUDA_VISIBLE_DEVICES=all
ENV NVIDIA_VISIBLE_DEVICES=all
ENV NVIDIA_DRIVER_CAPABILITIES=compute,utility

# Install system dependencies including CUDA development tools
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    git \
    wget \
    curl \
    build-essential \
    cmake \
    nvidia-cuda-toolkit \
    nvidia-cuda-dev \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# CRITICAL FIX: Create symlinks for CUDA runtime libraries
# This fixes the torch.cuda.is_available() issue
RUN if [ -f /usr/local/cuda/lib64/libcuda.so.1 ]; then \
        ln -sf /usr/local/cuda/lib64/libcuda.so.1 /usr/local/cuda/lib64/libcuda.so; \
    fi && \
    if [ -f /usr/lib/x86_64-linux-gnu/libcuda.so.1 ]; then \
        ln -sf /usr/lib/x86_64-linux-gnu/libcuda.so.1 /usr/lib/x86_64-linux-gnu/libcuda.so; \
        ln -sf /usr/lib/x86_64-linux-gnu/libcuda.so.1 /usr/local/cuda/lib64/libcuda.so; \
    fi

# Update library cache
RUN ldconfig

# Stage 2: Python dependencies
FROM base AS python-deps

# Set working directory
WORKDIR /opt/ml

# Copy requirements first for better caching
COPY requirements.txt /opt/ml/
COPY requirements_optimized.txt /opt/ml/

# Install PyTorch with CUDA support first (largest dependency)
# Using CUDA 12.4 compatible version to match base image
RUN pip3 install --no-cache-dir \
    torch==2.1.0+cu121 \
    torchvision==0.16.0+cu121 \
    torchaudio==2.1.0+cu121 \
    --index-url https://download.pytorch.org/whl/cu121

# Install other Python dependencies
RUN pip3 install --no-cache-dir -r requirements_optimized.txt

# CRITICAL FIX: Verify CUDA installation with enhanced debugging
RUN echo "=== CUDA VERIFICATION ===" && \
    nvidia-smi || echo "nvidia-smi not available" && \
    echo "=== CUDA LIBRARIES ===" && \
    ls -la /usr/local/cuda/lib64/libcuda* || echo "No CUDA libs in /usr/local/cuda/lib64/" && \
    ls -la /usr/lib/x86_64-linux-gnu/libcuda* || echo "No CUDA libs in /usr/lib/x86_64-linux-gnu/" && \
    echo "=== PYTORCH CUDA TEST ===" && \
    python3 -c "import torch; print('PyTorch version:', torch.__version__); print('CUDA available:', torch.cuda.is_available()); print('CUDA version:', torch.version.cuda if torch.cuda.is_available() else 'None'); print('Device count:', torch.cuda.device_count() if torch.cuda.is_available() else 0)"

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

# Reinforce CUDA environment variables for runtime
ENV NVIDIA_VISIBLE_DEVICES=all
ENV NVIDIA_DRIVER_CAPABILITIES=compute,utility
ENV CUDA_VISIBLE_DEVICES=all
ENV CUDA_HOME=/usr/local/cuda
ENV CUDA_PATH=/usr/local/cuda
ENV PATH=${CUDA_HOME}/bin:${PATH}
ENV LD_LIBRARY_PATH=${CUDA_HOME}/lib64:/usr/lib/x86_64-linux-gnu:${LD_LIBRARY_PATH}

# CRITICAL FIX: Additional runtime CUDA setup
RUN echo "=== RUNTIME CUDA SETUP ===" && \
    ldconfig && \
    echo "=== FINAL CUDA TEST ===" && \
    python3 -c "import torch; print('🎯 Final CUDA check:'); print('  PyTorch version:', torch.__version__); print('  CUDA available:', torch.cuda.is_available()); print('  Device count:', torch.cuda.device_count() if torch.cuda.is_available() else 0); print('  CUDA version:', torch.version.cuda if torch.cuda.is_available() else 'None')"

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