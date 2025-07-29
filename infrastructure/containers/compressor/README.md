# PlayCanvas SOGS Compression Container

This container implements **real** Self-Organizing Gaussian Splats (SOGS) compression using the official [PlayCanvas SOGS package](https://github.com/playcanvas/sogs).

## 🎯 What This Container Does

1. **Loads 3D Gaussian Splat PLY files** with proper spherical harmonics format
2. **Compresses using PlayCanvas SOGS** - the official implementation
3. **Generates WebP texture atlases** for different Gaussian parameters
4. **Creates metadata.json** with compression information
5. **Builds SuperSplat viewer bundles** for immediate use

## 🏗️ Architecture

### Dependencies (Official PlayCanvas SOGS Requirements)
- **PyTorch** with CUDA 12.1 support
- **CuPy** for GPU acceleration
- **TorchPQ** for quantization
- **PLAS** (Parallel Linear Assignment Sorting)
- **PlayCanvas SOGS** package from GitHub

### GPU Requirements
- **Instance Type**: ml.g4dn.xlarge (recommended)
- **GPU**: NVIDIA T4 with CUDA 12.x support
- **Memory**: 16GB GPU memory minimum

## 📊 Input Format Requirements

The container expects 3D Gaussian Splat PLY files with these fields:

```
property float x, y, z                    # Positions
property float f_dc_0, f_dc_1, f_dc_2     # Spherical harmonics DC
property float opacity                     # Opacity values
property float scale_0, scale_1, scale_2  # Scale parameters
property float rot_0, rot_1, rot_2, rot_3 # Quaternion rotations
property float f_rest_* (optional)         # Higher-order SH
```

## 🎨 Output Format

### WebP Texture Files
- `means.webp` - Position data texture
- `scales.webp` - Scale parameter texture  
- `quats.webp` - Rotation quaternion texture
- `sh0.webp` - Color + opacity RGBA texture
- `shN_centroids.webp` & `shN_labels.webp` - Higher-order SH (if present)

### Metadata Files
- `meta.json` - Compression metadata and parameters
- `settings.json` - SuperSplat viewer settings

### SuperSplat Bundle
The container automatically creates a `supersplat_bundle/` directory with:
- All WebP textures
- Metadata files
- Viewer settings
- Ready for use with SuperSplat viewer

## 🚀 Usage

### Via SageMaker Processing Job
```python
sagemaker.create_processing_job(
    ProcessingJobName='sogs-compression-job',
    RoleArn='arn:aws:iam::account:role/SageMakerExecutionRole',
    AppSpecification={
        'ImageUri': 'account.dkr.ecr.region.amazonaws.com/spaceport/compressor:latest'
    },
    ProcessingInputs=[{
        'InputName': 'input',
        'S3Input': {
            'S3Uri': 's3://bucket/path/to/3dgs-output/',
            'LocalPath': '/opt/ml/processing/input'
        }
    }],
    ProcessingOutputs=[{
        'OutputName': 'compressed',
        'S3Output': {
            'S3Uri': 's3://bucket/path/to/compressed-output/',
            'LocalPath': '/opt/ml/processing/output'
        }
    }],
    ProcessingResources={
        'ClusterConfig': {
            'InstanceType': 'ml.g4dn.xlarge',
            'InstanceCount': 1
        }
    }
)
```

### Direct CLI (for testing)
```bash
# Inside container
sogs-compress --ply final_model.ply --output-dir /output/
```

## 🔧 Implementation Details

### SOGS Algorithm Steps
1. **PLY Loading**: Parse 3D Gaussian splat data
2. **Validation**: Verify required fields for SOGS compatibility
3. **PLAS Sorting**: Apply Parallel Linear Assignment Sorting
4. **Parameter Preprocessing**: Transform data for compression
5. **Texture Generation**: Create WebP atlases for each parameter
6. **Metadata Creation**: Generate compression metadata
7. **Bundle Assembly**: Package for SuperSplat viewer

### Compression Techniques
- **8-bit Quantization** for most parameters
- **16-bit Quantization** for positions (higher precision)
- **K-means Clustering** for higher-order spherical harmonics
- **Quaternion Packing** for rotation data
- **Lossless WebP** compression for all textures

## 📈 Expected Performance

### Compression Ratios
- **Small Models** (< 100k Gaussians): 3-5x compression
- **Medium Models** (100k-500k Gaussians): 5-10x compression  
- **Large Models** (> 500k Gaussians): 10-20x compression

### Processing Times
- **Setup**: 2-3 minutes (dependency loading)
- **Compression**: 5-15 minutes (depending on model size)
- **Output**: 1-2 minutes (S3 upload)

## 🧪 Testing

Use the included test script:
```bash
cd /path/to/repo
python3 tests/test_sogs_compression_only.py
```

This will:
1. Verify the latest 3DGS training output
2. Run SOGS compression
3. Validate WebP texture generation
4. Check SuperSplat bundle creation
5. Provide viewer URL for testing

## 🔗 Integration with SuperSplat Viewer

The compressed output can be directly loaded in our SuperSplat viewer:

1. Navigate to `/viewer.html` on the website
2. Enter the S3 URL: `s3://bucket/path/supersplat_bundle/`
3. Click "Load 3D Model"
4. View the compressed model in real-time

## 📚 References

- [PlayCanvas SOGS Repository](https://github.com/playcanvas/sogs)
- [SuperSplat Viewer](https://github.com/playcanvas/supersplat-viewer)
- [Self-Organizing Gaussians Paper](https://github.com/fraunhoferhhi/Self-Organizing-Gaussians)
- [PLAS Algorithm](https://github.com/fraunhoferhhi/PLAS)

## 🛠️ Development

### Building Locally
```bash
cd infrastructure/containers/compressor/
docker build -t spaceport/compressor:latest .
```

### Testing Container
```bash
docker run --gpus all -it spaceport/compressor:latest sogs-compress --help
```

---

**Status**: Production Ready 🚀  
**Last Updated**: July 29, 2025  
**Version**: 2.0 (PlayCanvas SOGS Implementation)
