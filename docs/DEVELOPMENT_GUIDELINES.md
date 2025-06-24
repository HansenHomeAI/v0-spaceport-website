# 🛠️ Development Guidelines for AI Assistants

> **MANDATORY READING**: These guidelines MUST be followed by all AI assistants working on this codebase to maintain consistency and prevent regression.

## 🚨 **CRITICAL RULES - NEVER VIOLATE**

### **Container Architecture** ❌ **NEVER DO:**
1. Create multiple Dockerfiles in the same container directory
2. Add experimental containers without explicit user approval  
3. Create files ending in `.test`, `.dev`, `.optimized`, `.backup`, `.old`
4. Use local Docker builds on Mac (known platform issues)
5. Modify container entry points without full pipeline understanding

### **Container Architecture** ✅ **ALWAYS DO:**
1. Use the single existing Dockerfile in each container directory
2. Build containers via GitHub Actions (`.github/workflows/build-containers.yml`)
3. Use `--platform linux/amd64` for all container builds
4. Update documentation when making architectural changes
5. Test changes through the standardized build process

## 📁 **File Organization Standards**

### **Documentation Files**
- **Location**: ALL documentation goes in `docs/` directory
- **Never Create**: Documentation files in project root
- **Structure**: 
  ```
  docs/
  ├── CONTAINER_ARCHITECTURE.md    # ⚡ CRITICAL reference
  ├── PROJECT_STATUS.md            # Current status
  ├── README_ML_PIPELINE.md        # ML pipeline details
  └── [other guides]
  ```

### **Container Structure** 
```
infrastructure/containers/
├── sfm/
│   ├── Dockerfile               # ✅ ONLY Dockerfile
│   └── run_colmap_production.sh # Production script
├── 3dgs/  
│   ├── Dockerfile               # ✅ ONLY Dockerfile
│   └── train_gaussian_production.py # Production script
└── compressor/
    ├── Dockerfile               # ✅ ONLY Dockerfile
    └── compress.py              # Production script (NOT compress_model.py)
```

### **Test Organization**
```
tests/
├── pipeline/                    # End-to-end pipeline tests
├── containers/                  # Container-specific tests
└── utils/                       # Test utilities
```

## 🔧 **Build & Deployment Process**

### **Primary Build Method: GitHub Actions**
- **File**: `.github/workflows/build-containers.yml`
- **Trigger**: Manual or container file changes
- **Environment**: Ubuntu Linux (native linux/amd64)
- **Process**: ECR login → Build → Tag → Push

### **Local Development Script**
- **File**: `scripts/deployment/deploy.sh`
- **Usage**: `./scripts/deployment/deploy.sh [sfm|3dgs|compressor|all]`
- **Platform**: Includes `--platform linux/amd64` flag
- **Warning**: May fail on Mac due to Docker Desktop issues

### **Infrastructure Deployment**
- **File**: `.github/workflows/cdk-deploy.yml`  
- **Trigger**: Push to main branch
- **Process**: CDK bootstrap → Deploy stacks
- **Stacks**: SpaceportStack, SpaceportMLPipelineStack

## 📊 **Quality Assurance Standards**

### **Before Making Changes**
1. **Read** `docs/CONTAINER_ARCHITECTURE.md` thoroughly
2. **Understand** the current production architecture
3. **Plan** changes without breaking existing patterns
4. **Document** any architectural modifications

### **After Making Changes**
1. **Test** via GitHub Actions (not local builds)
2. **Validate** containers build successfully
3. **Update** relevant documentation
4. **Verify** end-to-end pipeline still works

### **Container Validation Checklist**
- [ ] Single Dockerfile per container directory
- [ ] No duplicate or experimental files
- [ ] Builds with `--platform linux/amd64`
- [ ] Pushes to ECR successfully
- [ ] Entry points use production scripts

## 🎯 **Production Readiness Criteria**

### **Container Requirements**
- **SfM**: 15-30 minute runtime (not 2-3 minutes)
- **3DGS**: 1-2 hour runtime (not 90 seconds)  
- **Compressor**: 10-15 minute runtime with real compression
- **Integration**: All three work together in Step Functions

### **Code Quality Requirements**
- **Organization**: Clean directory structure maintained
- **Documentation**: Up-to-date and comprehensive
- **Build Process**: Standardized and automated
- **Testing**: Comprehensive validation pipeline

## 🚨 **Common Pitfalls to Avoid**

### **"Let me create an optimized version" Trap**
- **Problem**: Adding experimental containers alongside production ones
- **Solution**: Modify existing containers or get explicit approval for new ones

### **"Local build isn't working" Trap**  
- **Problem**: Trying to fix Mac Docker issues locally
- **Solution**: Use GitHub Actions for all container builds

### **"Quick test file" Trap**
- **Problem**: Creating temporary files that become permanent
- **Solution**: Use `tests/` directory and clean up afterwards

### **"Multiple approaches" Trap**
- **Problem**: Creating several ways to do the same thing
- **Solution**: Maintain single source of truth for each process

## 📝 **Documentation Maintenance**

### **When to Update Documentation**
- Adding new containers or modifying existing ones
- Changing build processes or deployment methods  
- Updating infrastructure or architectural patterns
- Fixing critical issues or implementing major features

### **Which Documents to Update**
- `docs/CONTAINER_ARCHITECTURE.md` - For container changes
- `docs/PROJECT_STATUS.md` - For status updates
- `README.md` - For major architectural changes
- `.cursorrules` - For development rule changes

## 🔍 **Debugging & Troubleshooting**

### **Container Build Issues**
1. Check GitHub Actions logs (not local Docker)
2. Verify platform specification (`--platform linux/amd64`)
3. Review ECR authentication and permissions
4. Validate Dockerfile syntax and dependencies

### **Pipeline Runtime Issues**  
1. Check CloudWatch logs for actual execution details
2. Verify container entry points use production scripts
3. Validate instance types match specifications
4. Review Step Functions execution history

### **Architecture Confusion**
1. Read `docs/CONTAINER_ARCHITECTURE.md` first
2. Check `docs/PROJECT_STATUS.md` for current state
3. Review recent git commits for context
4. Ask user for clarification if still unclear

---

**Last Updated**: December 2024 - After major codebase refactoring and standardization  
**Next Review**: After successful end-to-end pipeline validation 