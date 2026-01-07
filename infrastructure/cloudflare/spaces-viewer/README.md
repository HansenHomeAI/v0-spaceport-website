# Spaces Viewer Worker

Hosts per-model HTML viewer files from Cloudflare R2 at branded URLs.

## Responsibilities
- Accept HTML uploads at `POST /publish` (admin-only).
- Store files in R2 under `models/{slug}/index.html`.
- Serve viewer pages at `GET /{slug}`.

## Configuration
- **R2 bucket**: `spaces-viewers` (binding `SPACES_BUCKET`)
- **Environment variables**:
  - `SPACES_HOST` (optional): default host for generated URLs.
  - `ADMIN_EMAIL_DOMAIN` or `ADMIN_EMAIL_ALLOWLIST`: restricts who can publish.
  - `COGNITO_REGION` + `COGNITO_USER_POOL_ID`: used to validate JWT tokens.
  - `SPACES_PUBLISH_TOKEN` (optional): shared secret override for publish requests.

## Deploy
```bash
cd infrastructure/cloudflare/spaces-viewer
wrangler r2 bucket create spaces-viewers
wrangler secret put COGNITO_REGION
wrangler secret put COGNITO_USER_POOL_ID
wrangler secret put SPACES_PUBLISH_TOKEN
wrangler deploy
```

## Test
```bash
curl -s https://spaces.spcprt.com/health
```
