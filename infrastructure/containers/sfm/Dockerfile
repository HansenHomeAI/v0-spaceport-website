# COLMAP GPU SfM container for SageMaker Processing.
#
# Non-obvious choices:
# - Base image: CUDA 11.8 + Ubuntu 22.04 keeps compatibility with g4dn (T4) while
#   using a modern compiler toolchain that COLMAP builds cleanly with.
# - Build flags: COLMAP is compiled with CUDA enabled (CUDA arch 75 for T4).
#   extraction/matching is available at runtime.
# - Vocabulary tree: we pre-create /opt/colmap/vocab and allow runtime download fallback
#   from the official COLMAP host to avoid brittle build-time network coupling.

FROM public.ecr.aws/nvidia/cuda:11.8.0-cudnn8-devel-ubuntu22.04

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    ca-certificates \
    cmake \
    curl \
    git \
    libboost-filesystem-dev \
    libboost-graph-dev \
    libboost-program-options-dev \
    libboost-system-dev \
    libeigen3-dev \
    libflann-dev \
    libfreeimage-dev \
    libgoogle-glog-dev \
    libgtest-dev \
    libmetis-dev \
    libsqlite3-dev \
    libglew-dev \
    libqt5opengl5-dev \
    libcgal-dev \
    libceres-dev \
    ninja-build \
    python3 \
    python3-pip \
    python3-setuptools \
    python3-wheel \
    wget \
    unzip \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /opt
RUN git clone --branch 3.10 --depth 1 https://github.com/colmap/colmap.git

WORKDIR /opt/colmap
RUN cmake -S . -B build -GNinja \
    -DCMAKE_BUILD_TYPE=Release \
    -DCUDA_ENABLED=ON \
    -DCMAKE_CUDA_ARCHITECTURES=75 \
    && cmake --build build -j"$(nproc)" \
    && cmake --install build

RUN mkdir -p /opt/ml/code /opt/ml/processing/input /opt/ml/processing/output /opt/colmap/vocab

COPY requirements.txt /opt/ml/code/requirements.txt
RUN python3 -m pip install --no-cache-dir -r /opt/ml/code/requirements.txt

COPY run_sfm.sh /opt/ml/code/run_sfm.sh
COPY run_colmap_sfm.py /opt/ml/code/run_colmap_sfm.py
RUN chmod +x /opt/ml/code/run_sfm.sh

WORKDIR /opt/ml/code
ENTRYPOINT ["/opt/ml/code/run_sfm.sh"]
