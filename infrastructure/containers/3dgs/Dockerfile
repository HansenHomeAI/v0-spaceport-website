# 3D Gaussian Splatting Training Container
FROM ubuntu:20.04

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

# Install Python dependencies
COPY requirements.txt .
RUN pip3 install -r requirements.txt

# Copy training script
COPY train_gaussian.py .
RUN chmod +x train_gaussian.py

# Set entrypoint
ENTRYPOINT ["python3", "/opt/ml/train_gaussian.py"] 