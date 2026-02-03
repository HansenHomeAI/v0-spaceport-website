#!/bin/bash

# Production OpenSfM EXIF-Constrained SfM Processing
# SageMaker entry point for EXIF-enhanced Structure-from-Motion
# Updated: 2026-02-03 (EXIF priors rebuild trigger #3)

set -e  # Exit on any error

log_mem() {
    echo "MEMORY_PROBE [${1}]:"
    cat /proc/meminfo 2>/dev/null | head -n 3 || true
    free -h 2>/dev/null || true
}

echo "============================================================"
echo "🚀 SPACEPORT OPENSFM EXIF-CONSTRAINED SfM PROCESSING"
echo "============================================================"
echo "📅 Started at: $(date)"
echo "🔧 Pipeline: OpenSfM with EXIF priors"
echo "📍 EXIF Enhancement: Drone photo metadata integration"
echo "🎯 Output: COLMAP-compatible format for 3DGS"
echo "============================================================"

# Function for error handling
error_exit() {
    echo "❌ ERROR: $1"
    echo "❌ Pipeline failed at: $(date)"
    echo "❌ Check logs for details"
    exit 1
}

# Verify Python environment and dependencies
echo "🔍 Verifying environment..."
python3 --version || error_exit "Python 3 not available"
pip3 list | grep -i opensfm > /dev/null || echo "⚠️ OpenSfM may not be installed"
pip3 list | grep -i pandas > /dev/null || error_exit "pandas not available"
pip3 list | grep -i numpy > /dev/null || error_exit "numpy not available"

echo "✅ Environment verification completed"
log_mem "startup"

# Set Python path for our modules
export PYTHONPATH="/opt/ml/code:$PYTHONPATH"

# Verify required scripts exist
REQUIRED_SCRIPTS=(
    "/opt/ml/code/run_opensfm_gps.py"
    "/opt/ml/code/gps_processor.py"
    "/opt/ml/code/colmap_converter.py"
    "/opt/ml/code/config_template.yaml"
)

echo "🔍 Verifying required scripts..."
for script in "${REQUIRED_SCRIPTS[@]}"; do
    if [ ! -f "$script" ]; then
        error_exit "Required script not found: $script"
    fi
    echo "✅ Found: $(basename $script)"
done

# Check input directory
INPUT_DIR="/opt/ml/processing/input"
OUTPUT_DIR="/opt/ml/processing/output"

echo "📁 Input directory: $INPUT_DIR"
echo "📁 Output directory: $OUTPUT_DIR"

if [ ! -d "$INPUT_DIR" ]; then
    error_exit "Input directory not found: $INPUT_DIR"
fi

# List input contents for debugging
echo "🔍 Input directory contents:"
ls -la "$INPUT_DIR" || error_exit "Cannot list input directory"

# Count input files
ZIP_COUNT=$(find "$INPUT_DIR" -name "*.zip" | wc -l)
CSV_COUNT=$(find "$INPUT_DIR" -name "*.csv" | wc -l)

echo "📦 ZIP files found: $ZIP_COUNT"
echo "🛰️ CSV files found: $CSV_COUNT (ignored; EXIF-only priors)"

if [ "$ZIP_COUNT" -eq 0 ]; then
    error_exit "No ZIP archive found in input directory"
fi

# Create output directory
mkdir -p "$OUTPUT_DIR" || error_exit "Cannot create output directory"

echo ""
echo "============================================================"
echo "🚀 LAUNCHING OPENSFM EXIF PROCESSOR"
echo "============================================================"

# Run the main Python processing script
echo "🔧 Executing OpenSfM EXIF-constrained reconstruction..."
log_mem "before_python"
python3 /opt/ml/code/run_opensfm_gps.py "$INPUT_DIR" "$OUTPUT_DIR"
log_mem "after_python"

# Check if the Python script succeeded
PYTHON_EXIT_CODE=$?
if [ $PYTHON_EXIT_CODE -ne 0 ]; then
    error_exit "OpenSfM processing failed with exit code: $PYTHON_EXIT_CODE"
fi

echo ""
echo "============================================================"
echo "🔍 VALIDATING OUTPUT"
echo "============================================================"

# Verify required output files exist
REQUIRED_OUTPUT_FILES=(
    "$OUTPUT_DIR/sparse/0/cameras.txt"
    "$OUTPUT_DIR/sparse/0/images.txt"
    "$OUTPUT_DIR/sparse/0/points3D.txt"
    "$OUTPUT_DIR/images"
    "$OUTPUT_DIR/sfm_metadata.json"
)

echo "🔍 Checking required output files..."
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

if [ "$ALL_FILES_PRESENT" = false ]; then
    error_exit "Some required output files are missing"
fi

# Validate COLMAP format
echo "🔍 Validating COLMAP format compatibility..."

# Check cameras.txt
CAMERA_COUNT=$(grep -c "^[0-9]" "$OUTPUT_DIR/sparse/0/cameras.txt" 2>/dev/null || echo "0")
if [ "$CAMERA_COUNT" -eq 0 ]; then
    error_exit "No cameras found in cameras.txt"
fi

# Check images.txt (count non-comment, non-empty lines and divide by 2)
IMAGE_LINES=$(grep -c "^[0-9]" "$OUTPUT_DIR/sparse/0/images.txt" 2>/dev/null || echo "0")
IMAGE_COUNT=$((IMAGE_LINES / 2))
if [ "$IMAGE_COUNT" -eq 0 ]; then
    error_exit "No images found in images.txt"
fi

# Check points3D.txt
POINT_COUNT=$(grep -c "^[0-9]" "$OUTPUT_DIR/sparse/0/points3D.txt" 2>/dev/null || echo "0")
MIN_POINTS_REQUIRED=1000

if [ "$POINT_COUNT" -lt "$MIN_POINTS_REQUIRED" ]; then
    error_exit "Insufficient 3D points: $POINT_COUNT < $MIN_POINTS_REQUIRED (quality check failed)"
fi

echo "✅ COLMAP format validation passed"

# Count copied images
COPIED_IMAGE_COUNT=$(find "$OUTPUT_DIR/images" -type f \( -iname "*.jpg" -o -iname "*.jpeg" -o -iname "*.png" \) | wc -l)

echo ""
echo "============================================================"
echo "📊 PROCESSING STATISTICS"
echo "============================================================"

echo "📷 Cameras registered: $CAMERA_COUNT"
echo "🖼️ Images registered: $IMAGE_COUNT"
echo "🖼️ Images copied for 3DGS: $COPIED_IMAGE_COUNT"
echo "🎯 3D points: $POINT_COUNT"
echo "✅ Quality check: PASSED (>= $MIN_POINTS_REQUIRED points)"

# Parse metadata for additional stats
if [ -f "$OUTPUT_DIR/sfm_metadata.json" ]; then
    echo "⏱️ Processing time: $(python3 -c "import json; print(json.load(open('$OUTPUT_DIR/sfm_metadata.json'))['processing_time_seconds'], 'seconds')" 2>/dev/null || echo "Unknown")"
    echo "📈 Pipeline optimization: EXIF-constrained reconstruction"
fi

echo ""
echo "============================================================"
echo "🎉 SPACEPORT OPENSFM PROCESSING COMPLETED SUCCESSFULLY!"
echo "============================================================"
echo "✅ EXIF-constrained Structure-from-Motion reconstruction completed"
echo "⚡ Enhanced with drone photo metadata for improved accuracy"
echo "📁 Output files ready for 3D Gaussian Splatting training"
echo "🔗 COLMAP format compatibility maintained"
echo "📅 Completed at: $(date)"
echo "============================================================"

exit 0 
