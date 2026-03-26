ARG UBUNTU_IMAGE=public.ecr.aws/lts/ubuntu:22.04
FROM ${UBUNTU_IMAGE}

ARG COLMAP_VERSION=3.12.6
ARG CUDA_APT_KEYRING=cuda-keyring_1.1-1_all.deb

# Base image choice: AWS Public ECR avoids Docker Hub rate limits in CodeBuild.
# COLMAP is pinned to 3.12.6 so the GPU matcher stack stays on a recent bug-fix
# release while remaining reproducible. We compile for CUDA SM 7.5 because the
# target SageMaker host is ml.g4dn.xlarge (T4 GPU), which reduces build time and
# keeps the binary focused on the instance we are actually paying for.
# The vocab tree stays external so we do not bake a 300MB+ artifact into ECR;
# runtime downloads the official FAISS tree once and caches it in the image path.
ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1 \
    PIP_BREAK_SYSTEM_PACKAGES=1 \
    NVIDIA_VISIBLE_DEVICES=all \
    NVIDIA_DRIVER_CAPABILITIES=compute,utility \
    CUDA_HOME=/usr/local/cuda \
    PATH=/usr/local/cuda/bin:${PATH} \
    LD_LIBRARY_PATH=/usr/local/cuda/lib64:${LD_LIBRARY_PATH} \
    CC=/usr/bin/gcc-10 \
    CXX=/usr/bin/g++-10 \
    CUDAHOSTCXX=/usr/bin/g++-10 \
    COLMAP_VOCAB_TREE_URL=https://github.com/colmap/colmap/releases/download/3.11.1/vocab_tree_faiss_flickr100K_words256K.bin \
    COLMAP_VOCAB_TREE_PATH=/opt/ml/code/resources/vocab_tree_faiss_flickr100K_words256K.bin

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        ca-certificates \
        curl \
        g++-10 \
        gcc-10 \
        gnupg2 \
        wget && \
    wget -q https://developer.download.nvidia.com/compute/cuda/repos/ubuntu2204/x86_64/${CUDA_APT_KEYRING} && \
    dpkg -i ${CUDA_APT_KEYRING} && \
    rm -f ${CUDA_APT_KEYRING} && \
    apt-get update && \
    apt-get install -y --no-install-recommends \
        build-essential \
        ccache \
        cmake \
        cuda-toolkit-12-4 \
        curl \
        libboost-filesystem-dev \
        libboost-graph-dev \
        libboost-program-options-dev \
        libboost-system-dev \
        libceres-dev \
        libcgal-dev \
        libcurl4-openssl-dev \
        libeigen3-dev \
        libflann-dev \
        libfreeimage-dev \
        libglew-dev \
        libgoogle-glog-dev \
        libgmock-dev \
        libgtest-dev \
        libimage-exiftool-perl \
        liblz4-dev \
        libmetis-dev \
        libopenblas-dev \
        libopenimageio-dev \
        libsqlite3-dev \
        libsuitesparse-dev \
        libssl-dev \
        ninja-build \
        openimageio-tools \
        python-is-python3 \
        python3 \
        python3-pip \
        python3-venv \
        sqlite3 \
        unzip \
    && mkdir -p /usr/include/opencv4 \
    && rm -rf /var/lib/apt/lists/*

RUN curl -fsSL https://github.com/colmap/colmap/archive/refs/tags/${COLMAP_VERSION}.tar.gz -o /tmp/colmap.tar.gz && \
    mkdir -p /tmp/colmap && \
    tar -xzf /tmp/colmap.tar.gz -C /tmp/colmap --strip-components=1 && \
    cmake -S /tmp/colmap -B /tmp/colmap/build -GNinja \
        -DCMAKE_BUILD_TYPE=Release \
        -DCMAKE_INSTALL_PREFIX=/usr/local \
        -DCMAKE_CUDA_ARCHITECTURES=75 \
        -DBLA_VENDOR=OpenBLAS \
        -DGUI_ENABLED=OFF \
        -DTESTS_ENABLED=OFF && \
    cmake --build /tmp/colmap/build --target install --parallel 4 && \
    rm -rf /tmp/colmap /tmp/colmap.tar.gz

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
