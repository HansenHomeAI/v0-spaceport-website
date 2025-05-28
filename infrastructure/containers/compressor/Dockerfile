# Model Compression Container
FROM python:3.9-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /opt/ml

# Install Python dependencies
COPY requirements.txt .
RUN pip install -r requirements.txt

# Copy compression script
COPY compress_model.py .
COPY *.sh .
RUN chmod +x *.sh

# Set entrypoint
ENTRYPOINT ["/opt/ml/compress_model.py"] 