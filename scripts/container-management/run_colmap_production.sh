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
    --SiftExtraction.use_gpu 0 \
    --SiftExtraction.num_threads 4 \
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

echo ""
echo "============================================================"
echo "🖼️ STEP 4: IMAGE UNDISTORTION"
echo "============================================================"

echo "🔧 Running COLMAP image undistorter..."

timeout 1800 colmap image_undistorter \
    --image_path "$WORK_DIR/images" \
    --input_path "$RECON_DIR" \
    --output_path "$WORK_DIR/dense" \
    --output_type COLMAP \
    --max_image_size 2000 \
    || {
        echo "❌ Image undistortion failed or timed out"
        exit 1
    }

echo "✅ Image undistortion completed"

echo ""
echo "============================================================"
echo "🎯 STEP 5: DENSE RECONSTRUCTION (OPTIONAL - SKIPPED FOR 3DGS)"
echo "============================================================"

echo "ℹ️ Skipping dense reconstruction for 3D Gaussian Splatting compatibility"
echo "ℹ️ Sparse reconstruction with 3D points is sufficient for 3DGS training"

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
)

ALL_PRESENT=true
for FILE in "${REQUIRED_FILES[@]}"; do
    if [ -f "$FILE" ]; then
        SIZE=$(stat -c%s "$FILE" 2>/dev/null || echo "0")
        echo "✅ $FILE ($SIZE bytes)"
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

echo "📷 Cameras registered: $CAMERA_COUNT"
echo "🖼️ Images registered: $IMAGE_COUNT"
echo "🎯 3D points: $POINT_COUNT"
echo "☁️ Reference point cloud size: $PLY_SIZE bytes"

# Create metadata file
cat > "$OUTPUT_DIR/sfm_metadata.json" << EOF
{
  "pipeline": "production_colmap",
  "version": "1.0",
  "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "statistics": {
    "cameras_registered": $CAMERA_COUNT,
    "images_registered": $IMAGE_COUNT,
    "sparse_points": $POINT_COUNT,
    "reference_pointcloud_bytes": $PLY_SIZE
  },
  "processing_steps": [
    "feature_extraction",
    "feature_matching", 
    "sparse_reconstruction",
    "image_undistortion"
  ],
  "output_format": "colmap_text",
  "ready_for_3dgs": true
}
EOF

echo ""
echo "============================================================"
echo "🎉 PRODUCTION COLMAP PROCESSING COMPLETED SUCCESSFULLY!"
echo "============================================================"
echo "✅ Real COLMAP Structure-from-Motion reconstruction completed"
echo "📁 Output files ready for 3D Gaussian Splatting training"
echo "⏱️ Processing completed at $(date)"
echo "============================================================"

# Cleanup work directory
echo "🧹 Cleaning up work directory..."
rm -rf "$WORK_DIR"

exit 0 