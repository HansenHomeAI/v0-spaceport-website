# Production OpenSfM Container with GPS-Constrained Reconstruction
# Replaces COLMAP with OpenSfM for enhanced accuracy using drone flight path data
# Updated: 2025-01-27

FROM python:3.9-slim

# Switch to root for installation
USER root

# Set environment to avoid interactive prompts
ENV DEBIAN_FRONTEND=noninteractive

# Install system dependencies for OpenSfM and GPS processing
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
        python3-pip \
        libboost-all-dev \
        libyaml-dev \
    && rm -rf /var/lib/apt/lists/*

# Create working directories
RUN mkdir -p /opt/ml/code /opt/ml/processing/input /opt/ml/processing/output

# Install Python dependencies for OpenSfM and GPS processing
# Install numpy early to satisfy many builds, but avoid duplicate install later
RUN pip3 install --no-cache-dir numpy==1.21.6

# Copy and install the remaining Python dependencies (excluding the already-installed numpy)
COPY requirements.txt /opt/ml/code/
# Remove numpy from requirements to prevent version conflicts
RUN grep -v "^numpy" /opt/ml/code/requirements.txt > /opt/ml/code/requirements_wo_numpy.txt && \
    pip3 install --no-cache-dir -r /opt/ml/code/requirements_wo_numpy.txt

# Clone and build OpenSfM with proper submodule initialization
# NOTE: v0.6.0 does not exist upstream, build fails. Use the default "main" branch (latest stable) instead.
RUN cd /opt && \
    git clone --depth 1 https://github.com/mapillary/OpenSfM.git && \
    cd OpenSfM && \
    git submodule update --init --recursive && \
    sed -i '/from sphinx.setup_command import BuildDoc/d' setup.py && \
    sed -i '/sphinx/d' setup.py && \
    python3 setup.py build && \
    python3 setup.py install

# Copy our production OpenSfM scripts
COPY run_opensfm_gps.py /opt/ml/code/
COPY run_sfm.sh /opt/ml/code/
COPY gps_processor.py /opt/ml/code/
COPY colmap_converter.py /opt/ml/code/
COPY config_template.yaml /opt/ml/code/

# Make scripts executable
RUN chmod +x /opt/ml/code/run_sfm.sh
RUN chmod +x /opt/ml/code/run_opensfm_gps.py

# Set working directory
WORKDIR /opt/ml/code

# Add OpenSfM to PATH and PYTHONPATH
ENV PATH="/opt/OpenSfM/bin:${PATH}"
ENV PYTHONPATH="/opt/OpenSfM"

# Use the expected script name as the entrypoint
ENTRYPOINT ["/opt/ml/code/run_sfm.sh"] 