# SfM Processing Container with COLMAP
FROM ubuntu:20.04

# Avoid interactive prompts during build
ENV DEBIAN_FRONTEND=noninteractive

# Install system dependencies
RUN apt-get update && apt-get install -y \
    cmake \
    build-essential \
    libboost-program-options-dev \
    libboost-filesystem-dev \
    libboost-graph-dev \
    libboost-system-dev \
    libboost-test-dev \
    libeigen3-dev \
    libsuitesparse-dev \
    libfreeimage-dev \
    libmetis-dev \
    libgoogle-glog-dev \
    libgflags-dev \
    libglew-dev \
    qtbase5-dev \
    libqt5opengl5-dev \
    libcgal-dev \
    libceres-dev \
    python3 \
    python3-pip \
    wget \
    unzip \
    && rm -rf /var/lib/apt/lists/*

# Install COLMAP
RUN wget https://github.com/colmap/colmap/archive/refs/tags/3.7.tar.gz \
    && tar -xzf 3.7.tar.gz \
    && cd colmap-3.7 \
    && mkdir build \
    && cd build \
    && cmake .. -DCMAKE_BUILD_TYPE=Release \
    && make -j$(nproc) \
    && make install \
    && cd ../.. \
    && rm -rf colmap-3.7 3.7.tar.gz

# Install Python dependencies
RUN pip3 install boto3 opencv-python-headless pillow

# Create working directories
RUN mkdir -p /opt/ml/code /opt/ml/processing/input /opt/ml/processing/output

# Copy processing script
COPY run_sfm.sh /opt/ml/code/
COPY process_sfm.py /opt/ml/code/

# Make scripts executable
RUN chmod +x /opt/ml/code/run_sfm.sh

# Set working directory
WORKDIR /opt/ml/code

# Default command
CMD ["/opt/ml/code/run_sfm.sh"] 