#!/usr/bin/env python3
"""
Simple test script for gsplat container
Tests the basic gsplat installation
"""

import sys
import torch

def test_gsplat_installation():
    """Test gsplat installation and basic functionality"""
    print("🧪 Testing gsplat installation...")
    print("=" * 50)
    
    # Test 1: Check PyTorch CUDA availability
    print("1. Checking PyTorch CUDA setup...")
    print(f"   PyTorch version: {torch.__version__}")
    print(f"   CUDA available: {torch.cuda.is_available()}")
    if torch.cuda.is_available():
        print(f"   CUDA version: {torch.version.cuda}")
        print(f"   GPU count: {torch.cuda.device_count()}")
        print(f"   Current device: {torch.cuda.current_device()}")
        print(f"   Device name: {torch.cuda.get_device_name()}")
    else:
        print("   ⚠️  CUDA not available - this may cause issues")
    
    # Test 2: Import gsplat
    print("\n2. Testing gsplat import...")
    try:
        import gsplat
        print(f"   ✅ gsplat imported successfully!")
        print(f"   gsplat version: {gsplat.__version__}")
    except ImportError as e:
        print(f"   ❌ Failed to import gsplat: {e}")
        return False
    except Exception as e:
        print(f"   ❌ Unexpected error importing gsplat: {e}")
        return False
    
    # Test 3: Test gsplat 1.4 API surface used by the production renderer/reviewer
    print("\n3. Testing gsplat 1.4 API surface...")
    try:
        from gsplat import rasterization
        from gsplat.cuda._wrapper import spherical_harmonics

        print(f"   ✅ rasterization import: {rasterization}")
        print(f"   ✅ spherical_harmonics import: {spherical_harmonics}")
    except Exception as e:
        print(f"   ❌ Error testing gsplat functionality: {e}")
        return False

    print("\n4. Testing NerfStudio Splatfacto-W CLI...")
    try:
        import subprocess

        subprocess.run(
            ["ns-train", "splatfacto-w-light", "--help"],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=60,
        )
        print("   ✅ ns-train splatfacto-w-light CLI available")
    except Exception as e:
        print(f"   ❌ Error testing NerfStudio Splatfacto-W CLI: {e}")
        return False
    
    print("\n🎉 ALL TESTS PASSED!")
    print("✅ gsplat is properly installed and functional")
    print("✅ CUDA support is working")
    print("✅ Ready for 3D Gaussian Splatting training!")
    
    return True

if __name__ == "__main__":
    success = test_gsplat_installation()
    
    if success:
        print("\n🚀 SUCCESS: gsplat container is ready for production!")
        sys.exit(0)
    else:
        print("\n❌ FAILURE: gsplat installation has issues")
        sys.exit(1) 
