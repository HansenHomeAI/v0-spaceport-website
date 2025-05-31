#!/bin/bash

# ENHANCED DEBUGGING AND LOGGING
set -e  # Exit on any error
set -x  # Print every command as it executes

echo "=== SfM PROCESSING STARTING ==="
echo "Date: $(date)"
echo "User: $(whoami)"
echo "Working directory: $(pwd)"
echo "Environment variables:"
env | sort

# Define paths
INPUT_DIR="/opt/ml/processing/input"
OUTPUT_DIR="/opt/ml/processing/output"
WORKSPACE_DIR="/tmp/colmap_workspace"

echo "=== CHECKING INPUT/OUTPUT DIRECTORIES ==="
echo "INPUT_DIR: $INPUT_DIR"
echo "OUTPUT_DIR: $OUTPUT_DIR"
echo "WORKSPACE_DIR: $WORKSPACE_DIR"

# List input directory
echo "=== INPUT DIRECTORY CONTENTS ==="
ls -la "$INPUT_DIR" || echo "INPUT_DIR does not exist or is empty"
find "$INPUT_DIR" -type f -name "*.zip" -o -name "*.jpg" -o -name "*.png" -o -name "*.jpeg" 2>/dev/null || echo "No image or zip files found"

# Create workspace directory
echo "=== CREATING WORKSPACE ==="
mkdir -p "$WORKSPACE_DIR"
mkdir -p "$WORKSPACE_DIR/images"
mkdir -p "$OUTPUT_DIR"

echo "Created directories:"
ls -la "$WORKSPACE_DIR"
ls -la "$OUTPUT_DIR"

# Check if input is a zip file and extract it
echo "=== PROCESSING INPUT FILES ==="
if find "$INPUT_DIR" -name "*.zip" -print -quit | grep -q .; then
    echo "Found ZIP file(s), extracting..."
    for zip_file in "$INPUT_DIR"/*.zip; do
        echo "Extracting: $zip_file"
        unzip -q "$zip_file" -d "$WORKSPACE_DIR/images/" || {
            echo "ERROR: Failed to extract $zip_file"
            exit 1
        }
        echo "Extraction completed for $zip_file"
    done
else
    echo "No ZIP files found, copying image files directly..."
    cp "$INPUT_DIR"/*.{jpg,jpeg,png,JPG,JPEG,PNG} "$WORKSPACE_DIR/images/" 2>/dev/null || {
        echo "ERROR: No image files found in input directory"
        ls -la "$INPUT_DIR"
        exit 1
    }
fi

echo "=== POST-EXTRACTION IMAGE COUNT ==="
image_count=$(find "$WORKSPACE_DIR/images" -type f \( -iname "*.jpg" -o -iname "*.jpeg" -o -iname "*.png" \) | wc -l)
echo "Total images found: $image_count"

if [ "$image_count" -eq 0 ]; then
    echo "ERROR: No images found after extraction!"
    echo "Contents of workspace/images:"
    ls -la "$WORKSPACE_DIR/images"
    exit 1
fi

# List first 10 images for verification
echo "=== SAMPLE IMAGES ==="
find "$WORKSPACE_DIR/images" -type f \( -iname "*.jpg" -o -iname "*.jpeg" -o -iname "*.png" \) | head -10

echo "=== STARTING COLMAP PROCESSING ==="
cd "$WORKSPACE_DIR"

# Feature extraction
echo "=== COLMAP FEATURE EXTRACTION ==="
colmap feature_extractor \
    --database_path "$WORKSPACE_DIR/database.db" \
    --image_path "$WORKSPACE_DIR/images" \
    --ImageReader.single_camera 1 \
    --ImageReader.camera_model SIMPLE_PINHOLE \
    --SiftExtraction.use_gpu 0 \
    --SiftExtraction.num_threads 4 \
    --SiftExtraction.max_image_size 3072 \
    --SiftExtraction.max_num_features 12288 \
    --SiftExtraction.first_octave -1 || {
    echo "ERROR: Feature extraction failed"
    exit 1
}
echo "Feature extraction completed successfully"

# Feature matching
echo "=== COLMAP FEATURE MATCHING ==="
colmap exhaustive_matcher \
    --database_path "$WORKSPACE_DIR/database.db" \
    --SiftMatching.use_gpu 0 \
    --SiftMatching.num_threads 4 \
    --SiftMatching.max_ratio 0.8 \
    --SiftMatching.max_distance 0.7 || {
    echo "ERROR: Feature matching failed"
    exit 1
}
echo "Feature matching completed successfully"

# Create sparse directory
sparse_dir="$WORKSPACE_DIR/sparse"
mkdir -p "$sparse_dir"

# Sparse reconstruction
echo "=== COLMAP SPARSE RECONSTRUCTION ==="
colmap mapper \
    --database_path "$WORKSPACE_DIR/database.db" \
    --image_path "$WORKSPACE_DIR/images" \
    --output_path "$sparse_dir" \
    --Mapper.num_threads 4 \
    --Mapper.init_max_forward_motion 0.95 \
    --Mapper.multiple_models 0 \
    --Mapper.extract_colors 0 || {
    echo "ERROR: Sparse reconstruction failed"
    exit 1
}
echo "Sparse reconstruction completed successfully"

# Check sparse reconstruction results
echo "=== SPARSE RECONSTRUCTION RESULTS ==="
ls -la "$sparse_dir"
find "$sparse_dir" -type f | head -10

# Create dense directory
dense_dir="$WORKSPACE_DIR/dense"
mkdir -p "$dense_dir"

# Dense reconstruction
echo "=== COLMAP DENSE RECONSTRUCTION ==="
colmap image_undistorter \
    --image_path "$WORKSPACE_DIR/images" \
    --input_path "$sparse_dir/0" \
    --output_path "$dense_dir" \
    --output_type COLMAP || {
    echo "ERROR: Image undistortion failed"
    exit 1
}
echo "Image undistortion completed successfully"

colmap patch_match_stereo \
    --workspace_path "$dense_dir" \
    --workspace_format COLMAP \
    --PatchMatchStereo.geom_consistency true \
    --PatchMatchStereo.gpu_index -1 \
    --PatchMatchStereo.depth_min 0.01 \
    --PatchMatchStereo.depth_max 100.0 || {
    echo "ERROR: Patch match stereo failed"
    exit 1
}
echo "Patch match stereo completed successfully"

colmap stereo_fusion \
    --workspace_path "$dense_dir" \
    --workspace_format COLMAP \
    --input_type geometric \
    --output_path "$dense_dir/fused.ply" || {
    echo "ERROR: Stereo fusion failed"
    exit 1
}
echo "Stereo fusion completed successfully"

echo "=== FINAL RESULTS SUMMARY ==="
echo "Workspace contents:"
find "$WORKSPACE_DIR" -type f | head -20

echo "=== COPYING RESULTS TO OUTPUT ==="
# Copy all results to output directory
cp -r "$sparse_dir" "$OUTPUT_DIR/" || {
    echo "ERROR: Failed to copy sparse results"
    exit 1
}
cp -r "$dense_dir" "$OUTPUT_DIR/" || {
    echo "ERROR: Failed to copy dense results"
    exit 1
}
cp "$WORKSPACE_DIR/database.db" "$OUTPUT_DIR/" || {
    echo "ERROR: Failed to copy database"
    exit 1
}

echo "=== OUTPUT VERIFICATION ==="
echo "Output directory contents:"
ls -la "$OUTPUT_DIR"
find "$OUTPUT_DIR" -type f | head -20

echo "=== SfM PROCESSING COMPLETED SUCCESSFULLY ==="
echo "Date: $(date)" 