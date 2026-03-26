# Build from AWS Public ECR Ubuntu instead of Docker Hub's prebuilt COLMAP
# image, because CodeBuild hits Docker Hub pull-rate limits on unattended CI.
FROM public.ecr.aws/lts/ubuntu:22.04

# Pin the COLMAP release and compile only T4-compatible CUDA kernels so CI
# rebuilds stay reproducible and the CodeBuild compile time remains reasonable
# for ml.g4dn.xlarge runtime targets.
ARG COLMAP_VERSION=4.0.2

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1 \
    PIP_BREAK_SYSTEM_PACKAGES=1 \
    NVIDIA_VISIBLE_DEVICES=all \
    NVIDIA_DRIVER_CAPABILITIES=compute,utility \
    CUDA_HOME=/usr/local/cuda \
    PATH=/usr/local/cuda/bin:${PATH} \
    LD_LIBRARY_PATH=/usr/local/cuda/lib64:${LD_LIBRARY_PATH} \
    COLMAP_VOCAB_TREE_PATH=/opt/ml/code/resources/colmap_vocab_tree.faiss \
    CC=/usr/bin/gcc-10 \
    CXX=/usr/bin/g++-10 \
    CUDAHOSTCXX=/usr/bin/g++-10

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        ca-certificates \
        curl \
        gnupg2 \
        wget && \
    wget https://developer.download.nvidia.com/compute/cuda/repos/ubuntu2204/x86_64/cuda-keyring_1.1-1_all.deb && \
    dpkg -i cuda-keyring_1.1-1_all.deb && \
    rm cuda-keyring_1.1-1_all.deb && \
    apt-get update && \
    apt-get install -y --no-install-recommends \
        build-essential \
        cmake \
        gcc-10 \
        g++-10 \
        ninja-build \
        cuda-toolkit-12-4 \
        libboost-program-options-dev \
        libboost-graph-dev \
        libboost-system-dev \
        libcgal-dev \
        libceres-dev \
        libcurl4-openssl-dev \
        libeigen3-dev \
        libflann-dev \
        libfreeimage-dev \
        libglew-dev \
        libgoogle-glog-dev \
        libgmock-dev \
        libgtest-dev \
        libimage-exiftool-perl \
        libmetis-dev \
        libopenblas-dev \
        libopenimageio-dev \
        libopenexr-dev \
        libsqlite3-dev \
        libssl-dev \
        python-is-python3 \
        python3 \
        python3-pip \
        python3-venv \
        sqlite3 \
        unzip && \
    rm -rf /var/lib/apt/lists/*

RUN mkdir -p /tmp/colmap-src && \
    curl -fsSL "https://github.com/colmap/colmap/archive/refs/tags/${COLMAP_VERSION}.tar.gz" | tar -xz --strip-components=1 -C /tmp/colmap-src && \
    cmake -S /tmp/colmap-src -B /tmp/colmap-build \
        -GNinja \
        -DCMAKE_BUILD_TYPE=Release \
        -DCMAKE_INSTALL_PREFIX=/usr/local \
        -DCMAKE_CUDA_ARCHITECTURES=75 \
        -DCUDA_ENABLED=ON \
        -DGUI_ENABLED=OFF \
        -DOPENGL_ENABLED=OFF \
        -DTESTS_ENABLED=OFF \
        -DBLA_VENDOR=OpenBLAS && \
    cmake --build /tmp/colmap-build --parallel "$(nproc)" && \
    cmake --install /tmp/colmap-build && \
    rm -rf /tmp/colmap-src /tmp/colmap-build

RUN mkdir -p /opt/ml/code /opt/ml/code/resources /opt/ml/processing/input /opt/ml/processing/output

COPY requirements.txt /opt/ml/code/requirements.txt
RUN python3 -m pip install --no-cache-dir -r /opt/ml/code/requirements.txt

COPY run_sfm.sh /opt/ml/code/run_sfm.sh
COPY run_colmap_sfm.py /opt/ml/code/run_colmap_sfm.py

RUN chmod +x /opt/ml/code/run_sfm.sh /opt/ml/code/run_colmap_sfm.py && \
    mkdir -p /opt/ml/processing/output/sparse /opt/ml/processing/output/dense && \
    chmod -R 755 /opt/ml/processing/output

WORKDIR /opt/ml/code

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD colmap help >/dev/null 2>&1 && python3 --version >/dev/null 2>&1 || exit 1

ENTRYPOINT ["/opt/ml/code/run_sfm.sh"]
