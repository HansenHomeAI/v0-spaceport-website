#!/bin/bash
set -e

echo "Starting SfM processing with COLMAP..."

INPUT_DIR="/opt/ml/processing/input"
OUTPUT_DIR="/opt/ml/processing/output"
WORKSPACE_DIR="/tmp/colmap_workspace"

# Create workspace directory
mkdir -p "$WORKSPACE_DIR"
mkdir -p "$WORKSPACE_DIR/images"

echo "Input directory: $INPUT_DIR"
echo "Output directory: $OUTPUT_DIR"
echo "Workspace directory: $WORKSPACE_DIR"

# Check if input directory exists and has content
if [ ! -d "$INPUT_DIR" ] || [ -z "$(ls -A $INPUT_DIR)" ]; then
    echo "Error: Input directory is empty or does not exist"
    exit 1
fi

# Extract ZIP file if present
if ls "$INPUT_DIR"/*.zip 1> /dev/null 2>&1; then
    echo "Found ZIP file, extracting..."
    cd "$INPUT_DIR"
    unzip -q *.zip -d "$WORKSPACE_DIR/images/"
    cd -
else
    # Copy images directly
    echo "Copying images from input directory..."
    cp -r "$INPUT_DIR"/* "$WORKSPACE_DIR/images/"
fi

# Verify we have images
IMAGE_COUNT=$(find "$WORKSPACE_DIR/images" -type f \( -iname "*.jpg" -o -iname "*.jpeg" -o -iname "*.png" \) | wc -l)
echo "Found $IMAGE_COUNT images"

if [ "$IMAGE_COUNT" -eq 0 ]; then
    echo "Error: No images found in input"
    exit 1
fi

# Create database
echo "Creating COLMAP database..."
colmap database_creator \
    --database_path "$WORKSPACE_DIR/database.db"

# Feature extraction
echo "Extracting features..."
colmap feature_extractor \
    --database_path "$WORKSPACE_DIR/database.db" \
    --image_path "$WORKSPACE_DIR/images" \
    --ImageReader.single_camera 1 \
    --SiftExtraction.use_gpu 0

# Feature matching
echo "Matching features..."
colmap exhaustive_matcher \
    --database_path "$WORKSPACE_DIR/database.db" \
    --SiftMatching.use_gpu 0

# Create sparse reconstruction directory
mkdir -p "$WORKSPACE_DIR/sparse"

# Sparse reconstruction
echo "Running sparse reconstruction..."
colmap mapper \
    --database_path "$WORKSPACE_DIR/database.db" \
    --image_path "$WORKSPACE_DIR/images" \
    --output_path "$WORKSPACE_DIR/sparse"

# Check if reconstruction was successful
if [ ! -d "$WORKSPACE_DIR/sparse/0" ]; then
    echo "Error: Sparse reconstruction failed"
    exit 1
fi

# Dense reconstruction
echo "Running dense reconstruction..."
mkdir -p "$WORKSPACE_DIR/dense"

# Image undistortion
colmap image_undistorter \
    --image_path "$WORKSPACE_DIR/images" \
    --input_path "$WORKSPACE_DIR/sparse/0" \
    --output_path "$WORKSPACE_DIR/dense" \
    --output_type COLMAP

# Patch match stereo
colmap patch_match_stereo \
    --workspace_path "$WORKSPACE_DIR/dense" \
    --workspace_format COLMAP \
    --PatchMatchStereo.geom_consistency true

# Stereo fusion
colmap stereo_fusion \
    --workspace_path "$WORKSPACE_DIR/dense" \
    --workspace_format COLMAP \
    --input_type geometric \
    --output_path "$WORKSPACE_DIR/dense/fused.ply"

# Copy results to output directory
echo "Copying results to output directory..."
cp -r "$WORKSPACE_DIR/sparse" "$OUTPUT_DIR/"
cp -r "$WORKSPACE_DIR/dense" "$OUTPUT_DIR/"
cp "$WORKSPACE_DIR/database.db" "$OUTPUT_DIR/"

# Create a summary file
echo "Creating processing summary..."
cat > "$OUTPUT_DIR/processing_summary.txt" << EOF
SfM Processing Summary
=====================
Input images: $IMAGE_COUNT
Sparse reconstruction: $(ls -la "$WORKSPACE_DIR/sparse/0" | wc -l) files
Dense reconstruction: $([ -f "$WORKSPACE_DIR/dense/fused.ply" ] && echo "Success" || echo "Failed")
Processing completed: $(date)
EOF

echo "SfM processing completed successfully!"
echo "Results saved to: $OUTPUT_DIR" 