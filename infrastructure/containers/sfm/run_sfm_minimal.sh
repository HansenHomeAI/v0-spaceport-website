#!/bin/bash

set -e
set -x

echo "=== MINIMAL SfM PROCESSING FOR PIPELINE TESTING ==="
echo "Input: /opt/ml/processing/input"
echo "Output: /opt/ml/processing/output"

INPUT_DIR="/opt/ml/processing/input"
OUTPUT_DIR="/opt/ml/processing/output"

# Create output directories
mkdir -p "$OUTPUT_DIR/sparse/0"
mkdir -p "$OUTPUT_DIR/dense"

echo "=== CREATING DUMMY SfM OUTPUTS ==="

# Create dummy sparse reconstruction files
cat > "$OUTPUT_DIR/sparse/0/cameras.txt" << 'EOF'
# Camera list with one line of data per camera:
#   CAMERA_ID, MODEL, WIDTH, HEIGHT, PARAMS[]
1 SIMPLE_PINHOLE 1920 1080 1000 960 540
EOF

cat > "$OUTPUT_DIR/sparse/0/images.txt" << 'EOF'
# Image list with two lines of data per image:
#   IMAGE_ID, QW, QX, QY, QZ, TX, TY, TZ, CAMERA_ID, NAME
#   POINTS2D[] as (X, Y, POINT3D_ID)
1 1.0 0.0 0.0 0.0 0.0 0.0 0.0 1 image1.jpg

2 1.0 0.0 0.0 0.0 1.0 0.0 0.0 1 image2.jpg

EOF

cat > "$OUTPUT_DIR/sparse/0/points3D.txt" << 'EOF'
# 3D point list with one line of data per point:
#   POINT3D_ID, X, Y, Z, R, G, B, ERROR, TRACK[] as (IMAGE_ID, POINT2D_IDX)
1 0.0 0.0 0.0 255 255 255 0.5 1 0 2 1
2 1.0 0.0 0.0 255 0 0 0.5 1 1 2 2
3 0.0 1.0 0.0 0 255 0 0.5 1 2 2 3
EOF

# Create dummy dense reconstruction
cat > "$OUTPUT_DIR/dense/fused.ply" << 'EOF'
ply
format ascii 1.0
element vertex 3
property float x
property float y
property float z
property uchar red
property uchar green
property uchar blue
end_header
0.0 0.0 0.0 255 255 255
1.0 0.0 0.0 255 0 0
0.0 1.0 0.0 0 255 0
EOF

# Create dummy database
touch "$OUTPUT_DIR/database.db"

echo "=== DUMMY SfM PROCESSING COMPLETED ==="
echo "Created sparse reconstruction with 3 points"
echo "Created dense point cloud with 3 vertices"
echo "Output directory contents:"
find "$OUTPUT_DIR" -type f

echo "✅ SfM processing completed successfully (minimal test version)" 