# Production COLMAP SfM Container for Large DJI Landscapes

ARG UBUNTU_IMAGE=public.ecr.aws/docker/library/ubuntu:24.04
FROM ${UBUNTU_IMAGE}

ARG COLMAP_GIT_SHA=83cb454fd2016687b5db313dc08370bf2137b08e

ENV DEBIAN_FRONTEND=noninteractive \
    PIP_BREAK_SYSTEM_PACKAGES=1 \
    PYTHONUNBUFFERED=1

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        ca-certificates \
        curl \
        python3 \
        python3-pip \
        python3-venv \
        python-is-python3 \
        libimage-exiftool-perl \
        sqlite3 \
        ccache \
        cmake \
        ninja-build \
        build-essential \
        pkg-config \
        libboost-program-options-dev \
        libboost-graph-dev \
        libboost-system-dev \
        libeigen3-dev \
        libopenimageio-dev \
        openimageio-tools \
        libmetis-dev \
        libgoogle-glog-dev \
        libgtest-dev \
        libgmock-dev \
        libsqlite3-dev \
        libglew-dev \
        libcgal-dev \
        libceres-dev \
        libsuitesparse-dev \
        libcurl4-openssl-dev \
        libssl-dev \
        libopenblas-dev \
    && mkdir -p /usr/include/opencv4 \
    && rm -rf /var/lib/apt/lists/*

RUN curl -fsSL "https://github.com/colmap/colmap/archive/${COLMAP_GIT_SHA}.tar.gz" -o /tmp/colmap.tar.gz && \
    mkdir -p /tmp/colmap && \
    tar -xzf /tmp/colmap.tar.gz -C /tmp/colmap --strip-components=1 && \
    cd /tmp/colmap && \
    cmake -S . -B build -GNinja \
        -DCMAKE_BUILD_TYPE=Release \
        -DCMAKE_INSTALL_PREFIX=/usr/local \
        -DBLA_VENDOR=OpenBLAS \
        -DGUI_ENABLED=OFF \
        -DTESTS_ENABLED=OFF \
        -DCUDA_ENABLED=OFF && \
    cmake --build build --target install --parallel 2 && \
    rm -rf /tmp/colmap /tmp/colmap.tar.gz

RUN mkdir -p /opt/ml/code /opt/ml/processing/input /opt/ml/processing/output

COPY requirements.txt /opt/ml/code/requirements.txt
RUN python3 -m pip install --no-cache-dir -r /opt/ml/code/requirements.txt

COPY run_sfm.sh /opt/ml/code/run_sfm.sh
COPY run_colmap_hybrid.py /opt/ml/code/run_colmap_hybrid.py
COPY run_opensfm_gps.py /opt/ml/code/run_opensfm_gps.py
COPY exif_manifest.py /opt/ml/code/exif_manifest.py
COPY segmenter.py /opt/ml/code/segmenter.py
COPY colmap_runner.py /opt/ml/code/colmap_runner.py
COPY model_merge.py /opt/ml/code/model_merge.py
COPY model_analyzer.py /opt/ml/code/model_analyzer.py
COPY cost_estimator.py /opt/ml/code/cost_estimator.py
COPY sfm_scaling.py /opt/ml/code/sfm_scaling.py

RUN chmod +x /opt/ml/code/run_sfm.sh /opt/ml/code/run_colmap_hybrid.py /opt/ml/code/run_opensfm_gps.py && \
    mkdir -p /opt/ml/processing/output/sparse /opt/ml/processing/output/dense && \
    chmod -R 755 /opt/ml/processing/output

WORKDIR /opt/ml/code

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python3 -c "import exif_manifest, segmenter, colmap_runner; print('COLMAP hybrid ready')" || exit 1

ENTRYPOINT ["/opt/ml/code/run_sfm.sh"]
