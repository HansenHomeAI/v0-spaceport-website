# API Configuration Guide - Spaceport Website

## 🎯 **Overview**

This guide documents how to configure and manage API endpoints using environment variables, ensuring consistency between development and production environments.

---

## 🔧 **Environment Variable Architecture**

### **Core Principle:**
- **NO hardcoded API URLs** in frontend code
- **100% environment variable driven** configuration
- **Branch-based routing** (development vs production)
- **Centralized configuration** management

### **Environment Variable Structure:**
```bash
# Production (main branch)
NEXT_PUBLIC_PROJECTS_API_URL=https://API_ID.execute-api.us-west-2.amazonaws.com/prod/projects
NEXT_PUBLIC_DRONE_PATH_API_URL=https://API_ID.execute-api.us-west-2.amazonaws.com/prod
NEXT_PUBLIC_FILE_UPLOAD_API_URL=https://API_ID.execute-api.us-west-2.amazonaws.com/prod
NEXT_PUBLIC_WAITLIST_API_URL=https://API_ID.execute-api.us-west-2.amazonaws.com/prod/waitlist
NEXT_PUBLIC_ML_PIPELINE_API_URL=https://API_ID.execute-api.us-west-2.amazonaws.com/prod

# Development (development branch)  
NEXT_PUBLIC_PROJECTS_API_URL=https://DEV_API_ID.execute-api.us-west-2.amazonaws.com/prod/projects
NEXT_PUBLIC_DRONE_PATH_API_URL=https://DEV_API_ID.execute-api.us-west-2.amazonaws.com/prod
NEXT_PUBLIC_FILE_UPLOAD_API_URL=https://DEV_API_ID.execute-api.us-west-2.amazonaws.com/prod
NEXT_PUBLIC_WAITLIST_API_URL=https://DEV_API_ID.execute-api.us-west-2.amazonaws.com/prod/waitlist
NEXT_PUBLIC_ML_PIPELINE_API_URL=https://DEV_API_ID.execute-api.us-west-2.amazonaws.com/prod
```

---

## 🚀 **Current API Gateway Configuration**

### **Production APIs (Account: 356638455876):**
| Service | API Gateway ID | Base URL | Status |
|---------|----------------|-----------|---------|
| **Projects** | `34ap3qgem7` | `https://34ap3qgem7.execute-api.us-west-2.amazonaws.com/prod` | ✅ Working |
| **Drone Path** | `0r3y4bx7lc` | `https://0r3y4bx7lc.execute-api.us-west-2.amazonaws.com/prod` | ✅ Working |
| **File Upload** | `rf3fnnejg2` | `https://rf3fnnejg2.execute-api.us-west-2.amazonaws.com/prod` | ✅ Working |
| **Waitlist** | `rf3fnnejg2` | `https://rf3fnnejg2.execute-api.us-west-2.amazonaws.com/prod/waitlist` | ✅ Working |

### **Development APIs (Account: 975050048887):**
| Service | API Gateway ID | Base URL | Status |
|---------|----------------|-----------|---------|
| **Projects** | `34ap3qgem7` | `https://34ap3qgem7.execute-api.us-west-2.amazonaws.com/prod` | ✅ Working |
| **Drone Path** | `34ap3qgem7` | `https://34ap3qgem7.execute-api.us-west-2.amazonaws.com/prod` | ✅ Working |
| **File Upload** | `34ap3qgem7` | `https://34ap3qgem7.execute-api.us-west-2.amazonaws.com/prod` | ✅ Working |
| **Waitlist** | `34ap3qgem7` | `https://34ap3qgem7.execute-api.us-west-2.amazonaws.com/prod/waitlist` | ✅ Working |

---

## 🔧 **Frontend Configuration Files**

### **1. API Configuration (`web/app/api-config.ts`)**
```typescript
export const API_CONFIG = {
  // Projects API - User project management
  PROJECTS_API_URL: process.env.NEXT_PUBLIC_PROJECTS_API_URL!,
  
  // Drone Path API - Flight path optimization and CSV generation
  DRONE_PATH_API_URL: process.env.NEXT_PUBLIC_DRONE_PATH_API_URL!,
  
  // File Upload API - File upload operations
  FILE_UPLOAD_API_URL: process.env.NEXT_PUBLIC_FILE_UPLOAD_API_URL!,
  
  // Waitlist API - User waitlist submissions
  WAITLIST_API_URL: process.env.NEXT_PUBLIC_WAITLIST_API_URL!,
  
  // ML Pipeline API - ML processing operations
  ML_PIPELINE_API_URL: process.env.NEXT_PUBLIC_ML_PIPELINE_API_URL!,
} as const;

// Helper function to build API URLs
export const buildApiUrl = (endpoint: string): string => {
  const baseUrl = process.env.NEXT_PUBLIC_DRONE_PATH_API_URL || '';
  return `${baseUrl}${endpoint}`;
};
```

### **2. GitHub Actions Environment Injection (`.github/workflows/deploy-cloudflare-pages.yml`)**
```yaml
- name: Inject build-time env (.env) for NEXT_PUBLIC_* per branch
  run: |
    set -euo pipefail
    BRANCH="${{ github.ref_name }}"
    echo "Preparing .env for branch $BRANCH"
    : > .env
    if [ "$BRANCH" = "main" ]; then
      echo "NEXT_PUBLIC_PROJECTS_API_URL=${{ secrets.PROJECTS_API_URL_PROD }}" >> .env
      echo "NEXT_PUBLIC_DRONE_PATH_API_URL=${{ secrets.DRONE_PATH_API_URL_PROD }}" >> .env
      echo "NEXT_PUBLIC_FILE_UPLOAD_API_URL=${{ secrets.FILE_UPLOAD_API_URL_PROD }}" >> .env
      echo "NEXT_PUBLIC_WAITLIST_API_URL=${{ secrets.WAITLIST_API_URL_PROD }}" >> .env
      echo "NEXT_PUBLIC_ML_PIPELINE_API_URL=${{ secrets.ML_PIPELINE_API_URL_PROD }}" >> .env
    else
      echo "NEXT_PUBLIC_PROJECTS_API_URL=${{ secrets.PROJECTS_API_URL_PREVIEW }}" >> .env
      echo "NEXT_PUBLIC_DRONE_PATH_API_URL=${{ secrets.DRONE_PATH_API_URL_PREVIEW }}" >> .env
      echo "NEXT_PUBLIC_FILE_UPLOAD_API_URL=${{ secrets.FILE_UPLOAD_API_URL_PREVIEW }}" >> .env
      echo "NEXT_PUBLIC_WAITLIST_API_URL=${{ secrets.WAITLIST_API_URL_PREVIEW }}" >> .env
      echo "NEXT_PUBLIC_ML_PIPELINE_API_URL=${{ secrets.ML_PIPELINE_API_URL_PREVIEW }}" >> .env
    fi
```

---

## 🔑 **GitHub Secrets Management**

### **Required Secrets for Production (main branch):**
```bash
PROJECTS_API_URL_PROD=https://34ap3qgem7.execute-api.us-west-2.amazonaws.com/prod/projects
DRONE_PATH_API_URL_PROD=https://0r3y4bx7lc.execute-api.us-west-2.amazonaws.com/prod
FILE_UPLOAD_API_URL_PROD=https://rf3fnnejg2.execute-api.us-west-2.amazonaws.com/prod
WAITLIST_API_URL_PROD=https://rf3fnnejg2.execute-api.us-west-2.amazonaws.com/prod/waitlist
ML_PIPELINE_API_URL_PROD=https://rf3fnnejg2.execute-api.us-west-2.amazonaws.com/prod
```

### **Required Secrets for Development (development branch):**
```bash
PROJECTS_API_URL_PREVIEW=https://34ap3qgem7.execute-api.us-west-2.amazonaws.com/prod/projects
DRONE_PATH_API_URL_PREVIEW=https://34ap3qgem7.execute-api.us-west-2.amazonaws.com/prod
FILE_UPLOAD_API_URL_PREVIEW=https://34ap3qgem7.execute-api.us-west-2.amazonaws.com/prod
WAITLIST_API_URL_PREVIEW=https://34ap3qgem7.execute-api.us-west-2.amazonaws.com/prod/waitlist
ML_PIPELINE_API_URL_PREVIEW=https://34ap3qgem7.execute-api.us-west-2.amazonaws.com/prod
```

---

## 🚀 **Adding New API Endpoints**

### **Step 1: Update Frontend Configuration**
```typescript
// Add to web/app/api-config.ts
export const API_CONFIG = {
  // ... existing configs ...
  NEW_API_URL: process.env.NEXT_PUBLIC_NEW_API_URL!,
} as const;
```

### **Step 2: Update GitHub Actions**
```yaml
# Add to .github/workflows/deploy-cloudflare-pages.yml
if [ "$BRANCH" = "main" ]; then
  echo "NEXT_PUBLIC_NEW_API_URL=${{ secrets.NEW_API_URL_PROD }}" >> .env
else
  echo "NEXT_PUBLIC_NEW_API_URL=${{ secrets.NEW_API_URL_PREVIEW }}" >> .env
fi
```

### **Step 3: Add GitHub Secrets**
```bash
# Production
gh secret set NEW_API_URL_PROD --repo HansenHomeAI/v0-spaceport-website --body "https://NEW_API_ID.execute-api.us-west-2.amazonaws.com/prod"

# Development  
gh secret set NEW_API_URL_PREVIEW --repo HansenHomeAI/v0-spaceport-website --body "https://DEV_API_ID.execute-api.us-west-2.amazonaws.com/prod"
```

### **Step 4: Update Frontend Components**
```typescript
// Use the new API configuration
import { API_CONFIG } from '../app/api-config';

const response = await fetch(`${API_CONFIG.NEW_API_URL}/endpoint`, {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify(data)
});
```

---

## 🔍 **Troubleshooting API Configuration**

### **Common Issues & Solutions:**

#### **1. "Server not found" errors**
- **Cause**: Frontend calling wrong API Gateway ID
- **Solution**: Check GitHub Secrets contain correct API IDs
- **Verification**: `gh secret list --repo HansenHomeAI/v0-spaceport-website`

#### **2. Environment variables not loading**
- **Cause**: Build not using latest secrets
- **Solution**: Trigger new Cloudflare Pages build
- **Verification**: Check `.env` file in build logs

#### **3. CORS errors**
- **Cause**: Missing OPTIONS methods in API Gateway
- **Solution**: Add CORS methods via AWS CLI
- **Verification**: Test OPTIONS request to endpoint

#### **4. Lambda permission errors**
- **Cause**: Lambda function lacks API Gateway invocation permissions
- **Solution**: Add Lambda permissions for specific endpoints
- **Verification**: Check Lambda function policy

---

## 📋 **Best Practices**

### **1. Never Hardcode API URLs**
```typescript
// ❌ WRONG - Hardcoded fallback
const API_URL = process.env.NEXT_PUBLIC_API_URL || "https://hardcoded-api.execute-api.us-west-2.amazonaws.com/prod";

// ✅ CORRECT - Environment variable only
const API_URL = process.env.NEXT_PUBLIC_API_URL;
```

### **2. Use Centralized Configuration**
```typescript
// ❌ WRONG - Scattered throughout components
const apiUrl = process.env.NEXT_PUBLIC_API_URL;

// ✅ CORRECT - Centralized in api-config.ts
import { API_CONFIG } from '../app/api-config';
const apiUrl = API_CONFIG.API_URL;
```

### **3. Validate Environment Variables**
```typescript
// Add validation to ensure required env vars are present
if (!process.env.NEXT_PUBLIC_API_URL) {
  throw new Error('NEXT_PUBLIC_API_URL environment variable is required');
}
```

### **4. Consistent Naming Convention**
```bash
# Use consistent prefix for all API-related environment variables
NEXT_PUBLIC_PROJECTS_API_URL
NEXT_PUBLIC_DRONE_PATH_API_URL
NEXT_PUBLIC_FILE_UPLOAD_API_URL
NEXT_PUBLIC_WAITLIST_API_URL
NEXT_PUBLIC_ML_PIPELINE_API_URL
```

---

## 🎯 **Future API Development Workflow**

### **When Adding New APIs:**
1. **Create API Gateway** in appropriate AWS account
2. **Deploy Lambda function** with proper permissions
3. **Add environment variable** to `api-config.ts`
4. **Update GitHub Actions** workflow
5. **Add GitHub Secrets** for both environments
6. **Test in development** branch first
7. **Deploy to production** after verification

### **When Modifying Existing APIs:**
1. **Update Lambda function** code
2. **Test locally** with environment variables
3. **Deploy Lambda** changes
4. **Test in development** environment
5. **Deploy to production** after verification

---

**Last Updated**: 2025-08-22 - After implementing environment variable architecture
**Status**: **Production Ready** ✅
**Next Review**: When adding new API endpoints or modifying existing ones

---

## 📧 **SES Email Status - PRODUCTION MODE** ✅

### **Current Configuration:**
- **SES Mode**: Production (not sandbox)
- **Sender Verification**: `gabriel@spcprt.com` fully verified
- **Sending Status**: Enabled and operational
- **Email Delivery**: Confirmation emails working for waitlist

### **Email Endpoints:**
- **Waitlist Confirmation**: Sent to users who sign up
- **Admin Notifications**: Sent to `gabriel@spcprt.com` for new signups
- **Templates**: HTML + Text versions with professional formatting

### **No Further Configuration Needed:**
- ✅ **Production access**: Already granted by AWS
- ✅ **Sender verification**: Complete
- ✅ **Lambda permissions**: Configured for SES
- ✅ **Email templates**: Implemented and tested
