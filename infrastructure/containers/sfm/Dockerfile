# COLMAP GPU SfM container for SageMaker Processing.
#
# Non-obvious choices:
# - Base image: supplied by CI as an internal ECR `:base` image, which avoids external
#   registry rate limits and keeps CUDA/compiler dependencies stable between builds.
# - Build flags: COLMAP is compiled with CUDA enabled so GPU SIFT
#   extraction/matching is available at runtime.
# - Vocabulary tree: we pre-create /opt/colmap/vocab and allow runtime download fallback
#   from the official COLMAP host to avoid brittle build-time network coupling.

ARG BASE_IMAGE=public.ecr.aws/nvidia/cuda:11.8.0-devel-ubuntu22.04
FROM ${BASE_IMAGE}

WORKDIR /opt
RUN git clone --branch 3.10 --depth 1 https://github.com/colmap/colmap.git

WORKDIR /opt/colmap
RUN cmake -S . -B build -GNinja \
    -DCMAKE_BUILD_TYPE=Release \
    -DCUDA_ENABLED=ON \
    -DCMAKE_CUDA_ARCHITECTURES=75 \
    && cmake --build build --target colmap -j"$(nproc)" \
    && cmake --install build

RUN mkdir -p /opt/ml/code /opt/ml/processing/input /opt/ml/processing/output /opt/colmap/vocab

COPY run_sfm.sh /opt/ml/code/run_sfm.sh
COPY run_colmap_sfm.py /opt/ml/code/run_colmap_sfm.py
RUN chmod +x /opt/ml/code/run_sfm.sh

WORKDIR /opt/ml/code
ENTRYPOINT ["/opt/ml/code/run_sfm.sh"]
