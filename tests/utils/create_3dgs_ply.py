#!/usr/bin/env python3
"""
Create a proper 3D Gaussian Splatting PLY file for SOGS testing
"""

import numpy as np
import struct
from plyfile import PlyData, PlyElement
import boto3

def create_3dgs_ply():
    """Create a proper 3DGS PLY file with all required fields"""
    
    # Number of Gaussians
    num_gaussians = 1000
    
    # Generate random 3D positions
    positions = np.random.randn(num_gaussians, 3) * 2.0
    
    # Generate spherical harmonics coefficients (f_dc_0, f_dc_1, f_dc_2)
    # These represent the color in spherical harmonics basis
    f_dc_0 = np.random.randn(num_gaussians) * 0.5
    f_dc_1 = np.random.randn(num_gaussians) * 0.5  
    f_dc_2 = np.random.randn(num_gaussians) * 0.5
    
    # Generate additional SH coefficients (higher order terms)
    # Standard 3DGS uses up to 3rd order SH (16 coefficients per color channel)
    sh_coeffs = {}
    for i in range(3, 16):  # f_rest_0 to f_rest_44 (3 channels * 15 coeffs each)
        for c in range(3):  # RGB channels
            key = f"f_rest_{i-3 + c*15}"
            sh_coeffs[key] = np.random.randn(num_gaussians) * 0.1
    
    # Generate opacity (sigmoid activation, so pre-activation values)
    opacity = np.random.randn(num_gaussians) * 2.0
    
    # Generate scale parameters (log scale, so pre-activation values)
    scale_0 = np.random.randn(num_gaussians) * 1.0 - 2.0  # Start smaller
    scale_1 = np.random.randn(num_gaussians) * 1.0 - 2.0
    scale_2 = np.random.randn(num_gaussians) * 1.0 - 2.0
    
    # Generate rotation quaternions (normalized)
    rot_raw = np.random.randn(num_gaussians, 4)
    rot_norm = rot_raw / np.linalg.norm(rot_raw, axis=1, keepdims=True)
    rot_0 = rot_norm[:, 0]
    rot_1 = rot_norm[:, 1] 
    rot_2 = rot_norm[:, 2]
    rot_3 = rot_norm[:, 3]
    
    # Create the vertex data with proper dtypes
    vertex_data = []
    for i in range(num_gaussians):
        vertex = [
            positions[i, 0], positions[i, 1], positions[i, 2],  # x, y, z
            f_dc_0[i], f_dc_1[i], f_dc_2[i],  # f_dc_0, f_dc_1, f_dc_2
            opacity[i],  # opacity
            scale_0[i], scale_1[i], scale_2[i],  # scale_0, scale_1, scale_2
            rot_0[i], rot_1[i], rot_2[i], rot_3[i],  # rot_0, rot_1, rot_2, rot_3
        ]
        
        # Add SH coefficients
        for key in sorted(sh_coeffs.keys()):
            vertex.append(sh_coeffs[key][i])
            
        vertex_data.append(tuple(vertex))
    
    # Define the PLY element structure
    dtype_list = [
        ('x', 'f4'), ('y', 'f4'), ('z', 'f4'),
        ('f_dc_0', 'f4'), ('f_dc_1', 'f4'), ('f_dc_2', 'f4'),
        ('opacity', 'f4'),
        ('scale_0', 'f4'), ('scale_1', 'f4'), ('scale_2', 'f4'),
        ('rot_0', 'f4'), ('rot_1', 'f4'), ('rot_2', 'f4'), ('rot_3', 'f4'),
    ]
    
    # Add SH coefficient dtypes
    for key in sorted(sh_coeffs.keys()):
        dtype_list.append((key, 'f4'))
    
    # Create numpy array
    vertex_array = np.array(vertex_data, dtype=dtype_list)
    
    # Create PLY element
    vertex_element = PlyElement.describe(vertex_array, 'vertex')
    
    # Create PLY file
    ply_data = PlyData([vertex_element])
    
    return ply_data

def upload_to_s3(ply_data, filename):
    """Upload PLY data to S3"""
    # Write to local file first
    ply_data.write(filename)
    
    # Upload to S3
    s3_client = boto3.client('s3')
    bucket_name = 'spaceport-sagemaker-us-west-2'
    s3_key = f'test-data/{filename}'
    
    s3_client.upload_file(filename, bucket_name, s3_key)
    
    # Get file size
    import os
    file_size = os.path.getsize(filename)
    
    print(f"✅ Created 3DGS PLY file: {filename}")
    print(f"📊 File size: {file_size:,} bytes ({file_size/1024:.1f} KB)")
    print(f"📤 Uploaded to: s3://{bucket_name}/{s3_key}")
    
    return s3_key

if __name__ == "__main__":
    print("🚀 Creating proper 3D Gaussian Splatting PLY file...")
    
    # Create the PLY data
    ply_data = create_3dgs_ply()
    
    # Upload to S3
    s3_key = upload_to_s3(ply_data, '3dgs_sample.ply')
    
    print("🎉 3DGS PLY file ready for SOGS compression!")
    print(f"📍 S3 Location: {s3_key}") 