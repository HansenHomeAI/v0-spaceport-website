# Local Development Setup

> ⚠️ **Security Note**: See [SECURITY_AND_LOCAL_DEVELOPMENT.md](../docs/SECURITY_AND_LOCAL_DEVELOPMENT.md) for full details on secrets, what's safe to use locally, and production vs development keys.

## Quick Start

### 1. Install Dependencies
```bash
cd web
npm install
```

### 2. Set Up Environment Variables

Create a `.env.local` file in the `web/` directory:

```bash
# Option A: Use the setup script (interactive)
cd ..
./scripts/setup-local-env.sh

# Option B: Manual setup
cp env.local.example .env.local
# Then edit .env.local and fill in your values
```

### 3. Get Your Google Maps API Key

You need a Google Maps API key for the flight-viewer feature:

1. **From GitHub Secrets** (if you have access):
   ```bash
   # The key is stored as: NEXT_PUBLIC_GOOGLE_MAPS_API_KEY
   # Contact repo maintainer for the value
   ```

2. **From Google Cloud Console**:
   - Go to https://console.cloud.google.com/apis/credentials
   - Create or copy an existing API key
   - Ensure it has these APIs enabled:
     - Map Tiles API
     - Photorealistic 3D Tiles API

3. **Add to `.env.local`**:
   ```env
   NEXT_PUBLIC_GOOGLE_MAPS_API_KEY=AIza...your-key-here
   ```

### 4. Run Development Server

```bash
npm run dev
```

Visit http://localhost:3000 to see your changes.

---

## Environment Variables

### Required for Flight Viewer
- `NEXT_PUBLIC_GOOGLE_MAPS_API_KEY` - Google Maps API key for 3D tiles

### Optional (for full app functionality)
- `NEXT_PUBLIC_PROJECTS_API_URL` - Projects API endpoint
- `NEXT_PUBLIC_DRONE_PATH_API_URL` - Drone path API endpoint
- `NEXT_PUBLIC_COGNITO_REGION` - AWS Cognito region
- `NEXT_PUBLIC_COGNITO_USER_POOL_ID` - Cognito User Pool ID
- `NEXT_PUBLIC_COGNITO_USER_POOL_CLIENT_ID` - Cognito Client ID
- `NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY` - Stripe public key

---

## Troubleshooting

### "Google Maps API key missing" Error

**Symptom**: Flight viewer shows "Google Maps API key missing" message

**Cause**: No `.env.local` file exists or it's missing the key

**Fix**:
1. Verify `.env.local` exists in the `web/` directory
2. Confirm it contains: `NEXT_PUBLIC_GOOGLE_MAPS_API_KEY=...`
3. Restart the dev server (`Ctrl+C`, then `npm run dev` again)

### Environment Variable Not Loading

**Remember**: 
- Next.js only reads `.env.local` at **startup**
- After changing `.env.local`, **restart the dev server**
- Variables must be prefixed with `NEXT_PUBLIC_` to be available in browser code

---

## Production vs Development

| Environment | Config Source | How It Works |
|------------|---------------|--------------|
| **Production** | GitHub Secrets | GitHub Actions creates `.env` during build |
| **Preview** | GitHub Secrets | Same as production, different values |
| **Local** | `.env.local` | You create this file manually |

The `.env.local` file is gitignored for security - never commit it!

---

## How GitHub Actions Works

For reference, here's how the production build gets its env vars:

1. GitHub Actions workflow runs on push
2. Script reads secrets from repository settings
3. Creates a `.env` file in `web/` directory
4. Next.js build bundles these into the static output
5. Deploys to Cloudflare Pages

You're replicating step 3 locally by creating `.env.local`.
