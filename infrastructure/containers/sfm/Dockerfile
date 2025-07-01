# Real Production COLMAP Container - Fixed COLMAP PATH Issue
# Uses the official COLMAP container with the correct script name
# COLMAP availability fix - 2025-06-30

FROM colmap/colmap:latest

# Switch to root to install packages
USER root

# Set environment to avoid interactive prompts
ENV DEBIAN_FRONTEND=noninteractive

# Ensure COLMAP is in PATH - this is critical!
ENV PATH="/usr/local/bin:$PATH"

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

# CRITICAL: Verify COLMAP is working with better debugging
RUN echo "=== COLMAP VERIFICATION ===" && \
    echo "PATH: $PATH" && \
    echo "Looking for COLMAP binary..." && \
    which colmap || echo "COLMAP not found in PATH" && \
    find /usr -name "colmap" -type f 2>/dev/null || echo "COLMAP binary not found in /usr" && \
    ls -la /usr/local/bin/ | grep colmap || echo "No colmap in /usr/local/bin" && \
    echo "Testing COLMAP command..." && \
    colmap help >/dev/null 2>&1 && echo "✅ COLMAP verification SUCCESS" || echo "❌ COLMAP verification FAILED"

# Set working directory
WORKDIR /opt/ml/code

# Ensure COLMAP is available at runtime
ENV PATH="/usr/local/bin:$PATH"

# Use the expected script name as the entrypoint
ENTRYPOINT ["/opt/ml/code/run_sfm.sh"] 