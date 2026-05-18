# Official CUDA-enabled COLMAP runtime, pinned to a dated tag so rebuilds stay
# reproducible and never depend on the mutable spaceport/sfm:latest tag.
FROM colmap/colmap:20260318.6455 AS runtime

# Leave the vocab tree URL empty by default so COLMAP 4 can use its own
# FAISS-compatible runtime tree path; the runtime script still accepts an
# explicit URL override and falls back to building a reduced local FAISS index
# from the extracted descriptors when the external/runtime path fails.
# GPU SIFT/matching flags stay in the runtime script so the same image can still
# be probed on CPU-only hosts by setting COLMAP_USE_GPU=0, while ml.g4dn.xlarge
# runs on CUDA by default.
ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1 \
    PIP_BREAK_SYSTEM_PACKAGES=1 \
    COLMAP_VOCAB_TREE_URL= \
    COLMAP_VOCAB_TREE_PATH=/opt/ml/code/resources/vocab_tree_flickr100K_words256K.bin

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        ca-certificates \
        curl \
        libimage-exiftool-perl \
        python3 \
        python3-pip \
        python3-venv \
        python-is-python3 \
        sqlite3 \
        unzip \
    && rm -rf /var/lib/apt/lists/*

RUN mkdir -p /opt/ml/code /opt/ml/code/resources /opt/ml/processing/input /opt/ml/processing/output

COPY requirements.txt /opt/ml/code/requirements.txt
RUN python3 -m pip install --no-cache-dir -r /opt/ml/code/requirements.txt

COPY run_sfm.sh /opt/ml/code/run_sfm.sh
COPY run_colmap_sfm.py /opt/ml/code/run_colmap_sfm.py

RUN chmod +x /opt/ml/code/run_sfm.sh /opt/ml/code/run_colmap_sfm.py && \
    mkdir -p /opt/ml/processing/output/sparse /opt/ml/processing/output/dense && \
    chmod -R 755 /opt/ml/processing/output

WORKDIR /opt/ml/code

FROM scratch

COPY --from=runtime / /

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1 \
    PIP_BREAK_SYSTEM_PACKAGES=1 \
    COLMAP_VOCAB_TREE_URL= \
    COLMAP_VOCAB_TREE_PATH=/opt/ml/code/resources/vocab_tree_flickr100K_words256K.bin

WORKDIR /opt/ml/code

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD colmap help >/dev/null 2>&1 && python3 --version >/dev/null 2>&1 || exit 1

ENTRYPOINT ["/opt/ml/code/run_sfm.sh"]
