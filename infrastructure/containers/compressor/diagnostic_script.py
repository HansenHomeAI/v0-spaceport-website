#!/usr/bin/env python3
"""
Simple diagnostic script for SOGS compression container
"""

import sys
import os
import subprocess

def main():
    print("=== CONTAINER DIAGNOSTICS ===")
    print(f"Python version: {sys.version}")
    print(f"Working directory: {os.getcwd()}")
    
    print("\n=== ENVIRONMENT VARIABLES ===")
    env_vars = ['CUDA_HOME', 'CUDA_VISIBLE_DEVICES', 'NVIDIA_VISIBLE_DEVICES', 'PATH', 'LD_LIBRARY_PATH']
    for key in env_vars:
        value = os.environ.get(key, 'Not set')
        print(f"  {key}: {value}")
    
    print("\n=== GPU DIAGNOSTICS ===")
    try:
        import torch
        print(f"PyTorch version: {torch.__version__}")
        print(f"CUDA available: {torch.cuda.is_available()}")
        if torch.cuda.is_available():
            print(f"CUDA device count: {torch.cuda.device_count()}")
            print(f"Device name: {torch.cuda.get_device_name(0)}")
    except Exception as e:
        print(f"PyTorch error: {e}")
    
    print("\n=== SYSTEM DIAGNOSTICS ===")
    try:
        result = subprocess.run(['nvidia-smi'], capture_output=True, text=True, timeout=10)
        print(f"nvidia-smi return code: {result.returncode}")
        if result.stdout:
            print("nvidia-smi output:")
            print(result.stdout[:500] + "..." if len(result.stdout) > 500 else result.stdout)
        if result.stderr:
            print(f"nvidia-smi stderr: {result.stderr}")
    except Exception as e:
        print(f"nvidia-smi error: {e}")
    
    print("\n=== SOGS DIAGNOSTICS ===")
    try:
        result = subprocess.run(['sogs-compress', '--help'], capture_output=True, text=True, timeout=10)
        print(f"sogs-compress return code: {result.returncode}")
        if result.stdout:
            print("sogs-compress help output:")
            print(result.stdout[:500] + "..." if len(result.stdout) > 500 else result.stdout)
        if result.stderr:
            print(f"sogs-compress stderr: {result.stderr}")
    except Exception as e:
        print(f"sogs-compress error: {e}")
    
    print("\n=== FILE SYSTEM DIAGNOSTICS ===")
    print(f"Current directory contents:")
    try:
        for item in os.listdir('.'):
            print(f"  {item}")
    except Exception as e:
        print(f"Error listing directory: {e}")
    
    print("\n=== DIAGNOSTICS COMPLETE ===")

if __name__ == "__main__":
    main() 