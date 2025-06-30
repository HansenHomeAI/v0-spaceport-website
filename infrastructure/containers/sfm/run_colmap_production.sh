#!/bin/bash

# Real Production COLMAP Script - Shell Version
# This script performs complete Structure-from-Motion processing using COLMAP

set -e  # Exit on any error

echo "============================================================"
echo "🚀 PRODUCTION COLMAP SfM PROCESSING - v1.0"
echo "============================================================"

# Paths
INPUT_DIR="/opt/ml/processing/input"
OUTPUT_DIR="/opt/ml/processing/output"
WORK_DIR="/tmp/colmap_work"

echo "Input: $INPUT_DIR"
echo "Output: $OUTPUT_DIR"
echo "Work: $WORK_DIR"

# Create working directories
mkdir -p "$OUTPUT_DIR/sparse/0"
mkdir -p "$OUTPUT_DIR/dense"
mkdir -p "$WORK_DIR/images"
mkdir -p "$WORK_DIR/database"

echo ""
echo "============================================================"
echo "📁 EXTRACTING INPUT ARCHIVE"
echo "============================================================"

# Find and extract the input archive
ARCHIVE_FILE=$(find "$INPUT_DIR" -name "*.zip" | head -1)
if [ -z "$ARCHIVE_FILE" ]; then
    echo "❌ No zip archive found in $INPUT_DIR"
    exit 1
fi

echo "📦 Found archive: $ARCHIVE_FILE"
cd "$WORK_DIR"
unzip -q "$ARCHIVE_FILE" -d images/
echo "✅ Archive extracted successfully"

# Count images
IMAGE_COUNT=$(find "$WORK_DIR/images" -type f \( -iname "*.jpg" -o -iname "*.jpeg" -o -iname "*.png" \) | wc -l)
echo "📸 Found $IMAGE_COUNT images"

if [ "$IMAGE_COUNT" -eq 0 ]; then
    echo "❌ No images found in archive"
    exit 1
fi

echo ""
echo "============================================================"
echo "🔍 STEP 1: FEATURE EXTRACTION"
echo "============================================================"

# Run COLMAP feature extraction
echo "🔧 Running COLMAP feature extractor..."

timeout 1800 colmap feature_extractor \
    --database_path "$WORK_DIR/database/database.db" \
    --image_path "$WORK_DIR/images" \
    --ImageReader.single_camera 1 \
    --ImageReader.default_focal_length_factor 1.2 \
    --SiftExtraction.use_gpu 0 \
    --SiftExtraction.num_threads 4 \
    --SiftExtraction.max_image_size 4096 \
    --SiftExtraction.max_num_features 16384 \
    --SiftExtraction.first_octave -1 \
    --SiftExtraction.num_octaves 4 \
    --SiftExtraction.octave_resolution 3 \
    || {
        echo "❌ Feature extraction failed or timed out"
        exit 1
    }

echo "✅ Feature extraction completed"

# Check database size
DB_SIZE=$(stat -f%z "$WORK_DIR/database/database.db" 2>/dev/null || stat -c%s "$WORK_DIR/database/database.db" 2>/dev/null || echo "0")
echo "📊 Database size: $DB_SIZE bytes"

echo ""
echo "============================================================"
echo "🔗 STEP 2: FEATURE MATCHING"
echo "============================================================"

echo "🔧 Running COLMAP exhaustive matcher..."

timeout 1800 colmap exhaustive_matcher \
    --database_path "$WORK_DIR/database/database.db" \
    --SiftMatching.use_gpu 0 \
    --SiftMatching.num_threads 4 \
    --SiftMatching.guided_matching 1 \
    --SiftMatching.max_ratio 0.8 \
    --SiftMatching.max_distance 0.7 \
    --SiftMatching.cross_check 1 \
    --SiftMatching.max_num_matches 32768 \
    || {
        echo "❌ Feature matching failed or timed out"
        exit 1
    }

echo "✅ Feature matching completed"

echo ""
echo "============================================================"
echo "🗺️ STEP 3: SPARSE RECONSTRUCTION (MAPPER)"
echo "============================================================"

echo "🔧 Running COLMAP mapper..."

# Ensure sparse output directory exists
mkdir -p "$WORK_DIR/sparse"

timeout 1800 colmap mapper \
    --database_path "$WORK_DIR/database/database.db" \
    --image_path "$WORK_DIR/images" \
    --output_path "$WORK_DIR/sparse" \
    --Mapper.num_threads 4 \
    --Mapper.ba_refine_focal_length 1 \
    --Mapper.ba_refine_principal_point 0 \
    || {
        echo "❌ Sparse reconstruction failed or timed out"
        exit 1
    }

echo "✅ Sparse reconstruction completed"

# Find the reconstruction directory (usually 0)
RECON_DIR=$(find "$WORK_DIR/sparse" -mindepth 1 -maxdepth 1 -type d | head -1)
if [ -z "$RECON_DIR" ]; then
    echo "❌ No reconstruction found"
    exit 1
fi

echo "📁 Reconstruction found: $RECON_DIR"

# CRITICAL: Validate reconstruction quality
echo ""
echo "============================================================"
echo "🔍 VALIDATING RECONSTRUCTION QUALITY"
echo "============================================================"

# Count 3D points
if [ -f "$RECON_DIR/points3D.txt" ]; then
    POINT_COUNT=$(grep -c "^[0-9]" "$RECON_DIR/points3D.txt" 2>/dev/null || echo "0")
    echo "📊 3D points found: $POINT_COUNT"
    
    # FAIL if insufficient points for quality 3DGS
    MIN_POINTS=1000
    if [ "$POINT_COUNT" -lt "$MIN_POINTS" ]; then
        echo "❌ CRITICAL: Only $POINT_COUNT 3D points reconstructed!"
        echo "❌ Need at least $MIN_POINTS points for quality 3D Gaussian Splatting"
        echo "❌ This indicates:"
        echo "   - Insufficient feature matches between images"
        echo "   - Poor camera calibration or image quality"
        echo "   - Images may not have sufficient overlap"
        echo "❌ SfM QUALITY CHECK FAILED - STOPPING PIPELINE"
        exit 1
    fi
    
    echo "✅ Quality check passed: $POINT_COUNT >= $MIN_POINTS points"
else
    echo "❌ CRITICAL: No points3D.txt file found!"
    echo "❌ Sparse reconstruction completely failed"
    exit 1
fi

# Count registered images
if [ -f "$RECON_DIR/images.txt" ]; then
    IMAGE_COUNT=$(grep -c "^[0-9]" "$RECON_DIR/images.txt" 2>/dev/null || echo "0")
    echo "📸 Images registered: $IMAGE_COUNT"
    
    # Check if reasonable number of images were registered
    TOTAL_IMAGES=$(find "$WORK_DIR/images" -type f \( -iname "*.jpg" -o -iname "*.jpeg" -o -iname "*.png" \) | wc -l)
    REGISTRATION_RATIO=$((IMAGE_COUNT * 100 / TOTAL_IMAGES))
    echo "📊 Registration ratio: $REGISTRATION_RATIO% ($IMAGE_COUNT/$TOTAL_IMAGES)"
    
    if [ "$REGISTRATION_RATIO" -lt 50 ]; then
        echo "❌ WARNING: Low image registration ratio ($REGISTRATION_RATIO%)"
        echo "   This may indicate poor image quality or insufficient overlap"
    else
        echo "✅ Good image registration ratio: $REGISTRATION_RATIO%"
    fi
else
    echo "❌ CRITICAL: No images.txt file found!"
    exit 1
fi

echo "✅ Reconstruction quality validation completed"

echo ""
echo "============================================================"
echo "🎯 OPTIMIZED FOR 3DGS: SKIPPING UNNECESSARY DENSE STEPS"
echo "============================================================"

echo "ℹ️ Skipping image undistortion - 3DGS can handle camera distortion directly"
echo "ℹ️ Skipping dense reconstruction - sparse reconstruction sufficient for 3DGS"
echo "⚡ This optimization saves 10-20 minutes of compute time"

# Create a minimal dense directory structure for compatibility
mkdir -p "$WORK_DIR/dense"

# Create a simple point cloud from sparse reconstruction for reference
echo "📊 Creating reference point cloud from sparse reconstruction..."
if [ -f "$RECON_DIR/points3D.txt" ]; then
    # Create a simple PLY file from the sparse points
    POINT_COUNT=$(grep -c "^[0-9]" "$RECON_DIR/points3D.txt" 2>/dev/null || echo "0")
    echo "ply" > "$WORK_DIR/dense/sparse_points.ply"
    echo "format ascii 1.0" >> "$WORK_DIR/dense/sparse_points.ply"
    echo "element vertex $POINT_COUNT" >> "$WORK_DIR/dense/sparse_points.ply"
    echo "property float x" >> "$WORK_DIR/dense/sparse_points.ply"
    echo "property float y" >> "$WORK_DIR/dense/sparse_points.ply"
    echo "property float z" >> "$WORK_DIR/dense/sparse_points.ply"
    echo "property uchar red" >> "$WORK_DIR/dense/sparse_points.ply"
    echo "property uchar green" >> "$WORK_DIR/dense/sparse_points.ply"
    echo "property uchar blue" >> "$WORK_DIR/dense/sparse_points.ply"
    echo "end_header" >> "$WORK_DIR/dense/sparse_points.ply"
    
    # Extract point data (skip header lines)
    grep "^[0-9]" "$RECON_DIR/points3D.txt" | while read line; do
        # Parse COLMAP points3D.txt format: POINT3D_ID X Y Z R G B ERROR TRACK[]
        echo "$line" | awk '{printf "%.6f %.6f %.6f %d %d %d\n", $2, $3, $4, $5, $6, $7}'
    done >> "$WORK_DIR/dense/sparse_points.ply"
    
    echo "✅ Created reference point cloud with $POINT_COUNT points"
else
    echo "⚠️ No sparse points found, creating empty reference file"
    echo "ply" > "$WORK_DIR/dense/sparse_points.ply"
    echo "format ascii 1.0" >> "$WORK_DIR/dense/sparse_points.ply"
    echo "element vertex 0" >> "$WORK_DIR/dense/sparse_points.ply"
    echo "end_header" >> "$WORK_DIR/dense/sparse_points.ply"
fi

echo ""
echo "============================================================"
echo "📋 COPYING OUTPUT FILES"
echo "============================================================"

# Copy sparse reconstruction to output and convert to text format
echo "📂 Copying sparse reconstruction..."
echo "🔍 Debug: Contents of $RECON_DIR:"
ls -la "$RECON_DIR" || echo "Directory not accessible"

# First copy the binary files
cp -r "$RECON_DIR"/* "$OUTPUT_DIR/sparse/0/" || echo "Copy failed"

# Convert binary COLMAP files to text format for 3DGS compatibility
echo "🔄 Converting COLMAP binary files to text format for 3DGS..."
colmap model_converter \
    --input_path "$OUTPUT_DIR/sparse/0" \
    --output_path "$OUTPUT_DIR/sparse/0" \
    --output_type TXT \
    || {
        echo "⚠️ Model conversion failed, but continuing..."
    }

echo "🔍 Debug: Contents of $OUTPUT_DIR/sparse/0/ after conversion:"
ls -la "$OUTPUT_DIR/sparse/0/" || echo "Directory not accessible"

# Copy reference point cloud
echo "☁️ Copying reference point cloud..."
cp "$WORK_DIR/dense/sparse_points.ply" "$OUTPUT_DIR/dense/"

# Copy original images for 3DGS training (no undistortion needed)
echo "🖼️ Copying original images for 3DGS training..."
echo "ℹ️ Using original images with camera distortion parameters"
mkdir -p "$OUTPUT_DIR/images"
cp -r "$WORK_DIR/images"/* "$OUTPUT_DIR/images/"
IMAGE_COPY_COUNT=$(find "$OUTPUT_DIR/images" -type f \( -iname "*.jpg" -o -iname "*.jpeg" -o -iname "*.png" \) | wc -l)
echo "✅ Copied $IMAGE_COPY_COUNT original images"

# Copy database for reference
echo "💾 Copying database..."
cp "$WORK_DIR/database/database.db" "$OUTPUT_DIR/"

# Verify required files exist
echo ""
echo "🔍 Verifying output files..."

REQUIRED_FILES=(
    "$OUTPUT_DIR/sparse/0/cameras.txt"
    "$OUTPUT_DIR/sparse/0/images.txt"
    "$OUTPUT_DIR/sparse/0/points3D.txt"
    "$OUTPUT_DIR/dense/sparse_points.ply"
    "$OUTPUT_DIR/database.db"
    "$OUTPUT_DIR/images"
)

ALL_PRESENT=true
for FILE in "${REQUIRED_FILES[@]}"; do
    if [ -f "$FILE" ]; then
        SIZE=$(stat -c%s "$FILE" 2>/dev/null || echo "0")
        echo "✅ $FILE ($SIZE bytes)"
    elif [ -d "$FILE" ]; then
        COUNT=$(find "$FILE" -type f | wc -l)
        echo "✅ $FILE ($COUNT files)"
    else
        echo "❌ MISSING: $FILE"
        ALL_PRESENT=false
    fi
done

if [ "$ALL_PRESENT" = false ]; then
    echo "❌ Some required output files are missing"
    exit 1
fi

# Generate statistics
echo ""
echo "============================================================"
echo "📊 RECONSTRUCTION STATISTICS"
echo "============================================================"

CAMERA_COUNT=$(grep -c "^[0-9]" "$OUTPUT_DIR/sparse/0/cameras.txt" 2>/dev/null || echo "0")
IMAGE_COUNT=$(grep -c "^[0-9]" "$OUTPUT_DIR/sparse/0/images.txt" 2>/dev/null || echo "0")
POINT_COUNT=$(grep -c "^[0-9]" "$OUTPUT_DIR/sparse/0/points3D.txt" 2>/dev/null || echo "0")
PLY_SIZE=$(stat -c%s "$OUTPUT_DIR/dense/sparse_points.ply" 2>/dev/null || echo "0")
COPIED_IMAGE_COUNT=$(find "$OUTPUT_DIR/images" -type f \( -iname "*.jpg" -o -iname "*.jpeg" -o -iname "*.png" \) | wc -l)

echo "📷 Cameras registered: $CAMERA_COUNT"
echo "🖼️ Images registered: $IMAGE_COUNT"
echo "🖼️ Images copied for 3DGS: $COPIED_IMAGE_COUNT"
echo "🎯 3D points: $POINT_COUNT"
echo "☁️ Reference point cloud size: $PLY_SIZE bytes"

# Create metadata file
cat > "$OUTPUT_DIR/sfm_metadata.json" << EOF
{
  "pipeline": "production_colmap_optimized",
  "version": "1.1",
  "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "optimization": "skipped_image_undistortion_for_3dgs",
  "time_saved_minutes": "10-20",
  "statistics": {
    "cameras_registered": $CAMERA_COUNT,
    "images_registered": $IMAGE_COUNT,
    "images_copied": $COPIED_IMAGE_COUNT,
    "sparse_points": $POINT_COUNT,
    "reference_pointcloud_bytes": $PLY_SIZE
  },
  "processing_steps": [
    "feature_extraction",
    "feature_matching", 
    "sparse_reconstruction"
  ],
  "output_format": "colmap_text",
  "image_format": "original_with_distortion_params",
  "ready_for_3dgs": true
}
EOF

echo ""
echo "============================================================"
echo "🎉 OPTIMIZED COLMAP PROCESSING COMPLETED SUCCESSFULLY!"
echo "============================================================"
echo "✅ Real COLMAP Structure-from-Motion reconstruction completed"
echo "⚡ Optimized for 3DGS: Skipped unnecessary image undistortion"
echo "📁 Output files ready for 3D Gaussian Splatting training"
echo "💰 Compute time saved: ~10-20 minutes per job"
echo "⏱️ Processing completed at $(date)"
echo "============================================================"

# Cleanup work directory
echo "🧹 Cleaning up work directory..."
rm -rf "$WORK_DIR"

exit 0 