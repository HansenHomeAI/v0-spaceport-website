#!/usr/bin/env python3
"""
Build gsplat wheel once and cache in S3 for future use.
This avoids the 15-20 minute compilation time on every container build.
"""

import subprocess
import boto3
import os
import sys
from pathlib import Path

def build_gsplat_wheel():
    """Build gsplat wheel with CUDA 11.8 support"""
    print("🔨 Building gsplat wheel with CUDA 11.8...")
    
    # Install build dependencies
    subprocess.run([
        "pip", "install", "--upgrade", "pip", "wheel", "setuptools"
    ], check=True)
    
    # Install CUDA compiler
    subprocess.run([
        "apt-get", "update"
    ], check=True)
    
    subprocess.run([
        "apt-get", "install", "-y", "cuda-nvcc-11-8"
    ], check=True)
    
    # Set CUDA environment
    os.environ["CUDA_HOME"] = "/usr/local/cuda"
    os.environ["PATH"] = f"{os.environ['CUDA_HOME']}/bin:{os.environ['PATH']}"
    os.environ["LD_LIBRARY_PATH"] = f"{os.environ['CUDA_HOME']}/lib64:{os.environ.get('LD_LIBRARY_PATH', '')}"
    os.environ["TORCH_CUDA_ARCH_LIST"] = "7.5"
    
    # Build gsplat wheel
    print("📦 Building gsplat wheel...")
    result = subprocess.run([
        "pip", "wheel", "gsplat==1.5.3", "--no-deps", "--wheel-dir", "/tmp/wheels"
    ], capture_output=True, text=True)
    
    if result.returncode != 0:
        print(f"❌ Failed to build gsplat wheel: {result.stderr}")
        sys.exit(1)
    
    # Find the built wheel
    wheel_files = list(Path("/tmp/wheels").glob("gsplat*.whl"))
    if not wheel_files:
        print("❌ No gsplat wheel found after build")
        sys.exit(1)
    
    wheel_path = wheel_files[0]
    print(f"✅ Built gsplat wheel: {wheel_path}")
    return wheel_path

def upload_to_s3(wheel_path):
    """Upload wheel to S3 for caching"""
    print("☁️ Uploading wheel to S3...")
    
    s3 = boto3.client('s3')
    bucket_name = "spaceport-build-cache"
    key = f"wheels/gsplat-1.5.3-cu118.whl"
    
    try:
        s3.upload_file(str(wheel_path), bucket_name, key)
        print(f"✅ Uploaded to s3://{bucket_name}/{key}")
        return f"s3://{bucket_name}/{key}"
    except Exception as e:
        print(f"❌ Failed to upload to S3: {e}")
        sys.exit(1)

def main():
    """Main function"""
    print("🚀 Building and caching gsplat wheel...")
    
    # Build the wheel
    wheel_path = build_gsplat_wheel()
    
    # Upload to S3
    s3_url = upload_to_s3(wheel_path)
    
    print(f"🎉 Success! Wheel cached at: {s3_url}")
    print("💡 Future builds can download this wheel instead of compiling")

if __name__ == "__main__":
    main() 