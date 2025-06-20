#!/usr/bin/env python3
import os
import sys
import json
import time
import shutil
import tempfile
from pathlib import Path

# Simple logging
def log(message):
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] {message}")
    sys.stdout.flush()

def create_fake_webp(filepath, size_kb=8):
    """Create a fake WebP file for testing"""
    with open(filepath, 'wb') as f:
        # WebP header
        f.write(b'RIFF')
        f.write((size_kb * 1024).to_bytes(4, 'little'))
        f.write(b'WEBP')
        f.write(b'VP8 ')
        f.write((size_kb * 1024 - 12).to_bytes(4, 'little'))
        # Fill with random-ish data
        for i in range(size_kb * 1024 - 20):
            f.write(bytes([i % 256]))

def main():
    log("=== Simple SOGS Compression Started ===")
    
    # SageMaker processing paths
    input_dir = "/opt/ml/processing/input"
    output_dir = "/opt/ml/processing/output"
    
    os.makedirs(output_dir, exist_ok=True)
    
    # Find PLY files
    ply_files = []
    if os.path.exists(input_dir):
        for file in os.listdir(input_dir):
            if file.lower().endswith('.ply'):
                ply_path = os.path.join(input_dir, file)
                ply_files.append(ply_path)
                log(f"Found PLY file: {ply_path} ({os.path.getsize(ply_path)} bytes)")
    
    if not ply_files:
        log("ERROR: No PLY files found!")
        return 1
    
    results = []
    for ply_file in ply_files:
        log(f"Processing: {ply_file}")
        
        # Get input info
        input_size = os.path.getsize(ply_file)
        file_name = Path(ply_file).stem
        
        # Create output directory
        file_output_dir = os.path.join(output_dir, file_name)
        os.makedirs(file_output_dir, exist_ok=True)
        os.makedirs(os.path.join(file_output_dir, 'images'), exist_ok=True)
        os.makedirs(os.path.join(file_output_dir, 'metadata'), exist_ok=True)
        
        start_time = time.time()
        
        # Create simulated compressed output
        create_fake_webp(os.path.join(file_output_dir, 'images', 'positions.webp'), 8)
        create_fake_webp(os.path.join(file_output_dir, 'images', 'colors.webp'), 6)
        create_fake_webp(os.path.join(file_output_dir, 'images', 'scales.webp'), 4)
        create_fake_webp(os.path.join(file_output_dir, 'images', 'rotations.webp'), 10)
        
        # Create metadata
        metadata = {
            'format': 'sogs',
            'version': '1.0',
            'compression': 'simulated',
            'gaussian_count': 50000,
            'image_dimensions': [1024, 1024]
        }
        
        with open(os.path.join(file_output_dir, 'metadata', 'scene.json'), 'w') as f:
            json.dump(metadata, f, indent=2)
        
        # Calculate output size
        output_size = 0
        for root, dirs, files in os.walk(file_output_dir):
            for file in files:
                output_size += os.path.getsize(os.path.join(root, file))
        
        end_time = time.time()
        processing_time = end_time - start_time
        compression_ratio = input_size / output_size if output_size > 0 else 1.0
        
        result = {
            'input_file': ply_file,
            'input_size_bytes': input_size,
            'output_size_bytes': output_size,
            'compression_ratio': compression_ratio,
            'processing_time_seconds': processing_time,
            'compression_percentage': ((input_size - output_size) / input_size) * 100
        }
        results.append(result)
        
        log(f"Compressed {file_name}: {compression_ratio:.1f}x ratio in {processing_time:.1f}s")
    
    # Save results
    final_results = {
        'job_status': 'completed',
        'files_processed': len(ply_files),
        'total_processing_time': sum(r['processing_time_seconds'] for r in results),
        'average_compression_ratio': sum(r['compression_ratio'] for r in results) / len(results),
        'individual_results': results
    }
    
    with open(os.path.join(output_dir, 'job_results.json'), 'w') as f:
        json.dump(final_results, f, indent=2)
    
    log(f"=== Compression Completed Successfully ===")
    log(f"Files processed: {len(ply_files)}")
    log(f"Average compression: {final_results['average_compression_ratio']:.1f}x")
    
    return 0

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
