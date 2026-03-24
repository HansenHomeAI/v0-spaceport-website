# Production COLMAP SfM Container for Large DJI Landscapes

FROM colmap/colmap:latest

ENV DEBIAN_FRONTEND=noninteractive \
    PIP_BREAK_SYSTEM_PACKAGES=1 \
    PYTHONUNBUFFERED=1

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        python3 \
        python3-pip \
        python3-venv \
        python-is-python3 \
        libimage-exiftool-perl \
        sqlite3 \
        ca-certificates \
    && rm -rf /var/lib/apt/lists/*

RUN mkdir -p /opt/ml/code /opt/ml/processing/input /opt/ml/processing/output

COPY requirements.txt /opt/ml/code/requirements.txt
RUN python3 -m pip install --no-cache-dir -r /opt/ml/code/requirements.txt

COPY run_sfm.sh /opt/ml/code/run_sfm.sh
COPY run_colmap_hybrid.py /opt/ml/code/run_colmap_hybrid.py
COPY run_opensfm_gps.py /opt/ml/code/run_opensfm_gps.py
COPY exif_manifest.py /opt/ml/code/exif_manifest.py
COPY segmenter.py /opt/ml/code/segmenter.py
COPY colmap_runner.py /opt/ml/code/colmap_runner.py
COPY model_merge.py /opt/ml/code/model_merge.py
COPY model_analyzer.py /opt/ml/code/model_analyzer.py
COPY cost_estimator.py /opt/ml/code/cost_estimator.py
COPY sfm_scaling.py /opt/ml/code/sfm_scaling.py

RUN chmod +x /opt/ml/code/run_sfm.sh /opt/ml/code/run_colmap_hybrid.py /opt/ml/code/run_opensfm_gps.py && \
    mkdir -p /opt/ml/processing/output/sparse /opt/ml/processing/output/dense && \
    chmod -R 755 /opt/ml/processing/output

WORKDIR /opt/ml/code

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python3 -c "import exif_manifest, segmenter, colmap_runner; print('COLMAP hybrid ready')" || exit 1

ENTRYPOINT ["/opt/ml/code/run_sfm.sh"]
