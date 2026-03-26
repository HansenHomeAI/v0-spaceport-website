#!/bin/bash
set -euo pipefail

echo "============================================================"
echo "🚀 SPACEPORT COLMAP GPU SfM PROCESSING"
echo "============================================================"
echo "📅 Started at: $(date -u)"
echo "🔧 Pipeline: COLMAP + GPU SIFT + vocabulary tree matching"
echo "============================================================"

INPUT_DIR="/opt/ml/processing/input"
OUTPUT_DIR="/opt/ml/processing/output"

if [ ! -d "$INPUT_DIR" ]; then
  echo "❌ Missing input directory: $INPUT_DIR"
  exit 1
fi

mkdir -p "$OUTPUT_DIR"
export PYTHONPATH="/opt/ml/code:${PYTHONPATH:-}"

python3 /opt/ml/code/run_colmap_gps.py "$INPUT_DIR" "$OUTPUT_DIR"

REQUIRED_OUTPUTS=(
  "$OUTPUT_DIR/images"
  "$OUTPUT_DIR/sparse/0/cameras.txt"
  "$OUTPUT_DIR/sparse/0/images.txt"
  "$OUTPUT_DIR/sparse/0/points3D.txt"
  "$OUTPUT_DIR/colmap_export/cameras.txt"
  "$OUTPUT_DIR/colmap_export/images.txt"
  "$OUTPUT_DIR/colmap_export/points3D.txt"
  "$OUTPUT_DIR/sfm_metadata.json"
  "$OUTPUT_DIR/database.db"
)

for item in "${REQUIRED_OUTPUTS[@]}"; do
  if [ ! -e "$item" ]; then
    echo "❌ Missing required output: $item"
    exit 1
  fi
  echo "✅ Output present: $item"
done

POINTS=$(grep -c '^[0-9]' "$OUTPUT_DIR/sparse/0/points3D.txt" || true)
IMAGES=$(find "$OUTPUT_DIR/images" -maxdepth 1 -type f | wc -l | tr -d ' ')

if [ "$POINTS" -lt 1 ]; then
  echo "❌ Invalid output: no sparse points"
  exit 1
fi

echo "✅ Output validation complete: images=$IMAGES points=$POINTS"
echo "🎉 COLMAP SfM processing complete"
