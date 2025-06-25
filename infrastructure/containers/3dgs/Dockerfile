# 3D Gaussian Splatting Training Container - Production GPU Version
FROM nvidia/cuda:11.8.0-devel-ubuntu20.04

# Prevent interactive prompts during package installation
ENV DEBIAN_FRONTEND=noninteractive

# Install system dependencies
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    git \
    wget \
    curl \
    build-essential \
    cmake \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /opt/ml

# Install PyTorch with CUDA support first
RUN pip3 install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118

# Install Python dependencies
COPY requirements.txt .
RUN pip3 install -r requirements.txt

# Copy training script
COPY train_gaussian_production.py /opt/ml/code/train.py
RUN chmod +x /opt/ml/code/train.py

# Set entrypoint
ENTRYPOINT ["python3", "/opt/ml/code/train.py"] 