# NerfStudio-based 3D Gaussian Splatting Container
# Implements Vincent Woo's Sutro Tower methodology for production use
# Based on Spaceport ML Pipeline requirements

FROM 763104351884.dkr.ecr.us-west-2.amazonaws.com/pytorch-training:2.0.1-gpu-py310-cu117-ubuntu20.04-sagemaker

# Set environment variables for CUDA (optimized for A10G GPU)
ENV CUDA_HOME=/usr/local/cuda
ENV PATH=${CUDA_HOME}/bin:${PATH}
ENV LD_LIBRARY_PATH=${CUDA_HOME}/lib64:${LD_LIBRARY_PATH}

# Set CUDA architecture for A10G GPU (Compute Capability 8.6)
ENV TORCH_CUDA_ARCH_LIST="8.6"
ENV CUDA_ARCH_FLAGS="-arch=sm_86"

# Set C++ standard for CUDA compilation
ENV CXXFLAGS="-std=c++17"
ENV NVCC_FLAGS="-std=c++17 --expt-relaxed-constexpr --use_fast_math -diag-suppress 20012,186 -arch=sm_86"

# Set working directory
WORKDIR /opt/ml/code

# ----------------------------------------------------------------------------
# 1. Install System Dependencies (CACHED LAYER)
# ----------------------------------------------------------------------------
RUN apt-get update && apt-get install -y \
    git \
    wget \
    build-essential \
    cmake \
    ffmpeg \
    libavformat-dev \
    libavcodec-dev \
    libavdevice-dev \
    libavutil-dev \
    libswscale-dev \
    libswresample-dev \
    pkg-config \
    colmap \
    && rm -rf /var/lib/apt/lists/*

# ----------------------------------------------------------------------------
# 2. Install Core Dependencies (CACHED LAYER)
# ----------------------------------------------------------------------------
# Fix NumPy compatibility first
RUN pip install --no-cache-dir "numpy<2.0" && \
    pip install --no-cache-dir \
        ninja \
        packaging \
        wheel \
        Pillow \
        PyYAML \
        requests \
        tqdm \
        rich \
        tyro \
        nuscenes-devkit \
        opencv-python \
        matplotlib \
        mediapy \
        scipy \
        torch-fidelity \
        lpips \
        tensorboard

# ----------------------------------------------------------------------------
# 3. Install NerfStudio with Vincent Woo's Exact Configuration
# ----------------------------------------------------------------------------
# Install NerfStudio (includes gsplat as dependency)
RUN pip install --no-cache-dir nerfstudio[all]>=1.0.0

# Verify NerfStudio installation includes required components
RUN python -c "import nerfstudio; print('✅ NerfStudio installed successfully')"
RUN python -c "import gsplat; print('✅ gsplat backend available')"
RUN ns-install-cli --help > /dev/null && echo "✅ NerfStudio CLI available"

# ----------------------------------------------------------------------------
# 4. AWS and Production Dependencies
# ----------------------------------------------------------------------------
RUN pip install --no-cache-dir \
    boto3>=1.26.0 \
    psutil>=5.9.0 \
    plyfile>=0.7.4

# ----------------------------------------------------------------------------
# 5. Copy Training Code and Configuration
# ----------------------------------------------------------------------------
COPY train_nerfstudio_production.py /opt/ml/code/
COPY nerfstudio_config.yaml /opt/ml/code/
COPY utils/ /opt/ml/code/utils/

# Set Python path
ENV PYTHONPATH="/opt/ml/code:${PYTHONPATH}"

# Create necessary directories
RUN mkdir -p /opt/ml/model /opt/ml/input /opt/ml/output

# Set the SageMaker entry point (Vincent Woo's methodology)
ENTRYPOINT ["python", "/opt/ml/code/train_nerfstudio_production.py"]