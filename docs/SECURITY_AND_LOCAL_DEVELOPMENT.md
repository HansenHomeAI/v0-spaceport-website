# Security & Local Development Guide

## TL;DR Security Model

**✅ SAFE**: `.env.local` is in `.gitignore` - secrets you put there **never get committed**

**✅ PRODUCTION**: All secrets stored in GitHub Secrets (encrypted, never in code)

**⚠️ LOCAL DEV REALITY**: Most features won't work locally without `.env.local` because they need API endpoints and auth credentials

---

## Understanding the Secret Types

### 1. **Public API Keys** (safe to expose in client code)
- `NEXT_PUBLIC_GOOGLE_MAPS_API_KEY` - Google Maps (restricted by domain/IP in Google Console)
- `NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY` - Stripe public key (designed to be public)
- `NEXT_PUBLIC_POSTHOG_KEY` - Analytics (read-only, client-safe)

**Why these are "safe"**: They're designed to be used in browsers and are domain/IP restricted in their respective platforms.

### 2. **API Endpoints** (not secrets, just configuration)
- `NEXT_PUBLIC_PROJECTS_API_URL` - Your API Gateway endpoints
- `NEXT_PUBLIC_DRONE_PATH_API_URL`
- `NEXT_PUBLIC_ML_PIPELINE_API_URL`
- etc.

**Why these aren't secrets**: They're just URLs. The actual security is in Cognito tokens sent with requests.

### 3. **Cognito Config** (not secrets, just IDs)
- `NEXT_PUBLIC_COGNITO_REGION`
- `NEXT_PUBLIC_COGNITO_USER_POOL_ID`
- `NEXT_PUBLIC_COGNITO_USER_POOL_CLIENT_ID`

**Why these aren't secrets**: These are service identifiers. Security comes from user authentication, not hiding the pool ID.

### 4. **Server-Side Secrets** (NEVER in NEXT_PUBLIC_*)
- `AWS_ROLE_TO_ASSUME` - Never exposed to client
- `STRIPE_SECRET_KEY` - Backend only, never in browser
- `CLOUDFLARE_API_TOKEN` - CI/CD only

**These are never bundled into client code** because they don't have the `NEXT_PUBLIC_` prefix.

---

## How Production Stays Secure

### GitHub Secrets Storage
```
Repository Settings > Secrets and variables > Actions > Repository secrets
```

- 56 secrets stored encrypted in GitHub
- Only accessible during GitHub Actions runs
- Never appear in logs or artifacts
- Access controlled by repository permissions

### Build-Time Injection
```yaml
# .github/workflows/deploy-cloudflare-pages.yml
- name: Inject build-time env (.env) for NEXT_PUBLIC_* per branch
  env:
    MAPS_KEY_PRIMARY: ${{ secrets.NEXT_PUBLIC_GOOGLE_MAPS_API_KEY }}
  run: |
    echo "NEXT_PUBLIC_GOOGLE_MAPS_API_KEY=$MAPS_KEY_PRIMARY" >> .env
```

- GitHub Actions creates `.env` file temporarily
- Next.js build reads it and bundles `NEXT_PUBLIC_*` vars into client code
- File is never committed
- Cloudflare Workers get runtime env vars separately

### What Gets Deployed
- **Client bundle**: Contains `NEXT_PUBLIC_*` vars (by design - they're public)
- **Cloudflare runtime**: Gets sensitive vars as Worker environment variables (encrypted)
- **No `.env` files**: Never deployed, only used during build

---

## Local Development Reality Check

### What Works Without `.env.local`
✅ Static pages (landing, about, pricing)  
✅ Component rendering  
✅ Basic navigation  

### What Doesn't Work Without `.env.local`
❌ Flight viewer (needs Google Maps API key)  
❌ Authentication (needs Cognito config)  
❌ Creating projects (needs API endpoints)  
❌ ML pipeline (needs API endpoints)  
❌ Subscription management (needs Stripe + API endpoints)  
❌ Analytics tracking  

**Why?** All those features call `process.env.NEXT_PUBLIC_*` which returns `undefined` without `.env.local`.

---

## Recommended Local Setup

### Option 1: Full Setup (All Features)

Create `web/.env.local` with all the secrets:

```bash
# Run the interactive setup
./scripts/setup-local-env.sh

# Or manually create web/.env.local with:
NEXT_PUBLIC_GOOGLE_MAPS_API_KEY=<from Google Cloud Console>
NEXT_PUBLIC_GOOGLE_MAPS_MAP_ID=<optional>

# Cognito (from CDK outputs or GitHub secrets)
NEXT_PUBLIC_COGNITO_REGION=us-west-2
NEXT_PUBLIC_COGNITO_USER_POOL_ID=us-west-2_xxxxx
NEXT_PUBLIC_COGNITO_USER_POOL_CLIENT_ID=xxxxx

# API Endpoints (use preview URLs)
NEXT_PUBLIC_PROJECTS_API_URL=https://xxx.execute-api.us-west-2.amazonaws.com/preview
NEXT_PUBLIC_DRONE_PATH_API_URL=https://xxx.execute-api.us-west-2.amazonaws.com/preview
NEXT_PUBLIC_FILE_UPLOAD_API_URL=https://xxx.execute-api.us-west-2.amazonaws.com/preview
NEXT_PUBLIC_WAITLIST_API_URL=https://xxx.execute-api.us-west-2.amazonaws.com/preview
NEXT_PUBLIC_ML_PIPELINE_API_URL=https://xxx.execute-api.us-west-2.amazonaws.com/preview
NEXT_PUBLIC_BETA_ACCESS_API_URL=https://xxx.execute-api.us-west-2.amazonaws.com/preview
NEXT_PUBLIC_FEEDBACK_API_URL=https://xxx.execute-api.us-west-2.amazonaws.com/preview
NEXT_PUBLIC_SUBSCRIPTION_API_URL=https://xxx.execute-api.us-west-2.amazonaws.com/preview

# Stripe (use test keys for local)
NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY=pk_test_xxxxx

# Analytics (optional)
NEXT_PUBLIC_SENTRY_DSN=https://xxxxx
NEXT_PUBLIC_POSTHOG_KEY=phc_xxxxx
NEXT_PUBLIC_POSTHOG_HOST=https://app.posthog.com
```

### Option 2: Minimal Setup (Just Flight Viewer)

```bash
# web/.env.local
NEXT_PUBLIC_GOOGLE_MAPS_API_KEY=<your-key>
```

This is enough to test the flight viewer. Other features will gracefully degrade.

### Option 3: Use Preview Deployment

```bash
# Don't run locally, just test on preview URLs
https://agent-<branch>.v0-spaceport-website-preview2.pages.dev/
```

This is often faster than setting up all local secrets.

---

## Security Best Practices

### ✅ DO
- Keep `.env.local` in your home directory or project root
- Use **test/development** API keys for local work
- Use **preview** environment endpoints (not production!)
- Rotate keys if you accidentally commit them
- Use GitHub CLI to check what secrets exist: `gh secret list`

### ❌ DON'T
- Commit `.env`, `.env.local`, or `.env.production` (already gitignored)
- Put secrets in code comments or documentation
- Use production Stripe/AWS keys locally
- Share your `.env.local` file with others
- Screenshot terminal output with secrets visible

---

## How to Get Secret Values

### Google Maps API Key
1. Go to https://console.cloud.google.com/apis/credentials
2. Create new API key or use existing
3. Restrict it to:
   - HTTP referrers: `localhost:*`, `*.pages.dev`, `spcprt.com`
   - APIs: Map Tiles API, Photorealistic 3D Tiles API

### Cognito Config
```bash
# From CDK outputs after deployment
cd infrastructure/spaceport_cdk
cdk deploy --outputs-file cdk-outputs.json
cat cdk-outputs.json | grep -i cognito
```

### API Endpoints
```bash
# From CDK outputs
cd infrastructure/spaceport_cdk
cdk deploy --outputs-file cdk-outputs.json
cat cdk-outputs.json | jq '.SpaceportStack'
```

Or check GitHub secrets:
```bash
gh secret list | grep API_URL
```

### Stripe Keys
- Use **test mode** keys for local: `pk_test_...` and `sk_test_...`
- Get from: https://dashboard.stripe.com/test/apikeys

---

## Troubleshooting

### "Google Maps API key missing"
**Cause**: No `.env.local` or missing `NEXT_PUBLIC_GOOGLE_MAPS_API_KEY`  
**Fix**: Create `web/.env.local` with the key, restart dev server

### "Auth not available" / Login doesn't work
**Cause**: Missing Cognito config in `.env.local`  
**Fix**: Add `NEXT_PUBLIC_COGNITO_*` variables

### API calls fail with 404/403
**Cause**: Wrong API endpoint URLs or not authenticated  
**Fix**: 
1. Verify API URLs in `.env.local` match deployed endpoints
2. Check Cognito login works first
3. Use preview environment URLs, not production

### Changes to `.env.local` not taking effect
**Cause**: Next.js only reads env files at startup  
**Fix**: Stop dev server (`Ctrl+C`) and restart (`npm run dev`)

---

## FAQ

### Q: Can someone steal my Google Maps API key from my deployed site?
**A**: They can extract it from the client bundle, but it's restricted by domain in Google Cloud Console. Set allowed referrers to only your domains.

### Q: Why does production work but local dev doesn't?
**A**: Production has secrets injected by GitHub Actions. Local dev needs `.env.local` created manually.

### Q: Is it safe to use production secrets locally?
**A**: **No.** Use test/development keys and preview environment endpoints for local work.

### Q: Do I need ALL the secrets for local dev?
**A**: No. Only add the ones for features you're actively testing. Most features gracefully degrade when env vars are missing.

### Q: Can I commit `.env.local.example`?
**A**: Yes! Example/template files with placeholder values are safe to commit. Just never commit the actual `.env.local` with real values.

### Q: How do I share secrets with teammates?
**A**: Use a password manager (1Password, LastPass) or have them:
1. Get API keys from the respective platforms themselves
2. Ask repo admin to add them to GitHub Secrets
3. Use the same shared development API endpoints

---

## Summary

**For You Personally (Local Dev)**:
1. Create `web/.env.local` (gitignored, safe)
2. Add only the secrets you need for testing
3. Use test/development keys, not production
4. Never commit it

**For Production (GitHub/Cloudflare)**:
1. All secrets in GitHub Secrets (encrypted)
2. GitHub Actions injects them during build
3. Client-safe vars bundled, sensitive vars stay server-side
4. Nothing committed to repository

**Security is maintained** because:
- `.env.local` is gitignored ✅
- GitHub Secrets are encrypted ✅
- Production secrets never in code ✅
- `NEXT_PUBLIC_*` vars are designed to be public ✅

