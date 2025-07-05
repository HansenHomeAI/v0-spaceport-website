# Production OpenSfM Container with GPS-Constrained Reconstruction
# Replaces COLMAP with OpenSfM for enhanced accuracy using drone flight path data
# Updated: 2025-01-27
# Build optimization: Multi-stage build for better caching

FROM python:3.9-slim as base

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

# Dependencies stage - changes less frequently, better for caching
FROM base as dependencies

# Copy requirements and install Python dependencies
# CRITICAL: Install all dependencies together to ensure numpy<2.0 constraint is respected
COPY requirements.txt /opt/ml/code/
RUN pip3 install --no-cache-dir -r /opt/ml/code/requirements.txt && \
    pip3 install --no-cache-dir sphinx==4.5.0

# Clone and build OpenSfM with proper submodule initialization
# NOTE: v0.6.0 does not exist upstream, build fails. Use the default "main" branch (latest stable) instead.
RUN cd /opt && \
    git clone --depth 1 https://github.com/mapillary/OpenSfM.git && \
    cd OpenSfM && \
    git submodule update --init --recursive && \
    python3 setup.py build && \
    python3 setup.py install

# Final stage - application code that changes more frequently
FROM dependencies as final

# Copy processing scripts
COPY run_sfm.sh /opt/ml/code/run_sfm.sh
COPY run_opensfm_gps.py /opt/ml/code/run_opensfm_gps.py
COPY gps_processor.py /opt/ml/code/gps_processor.py
COPY gps_processor_3d.py /opt/ml/code/gps_processor_3d.py
COPY colmap_converter.py /opt/ml/code/colmap_converter.py
COPY config_template.yaml /opt/ml/code/config_template.yaml

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