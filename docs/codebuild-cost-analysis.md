# AWS CodeBuild Cost Analysis & Optimization Report

## Executive Summary

Your current setup uses AWS CodeBuild for building ML containers, which is costing more than expected. This analysis reveals specific opportunities to optimize costs while maintaining build reliability.

## Current Architecture Analysis

### 🏗️ Build Setup Overview
- **GitHub Actions** triggers **AWS CodeBuild** for container builds
- **CodeBuild Instance Type**: `build.general1.large` ($0.02/minute)
- **Container Count**: 3 large ML containers (SfM, 3DGS, Compressor)
- **Smart Change Detection**: Only builds changed containers
- **Build Environment**: Linux with Docker support, 15GB RAM, 8 vCPUs

### 💰 Cost Breakdown
**Current CodeBuild Pricing:**
- **LARGE Instance**: $0.02/minute ($1.20/hour)
- **Your Setup**: Privileged mode for Docker builds
- **Free Tier**: 100 minutes/month on SMALL instances (not applicable to your LARGE usage)

### 📊 Container Analysis

#### 1. **SfM Container** (Structure-from-Motion)
- **Base Image**: `python:3.9-slim`
- **Dependencies**: OpenCV, COLMAP, GPS processing libraries
- **Build Complexity**: Medium (C++ compilation required)
- **Estimated Build Time**: 15-25 minutes

#### 2. **3DGS Container** (3D Gaussian Splatting)
- **Base Image**: `nvidia/cuda:11.8.0-devel-ubuntu22.04`
- **Dependencies**: PyTorch with CUDA, large GPU libraries
- **Build Complexity**: High (CUDA compilation, large downloads)
- **Estimated Build Time**: 25-40 minutes

#### 3. **Compressor Container** (SOGS Compression)
- **Base Image**: `nvidia/cuda:12.9.1-runtime-ubuntu22.04`
- **Dependencies**: PyTorch, CuPy, CUDA libraries
- **Build Complexity**: High (GPU libraries, multiple PyTorch versions)
- **Estimated Build Time**: 20-35 minutes

## Cost Impact Analysis

### 🔍 Estimated Monthly Costs
Assuming typical development activity (2-3 builds per week):

**Current CodeBuild Usage:**
- **Average Build Time**: 30 minutes per container
- **Monthly Builds**: ~10 builds
- **Monthly Cost**: 10 builds × 30 minutes × $0.02 = **$6.00/month**

**If Building All 3 Containers:**
- **Total Build Time**: 90 minutes per full build
- **Monthly Cost**: 10 builds × 90 minutes × $0.02 = **$18.00/month**

### 📈 Cost Drivers
1. **LARGE Instance Requirement**: Necessary for Docker builds with sufficient RAM
2. **Complex Dependencies**: Long download/compilation times
3. **GPU Libraries**: Large PyTorch/CUDA downloads
4. **No Build Caching**: Each build downloads dependencies from scratch

## GitHub Actions Memory Limitations

### 💾 Runner Specifications
- **Standard Runner**: 7GB RAM, 2 vCPUs
- **Large Runner**: 16GB RAM, 4 vCPUs (paid accounts)
- **Your Issue**: GPU containers with PyTorch require significant memory

### 🚫 Why You Moved to CodeBuild
- PyTorch with CUDA downloads are memory-intensive
- Multiple simultaneous container builds exhaust GitHub Actions memory
- CodeBuild LARGE provides 15GB RAM vs GitHub's 7GB

## Optimization Strategies

### 💡 Strategy 1: Hybrid Build Approach
**Recommendation**: Use GitHub Actions for lightweight containers, CodeBuild for heavy ones

**Implementation:**
- **GitHub Actions**: SfM container (lightest, no GPU dependencies)
- **CodeBuild**: 3DGS and Compressor containers (GPU-heavy)

**Expected Savings**: ~30% reduction in CodeBuild usage

### 💡 Strategy 2: Enhanced Caching
**Current Gap**: No Docker layer caching between builds

**Recommendations:**
1. **CodeBuild Docker Layer Cache**: Enable Docker layer caching
2. **ECR Cache**: Use multi-stage builds with cached base images
3. **S3 Dependency Cache**: Cache downloaded wheels/packages

**Expected Savings**: 40-60% reduction in build times

### 💡 Strategy 3: Optimized Build Matrix
**Current Setup**: Builds all containers when deployment scripts change

**Optimization:**
```yaml
# Enhanced change detection
- name: Detect changed containers
  run: |
    # More granular change detection
    # Only build 'all' for critical infrastructure changes
    if echo "$CHANGED_FILES" | grep -q "Dockerfile\|requirements.txt"; then
      # Build only specific containers with changes
    fi
```

### 💡 Strategy 4: Resource Right-Sizing
**Current**: All builds use LARGE instances

**Optimization:**
- **SfM Container**: Could use MEDIUM instances ($0.01/minute)
- **GPU Containers**: Keep LARGE instances for memory requirements

**Expected Savings**: 50% cost reduction for SfM builds

## Implementation Roadmap

### 📋 Phase 1: Immediate Optimizations (0-2 weeks)
1. **Enable Docker Layer Caching** in CodeBuild
2. **Optimize Container Build Order** (lightest first)
3. **Implement Multi-stage Dockerfiles** for better caching

### 📋 Phase 2: Hybrid Strategy (2-4 weeks)
1. **Move SfM Container to GitHub Actions** with increased memory
2. **Implement Conditional Build Logic** based on container complexity
3. **Add Build Metrics Dashboard** for cost tracking

### 📋 Phase 3: Advanced Optimizations (4-8 weeks)
1. **Implement ECR Base Image Strategy** with pre-built dependencies
2. **Add S3 Dependency Caching** for Python packages
3. **Create Build Performance Monitoring** for continuous optimization

## Recommended Workflow

### 🔄 Smart Build Decision Tree
```
Container Change Detected
├── SfM Container (Light)
│   ├── RAM Required: <8GB → GitHub Actions
│   └── RAM Required: >8GB → CodeBuild MEDIUM
├── 3DGS Container (Heavy)
│   └── Always → CodeBuild LARGE
└── Compressor Container (Heavy)
    └── Always → CodeBuild LARGE
```

### 📊 Expected Cost Reduction
- **Immediate** (Phase 1): 25-40% reduction
- **Short-term** (Phase 2): 40-60% reduction  
- **Long-term** (Phase 3): 50-70% reduction

## Monitoring & Alerts

### 📈 Key Metrics to Track
1. **Build Duration per Container**
2. **CodeBuild Minutes Used per Month**
3. **Cost per Build**
4. **Build Success Rate**

### 🚨 Cost Control Alerts
- **Monthly CodeBuild Budget**: Set at $25/month
- **Long Build Alert**: >45 minutes per container
- **Failed Build Alert**: Multiple consecutive failures

## Alternative Approaches

### 🐳 Container Registry Optimization
- **Pre-built Base Images**: Create base images with common dependencies
- **Multi-arch Builds**: Build once, deploy anywhere
- **Registry Mirroring**: Use regional ECR repos for faster pulls

### ☁️ Spot Instance Strategy
- **CodeBuild Spot**: Not available for on-demand builds
- **Self-managed Builders**: EC2 Spot instances with custom build agents
- **Cost**: 60-80% savings but requires more management

## Conclusion

Your current CodeBuild setup is justified for the heavy GPU containers but can be optimized significantly. The hybrid approach combining GitHub Actions for lightweight builds and CodeBuild for heavy containers offers the best balance of cost and reliability.

**Recommended Next Steps:**
1. Implement Docker layer caching immediately
2. Move SfM container to GitHub Actions
3. Add cost monitoring dashboard
4. Review and optimize after 1 month

**Expected Outcome**: 40-60% reduction in CodeBuild costs while maintaining build reliability.