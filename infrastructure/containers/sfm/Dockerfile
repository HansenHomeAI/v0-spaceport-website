# COLMAP GPU SfM container for SageMaker processing jobs.
# Non-obvious choices:
# - CUDA 12.3 + Ubuntu 22.04 works with T4 on ml.g4dn.xlarge.
# - COLMAP is compiled from source with CUDA so GPU SIFT/matching are guaranteed.
# - The official 100K/32K vocabulary tree is bundled at build-time for deterministic runtime behavior.

FROM nvidia/cuda:12.3.2-devel-ubuntu22.04

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1 \
    COLMAP_VOCAB_TREE=/opt/ml/code/vocab_tree_flickr100K_words32K.bin

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential cmake ninja-build git wget curl ca-certificates \
    libboost-program-options-dev libboost-filesystem-dev libboost-graph-dev \
    libboost-system-dev libboost-test-dev libeigen3-dev libsuitesparse-dev \
    libfreeimage-dev libmetis-dev libgoogle-glog-dev libgflags-dev \
    libsqlite3-dev libglew-dev qtbase5-dev libqt5opengl5-dev libcgal-dev \
    python3 python3-pip python3-dev python3-setuptools python3-wheel \
    && rm -rf /var/lib/apt/lists/*

RUN git clone --depth 1 https://github.com/colmap/colmap.git /opt/colmap && \
    cmake -S /opt/colmap -B /opt/colmap/build -GNinja \
      -DCMAKE_BUILD_TYPE=Release \
      -DCUDA_ENABLED=ON \
      -DGUI_ENABLED=OFF && \
    cmake --build /opt/colmap/build && \
    cmake --install /opt/colmap/build && \
    rm -rf /opt/colmap

COPY requirements.txt /tmp/requirements.txt
RUN python3 -m pip install --no-cache-dir --upgrade pip && \
    python3 -m pip install --no-cache-dir -r /tmp/requirements.txt && \
    rm -f /tmp/requirements.txt

WORKDIR /opt/ml/code
COPY run_sfm.sh /opt/ml/code/run_sfm.sh
COPY run_colmap_gps.py /opt/ml/code/run_colmap_gps.py

RUN chmod +x /opt/ml/code/run_sfm.sh /opt/ml/code/run_colmap_gps.py && \
    wget -O /opt/ml/code/vocab_tree_flickr100K_words32K.bin \
      https://demuc.de/colmap/vocab_tree_flickr100K_words32K.bin

ENTRYPOINT ["/opt/ml/code/run_sfm.sh"]
