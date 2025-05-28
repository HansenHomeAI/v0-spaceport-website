# SfM Processing Container with COLMAP
FROM colmap/colmap:latest

# Install Python and dependencies
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
RUN pip3 install boto3 opencv-python-headless pillow

# Create working directories
RUN mkdir -p /opt/ml/code /opt/ml/processing/input /opt/ml/processing/output

# Copy processing scripts
COPY run_sfm_fast.sh /opt/ml/code/
COPY process_sfm.py /opt/ml/code/

# Make scripts executable
RUN chmod +x /opt/ml/code/run_sfm_fast.sh /opt/ml/code/process_sfm.py

# Set working directory
WORKDIR /opt/ml/code

# Use Python script as entrypoint for S3 integration
ENTRYPOINT ["/opt/ml/code/process_sfm.py"] 