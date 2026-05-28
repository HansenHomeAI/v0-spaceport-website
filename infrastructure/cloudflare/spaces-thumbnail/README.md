# Spaces Thumbnail Worker

Generates 4:3 thumbnails for Spaceport viewer pages using Cloudflare Browser Rendering.

## Responsibilities
- Accept `POST /spaces-thumb/thumbnail` with `{ slug, viewerUrl?, force? }`.
- Render the viewer in headless Chrome at 1200x900.
- Store the JPEG at `models/{slug}/thumb.jpg` in R2 (`spaces-viewers`).

## Configuration
- **R2 bucket**: `spaces-viewers` (binding `SPACES_BUCKET`)
- **Browser rendering**: `browser` binding as `BROWSER`
- **Environment variables**:
  - `SPACES_HOST` (optional): default host for viewer URLs.
  - `SPACES_PATH_PREFIX` (optional): defaults to `/spaces`.
  - `THUMBNAIL_TOKEN` (optional): shared secret for thumbnail requests.

## Deploy
```bash
cd infrastructure/cloudflare/spaces-thumbnail
wrangler deploy
```

## Test
```bash
curl -s https://spcprt.com/spaces-thumb/health
```
