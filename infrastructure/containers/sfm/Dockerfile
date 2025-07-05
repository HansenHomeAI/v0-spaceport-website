# Production OpenSfM Container with GPS-Constrained Reconstruction - Multi-Stage Build
# Optimized for layer caching and build efficiency

# Stage 1: Base system with dependencies
FROM python:3.9-slim AS base

# Set environment to avoid interactive prompts
ENV DEBIAN_FRONTEND=noninteractive

# Install system dependencies for OpenSfM and GPS processing (cached layer)
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        build-essential \
        cmake \
        git \
        wget \
        curl \
        unzip \
        ca-certificates \
        pkg-config \
        libeigen3-dev \
        libopencv-dev \
        libceres-dev \
        libgoogle-glog-dev \
        libgflags-dev \
        libatlas-base-dev \
        libsuitesparse-dev \
        libproj-dev \
        libgdal-dev \
        python3-dev \
        libboost-all-dev \
        libyaml-dev \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Stage 2: Python dependencies
FROM base AS python-deps

# Create working directories
RUN mkdir -p /opt/ml/code /opt/ml/processing/input /opt/ml/processing/output

# Copy requirements first for better caching
COPY requirements.txt /opt/ml/code/

# Install Python dependencies together to ensure numpy<2.0 constraint
RUN pip3 install --no-cache-dir -r /opt/ml/code/requirements.txt \
    && pip3 install --no-cache-dir sphinx==4.5.0 \
    && pip3 cache purge \
    && rm -rf ~/.cache/pip

# Stage 3: OpenSfM build
FROM python-deps AS opensfm-build

# Clone and build OpenSfM with proper submodule initialization
RUN cd /opt && \
    git clone --depth 1 https://github.com/mapillary/OpenSfM.git && \
    cd OpenSfM && \
    git submodule update --init --recursive && \
    python3 setup.py build && \
    python3 setup.py install && \
    rm -rf /opt/OpenSfM/.git

# Stage 4: Application code
FROM opensfm-build AS app-build

# Copy processing scripts (most frequently changed)
COPY run_sfm.sh /opt/ml/code/run_sfm.sh
COPY run_opensfm_gps.py /opt/ml/code/run_opensfm_gps.py
COPY gps_processor.py /opt/ml/code/gps_processor.py
COPY gps_processor_3d.py /opt/ml/code/gps_processor_3d.py
COPY colmap_converter.py /opt/ml/code/colmap_converter.py
COPY config_template.yaml /opt/ml/code/config_template.yaml

# Make scripts executable
RUN chmod +x /opt/ml/code/run_sfm.sh \
    && chmod +x /opt/ml/code/run_opensfm_gps.py

# Stage 5: Final runtime image
FROM app-build AS runtime

# Create non-root user for security
RUN useradd --create-home --shell /bin/bash sagemaker \
    && chown -R sagemaker:sagemaker /opt/ml

# Set working directory
WORKDIR /opt/ml/code

# Add OpenSfM to PATH and PYTHONPATH
ENV PATH="/opt/OpenSfM/bin:${PATH}"
ENV PYTHONPATH="/opt/OpenSfM"

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python3 -c "import opensfm; print('OpenSfM available')" || exit 1

# Switch to non-root user
USER sagemaker

# Use the expected script name as the entrypoint
ENTRYPOINT ["/opt/ml/code/run_sfm.sh"] 