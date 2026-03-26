#!/usr/bin/env bash
set -euo pipefail

echo "============================================================"
echo "🚀 SPACEPORT COLMAP GPU SfM PROCESSING"
echo "============================================================"
echo "Started: $(date -u)"

INPUT_DIR="${SFM_INPUT_DIR:-/opt/ml/processing/input}"
OUTPUT_DIR="${SFM_OUTPUT_DIR:-/opt/ml/processing/output}"

if [[ ! -d "$INPUT_DIR" ]]; then
  echo "❌ Missing input dir: $INPUT_DIR"
  exit 1
fi

mkdir -p "$OUTPUT_DIR"

python3 /opt/ml/code/run_colmap_sfm.py

for required in \
  "$OUTPUT_DIR/sparse/0/cameras.txt" \
  "$OUTPUT_DIR/sparse/0/images.txt" \
  "$OUTPUT_DIR/sparse/0/points3D.txt" \
  "$OUTPUT_DIR/images" \
  "$OUTPUT_DIR/sfm_metadata.json"
do
  if [[ ! -e "$required" ]]; then
    echo "❌ Missing required output: $required"
    exit 1
  fi
done

echo "✅ COLMAP output contract satisfied"
echo "Completed: $(date -u)"
