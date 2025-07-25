# ---- Spaceport 3DGS Training Container ---------------------------------------
# Re-base on AWS SageMaker's official PyTorch GPU image so the driver mount
# logic is guaranteed to work.  CUDA 11.8 → compatible with ml.g4dn.xlarge.
FROM 763104351884.dkr.ecr.us-west-2.amazonaws.com/pytorch-training:2.0.1-gpu-py310-cu118-ubuntu20.04-sagemaker

# ----------------------------------------------------------------------------
# 1. Install CUDA development tools for compiling extensions (gsplat, etc.)
# ----------------------------------------------------------------------------
RUN apt-get update && apt-get install -y \
    build-essential \
    g++ \
    cmake \
    ninja-build \
    git \
    && rm -rf /var/lib/apt/lists/*

# ----------------------------------------------------------------------------
# 2.  Install additional Python libraries (excluding gsplat for now)
# ----------------------------------------------------------------------------
WORKDIR /opt/ml

# Copy requirements first for better layer caching
COPY requirements_optimized.txt /opt/ml/

# Install all requirements EXCEPT gsplat (we'll compile it from source)
RUN pip install --no-cache-dir -r /opt/ml/requirements_optimized.txt || \
    (grep -v "gsplat" /opt/ml/requirements_optimized.txt > /tmp/requirements_no_gsplat.txt && \
     pip install --no-cache-dir -r /tmp/requirements_no_gsplat.txt)

# ----------------------------------------------------------------------------
# 2.1 Compile gsplat from source with CUDA 11.8 support
# ----------------------------------------------------------------------------
RUN echo "🔧 Compiling gsplat from source with CUDA 11.8..." && \
    # Set CUDA compilation environment variables
    export CUDA_HOME=/usr/local/cuda && \
    export PATH=$CUDA_HOME/bin:$PATH && \
    export LD_LIBRARY_PATH=$CUDA_HOME/lib64:$LD_LIBRARY_PATH && \
    export TORCH_CUDA_ARCH_LIST="7.5" && \
    export FORCE_CUDA=1 && \
    # Clone and compile gsplat
    git clone --recursive https://github.com/nerfstudio-project/gsplat.git /tmp/gsplat && \
    cd /tmp/gsplat && \
    # Install with specific CUDA flags
    pip install . --no-cache-dir --verbose && \
    cd / && \
    rm -rf /tmp/gsplat && \
    echo "✅ gsplat CUDA compilation complete"

# Verify gsplat CUDA installation
RUN python3 -c "import gsplat; import torch; print('✅ PyTorch CUDA:', torch.cuda.is_available()); print('✅ gsplat imported successfully'); print('✅ gsplat rasterization available:', hasattr(gsplat, 'rasterization'))" || \
    (echo "❌ gsplat CUDA verification failed" && exit 1)

# ----------------------------------------------------------------------------
# 3. Copy training code
# ----------------------------------------------------------------------------
COPY train_gaussian_production.py /opt/ml/code/
COPY utils/ /opt/ml/code/utils/
COPY progressive_config.yaml /opt/ml/code/

# ----------------------------------------------------------------------------
# 4. SageMaker entry point
# ----------------------------------------------------------------------------
ENV SAGEMAKER_PROGRAM=/opt/ml/code/train_gaussian_production.py

# ----------------------------------------------------------------------------
# 5.  Runtime configuration
#    NOTE: Do NOT set CUDA_VISIBLE_DEVICES / NVIDIA_VISIBLE_DEVICES here –
#    SageMaker sets those at runtime.  We only keep standard SageMaker vars.
# ----------------------------------------------------------------------------
ENV SM_MODEL_DIR=/opt/ml/model \
    SM_CHANNEL_TRAINING=/opt/ml/input/data/training \
    SM_OUTPUT_DATA_DIR=/opt/ml/output

# ----------------------------------------------------------------------------
# 6.  Entrypoint – launch the real training script
# ----------------------------------------------------------------------------
ENTRYPOINT ["python3", "/opt/ml/code/train_gaussian_production.py"] 