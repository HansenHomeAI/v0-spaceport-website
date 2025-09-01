# =================================================================
# AWS SageMaker 3D Gaussian Splatting Training Container
# Vincent Woo's Sutro Tower Methodology - JIT Compilation Approach
# =================================================================

FROM 763104351884.dkr.ecr.us-west-2.amazonaws.com/pytorch-training:2.0.1-gpu-py310-cu118-ubuntu20.04-sagemaker

LABEL maintainer="Spaceport ML Team"
LABEL version="3.0"
LABEL description="3D Gaussian Splatting training with gsplat JIT compilation for AWS ml.g5.xlarge"

# Set working directory
WORKDIR /opt/ml/code

# ---------------------------------------------------------------
# 1. Install System Dependencies
# ---------------------------------------------------------------

# Install COLMAP for model conversion (required by training script)
RUN apt-get update && apt-get install -y \
    colmap \
    && rm -rf /var/lib/apt/lists/*

# ---------------------------------------------------------------
# 2. Install NerfStudio with gsplat JIT Compilation (Vincent Woo's Approach)
# ---------------------------------------------------------------

# Install NerfStudio - this automatically includes gsplat as a dependency
# gsplat will use JIT (Just-In-Time) compilation on first execution
RUN pip install --no-cache-dir nerfstudio[all]>=1.0.0

# Verify installations
RUN python -c "import nerfstudio; print('✅ NerfStudio installed successfully')"
RUN python -c "import gsplat; print('✅ gsplat backend available (will JIT compile on first use)')"
RUN ns-install-cli --help > /dev/null && echo "✅ NerfStudio CLI available"

# ---------------------------------------------------------------
# 2. AWS and Production Dependencies
# ---------------------------------------------------------------

RUN pip install --no-cache-dir \
    boto3>=1.26.0 \
    psutil>=5.9.0 \
    plyfile>=0.7.4

# ---------------------------------------------------------------
# 3. Copy Training Code and Configuration
# ---------------------------------------------------------------

COPY train_nerfstudio_production.py /opt/ml/code/
COPY nerfstudio_config.yaml /opt/ml/code/
COPY utils/ /opt/ml/code/utils/

# Set Python path
ENV PYTHONPATH="/opt/ml/code:${PYTHONPATH}"

# CRITICAL: Disable PyTorch Triton compilation to prevent CUDA development header errors
# PyTorch 2.0+ tries to use Triton/Inductor backends which need cuda.h at runtime
# SageMaker containers only have CUDA runtime, not development environment
ENV TORCH_COMPILE_DISABLE=1

# Create necessary directories
RUN mkdir -p /opt/ml/model /opt/ml/input /opt/ml/output

# Set the SageMaker entry point (Vincent Woo's methodology)
ENTRYPOINT ["python", "/opt/ml/code/train_nerfstudio_production.py"]