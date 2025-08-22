# Production Deployment Troubleshooting Guide

## 🚨 Issue: Production Site Unable to Save/Load Projects

**Date Resolved**: 2025-08-22  
**Status**: ✅ **RESOLVED** - Production site now fully functional  
**Impact**: Users could authenticate but couldn't create, save, or view projects

## 🔍 Symptoms

### Frontend Behavior
- ✅ **Authentication working** - Users could sign in successfully
- ❌ **Projects not loading** - Empty project list despite migrated data
- ❌ **Save failing** - "Load failed" errors when trying to save projects
- ❌ **Console errors** - CORS and 401 errors in browser console

### Console Error Messages
```
[Error] Origin https://spcprt.com is not allowed by Access-Control-Allow-Origin. Status code: 401
[Error] Fetch API cannot load https://sactt3t5rd.execute-api.us-west-2.amazonaws.com/prod/projects due to access control checks.
[Error] Save failed: TypeError: Load failed
```

## 🎯 Root Causes Identified

### 1. Missing Lambda Function
- **Problem**: `Spaceport-ProjectsFunction` not deployed to production
- **Evidence**: API Gateway configured to call non-existent Lambda
- **Impact**: All project CRUD operations failing with 5xx errors

### 2. Wrong Cognito User Pool ID
- **Problem**: Using non-existent User Pool ID (`us-west-2_3Rx92caFz`)
- **Evidence**: CDK stack not properly deployed to production
- **Impact**: Authentication working but with wrong User Pool

### 3. Wrong API Gateway Endpoint
- **Problem**: Frontend calling non-existent API Gateway (`sactt3t5rd`)
- **Evidence**: Environment variables pointing to wrong endpoint
- **Impact**: Network requests failing with connection errors

### 4. Environment Variables Not Injected
- **Problem**: `NEXT_PUBLIC_*` variables not available at build time
- **Evidence**: Frontend built without production configuration
- **Impact**: Hardcoded development endpoints in production build

## 🔧 Solutions Implemented

### Phase 1: Infrastructure Deployment
1. **Deploy CDK Stack**: Successfully deployed `SpaceportAuthStack` to production
2. **Create Lambda Function**: `Spaceport-ProjectsFunction` now exists and configured
3. **Configure API Gateway**: Proper Lambda integration and CORS settings

### Phase 2: Credential Correction
1. **Fix Cognito User Pool ID**: Updated to correct ID (`us-west-2_a2jf3ldGV`)
2. **Verify User Account**: Confirmed user account exists in production User Pool
3. **Test Authentication**: Verified sign-in working with correct credentials

### Phase 3: API Endpoint Fix
1. **Identify Correct Endpoint**: Found working production API Gateway (`34ap3qgem7`)
2. **Update GitHub Secrets**: Corrected `PROJECTS_API_URL_PROD` environment variable
3. **Verify API Response**: Confirmed endpoint returning proper 401 (expected without auth)

### Phase 4: Frontend Configuration
1. **Update GitHub Actions**: Modified workflow to inject environment variables during build
2. **Create .env File**: Build process now creates `.env` with correct values
3. **Trigger Rebuild**: New deployment with proper production configuration

## 📋 Step-by-Step Resolution Process

### Step 1: Investigate Infrastructure
```bash
# Check if Lambda function exists
aws lambda get-function --function-name Spaceport-ProjectsFunction

# Check API Gateway endpoints
aws apigateway get-rest-apis

# Check CDK stack status
cdk diff SpaceportAuthStack
```

### Step 2: Deploy Missing Infrastructure
```bash
# Deploy the auth stack
cdk deploy SpaceportAuthStack --require-approval never

# Verify deployment
aws cloudformation describe-stacks --stack-name SpaceportAuthStack
```

### Step 3: Fix Environment Variables
```bash
# Update GitHub Secrets with correct values
gh secret set PROJECTS_API_URL_PROD --body "https://34ap3qgem7.execute-api.us-west-2.amazonaws.com/prod/projects"
gh secret set COGNITO_USER_POOL_ID_PROD --body "us-west-2_a2jf3ldGV"
gh secret set COGNITO_USER_POOL_CLIENT_ID_PROD --body "3ctkuqu98pmug5k5kgc119sq67"
```

### Step 4: Update GitHub Actions Workflow
```yaml
- name: Inject build-time env (.env) for NEXT_PUBLIC_* per branch
  run: |
    set -euo pipefail
    BRANCH="${{ github.ref_name }}"
    echo "Preparing .env for branch $BRANCH"
    : > .env
    if [ "$BRANCH" = "main" ]; then
      echo "NEXT_PUBLIC_PROJECTS_API_URL=${{ secrets.PROJECTS_API_URL_PROD }}" >> .env
      echo "NEXT_PUBLIC_COGNITO_REGION=${{ secrets.COGNITO_REGION_PROD }}" >> .env
      echo "NEXT_PUBLIC_COGNITO_USER_POOL_ID=${{ secrets.COGNITO_USER_POOL_ID_PROD }}" >> .env
      echo "NEXT_PUBLIC_COGNITO_USER_POOL_CLIENT_ID=${{ secrets.COGNITO_USER_POOL_CLIENT_ID_PROD }}" >> .env
    else
      # Preview environment variables
    fi
```

### Step 5: Test and Verify
```bash
# Test API endpoint
curl -s -D - -o /dev/null -H 'Origin: https://spcprt.com' \
  https://34ap3qgem7.execute-api.us-west-2.amazonaws.com/prod/projects

# Expected: 401 Unauthorized (proper response, not connection error)
```

## 🎓 Lessons Learned

### 1. Environment Variable Injection
- **Problem**: Cloudflare Pages "Secrets" are runtime-only, not build-time
- **Solution**: Use GitHub Actions to create `.env` file during build process
- **Best Practice**: Always verify environment variables are available at build time

### 2. CDK Deployment Verification
- **Problem**: Assuming CDK deployment succeeded without verification
- **Solution**: Always run `cdk diff` and verify actual deployment
- **Best Practice**: Check CloudFormation stack status and resources after deployment

### 3. API Gateway ID Management
- **Problem**: Hardcoded API Gateway IDs in environment variables
- **Solution**: Use CDK outputs and GitHub Secrets for dynamic configuration
- **Best Practice**: Never hardcode AWS resource IDs in frontend code

### 4. Infrastructure vs Frontend Dependencies
- **Problem**: Frontend deployment before infrastructure was ready
- **Solution**: Ensure infrastructure deployment completes before frontend build
- **Best Practice**: Use deployment order and dependency management

## 🔍 Prevention Strategies

### 1. Automated Testing
- **Pre-deployment**: Test API endpoints before frontend deployment
- **Post-deployment**: Verify Lambda functions and API Gateway integration
- **Monitoring**: Set up CloudWatch alarms for API errors

### 2. Environment Validation
- **Build-time**: Verify all required environment variables are present
- **Runtime**: Validate API endpoints are accessible
- **Fallbacks**: Implement graceful degradation for missing services

### 3. Deployment Order
- **Infrastructure First**: Always deploy CDK stacks before frontend
- **Verification**: Confirm resources exist before proceeding
- **Rollback Plan**: Have rollback strategy for failed deployments

## 📊 Current Status

### ✅ Resolved Issues
- **Lambda Function**: `Spaceport-ProjectsFunction` deployed and working
- **API Gateway**: Using correct production endpoint (`34ap3qgem7`)
- **Cognito**: Correct User Pool ID configured
- **Environment Variables**: Properly injected during build
- **Frontend**: Production site fully functional

### 🔍 Monitoring
- **API Gateway**: CloudWatch logs enabled for debugging
- **Lambda**: Function monitoring and error tracking
- **Frontend**: Error tracking and user experience monitoring

### 🚀 Next Steps
1. **Monitor Stability**: Watch for any recurring issues
2. **Performance Optimization**: Optimize Lambda cold starts and API response times
3. **User Analytics**: Track project creation and usage patterns

## 📚 Related Documentation

- [PROJECT_STATUS.md](./PROJECT_STATUS.md) - Overall project status
- [TROUBLESHOOTING_3DGS.md](./TROUBLESHOOTING_3DGS.md) - ML pipeline troubleshooting
- [DEVELOPMENT_GUIDELINES.md](./DEVELOPMENT_GUIDELINES.md) - Development best practices

---

**Last Updated**: 2025-08-22  
**Status**: ✅ **RESOLVED** - Production deployment issues fully resolved  
**Next Review**: 2025-09-05 - Monitor stability and plan optimizations
