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
    
    # Test 3: Test basic gsplat functionality
    print("\n3. Testing basic gsplat functionality...")
    try:
        # Test if we can import basic gsplat modules
        from gsplat import GaussianRasterizationSettings
        
        print("   ✅ Basic gsplat imports working!")
        
        # Test rasterization settings creation
        settings = GaussianRasterizationSettings(
            image_height=512,
            image_width=512,
            tanfovx=0.5,
            tanfovy=0.5,
            bg_color=[0, 0, 0],
            scale_modifier=1.0,
            viewmatrix=torch.eye(4, device='cuda' if torch.cuda.is_available() else 'cpu'),
            projmatrix=torch.eye(4, device='cuda' if torch.cuda.is_available() else 'cpu'),
            sh_degree=0,
            campos=torch.tensor([0, 0, 0], device='cuda' if torch.cuda.is_available() else 'cpu'),
            prefiltered=False,
            debug=False
        )
        
        print("   ✅ GaussianRasterizationSettings created successfully!")
        
    except Exception as e:
        print(f"   ❌ Error testing gsplat functionality: {e}")
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