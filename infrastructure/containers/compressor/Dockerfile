# Model Compression Container
FROM python:3.9-slim

# Set working directory
WORKDIR /opt/ml

# Install Python dependencies
COPY requirements.txt .
RUN pip install -r requirements.txt

# Copy compression script
COPY compress_model.py .
RUN chmod +x compress_model.py

# Set entrypoint
ENTRYPOINT ["python", "/opt/ml/compress_model.py"] 