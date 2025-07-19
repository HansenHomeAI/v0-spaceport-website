# ---- Spaceport 3DGS Training Container ---------------------------------------
# Re-base on AWS SageMaker’s official PyTorch GPU image so the driver mount
# logic is guaranteed to work.  CUDA 11.8 → compatible with ml.g4dn.xlarge.
FROM 763104351884.dkr.ecr.us-west-2.amazonaws.com/pytorch-training:2.0.1-gpu-py310-cu118-ubuntu20.04-sagemaker

# ----------------------------------------------------------------------------
# 1.  Install additional Python libraries (gsplat, OpenCV, etc.)
# ----------------------------------------------------------------------------
WORKDIR /opt/ml

# Copy requirements first for better layer caching
COPY requirements_optimized.txt /opt/ml/

RUN pip install --no-cache-dir -r /opt/ml/requirements_optimized.txt

# ----------------------------------------------------------------------------
# 2.  Add application code
# ----------------------------------------------------------------------------
WORKDIR /opt/ml/code
COPY . /opt/ml/code

# Ensure the code directory is on PYTHONPATH
ENV PYTHONPATH="/opt/ml/code:${PYTHONPATH}"

# ----------------------------------------------------------------------------
# 3.  Runtime configuration
#    NOTE: Do NOT set CUDA_VISIBLE_DEVICES / NVIDIA_VISIBLE_DEVICES here –
#    SageMaker sets those at runtime.  We only keep standard SageMaker vars.
# ----------------------------------------------------------------------------
ENV SM_MODEL_DIR=/opt/ml/model \
    SM_CHANNEL_TRAINING=/opt/ml/input/data/training \
    SM_OUTPUT_DATA_DIR=/opt/ml/output

# ----------------------------------------------------------------------------
# 4.  Entrypoint – launch the real training script
# ----------------------------------------------------------------------------
ENTRYPOINT ["python3", "train_gaussian_production.py"] 