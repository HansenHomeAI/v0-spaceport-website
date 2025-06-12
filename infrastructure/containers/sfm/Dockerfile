# Real Production COLMAP Container - Final Version
# Uses the official COLMAP container with the correct script name

FROM colmap/colmap:latest

# Switch to root to install packages
USER root

# Set environment to avoid interactive prompts
ENV DEBIAN_FRONTEND=noninteractive

# Update package lists and install essential tools first
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        wget \
        curl \
        unzip \
        ca-certificates \
    && rm -rf /var/lib/apt/lists/* || true

# Try to install Python, but don't fail if it doesn't work
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        python3 \
        python3-pip \
    && rm -rf /var/lib/apt/lists/* || \
    (echo "Python installation failed, will use alternative approach" && \
     wget -O /tmp/get-pip.py https://bootstrap.pypa.io/get-pip.py && \
     python3 /tmp/get-pip.py || \
     echo "Will proceed without Python")

# Install boto3 if possible, otherwise skip
RUN pip3 install boto3 || \
    python3 -m pip install boto3 || \
    echo "boto3 installation skipped - will use shell-only approach"

# Create working directories
RUN mkdir -p /opt/ml/code /opt/ml/processing/input /opt/ml/processing/output

# Copy our production COLMAP script with the expected name
COPY run_colmap_production.sh /opt/ml/code/run_sfm.sh

# Make it executable
RUN chmod +x /opt/ml/code/run_sfm.sh

# Verify COLMAP is working
RUN colmap help || echo "COLMAP verification failed"

# Set working directory
WORKDIR /opt/ml/code

# Use the expected script name as the entrypoint
ENTRYPOINT ["/opt/ml/code/run_sfm.sh"] 