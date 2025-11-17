# Flight Viewer Local Environment Fix - October 7, 2025

## Problem Statement

User reported: "Google Maps API key missing. Set NEXT_PUBLIC_GOOGLE_MAPS_API_KEY to enable photorealistic terrain" when testing flight-viewer locally via `npm run dev`, even though the key worked fine in production/preview deployments.

## Root Cause Analysis

### How Production Works
- GitHub Actions workflow (`deploy-cloudflare-pages.yml`) runs on push
- Line 53: Creates a `.env` file in `web/` directory
- Lines 72, 91: Injects `NEXT_PUBLIC_GOOGLE_MAPS_API_KEY` from GitHub secrets
- Next.js build reads `.env` and bundles vars into client code
- Cloudflare Pages deployment includes the bundled env vars

### Why Local Dev Failed
- No `.env` or `.env.local` file existed in `web/` directory
- Next.js requires these files to provide `NEXT_PUBLIC_*` variables during development
- `process.env.NEXT_PUBLIC_GOOGLE_MAPS_API_KEY` returned empty string
- Flight viewer code defaulted to showing the error message

## Solution Implemented

### 1. Setup Script (`scripts/setup-local-env.sh`)
- Interactive script to create `web/.env.local`
- Attempts to use GitHub CLI to check for secrets
- Prompts user for Google Maps API key if needed
- Creates properly formatted `.env.local` file
- Made executable with `chmod +x`

### 2. Example Template (`web/env.local.example`)
- Template file showing required variables
- Includes comments explaining each variable
- Safe to commit (no sensitive data)
- Users can `cp env.local.example .env.local` and fill in values

### 3. Documentation (`web/LOCAL_DEVELOPMENT.md`)
Comprehensive guide covering:
- Quick start instructions
- How to get Google Maps API key (from GitHub or Google Cloud)
- Environment variable reference
- Troubleshooting section
- Explanation of production vs local differences
- Why `.env.local` is needed

### 4. Security Verification
- Confirmed `.env.local` is in `.gitignore` (line 43)
- Confirmed `.env` is also ignored (lines 42, 75)
- No secrets committed to repository

## Files Changed

```
scripts/setup-local-env.sh (new)          - Interactive setup script
web/env.local.example (new)               - Template for local env vars  
web/LOCAL_DEVELOPMENT.md (new)            - Comprehensive dev guide
web/next.config.cjs (modified)            - Minor formatting changes
```

## How to Use (For Developers)

### Option A: Automated Setup
```bash
./scripts/setup-local-env.sh
```

### Option B: Manual Setup
```bash
cd web
cp env.local.example .env.local
# Edit .env.local and add your Google Maps API key
# Get the key from GitHub secrets or Google Cloud Console
npm run dev
```

### Key Point
**After creating `.env.local`, restart the dev server!** Next.js only reads env files at startup.

## Testing

1. ✅ Build succeeds: `npm run build` completes without errors
2. ✅ Documentation created with clear troubleshooting steps
3. ✅ Setup script is executable and ready to use
4. ✅ Template file provides clear guidance
5. ✅ Security confirmed: .env.local is gitignored

## Expected Outcome

When developers now run `npm run dev` locally:
1. If they don't have `.env.local`: See the "API key missing" message (expected)
2. Run setup script or copy template → Create `.env.local` with their key
3. Restart dev server
4. Flight viewer loads with photorealistic 3D terrain ✅

## Related Issues Fixed

This also resolves a broader issue: the project had no documentation on how to set up local development environment variables. The new `LOCAL_DEVELOPMENT.md` provides this for all future developers.

## Future Improvements

Consider:
- Adding `.env.local` check to development workflow
- CI job to validate env.local.example stays in sync with production requirements
- Extending setup script to handle all `NEXT_PUBLIC_*` variables (Cognito, Stripe, etc.)

