# COLMAP GPU SfM container for SageMaker Processing.
#
# Non-obvious choices:
# - Base image: use Public ECR Ubuntu mirror to avoid Docker Hub anonymous pull limits
#   observed in CodeBuild while still keeping a CUDA-capable host runtime on g4dn.
# - COLMAP install: apt package is used for deterministic, fast CI builds and lower
#   build cost; GPU acceleration is enabled at runtime via COLMAP flags.
# - Vocabulary tree: downloaded lazily at runtime to keep image size smaller and avoid
#   brittle build-time external fetches.

FROM public.ecr.aws/docker/library/ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    colmap \
    curl \
    python3 \
    python3-pip \
    python3-setuptools \
    python3-wheel \
    unzip \
    && rm -rf /var/lib/apt/lists/*

RUN mkdir -p /opt/ml/code /opt/ml/processing/input /opt/ml/processing/output /opt/colmap/vocab

COPY requirements.txt /opt/ml/code/requirements.txt
RUN python3 -m pip install --no-cache-dir -r /opt/ml/code/requirements.txt

COPY run_sfm.sh /opt/ml/code/run_sfm.sh
COPY run_colmap_sfm.py /opt/ml/code/run_colmap_sfm.py
RUN chmod +x /opt/ml/code/run_sfm.sh

WORKDIR /opt/ml/code
ENTRYPOINT ["/opt/ml/code/run_sfm.sh"]
