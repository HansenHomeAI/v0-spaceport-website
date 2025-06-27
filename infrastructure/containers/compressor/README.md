# SOGS Compression Container

Production-ready container for SOGS (Spatial Octree Gaussian Splatting) compression using GPU acceleration.

## Features
- Pure PlayCanvas SOGS implementation
- GPU-accelerated compression using CUDA
- No fallback modes - fails fast if GPU unavailable
- Optimized for ml.g4dn.xlarge instances

## Build Status
- ✅ Docker Hub authentication configured
- ✅ GPU quota approved (ml.g4dn.xlarge)
- 🔄 Testing Docker Hub rate limit fix...

## Overview

The container replaces the previous simulation-based compression with actual SOGS compression, providing:
- **Real compression** using the PlayCanvas SOGS library
- **Up to 20x compression ratios** (as demonstrated by PlayCanvas)
- **Production-ready implementation** with comprehensive error handling
- **S3 integration** for SageMaker Processing Jobs
- **Structured logging** with detailed reports

## Architecture

```
Input PLY File (S3) → SOGS Compression → Compressed Output (S3)
                          ↓
                    WebP Images + Metadata
```

### Key Components

1. **SOGSCompressor Class**: Manages the compression workflow
2. **S3Manager Class**: Handles S3 upload/download operations  
3. **Compression Pipeline**: PLY validation → SOGS compression → Result analysis
4. **Comprehensive Reporting**: JSON and text reports with detailed metrics

## Files

- `Dockerfile` - Full CUDA-enabled production container
- `Dockerfile.minimal` - CPU-only container for testing
- `compress_model.py` - Main compression script with SOGS integration
- `requirements.txt` - Python dependencies
- `test_sogs_local.py` - Local testing script
- `README.md` - This documentation

## Dependencies

### System Requirements
- **CUDA 12.6** (for production container)
- **Python 3.9+**
- **NVIDIA GPU** (ml.c6i.4xlarge instances have GPU support)

### Python Libraries
- **torch** with CUDA support
- **cupy-cuda12x** for GPU acceleration
- **torchpq** for quantization
- **PLAS** (Parallel Linear Assignment Sorting)
- **sogs** (PlayCanvas SOGS library)
- **boto3** for AWS S3 integration
- **structlog** for structured logging

## Usage

### Environment Variables

The container expects standard SageMaker Processing Job environment variables:

```bash
SM_CHANNEL_INPUT=/opt/ml/processing/input      # Input directory
SM_OUTPUT_DATA_DIR=/opt/ml/processing/output   # Output directory  
SM_CURRENT_HOST=processing-job-name            # Job identifier
```

Optional S3 URIs for direct S3 integration:
```bash
S3_INPUT_URI=s3://bucket/path/to/input/
S3_OUTPUT_URI=s3://bucket/path/to/output/
```

### Input Format

The container expects PLY files in the input directory:
```
/opt/ml/processing/input/
├── model.ply          # 3D Gaussian Splat in PLY format
└── metadata.json      # Optional metadata
```

### Output Format

The container produces compressed outputs:
```
/opt/ml/processing/output/
├── compressed_images/         # WebP compressed attribute images
│   ├── positions.webp
│   ├── scales.webp  
│   ├── rotations.webp
│   ├── colors.webp
│   └── opacities.webp
├── metadata.json             # Compression metadata
├── compression_report.json   # Detailed compression report
└── compression_report.txt    # Human-readable report
```

## Testing

### Local Testing

Run the local test script to validate functionality:

```bash
cd infrastructure/containers/compressor
python3 test_sogs_local.py
```

This will:
1. Create a test PLY file
2. Run the compression script locally
3. Validate outputs and reports
4. Test Docker container build

### Manual Testing

Test the compression script directly:

```bash
# Set environment variables
export SM_CHANNEL_INPUT=/path/to/input
export SM_OUTPUT_DATA_DIR=/path/to/output  
export SM_CURRENT_HOST=test-job

# Run compression
python3 compress_model.py
```

## Deployment

### Option 1: Use Deployment Script

```bash
# Deploy full CUDA-enabled version
./scripts/deployment/deploy_sogs_container.sh

# Deploy minimal CPU version for testing
./scripts/deployment/deploy_sogs_container.sh --minimal

# Test only (no deployment)
./scripts/deployment/deploy_sogs_container.sh --test-only
```

### Option 2: Manual Deployment

```bash
# Build container
docker build -t sogs-compressor .

# Tag for ECR
docker tag sogs-compressor:latest $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/spaceport-ml-sogs-compressor:latest

# Push to ECR
docker push $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/spaceport-ml-sogs-compressor:latest
```

## Integration with ML Pipeline

Update your CDK stack to use the new container:

```python
# In ml_pipeline_stack.py
compression_job = sagemaker.ProcessingJob(
    self, "CompressionJob",
    definition=sagemaker.ProcessingJobDefinition(
        container=sagemaker.ContainerDefinition(
            image_uri=f"{account_id}.dkr.ecr.{region}.amazonaws.com/spaceport-ml-sogs-compressor:latest",
            # ... other configuration
        )
    )
)
```

## Performance Expectations

Based on PlayCanvas SOGS benchmarks:

| Metric | Expected Value |
|--------|----------------|
| Compression Ratio | 10x - 20x |
| Processing Time | 15-30 minutes for typical scenes |
| Instance Type | ml.c6i.4xlarge (16 vCPUs, 32 GB RAM) |
| Memory Usage | ~8-16 GB for large scenes |

## Troubleshooting

### Common Issues

1. **CUDA Not Available**
   - Use `Dockerfile.minimal` for CPU-only testing
   - Ensure SageMaker instance has GPU support

2. **SOGS Installation Failed**
   - Check internet connectivity in container
   - Verify CUDA version compatibility

3. **PLY File Invalid**
   - Validate PLY format meets 3D Gaussian Splat specifications
   - Check file is not corrupted during S3 transfer

4. **Out of Memory**
   - Reduce PLY file size or split into chunks
   - Use larger SageMaker instance type

### Logging

The container uses structured logging. Check CloudWatch logs for:
- Input validation results
- SOGS compression progress
- S3 transfer status
- Error details with stack traces

### Debug Mode

Set environment variable for verbose logging:
```bash
export LOG_LEVEL=DEBUG
```

## Comparison with Previous Implementation

| Aspect | Previous (Simulation) | New (Real SOGS) |
|--------|----------------------|-----------------|
| Compression | Fake/simulated | Real SOGS algorithm |
| Output Format | Custom `.gsplat` files | WebP images + metadata |
| Compression Ratio | Fixed ~4x simulation | Real 10x-20x |
| Processing Time | 2-3 minutes (fake) | 15-30 minutes (real) |
| Dependency | Minimal | CUDA + SOGS ecosystem |
| Validation | Basic | Comprehensive PLY validation |

## Future Enhancements

1. **Batch Processing**: Support multiple PLY files in single job
2. **Progressive Compression**: Different quality levels
3. **Real-time Progress**: WebSocket progress updates
4. **Automatic Scaling**: Dynamic instance selection based on file size
5. **Caching**: Avoid recompressing identical files

## Contributing

When modifying the container:

1. Test locally first: `python3 test_sogs_local.py`
2. Test minimal build: `docker build -f Dockerfile.minimal -t test .`
3. Update documentation if changing interfaces
4. Validate with real PLY files before deployment

## Resources

- [PlayCanvas SOGS Repository](https://github.com/playcanvas/sogs)
- [PlayCanvas SOGS Blog Post](https://blog.playcanvas.com/playcanvas-adopts-sogs-for-20x-3dgs-compression)
- [3D Gaussian Splatting Paper](https://repo-sam.inria.fr/fungraph/3d-gaussian-splatting/)
- [AWS SageMaker Processing Jobs](https://docs.aws.amazon.com/sagemaker/latest/dg/processing-job.html) # Container build triggered at Fri Jun 27 13:18:17 MDT 2025
