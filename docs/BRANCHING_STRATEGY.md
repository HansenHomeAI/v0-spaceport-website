## Branching & CI/CD (Concise)

### Branch roles
- `development` (staging): integration branch; every push deploys the Next.js app to a staging Cloudflare Pages project/alias.
- `main` (production): release branch; every push deploys to production Pages (`v0-spaceport-website-prod-fresh`).

### Workflow
1) Create feature branch from `development`.
2) PR → merge to `development`. CI deploys to staging.
3) When stable, merge `development` → `main`. CI deploys to production and verifies endpoints.

### CI essentials (web/)
- Build with `next build` → run `@cloudflare/next-on-pages`.
- Deploy `.vercel/output/static` so `_worker.js` is at the upload root (required for Functions mount).
- Verify endpoints automatically: `/`, `/landing`, `/about`, `/pricing`, `/create`, `/signup`, `/api/health`.

### Do / Don’t
- Do: keep `export const runtime = 'edge'` on app/API routes; avoid `output: 'export'` in `web/next.config.cjs`.
- Don’t: deploy `.vercel/output` root; this can serve 404s (worker not mounted).

### Rollback
- Revert the offending commit on `main` and push; CI redeploys the last good state.

---

Last Updated: After Cloudflare Pages SSR fix (worker mount via `.vercel/output/static`).