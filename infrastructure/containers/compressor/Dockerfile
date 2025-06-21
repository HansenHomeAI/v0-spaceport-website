# Production SOGS Compression Container
# Optimized for AWS SageMaker with GPU support

FROM nvidia/cuda:12.1.0-devel-ubuntu22.04

# Prevent interactive prompts
ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1
ENV CUDA_HOME=/usr/local/cuda
ENV PATH=${CUDA_HOME}/bin:${PATH}
ENV LD_LIBRARY_PATH=${CUDA_HOME}/lib64:${LD_LIBRARY_PATH}
ENV ENVIRONMENT=production
ENV PYTHONPATH=/opt/ml/code

# Install system dependencies
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    python3-dev \
    build-essential \
    cmake \
    git \
    wget \
    curl \
    libjpeg-dev \
    libpng-dev \
    libwebp-dev \
    libtiff-dev \
    libopencv-dev \
    pkg-config \
    software-properties-common \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Create and use a Python virtual environment
RUN python3 -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Upgrade pip and install core packages
RUN pip install --no-cache-dir --upgrade pip setuptools wheel

# Install PyTorch with CUDA support
RUN pip install --no-cache-dir torch==2.1.0 torchvision==0.16.0 torchaudio==2.1.0 --index-url https://download.pytorch.org/whl/cu121

# Install other core dependencies
RUN pip install --no-cache-dir \
    cupy-cuda12x \
    boto3 \
    awscli \
    numpy \
    scipy \
    pandas \
    scikit-learn \
    Pillow \
    opencv-python \
    imageio \
    tqdm \
    structlog \
    orjson \
    plyfile

# Install PLAS algorithm (required for SOGS)
RUN pip install --no-cache-dir git+https://github.com/fraunhoferhhi/PLAS.git

# Clone and install PlayCanvas SOGS
WORKDIR /opt
RUN git clone https://github.com/playcanvas/sogs.git
WORKDIR /opt/sogs
RUN pip install --no-cache-dir -e .

# Create SageMaker directory structure
RUN mkdir -p /opt/ml/code /opt/ml/input/data /opt/ml/model /opt/ml/output

# Set working directory
WORKDIR /opt/ml/code

# Copy compression script
COPY compress.py /opt/ml/code/compress.py
RUN chmod +x /opt/ml/code/compress.py

# Create entrypoint script for SageMaker
RUN echo '#!/bin/bash\n\
set -e\n\
\n\
echo "🚀 Starting Production SOGS Compression Container"\n\
echo "Environment: $ENVIRONMENT"\n\
echo "GPU Info:"\n\
nvidia-smi || echo "No GPU available"\n\
\n\
echo "Verifying installations..."\n\
python -c "import torch; print(f''CUDA available: {torch.cuda.is_available()}''); import sogs; print(''SOGS imported successfully'')" \n\
\n\
echo "Input Data:"\n\
ls -la /opt/ml/input/data/ || echo "No input data directory"\n\
\n\
echo "Starting compression..."\n\
python3 compress.py\n\
\n\
echo "Compression completed! Output files:"\n\
ls -la /opt/ml/model/\n\
' > /opt/ml/code/entrypoint.sh

RUN chmod +x /opt/ml/code/entrypoint.sh

# Set proper permissions for SageMaker
RUN chmod -R 755 /opt/ml/

# Final environment setup
ENV SAGEMAKER_PROGRAM=compress.py
ENV SAGEMAKER_SUBMIT_DIRECTORY=/opt/ml/code

# Use production entrypoint
ENTRYPOINT ["/opt/ml/code/entrypoint.sh"] 