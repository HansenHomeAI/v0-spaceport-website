# NerfStudio-based 3D Gaussian Splatting Container
# Implements Vincent Woo's Sutro Tower methodology for production use
# Based on Spaceport ML Pipeline requirements

FROM 763104351884.dkr.ecr.us-west-2.amazonaws.com/pytorch-training:2.0.1-gpu-py310-cu118-ubuntu20.04-sagemaker

# Set environment variables for CUDA (optimized for A10G GPU)
ENV CUDA_HOME=/usr/local/cuda
ENV PATH=${CUDA_HOME}/bin:${PATH}
ENV LD_LIBRARY_PATH=${CUDA_HOME}/lib64:${LD_LIBRARY_PATH}

# Set CUDA architecture for A10G GPU (Compute Capability 8.6)
# Include multiple architectures for broader compatibility
ENV TORCH_CUDA_ARCH_LIST="7.0;7.5;8.0;8.6"
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
# 2. Install CUDA Toolkit (CACHED LAYER - Required for gsplat source compilation)
# ----------------------------------------------------------------------------
# Install CUDA compiler (nvcc) for gsplat JIT build – Ubuntu 20.04
RUN apt-get update && apt-get install -y wget gnupg2 \
 && wget https://developer.download.nvidia.com/compute/cuda/repos/ubuntu2004/x86_64/cuda-keyring_1.1-1_all.deb \
 && dpkg -i cuda-keyring_1.1-1_all.deb \
 && apt-get update \
 && apt-get install -y cuda-toolkit-11-8 \
 && rm -f cuda-keyring_1.1-1_all.deb \
 && rm -rf /var/lib/apt/lists/*

# ----------------------------------------------------------------------------
# 3. Install Core Dependencies (CACHED LAYER)
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
# 5. Install TorchAudio compatible with PyTorch 2.0.1 BEFORE NerfStudio
# ----------------------------------------------------------------------------
# This prevents NerfStudio/torchmetrics from installing incompatible TorchAudio version
RUN pip install --no-cache-dir torchaudio==2.0.2+cu118 --index-url https://download.pytorch.org/whl/cu118 && \
    python -c "import torch; import torchaudio; print(f'✅ PyTorch {torch.__version__} + TorchAudio {torchaudio.__version__} compatibility verified')"

# Disable TorchMetrics audio functionality to prevent import issues
ENV TORCHMETRICS_AUDIO_AVAILABLE=0

# ----------------------------------------------------------------------------
# 4. Install NerfStudio with Vincent Woo's Exact Configuration
# ----------------------------------------------------------------------------
# Install NerfStudio (includes gsplat as dependency)
RUN pip install --no-cache-dir nerfstudio[all]>=1.0.0

# Verify NerfStudio installation includes required components
RUN python -c "import nerfstudio; print('✅ NerfStudio installed successfully')"
\
# CRITICAL: Force gsplat SOURCE COMPILATION with A10G architecture support
# This is the proven approach that works with our A10G setup (July 2025 commits)
# Precompiled wheels failed - source compilation with nvcc is required
RUN TORCH_CUDA_ARCH_LIST="7.0;7.5;8.0;8.6" MAX_JOBS=2 pip install git+https://github.com/nerfstudio-project/gsplat.git@v1.4.0 --no-cache-dir --force-reinstall && \
    pip install --no-cache-dir --no-deps --force-reinstall "numpy<2.0" && \
    python -c "import gsplat; print('✅ gsplat 1.4.0 compiled from source with A10G support (MAX_JOBS=2)')" && \
    python -c "import numpy; print(f'✅ NumPy version: {numpy.__version__}')"
RUN ns-install-cli --help > /dev/null && echo "✅ NerfStudio CLI available"

# ----------------------------------------------------------------------------
# 5. AWS and Production Dependencies
# ----------------------------------------------------------------------------
RUN pip install --no-cache-dir \
    boto3>=1.26.0 \
    psutil>=5.9.0 \
    plyfile>=0.7.4

# ----------------------------------------------------------------------------
# 6. Copy Training Code and Configuration
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