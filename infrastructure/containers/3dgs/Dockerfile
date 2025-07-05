# 3D Gaussian Splatting Training Container - Multi-Stage Production Build
# Optimized for layer caching and build efficiency

# Stage 1: Base environment with system dependencies
FROM nvidia/cuda:11.8.0-devel-ubuntu22.04 AS base

# Prevent interactive prompts during package installation
ENV DEBIAN_FRONTEND=noninteractive

# Install system dependencies (cached layer)
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    git \
    wget \
    curl \
    build-essential \
    cmake \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Stage 2: Python dependencies
FROM base AS python-deps

# Set working directory
WORKDIR /opt/ml

# Copy requirements first for better caching
COPY requirements.txt /opt/ml/
COPY requirements_optimized.txt /opt/ml/

# Install PyTorch with CUDA support first (largest dependency)
RUN pip3 install --no-cache-dir \
    torch==2.0.1+cu118 \
    torchvision==0.15.2+cu118 \
    torchaudio==2.0.2+cu118 \
    --index-url https://download.pytorch.org/whl/cu118

# Install other Python dependencies
RUN pip3 install --no-cache-dir -r requirements_optimized.txt

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

# Create non-root user for security
RUN useradd --create-home --shell /bin/bash sagemaker \
    && chown -R sagemaker:sagemaker /opt/ml

# Set runtime environment
ENV NVIDIA_VISIBLE_DEVICES=all
ENV NVIDIA_DRIVER_CAPABILITIES=compute,utility
ENV CUDA_VISIBLE_DEVICES=all

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python3 -c "import torch; print('CUDA available:', torch.cuda.is_available())" || exit 1

# Switch to non-root user
USER sagemaker

# Set the correct entrypoint for SageMaker Training Jobs
ENTRYPOINT ["python3", "train_gaussian_production.py"] 