# 3D Gaussian Splatting Training Container - Production GPU Version
# Test build trigger - IAM permissions fix verification
FROM nvidia/cuda:11.8.0-devel-ubuntu22.04

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

# Copy all code and dependencies
COPY . /opt/ml/code/
WORKDIR /opt/ml/code

# Install Python dependencies
RUN pip3 install -r requirements.txt

# Make the main script executable
RUN chmod +x train_gaussian_production.py

# Set the correct entrypoint with the config file argument
ENTRYPOINT ["python3", "train_gaussian_production.py", "--config", "progressive_config.yaml"] 