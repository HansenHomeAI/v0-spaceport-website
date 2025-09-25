# 🚀 Branching Strategy & CI/CD

## Branch Roles & Environment Separation

### Branch Strategy
- **`development`** (staging): Integration branch for testing and validation
  - Every push deploys to **staging AWS account** via CDK
  - Frontend deploys to staging Cloudflare Pages project
  - Safe environment for experimentation and testing

- **`main`** (production): Release branch for live production
  - Every push deploys to **production AWS account** via CDK
  - Frontend deploys to production Cloudflare Pages project
  - Live environment for end users

## 🔄 Development Workflow

### 1. Feature Development
```bash
git checkout development
git checkout -b feature/new-feature
# Make changes, test locally
git commit -m "Add new feature"
git push origin feature/new-feature
```

### 2. Staging Deployment
```bash
# Merge feature branch to development (preserve history)
git checkout development
git merge --no-ff feature/new-feature
git push origin development
# ✅ Auto-deploys to staging AWS account
```

### 3. Production Release
```bash
# Merge development to main (preserve history)
git checkout main
git merge --no-ff development
git push origin main
# 🚀 Auto-deploys to production AWS account
```

### 4. Branch Archiving (After Successful Merge)
```bash
# Create archive tag to preserve branch history
git tag archive/feature-name HEAD~1

# Delete remote branch (keeps repository clean)
git push origin --delete feature/new-feature

# Optional: Delete local branch
git branch -d feature/new-feature
```

## 🏗️ Infrastructure Deployment

### AWS CDK Stacks
- **SpaceportStack**: Main application infrastructure
- **MLPipelineStack**: ML processing infrastructure  
- **AuthStack**: Authentication and user management

### Environment Targeting
```yaml
# .github/workflows/cdk-deploy.yml
environment: ${{ github.ref_name == 'main' && 'production' || 'staging' }}
```

### Security & Authentication
- **OIDC Authentication**: GitHub Actions securely authenticate with AWS
- **Environment Secrets**: Separate secrets for staging vs production
- **Role-Based Access**: Least-privilege IAM policies per environment
- **Complete Isolation**: No resource sharing between environments

## 🌐 Frontend Deployment

### Cloudflare Pages
- **Build Command**: `next build` → `@cloudflare/next-on-pages`
- **Output**: `.vercel/output/static` (worker.js at root)
- **SSR/ISR**: Edge runtime for dynamic content

### Environment Projects
- **Staging**: `v0-spaceport-website-preview2` (development branch)
- **Production**: `v0-spaceport-website-prod-fresh` (main branch)

## ✅ CI/CD Essentials

### Do's
- ✅ Keep `export const runtime = 'edge'` on app/API routes
- ✅ Deploy `.vercel/output/static` (worker mounts correctly)
- ✅ Use environment-specific secrets and configurations
- ✅ Test in staging before merging to main

### Don'ts
- ❌ Deploy `.vercel/output` root (causes 404s)
- ❌ Use `output: 'export'` in Next.js config
- ❌ Share credentials between environments
- ❌ Deploy untested changes directly to main

## 🗂️ Branch Archiving Strategy

### Archive Tags Approach
After successful feature completion and merge, branches are archived using git tags:

```bash
# 1. Create archive tag (preserves exact branch state)
git tag archive/agent-12345678-feature-name HEAD~1

# 2. Delete remote branch (cleans repository)
git push origin --delete agent-12345678-feature-name

# 3. Push archive tag to remote
git push origin archive/agent-12345678-feature-name
```

### Archive Tag Benefits
- ✅ **Clean repository** - No cluttered feature branches
- ✅ **Preserved history** - All work accessible via archive tags
- ✅ **Easy reference** - `git show archive/agent-12345678-feature-name`
- ✅ **Organized structure** - Clear separation between active and archived work

### Current Archive Tags
```bash
# View all archive tags
git tag -l "archive/*"
# archive/agent-20250919184906-improve-the-custom
# archive/agent-274
# archive/agent-58392017-footer-feedback
# archive/agent-73510264
# archive/agent-80aef7e9
# archive/agent-ba4c1671
# archive/agent-c24d0458
# archive/agent-setup-sop

# Check out archived branch for reference
git checkout archive/agent-58392017-footer-feedback
```

## 🔄 Rollback Strategy

### Infrastructure Rollback
```bash
# Revert CDK deployment
git revert <commit-hash>
git push origin main  # Triggers new deployment
```

### Frontend Rollback
```bash
# Revert to previous commit
git revert <commit-hash>
git push origin main  # Cloudflare Pages redeploys
```

## 📊 Deployment Status

### Current Status: ✅ PRODUCTION READY
- **Staging Environment**: Fully operational
- **Production Environment**: All AWS infrastructure deployed successfully
- **Environment Separation**: 100% isolated and secure
- **Deployment Automation**: Push-to-deploy working perfectly

### Success Metrics
- **Infrastructure Deployment**: ~90 seconds
- **Environment Isolation**: 100% complete
- **Security**: OIDC + least-privilege access
- **Zero Downtime**: Rolling deployments with health checks

---

**Last Updated**: August 21, 2025 - After successful production infrastructure deployment  
**Status**: Production-ready with enterprise-grade deployment strategy