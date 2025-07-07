# 3D Gaussian Splatting Hyperparameter Tuning Guide

This guide explains how to tune the 23 hyperparameters in our 3DGS pipeline for optimal quality and performance.

## 🎯 Quick Start: Pre-configured Settings

### High-Quality Configuration (Default)
```python
HYPERPARAMETERS = {
    "sh_degree": 3,                    # Photorealistic view-dependent effects
    "max_iterations": 30000,           # Full convergence
    "densify_grad_threshold": 0.0002,  # High detail sensitivity
    "lambda_dssim": 0.2,              # Balanced texture preservation
    "target_psnr": 35.0,              # High quality target
}
```

### Fast Testing Configuration
```python
HYPERPARAMETERS = {
    "sh_degree": 1,                    # Reduced complexity
    "max_iterations": 5000,            # Quick convergence
    "densify_grad_threshold": 0.0005,  # Less sensitive
    "lambda_dssim": 0.1,              # Faster training
    "target_psnr": 28.0,              # Reasonable quality
}
```

### Ultra-High Quality Configuration
```python
HYPERPARAMETERS = {
    "sh_degree": 3,                    # Maximum view-dependent quality
    "max_iterations": 50000,           # Extended training
    "densify_grad_threshold": 0.0001,  # Maximum detail sensitivity
    "lambda_dssim": 0.3,              # Strong texture preservation
    "target_psnr": 38.0,              # Very high quality target
    "densification_interval": 50,      # More frequent densification
}
```

## 📊 Parameter Categories and Impact

### 1. Quality Control Parameters

#### `sh_degree` (Spherical Harmonics Degree) - **CRITICAL FOR QUALITY**
- **Range**: 0-3
- **Default**: 3
- **Impact**: Controls view-dependent effects (reflections, shininess)
  - `0`: Lambertian (matte) surfaces only
  - `1`: Basic view-dependent effects
  - `2`: Good view-dependent effects
  - `3`: Photorealistic view-dependent effects
- **Recommendation**: Always use `3` for final results

#### `lambda_dssim` (SSIM Loss Weight)
- **Range**: 0.0-1.0
- **Default**: 0.2
- **Impact**: Balances L1 loss vs SSIM loss
  - Higher values → Better texture preservation
  - Lower values → Faster convergence
- **Tuning**: Increase for scenes with fine textures

#### `target_psnr` (Peak Signal-to-Noise Ratio Target)
- **Range**: 25.0-40.0
- **Default**: 35.0
- **Impact**: Early stopping criterion
  - Higher values → Better quality but longer training
  - Lower values → Faster training but potentially lower quality

### 2. Densification Parameters - **KEY FOR DETAIL**

#### `densify_grad_threshold` - **MOST IMPORTANT FOR DETAIL**
- **Range**: 0.00005-0.001
- **Default**: 0.0002
- **Impact**: Controls when Gaussians are split for more detail
  - Lower values → More Gaussians → Higher detail → Slower training
  - Higher values → Fewer Gaussians → Less detail → Faster training
- **Tuning Tips**:
  - Complex scenes: 0.0001-0.00015
  - Simple scenes: 0.0003-0.0005
  - Ultra-detail: 0.00005-0.0001

#### `densification_interval`
- **Range**: 50-200
- **Default**: 100
- **Impact**: How often densification runs
  - Lower values → More frequent checks → Better adaptation
  - Higher values → Less frequent checks → Faster training

#### `densify_from_iter` / `densify_until_iter`
- **Defaults**: 500 / 15000
- **Impact**: When densification is active
- **Tuning**: Extend `densify_until_iter` for complex scenes

### 3. Training Duration

#### `max_iterations`
- **Range**: 5000-50000
- **Default**: 30000
- **Impact**: Total training time
- **Guidelines**:
  - Testing: 5000-10000
  - Production: 25000-35000
  - Ultra-quality: 40000-50000

### 4. Learning Rates (Advanced)

These are well-tuned defaults from gsplat research. Only modify if you understand the implications:

- `learning_rate`: 0.0025 (base rate)
- `position_lr_scale`: 0.00016 (Gaussian positions)
- `scaling_lr`: 0.005 (Gaussian sizes)
- `rotation_lr`: 0.001 (Gaussian orientations)
- `opacity_lr`: 0.05 (Gaussian transparency)
- `feature_lr`: 0.0025 (Gaussian colors/features)

## 🧪 Experimental Workflow

### Step 1: Start with Fast Testing
```python
# In test_full_pipeline_with_gps.py
EXPERIMENTAL_HYPERPARAMETERS = {
    "max_iterations": 5000,
    "sh_degree": 1,
    "target_psnr": 28.0,
}
```

### Step 2: Tune for Your Scene
Based on initial results, adjust:
- **Too blurry?** → Decrease `densify_grad_threshold`
- **Training too slow?** → Increase `densify_grad_threshold`
- **Poor textures?** → Increase `lambda_dssim`
- **Need reflections?** → Ensure `sh_degree` = 3

### Step 3: Scale to Production
Once satisfied with quality, increase:
- `max_iterations` to 25000-30000
- Consider lowering `densify_grad_threshold` slightly

## 🔍 Quality Assessment

### Metrics to Monitor
1. **PSNR**: Peak Signal-to-Noise Ratio (higher = better)
2. **SSIM**: Structural Similarity (closer to 1.0 = better)
3. **Gaussian Count**: Number of splats (more = higher detail but slower)

### Visual Quality Indicators
- **Sharp details**: Lower `densify_grad_threshold`
- **Smooth surfaces**: Proper learning rates
- **View-dependent effects**: `sh_degree` = 3
- **Texture preservation**: Higher `lambda_dssim`

## 📈 Performance vs Quality Trade-offs

| Priority | Configuration | Training Time | Quality |
|----------|---------------|---------------|---------|
| Speed | `sh_degree=1, max_iter=5000, threshold=0.0005` | ~30 min | Good |
| Balanced | `sh_degree=3, max_iter=25000, threshold=0.0002` | ~2 hours | Excellent |
| Ultimate | `sh_degree=3, max_iter=50000, threshold=0.0001` | ~4 hours | Outstanding |

## 🛠️ How to Use in Pipeline

### Method 1: Modify Test Script
```python
# In test_full_pipeline_with_gps.py
EXPERIMENTAL_HYPERPARAMETERS = {
    "sh_degree": 3,
    "densify_grad_threshold": 0.0001,  # Your custom value
    "max_iterations": 35000,
}
```

### Method 2: API Request
```python
payload = {
    "s3Url": "...",
    "hyperparameters": {
        "sh_degree": 3,
        "densify_grad_threshold": 0.0001,
    }
}
```

### Method 3: Use Presets
The Lambda includes intelligent defaults, so you can omit `hyperparameters` entirely for standard high-quality results.

## 🎯 Recommended Tuning Sequence

1. **Start**: Use defaults (high-quality preset)
2. **Assess**: Check initial results for quality/speed balance
3. **Adjust**: Modify 1-2 key parameters:
   - `densify_grad_threshold` for detail level
   - `max_iterations` for training time
   - `lambda_dssim` for texture quality
4. **Iterate**: Test and refine based on your specific scene requirements

## 📚 References

- [gsplat Documentation](https://docs.gsplat.studio/)
- [3D Gaussian Splatting Paper](https://repo-sam.inria.fr/fungraph/3d-gaussian-splatting/)
- [Nerfstudio gsplat Integration](https://github.com/nerfstudio-project/gsplat) 