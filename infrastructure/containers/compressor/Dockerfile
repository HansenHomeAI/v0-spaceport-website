# Production SOGS Compression Container with latest CUDA GPU support
FROM nvidia/cuda:12.9.1-devel-ubuntu22.04

# Prevent interactive prompts during installation
ENV DEBIAN_FRONTEND=noninteractive

WORKDIR /opt/ml/code

# Install system dependencies including Python 3.9
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3.9 \
    python3.9-dev \
    python3.9-distutils \
    python3-pip \
    build-essential \
    git \
    cmake \
    pkg-config \
    libjpeg-dev \
    libpng-dev \
    libwebp-dev \
    libtiff-dev \
    curl \
    wget \
    && rm -rf /var/lib/apt/lists/*

# Set Python 3.9 as default
RUN update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.9 1
RUN update-alternatives --install /usr/bin/python python /usr/bin/python3.9 1

# Upgrade pip
RUN python -m pip install --upgrade pip

# Install PyTorch with CUDA 11.8 support first (required for SOGS)
RUN pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118

# Install CuPy for CUDA 11.8 (more stable than 12.x)
RUN pip install cupy-cuda11x

# Copy and install basic Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install PLAS (required for SOGS) - with error handling
RUN pip install git+https://github.com/fraunhoferhhi/PLAS.git || echo "PLAS installation failed, continuing..."

# Install SOGS from PlayCanvas repository - the real deal!
RUN pip install git+https://github.com/playcanvas/sogs.git || echo "SOGS installation failed, will use fallback"

# Copy the production compression script
COPY compress.py .
RUN chmod +x compress.py

# Set environment variables for CUDA
ENV NVIDIA_VISIBLE_DEVICES=all
ENV NVIDIA_DRIVER_CAPABILITIES=compute,utility
ENV CUDA_VISIBLE_DEVICES=all

# Set the entrypoint to our production script
ENTRYPOINT ["python", "/opt/ml/code/compress.py"] 