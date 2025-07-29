# PlayCanvas SOGS Compression Container

## Overview
Production-ready container for Self-Organizing Gaussian Splats (SOGS) compression using the official PlayCanvas SOGS implementation.

## Architecture
- **Base Image**: `nvidia/cuda:11.8.0-devel-ubuntu22.04` (SageMaker g4dn compatible)
- **PyTorch**: 2.0.1+cu118 (matches SageMaker driver 470.xx)
- **Core Dependencies**: 
  - `cupy-cuda11x` for GPU acceleration
  - `torchpq` for quantization
  - `PLAS` for parallel linear assignment sorting
  - `sogs` (official PlayCanvas package)

## Input/Output Format
- **Input**: PLY files with spherical harmonics (`f_dc_0`, `f_dc_1`, `f_dc_2`, `f_rest_X`)
- **Output**: WebP texture files + `meta.json` + SuperSplat viewer bundle
- **Compression**: 8-bit/16-bit quantization with WebP image compression

## Usage
```bash
# SageMaker Processing Job
python3 compress.py

# Direct usage
docker run spaceport/compressor:latest
```

## GPU Requirements
- **Instance Type**: `ml.g4dn.xlarge` (T4 GPU) or `ml.g5.xlarge` (A10G GPU)
- **Driver**: CUDA 11.8 compatible (SageMaker g4dn: 470.xx, g5: 525.xx)
- **Memory**: 16GB+ RAM recommended

## Diagnostics
The container includes comprehensive GPU diagnostics:
- PyTorch CUDA availability check
- Device information and capabilities
- System CUDA runtime verification
- Environment variable validation

## Performance
- **Compression Time**: 3-5 minutes for 250K gaussians
- **Compression Ratio**: 10-20x reduction
- **Output Size**: ~50-100MB for typical models

## Testing
```bash
# Run SOGS-only test
python tests/test_sogs_compression_only.py
```

## Viewer Integration
Compressed models can be viewed using the SuperSplat viewer at `/viewer.html` with S3 bundle URLs.

## Troubleshooting
If GPU detection fails:
1. Check SageMaker instance type (must be GPU-enabled)
2. Verify CUDA driver compatibility
3. Review diagnostic logs for detailed information
4. Ensure sufficient quota for GPU instances
