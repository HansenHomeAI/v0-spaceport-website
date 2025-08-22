## Spaceport Docs Index

Canonical, concise docs for AI agents and developers. Prefer these over legacy files.

- Development: see `DEVELOPMENT_GUIDELINES.md`
- Deployment (AWS CDK + Cloudflare Pages): see `DEPLOYMENT.md`
- Branching and CI summary: see `BRANCHING_STRATEGY.md`

Legacy/Deep-dive docs remain in this folder (SOGS, 3DGS, COLMAP, etc.). Treat them as reference. If they disagree with the three canonical docs above, the canonical docs win.

Quick facts
- App: Next.js (App Router) under `web/`, SSR/ISR via Edge.
- Build: `next build` then `@cloudflare/next-on-pages` → produces `.vercel/output/static/_worker.js`.
- Deploy: CI uploads `.vercel/output/static` to Cloudflare Pages so the worker mounts.
- **Branches**: `development` → staging deploy; `main` → production deploy (AWS CDK + Cloudflare).
- **Infrastructure**: AWS CDK deploys backend infrastructure to separate staging/production accounts.

# 📖 Documentation Overview

This directory contains the essential documentation for the Spaceport ML Pipeline project.

## 📋 Documentation Index

### 🏠 [Main README](../README.md)
**Start here** - Complete project overview, architecture, and quick start guide
- Project overview and architecture
- ML pipeline workflow  
- AWS infrastructure details
- Quick start deployment guide
- Current status and achievements

### 📊 [Project Status](PROJECT_STATUS.md) 
**Current state** - Comprehensive project status and metrics
- Executive summary of achievements
- Infrastructure and component status
- Recent fixes and validations
- Performance metrics and targets
- Next phase priorities

### 🚀 [Deployment Guide](DEPLOYMENT.md)
**How to deploy** - Complete deployment and troubleshooting guide  
- Step-by-step deployment instructions
- AWS CDK infrastructure deployment
- Container build and push procedures
- Testing and validation steps
- Troubleshooting common issues
- Maintenance and update procedures

### 🔧 [Production Deployment Troubleshooting](PRODUCTION_DEPLOYMENT_TROUBLESHOOTING.md)
**Production issues resolved** - Complete guide to fixing production deployment problems
- Production site authentication vs API issues
- Missing Lambda functions and wrong API endpoints
- Environment variable injection problems
- Step-by-step resolution process
- Prevention strategies and best practices

### 🔌 [API Reference](api.md)
**API usage** - API endpoints and usage examples
- ML pipeline API endpoints
- Request/response formats
- Pipeline step options
- Error handling

## 🎯 Quick Navigation

| Need | Document | Section |
|------|----------|---------|
| **Project Overview** | [Main README](../README.md) | Project Overview |
| **Current Status** | [Project Status](PROJECT_STATUS.md) | Executive Summary |
| **Deploy System** | [Deployment Guide](DEPLOYMENT.md) | Infrastructure Deployment |
| **Fix Production Issues** | [Production Troubleshooting](PRODUCTION_DEPLOYMENT_TROUBLESHOOTING.md) | Root Causes & Solutions |
| **Use API** | [API Reference](api.md) | ML Pipeline API |
| **Troubleshoot Issues** | [Deployment Guide](DEPLOYMENT.md) | Troubleshooting Guide |
| **Check Progress** | [Project Status](PROJECT_STATUS.md) | Success Metrics |

## 📈 Recent Updates

- ✅ **Production Site Fully Functional**: Projects API working, authentication working, all features operational
- ✅ **Production Deployment Issues Resolved**: Complete troubleshooting guide created for future reference
- ✅ **Environment Variable Injection Fixed**: GitHub Actions now properly injects build-time environment variables
- ✅ **Infrastructure Deployment Completed**: SpaceportAuthStack successfully deployed with Lambda function
- ✅ **Production Infrastructure Deployed**: All AWS CDK stacks successfully deployed to production account
- ✅ **Environment Separation**: Clean staging/production separation with OIDC authentication
- ✅ **Deployment Strategy**: Branch-based deployment with automatic environment targeting
- ✅ **Documentation Consolidated**: Streamlined from 10+ scattered files to 4 key documents
- ✅ **Pipeline Fixed**: Compression step issues resolved and validated  
- ✅ **Status Updated**: Current production-ready status documented
- ✅ **Deployment Guide**: Comprehensive troubleshooting and maintenance procedures

---

**Status**: All documentation current as of August 2025  
**Next Review**: Update when production ML pipeline testing begins 