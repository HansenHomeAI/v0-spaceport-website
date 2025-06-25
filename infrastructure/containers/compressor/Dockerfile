# Production Model Compression Container
# Test build trigger - IAM permissions fix verification
FROM python:3.9-slim

WORKDIR /opt/ml/code

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the production compression script
COPY compress.py .
RUN chmod +x compress.py

# Set the entrypoint to our production script
ENTRYPOINT ["python", "/opt/ml/code/compress.py"] 