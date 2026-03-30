# 🚀 Branching Strategy & CI/CD

## Branch Roles & Environment Separation

### Branch Strategy
- **`development`** (staging): integration branch for testing and validation
  - Every push deploys to the staging AWS account
  - Deploys the shared staging auth stack by default
  - Deploys to the staging Cloudflare Pages preview project

- **`main`** (production): release branch for live production
  - Every push deploys to the production AWS account
  - Deploys the production auth stack by default
  - Deploys to the production Cloudflare Pages project

- **Preview branches** (`agent-*`, `codex/agent-*`): branch-local application previews
  - Deploy branch-specific Spaceport and ML stacks by default
  - Reuse the shared staging auth stack unless the branch explicitly opts in
  - Deploy to the shared preview Pages project, but each run must use the `PREVIEW_URL` emitted by that run

### Preview Branch Auth Contract
- Preview branches are auth read-only by default.
- Add `.spaceport/deploy-auth-preview` on a preview branch to redeploy the shared staging auth stack on every push.
- Remove `.spaceport/deploy-auth-preview` to return that branch to the default auth read-only behavior.
- Child branches inherit the marker file naturally. Remove it in the child branch if that branch should stop redeploying auth.
- Shared staging auth deploys run in a dedicated serialized CI lane so opt-in branches do not collide with each other or with `development`.

### Preview URL Contract
- Cloudflare Pages preview validation must use the `PREVIEW_URL` emitted by the current workflow run.
- `PREVIEW_URL` prefers the branch alias URL when Wrangler emits one and falls back to the current deploy hash URL.
- Do not query the latest deployment in the Pages project for branch validation. Concurrent branch deploys can return another branch's preview.

## 🔄 Development Workflow

### 1. Feature Development
```bash
git checkout development
git checkout -b agent-12345678-new-feature
# Make changes, test locally
git commit -m "Add new feature"
git push origin agent-12345678-new-feature
```

### 2. Preview Deployment
```bash
# Push your preview branch and wait for both workflows
gh run list --branch agent-12345678-new-feature
gh run watch <pages-run-id> --exit-status
gh run watch <cdk-run-id> --exit-status

# Read PREVIEW_URL from that Pages run and validate against it
```

### 3. Staging Deployment
```bash
# Merge preview branch to development (preserve history)
git checkout development
git merge --no-ff agent-12345678-new-feature
git push origin development
# ✅ Auto-deploys shared staging infra, including auth
```

### 4. Production Release
```bash
# Merge development to main (preserve history)
git checkout main
git merge --no-ff development
git push origin main
# 🚀 Auto-deploys production
```

### 5. Branch Archiving (After Successful Merge)
```bash
# Create archive tag to preserve branch history
git tag archive/agent-12345678-new-feature HEAD~1

# Delete remote branch (keeps repository clean)
git push origin --delete agent-12345678-new-feature

# Optional: delete local branch
git branch -d agent-12345678-new-feature
```

## 🏗️ Infrastructure Deployment

### AWS CDK Stacks
- **SpaceportStack**: main application infrastructure
- **MLPipelineStack**: ML processing infrastructure
- **AuthStack**: authentication and user management

### Environment Targeting
```yaml
# .github/workflows/cdk-deploy.yml
environment: ${{ github.ref_name == 'main' && 'production' || 'staging' }}
```

### Security & Authentication
- **OIDC Authentication**: GitHub Actions securely authenticate with AWS
- **Environment Secrets**: separate secrets for staging vs production
- **Role-Based Access**: least-privilege IAM policies per environment
- **Shared Preview Auth**: preview branches share the staging auth stack unless they opt into redeploying it

## 🌐 Frontend Deployment

### Cloudflare Pages
- **Build Command**: `next build` then `@cloudflare/next-on-pages`
- **Output**: `.vercel/output/static` so `_worker.js` sits at the upload root
- **SSR/ISR**: Edge runtime for dynamic content

### Environment Projects
- **Preview/Staging**: `v0-spaceport-website-preview2` (`development` and preview branches)
- **Production**: `v0-spaceport-website-prod-fresh` (`main`)

## ✅ CI/CD Essentials

### Do's
- ✅ Keep `export const runtime = 'edge'` on app/API routes
- ✅ Deploy `.vercel/output/static` so the worker mounts correctly
- ✅ Use environment-specific secrets and configurations
- ✅ Use the workflow-emitted `PREVIEW_URL` for preview testing
- ✅ Add `.spaceport/deploy-auth-preview` only when a preview branch intentionally needs shared auth redeploys
- ✅ Test in staging before merging to main

### Don'ts
- ❌ Deploy `.vercel/output` root
- ❌ Use `output: 'export'` in Next.js config
- ❌ Share credentials between environments
- ❌ Query "latest deployment in project" when validating a branch preview
- ❌ Deploy untested changes directly to main

## 🗂️ Branch Archiving Strategy

### Archive Tags Approach
After successful feature completion and merge, branches are archived using Git tags:

```bash
# 1. Create archive tag (preserves exact branch state)
git tag archive/agent-12345678-feature-name HEAD~1

# 2. Delete remote branch (cleans repository)
git push origin --delete agent-12345678-feature-name

# 3. Push archive tag to remote
git push origin archive/agent-12345678-feature-name
```

### Archive Tag Benefits
- ✅ **Clean repository**: no cluttered feature branches
- ✅ **Preserved history**: all work accessible via archive tags
- ✅ **Easy reference**: `git show archive/agent-12345678-feature-name`
- ✅ **Organized structure**: clear separation between active and archived work

## 🔄 Rollback Strategy

### Infrastructure Rollback
```bash
# Revert CDK deployment
git revert <commit-hash>
git push origin main
```

### Frontend Rollback
```bash
# Revert to previous commit
git revert <commit-hash>
git push origin main
```

## 📊 Deployment Status

### Current Status: ✅ PRODUCTION READY
- **Staging Environment**: fully operational
- **Production Environment**: AWS and Pages deployments operational
- **Preview Branching**: branch-local app stacks with explicit shared-auth opt-in
- **Deployment Automation**: push-to-deploy with branch-bound preview URLs

### Success Metrics
- **Infrastructure Deployment**: ~90 seconds
- **Auth Contention Control**: shared auth deploys serialized when explicitly requested
- **Security**: OIDC + least-privilege access
- **Preview Validation**: current-run `PREVIEW_URL` prevents cross-branch Pages races

---

**Last Updated**: March 28, 2026
**Status**: Production-ready with explicit preview auth controls
