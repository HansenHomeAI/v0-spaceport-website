#!/usr/bin/env python3
"""
Create a simple test PLY file for compression testing
"""

import numpy as np
import random

def create_test_ply(filename='sample.ply', num_points=10000):
    """Create a simple PLY file with random 3D points and colors"""
    
    # Generate random 3D points
    points = np.random.uniform(-10, 10, (num_points, 3)).astype(np.float32)
    
    # Generate random colors (0-255)
    colors = np.random.randint(0, 256, (num_points, 3), dtype=np.uint8)
    
    # Generate random normals
    normals = np.random.uniform(-1, 1, (num_points, 3)).astype(np.float32)
    # Normalize
    norms = np.linalg.norm(normals, axis=1, keepdims=True)
    normals = normals / (norms + 1e-8)
    
    # Write PLY file
    with open(filename, 'w') as f:
        # Write header
        f.write("ply\n")
        f.write("format ascii 1.0\n")
        f.write(f"element vertex {num_points}\n")
        f.write("property float x\n")
        f.write("property float y\n")
        f.write("property float z\n")
        f.write("property float nx\n")
        f.write("property float ny\n")
        f.write("property float nz\n")
        f.write("property uchar red\n")
        f.write("property uchar green\n")
        f.write("property uchar blue\n")
        f.write("end_header\n")
        
        # Write vertex data
        for i in range(num_points):
            x, y, z = points[i]
            nx, ny, nz = normals[i]
            r, g, b = colors[i]
            f.write(f"{x:.6f} {y:.6f} {z:.6f} {nx:.6f} {ny:.6f} {nz:.6f} {r} {g} {b}\n")
    
    print(f"Created {filename} with {num_points} points")
    
    # Print file size
    import os
    size = os.path.getsize(filename)
    print(f"File size: {size} bytes ({size/1024:.1f} KB)")

if __name__ == "__main__":
    create_test_ply() 