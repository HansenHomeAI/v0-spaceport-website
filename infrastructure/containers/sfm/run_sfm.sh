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
echo "🚀 SPACEPORT COLMAP HYBRID SfM PROCESSING"
echo "============================================================"
echo "📅 Started at: $(date)"
echo "🔧 Pipeline: COLMAP EXIF-first segmented mapping"
echo "📍 GPS Priors: DJI EXIF metadata"
echo "🎯 Output: COLMAP-compatible format for 3DGS"
echo "============================================================"

echo "🔍 Verifying environment..."
python3 --version || error_exit "Python 3 not available"
colmap help >/dev/null 2>&1 || error_exit "COLMAP not available"
exiftool -ver >/dev/null 2>&1 || error_exit "exiftool not available"
echo "✅ Environment verification completed"
log_mem "startup"

export PYTHONPATH="/opt/ml/code:$PYTHONPATH"

REQUIRED_SCRIPTS=(
    "/opt/ml/code/run_colmap_hybrid.py"
    "/opt/ml/code/exif_manifest.py"
    "/opt/ml/code/segmenter.py"
    "/opt/ml/code/colmap_runner.py"
    "/opt/ml/code/model_merge.py"
    "/opt/ml/code/model_analyzer.py"
    "/opt/ml/code/cost_estimator.py"
    "/opt/ml/code/sfm_scaling.py"
)

echo "🔍 Verifying required scripts..."
for script in "${REQUIRED_SCRIPTS[@]}"; do
    if [ ! -f "$script" ]; then
        error_exit "Required script not found: $script"
    fi
    echo "✅ Found: $(basename "$script")"
done

INPUT_DIR="/opt/ml/processing/input"
OUTPUT_DIR="/opt/ml/processing/output"
SFM_ONLY="${SPACEPORT_SFM_ONLY:-false}"

echo "📁 Input directory: $INPUT_DIR"
echo "📁 Output directory: $OUTPUT_DIR"
echo "🎛️ SfM-only mode: $SFM_ONLY"

[ -d "$INPUT_DIR" ] || error_exit "Input directory not found: $INPUT_DIR"
mkdir -p "$OUTPUT_DIR" || error_exit "Cannot create output directory"

echo "🔍 Input directory contents:"
ls -la "$INPUT_DIR" || error_exit "Cannot list input directory"

ZIP_COUNT=$(find "$INPUT_DIR" -name "*.zip" | wc -l | tr -d ' ')
echo "📦 ZIP files found: $ZIP_COUNT"
[ "$ZIP_COUNT" -gt 0 ] || error_exit "No ZIP archive found in input directory"

echo ""
echo "============================================================"
echo "🚀 LAUNCHING COLMAP HYBRID PROCESSOR"
echo "============================================================"

log_mem "before_python"
python3 /opt/ml/code/run_colmap_hybrid.py "$INPUT_DIR" "$OUTPUT_DIR"
PYTHON_EXIT_CODE=$?
log_mem "after_python"

[ $PYTHON_EXIT_CODE -eq 0 ] || error_exit "COLMAP hybrid processing failed with exit code: $PYTHON_EXIT_CODE"

echo ""
echo "============================================================"
echo "🔍 VALIDATING OUTPUT"
echo "============================================================"

REQUIRED_OUTPUT_FILES=(
    "$OUTPUT_DIR/sparse/0/cameras.txt"
    "$OUTPUT_DIR/sparse/0/images.txt"
    "$OUTPUT_DIR/sparse/0/points3D.txt"
    "$OUTPUT_DIR/database.db"
    "$OUTPUT_DIR/sfm_metadata.json"
    "$OUTPUT_DIR/segment_manifest.json"
    "$OUTPUT_DIR/cost_report.json"
)

if [ "$SFM_ONLY" != "true" ]; then
    REQUIRED_OUTPUT_FILES+=("$OUTPUT_DIR/images")
fi

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

[ "$CAMERA_COUNT" -gt 0 ] || error_exit "No cameras found in cameras.txt"
[ "$IMAGE_COUNT" -gt 0 ] || error_exit "No images found in images.txt"
[ "$POINT_COUNT" -gt 0 ] || error_exit "No 3D points found in points3D.txt"

QUALITY_PASSED=$(python3 - <<'PY'
import json
from pathlib import Path
metadata = json.loads(Path("/opt/ml/processing/output/sfm_metadata.json").read_text(encoding="utf-8"))
print("true" if metadata.get("quality_check_passed") else "false")
PY
)

[ "$QUALITY_PASSED" = "true" ] || error_exit "Metadata quality check failed"

echo "✅ COLMAP format validation passed"
echo ""
echo "============================================================"
echo "📊 PROCESSING STATISTICS"
echo "============================================================"
echo "📷 Cameras registered: $CAMERA_COUNT"
echo "🖼️ Images registered: $IMAGE_COUNT"
if [ "$SFM_ONLY" != "true" ]; then
    COPIED_IMAGE_COUNT=$(find "$OUTPUT_DIR/images" -type f \( -iname "*.jpg" -o -iname "*.jpeg" -o -iname "*.png" \) | wc -l)
    echo "🖼️ Images exported for 3DGS: $COPIED_IMAGE_COUNT"
else
    echo "🖼️ Images exported for 3DGS: skipped (SfM-only run)"
fi
echo "🎯 3D points: $POINT_COUNT"
echo "✅ Quality check: PASSED"

python3 - <<'PY'
import json
from pathlib import Path
metadata = json.loads(Path("/opt/ml/processing/output/sfm_metadata.json").read_text(encoding="utf-8"))
print(f"⏱️ Processing time: {metadata.get('processing_time_seconds')} seconds")
print(f"📈 Profile: {metadata.get('selected_profile')}")
print(f"🧩 Segments: {metadata.get('segment_count')}")
PY

echo ""
echo "============================================================"
echo "🎉 SPACEPORT COLMAP HYBRID SfM COMPLETED SUCCESSFULLY!"
echo "============================================================"
echo "✅ EXIF-first segmented SfM reconstruction completed"
echo "📁 Output files ready for 3D Gaussian Splatting training"
echo "🔗 COLMAP format compatibility maintained"
echo "📅 Completed at: $(date)"
echo "============================================================"
