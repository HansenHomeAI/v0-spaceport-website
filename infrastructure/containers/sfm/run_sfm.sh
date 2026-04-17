#!/bin/bash

set -euo pipefail

log_mem() {
    echo "MEMORY_PROBE [${1}]:"
    cat /proc/meminfo 2>/dev/null | head -n 3 || true
    free -h 2>/dev/null || true
}

error_exit() {
    echo "❌ ERROR: $1"
    echo "❌ Pipeline failed at: $(date)"
    exit 1
}

echo "============================================================"
echo "🚀 SPACEPORT COLMAP GPU SfM PROCESSING"
echo "============================================================"
echo "📅 Started at: $(date)"
echo "🔧 Pipeline: COLMAP mapper with GPU SIFT + spatial/vocab matching"
echo "📍 GPS Priors: image EXIF metadata"
echo "🎯 Output: COLMAP TXT export for 3DGS"
echo "============================================================"

echo "🔍 Verifying environment..."
python3 --version || error_exit "Python 3 not available"
colmap help >/dev/null 2>&1 || error_exit "COLMAP not available"
exiftool -ver >/dev/null 2>&1 || error_exit "exiftool not available"
if command -v nvidia-smi >/dev/null 2>&1; then
    nvidia-smi || true
else
    echo "⚠️ nvidia-smi not found in container PATH"
fi
echo "✅ Environment verification completed"
log_mem "startup"

export PYTHONPATH="/opt/ml/code:${PYTHONPATH:-}"

INPUT_DIR="/opt/ml/processing/input"
OUTPUT_DIR="/opt/ml/processing/output"

echo "📁 Input directory: $INPUT_DIR"
echo "📁 Output directory: $OUTPUT_DIR"
[ -d "$INPUT_DIR" ] || error_exit "Input directory not found: $INPUT_DIR"
mkdir -p "$OUTPUT_DIR" || error_exit "Cannot create output directory"

echo "🔍 Input directory contents:"
ls -la "$INPUT_DIR" || error_exit "Cannot list input directory"

ZIP_COUNT=$(find "$INPUT_DIR" -name "*.zip" | wc -l | tr -d ' ')
echo "📦 ZIP files found: $ZIP_COUNT"
[ "$ZIP_COUNT" -gt 0 ] || error_exit "No ZIP archive found in input directory"

echo ""
echo "============================================================"
echo "🚀 LAUNCHING COLMAP GPU PROCESSOR"
echo "============================================================"

log_mem "before_python"
python3 /opt/ml/code/run_colmap_sfm.py "$INPUT_DIR" "$OUTPUT_DIR"
PYTHON_EXIT_CODE=$?
log_mem "after_python"
[ "$PYTHON_EXIT_CODE" -eq 0 ] || error_exit "COLMAP processing failed with exit code: $PYTHON_EXIT_CODE"

echo ""
echo "============================================================"
echo "🔍 VALIDATING OUTPUT"
echo "============================================================"

[ -f "$OUTPUT_DIR/sfm_metadata.json" ] || error_exit "Missing sfm_metadata.json"

SNAPSHOT_MODE=$(python3 - <<'PY'
import json
import os
from pathlib import Path

metadata = json.loads(Path("/opt/ml/processing/output/sfm_metadata.json").read_text(encoding="utf-8"))
if os.environ.get("SFM_CAPABILITY_SNAPSHOT_ONLY") == "1" or metadata.get("capability_snapshot_only"):
    print("capability")
elif os.environ.get("SFM_PLANNER_SNAPSHOT_ONLY") == "1" or metadata.get("planner_snapshot_only"):
    print("planner")
else:
    print("")
PY
)

if [ "$SNAPSHOT_MODE" = "capability" ]; then
    echo "✅ Snapshot-only capability metadata written"
    python3 - <<'PY'
import json
from pathlib import Path

metadata = json.loads(Path("/opt/ml/processing/output/sfm_metadata.json").read_text(encoding="utf-8"))
capabilities = metadata.get("colmap_capabilities", {})
print(f"🧪 Snapshot mode: capability")
print(f"🗺️ global_mapper supported: {capabilities.get('supports_global_mapper')}")
print(f"🔧 view_graph_calibrator available: {'view_graph_calibrator' in capabilities.get('available_commands', [])}")
PY
    echo "✅ Capability snapshot validation passed"
    exit 0
fi

if [ "$SNAPSHOT_MODE" = "planner" ]; then
    [ -f "$OUTPUT_DIR/chunk_planner_manifest.json" ] || error_exit "Missing chunk_planner_manifest.json"
    echo "✅ Planner snapshot artifacts written"
    python3 - <<'PY'
import json
from pathlib import Path

metadata = json.loads(Path("/opt/ml/processing/output/sfm_metadata.json").read_text(encoding="utf-8"))
manifest = json.loads(Path("/opt/ml/processing/output/chunk_planner_manifest.json").read_text(encoding="utf-8"))
print(f"🧪 Snapshot mode: planner")
print(f"🧩 Chunk count: {manifest.get('chunk_count')}")
print(f"🔎 Probe subsets: {sorted((manifest.get('probe_subsets') or {}).keys())}")
print(f"⏱️ Processing time: {metadata.get('processing_time_seconds')} seconds")
PY
    echo "✅ Planner snapshot validation passed"
    exit 0
fi

REQUIRED_OUTPUT_FILES=(
    "$OUTPUT_DIR/sparse/0/cameras.txt"
    "$OUTPUT_DIR/sparse/0/images.txt"
    "$OUTPUT_DIR/sparse/0/points3D.txt"
    "$OUTPUT_DIR/images"
    "$OUTPUT_DIR/database.db"
)

ALL_FILES_PRESENT=true
for file in "${REQUIRED_OUTPUT_FILES[@]}"; do
    if [ -f "$file" ]; then
        SIZE=$(stat -c%s "$file" 2>/dev/null || echo "0")
        echo "✅ $file ($SIZE bytes)"
    elif [ -d "$file" ]; then
        COUNT=$(find "$file" -type f | wc -l)
        echo "✅ $file ($COUNT files)"
    else
        echo "❌ MISSING: $file"
        ALL_FILES_PRESENT=false
    fi
done

[ "$ALL_FILES_PRESENT" = true ] || error_exit "Some required output files are missing"

CAMERA_COUNT=$(grep -c "^[0-9]" "$OUTPUT_DIR/sparse/0/cameras.txt" 2>/dev/null || echo "0")
IMAGE_LINES=$(grep -c "^[0-9]" "$OUTPUT_DIR/sparse/0/images.txt" 2>/dev/null || echo "0")
IMAGE_COUNT=$((IMAGE_LINES / 2))
POINT_COUNT=$(grep -c "^[0-9]" "$OUTPUT_DIR/sparse/0/points3D.txt" 2>/dev/null || echo "0")
COPIED_IMAGE_COUNT=$(find "$OUTPUT_DIR/images" -type f \( -iname "*.jpg" -o -iname "*.jpeg" -o -iname "*.png" \) | wc -l)

[ "$CAMERA_COUNT" -gt 0 ] || error_exit "No cameras found in cameras.txt"
[ "$IMAGE_COUNT" -gt 0 ] || error_exit "No images found in images.txt"
[ "$POINT_COUNT" -ge 1000 ] || error_exit "Insufficient 3D points: $POINT_COUNT < 1000"

echo "✅ COLMAP format validation passed"
echo ""
echo "============================================================"
echo "📊 PROCESSING STATISTICS"
echo "============================================================"
echo "📷 Cameras registered: $CAMERA_COUNT"
echo "🖼️ Images registered: $IMAGE_COUNT"
echo "🖼️ Images copied for 3DGS: $COPIED_IMAGE_COUNT"
echo "🎯 3D points: $POINT_COUNT"
python3 - <<'PY'
import json
from pathlib import Path
metadata = json.loads(Path("/opt/ml/processing/output/sfm_metadata.json").read_text(encoding="utf-8"))
print(f"⏱️ Processing time: {metadata.get('processing_time_seconds')} seconds")
print(f"🛰️ GPS priors detected: {metadata.get('gps_priors_detected')}")
print(f"🔗 Matchers: {', '.join(metadata.get('matchers_run', []))}")
print(f"🎯 Vocab tree candidates: {metadata.get('vocab_tree_num_images')}")
print(f"📌 SIFT max features: {metadata.get('sift_max_num_features')}")
PY

echo ""
echo "============================================================"
echo "🎉 SPACEPORT COLMAP GPU SfM COMPLETED SUCCESSFULLY!"
echo "============================================================"
echo "✅ GPU-accelerated COLMAP SfM completed"
echo "📁 Output files ready for 3D Gaussian Splatting training"
echo "🔗 COLMAP TXT handoff maintained"
echo "📅 Completed at: $(date)"
echo "============================================================"
