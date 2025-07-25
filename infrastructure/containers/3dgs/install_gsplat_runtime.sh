#!/bin/bash

# =============================================================================
# gsplat Runtime Installation Script
# =============================================================================
# This script installs gsplat with CUDA support when the container runs
# on an actual GPU instance (SageMaker ml.g4dn.xlarge)
#
# Advantages:
# - GPU runtime is available for CUDA compilation
# - Guaranteed CUDA toolkit access
# - Can detect actual GPU architecture
# =============================================================================

set -e  # Exit on any error

echo "🚀 Starting gsplat runtime installation..."
echo "📅 $(date)"
echo "🖥️  Instance type: ${SM_CURRENT_INSTANCE_TYPE:-unknown}"

# Check if gsplat is already installed
if python3 -c "import gsplat" 2>/dev/null; then
    echo "✅ gsplat already installed, verifying CUDA support..."
    if python3 -c "import gsplat; print('✅ gsplat CUDA rasterization:', hasattr(gsplat, 'rasterization'))" 2>/dev/null; then
        echo "✅ gsplat with CUDA support is ready!"
        exit 0
    else
        echo "⚠️  gsplat installed but missing CUDA support, reinstalling..."
        pip uninstall -y gsplat || true
    fi
fi

# Verify GPU availability
echo "🔍 Checking GPU availability..."
python3 -c "import torch; print('PyTorch CUDA available:', torch.cuda.is_available()); print('CUDA device count:', torch.cuda.device_count())"

if ! python3 -c "import torch; assert torch.cuda.is_available()" 2>/dev/null; then
    echo "❌ ERROR: CUDA not available in PyTorch - cannot install gsplat with GPU support"
    echo "❌ This should not happen on ml.g4dn.xlarge instances"
    exit 1
fi

# Check nvidia-smi
echo "🔍 Checking NVIDIA driver..."
nvidia-smi || echo "⚠️  nvidia-smi not available, but PyTorch CUDA works"

# Set CUDA environment variables
echo "🔧 Setting CUDA environment variables..."
export CUDA_HOME=/usr/local/cuda
export PATH=$CUDA_HOME/bin:$PATH
export LD_LIBRARY_PATH=$CUDA_HOME/lib64:$LD_LIBRARY_PATH
export TORCH_CUDA_ARCH_LIST="7.5"  # T4 GPU architecture
export FORCE_CUDA=1
export MAX_JOBS=4  # Limit parallel compilation to avoid memory issues

echo "🔧 CUDA_HOME: $CUDA_HOME"
echo "🔧 TORCH_CUDA_ARCH_LIST: $TORCH_CUDA_ARCH_LIST"

# Verify CUDA compiler
if which nvcc >/dev/null 2>&1; then
    echo "✅ nvcc found: $(nvcc --version | grep 'release')"
else
    echo "⚠️  nvcc not found in PATH, but proceeding anyway"
fi

# Install gsplat from source with robust error handling
echo "🔧 Installing gsplat from source..."
INSTALL_START=$(date +%s)

# Create temporary directory
TEMP_DIR=$(mktemp -d)
cd "$TEMP_DIR"

# Clone gsplat repository
echo "📥 Cloning gsplat repository..."
if ! git clone --recursive https://github.com/nerfstudio-project/gsplat.git; then
    echo "❌ Failed to clone gsplat repository"
    cd / && rm -rf "$TEMP_DIR"
    exit 1
fi

cd gsplat

# Install with detailed logging
echo "🔨 Compiling gsplat with CUDA support..."
if pip install . --no-cache-dir --verbose; then
    INSTALL_END=$(date +%s)
    INSTALL_TIME=$((INSTALL_END - INSTALL_START))
    echo "✅ gsplat installation completed in ${INSTALL_TIME} seconds"
else
    echo "❌ gsplat installation failed"
    cd / && rm -rf "$TEMP_DIR"
    exit 1
fi

# Cleanup
cd /
rm -rf "$TEMP_DIR"

# Verify installation
echo "🔍 Verifying gsplat installation..."
if python3 -c "import gsplat; print('✅ gsplat imported successfully')"; then
    echo "✅ gsplat import: SUCCESS"
else
    echo "❌ gsplat import: FAILED"
    exit 1
fi

if python3 -c "import gsplat; print('✅ gsplat rasterization available:', hasattr(gsplat, 'rasterization'))"; then
    echo "✅ gsplat CUDA rasterization: AVAILABLE"
else
    echo "❌ gsplat CUDA rasterization: NOT AVAILABLE"
    exit 1
fi

# Final verification with GPU
echo "🎯 Final GPU compatibility test..."
if python3 -c "
import torch
import gsplat
print('✅ PyTorch CUDA:', torch.cuda.is_available())
print('✅ GPU device:', torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'None')
print('✅ gsplat version:', getattr(gsplat, '__version__', 'unknown'))
print('✅ gsplat rasterization function:', hasattr(gsplat, 'rasterization'))
"; then
    echo "🎉 gsplat runtime installation: COMPLETE SUCCESS!"
    echo "⏱️  Ready for 3D Gaussian Splatting training"
else
    echo "❌ Final verification failed"
    exit 1
fi 