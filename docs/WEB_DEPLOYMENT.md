## Web Deployment: Next.js on Cloudflare Pages (SSR/ISR)

High-signal reference for agents and developers.

### TL;DR
- App: Next.js (App Router) in `web/`, Edge runtime (`export const runtime = 'edge'`).
- Build: `next build` then `npx @cloudflare/next-on-pages`.
- Deploy: Upload `.vercel/output/static` (contains `_worker.js`) to Cloudflare Pages. This is critical for Functions mount.
- Flags: Set `compatibility_date` ≥ 2025‑08‑09 and `nodejs_compat,nodejs_compat_populate_process_env` on the Pages project.

### Branch-to-Environment
- `development` → Staging Pages project/branch alias.
- `main` → Production Pages project `v0-spaceport-website-prod-fresh`.

### Required Secrets (GitHub Actions)
- `CLOUDFLARE_ACCOUNT_ID`
- `CLOUDFLARE_API_TOKEN`
- `CF_PAGES_PROJECT` (base project, prod override may be enforced in workflow)
- Optional overrides: `CF_PAGES_PROJECT_DEV_OVERRIDE`, `CF_PAGES_PROJECT_PROD_OVERRIDE`, `CF_PAGES_PROJECT_PROD_FRESH`

### CI Build Steps (summarized)
1) `npm ci`
2) `npm run build` (Next.js) → do not enable static export (`next.config` must not set `output: 'export'`).
3) `npx @cloudflare/next-on-pages` → generates `.vercel/output/static/_worker.js` and Edge routes.
4) `wrangler pages deploy .vercel/output/static --project-name <PROJECT> --branch <ALIAS>`.
5) Verify endpoints: `/`, `/landing`, `/about`, `/pricing`, `/create`, `/signup`, `/api/health`.

### Project Runtime Flags via API (idempotent)
```
PATCH /client/v4/accounts/{ACCOUNT_ID}/pages/projects/{PROJECT}
{
  "deployment_configs": {
    "production": {
      "compatibility_date": "2025-08-09",
      "compatibility_flags": ["nodejs_compat","nodejs_compat_populate_process_env"]
    },
    "preview": {
      "compatibility_date": "2025-08-09",
      "compatibility_flags": ["nodejs_compat","nodejs_compat_populate_process_env"]
    }
  }
}
```

### Gotchas and Fixes
- If you deploy `.vercel/output` (parent) instead of `.vercel/output/static`, Pages may not mount the worker → 404 on SSR/API.
- Ensure `runtime = 'edge'` on app/API routes and no static export in `web/next.config.cjs`.
- Keep the project clean (avoid legacy Git-linked configs). Creating a “fresh” project with flags pre-set improves mount reliability.

### Local parity (optional)
- Preview locally: `npm run cf:preview` → proxies `.vercel/output/static`.


