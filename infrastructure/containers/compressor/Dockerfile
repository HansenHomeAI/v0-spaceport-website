# Production SOGS Compression Container with GPU support
FROM nvidia/cuda:12.1-devel-ubuntu20.04

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
    && rm -rf /var/lib/apt/lists/*

# Set Python 3.9 as default
RUN update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.9 1
RUN update-alternatives --install /usr/bin/python python /usr/bin/python3.9 1

# Upgrade pip
RUN python -m pip install --upgrade pip

# Install PyTorch with CUDA support first (required for SOGS)
RUN pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121

# Install CuPy for CUDA 12.1
RUN pip install cupy-cuda12x

# Copy and install basic Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install PLAS (required for SOGS)
RUN pip install git+https://github.com/fraunhoferhhi/PLAS.git

# Install SOGS from PlayCanvas repository
RUN pip install git+https://github.com/playcanvas/sogs.git

# Copy the production compression script
COPY compress.py .
RUN chmod +x compress.py

# Set environment variables for CUDA
ENV NVIDIA_VISIBLE_DEVICES=all
ENV NVIDIA_DRIVER_CAPABILITIES=compute,utility

# Set the entrypoint to our production script
ENTRYPOINT ["python", "/opt/ml/code/compress.py"] 