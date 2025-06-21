# Production SFM (COLMAP) Container
# Optimized for AWS SageMaker Processing Jobs

FROM colmap/colmap:latest

# Switch to root to install packages
USER root

# Prevent interactive prompts
ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1
ENV ENVIRONMENT=production
ENV PYTHONPATH=/opt/ml/code

# Install system dependencies
RUN for i in 1 2 3; do \
    echo "🛠️  Attempt $i: Installing system dependencies..." && \
    apt-get update --fix-missing && \
    apt-get install -y --no-install-recommends \
        python3 \
        python3-pip \
        python3-venv \
        unzip \
        ca-certificates && \
    rm -rf /var/lib/apt/lists/* && \
    apt-get clean && \
    break || echo "⚠️  apt-get failed, retrying in 30s..." && sleep 30; \
  done

# Create and use a Python virtual environment
RUN python3 -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Upgrade pip and install AWS SDK
RUN pip install --no-cache-dir --upgrade pip
RUN pip install --no-cache-dir boto3

# Create SageMaker directory structure
RUN mkdir -p /opt/ml/code /opt/ml/processing/input /opt/ml/processing/output

# Set working directory
WORKDIR /opt/ml/code

# Copy processing script
COPY process.py /opt/ml/code/process.py
RUN chmod +x /opt/ml/code/process.py

# Create entrypoint script for SageMaker
RUN echo '#!/bin/bash\n\
set -e\n\
\n\
echo "🚀 Starting Production SFM (COLMAP) Container"\n\
echo "Environment: $ENVIRONMENT"\n\
echo "Verifying installations..."\n\
python3 --version \n\
colmap help > /dev/null || (echo "COLMAP command not found!" && exit 1)\n\
echo "COLMAP OK"\n\
\n\
echo "Input Data:"\n\
ls -la /opt/ml/processing/input/ || echo "No input data directory"\n\
\n\
echo "Starting processing..."\n\
python3 process.py\n\
\n\
echo "Processing completed! Output files:"\n\
ls -la /opt/ml/processing/output/\n\
' > /opt/ml/code/entrypoint.sh

RUN chmod +x /opt/ml/code/entrypoint.sh

# Set proper permissions for SageMaker
RUN chmod -R 755 /opt/ml/

# Final environment setup
ENV SAGEMAKER_PROGRAM=process.py
ENV SAGEMAKER_SUBMIT_DIRECTORY=/opt/ml/code

# Use production entrypoint
ENTRYPOINT ["/opt/ml/code/entrypoint.sh"] 