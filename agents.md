# Repository Guidelines

## Agentic Dev Loop SOP
1. **Branch**: from `development` create `agent-12345678-task-name`; use a unique eight-digit ID and clear slug (e.g. `agent-74120953-update-web-copy`).
2. **Baseline**: deploy immediately and watch GitHub Actions until the Cloudflare preview is green, capturing failing logs.
3. **Test**: start Playwright MCP with `python scripts/playwright-mcp-manager.py ensure`, record a baseline run, and extend coverage if gaps appear.
4. **Iterate**: apply the smallest fix set, redeploy, and rerun the full baseline until every check passes.
5. **Wrap**: open a `development` PR only after preview and tests are green; escalate secret or production-config work.

## Guardrails (Never Do)
- Touch `main` or production configuration.
- Rotate or edit secrets, or create new deploy targets.
- Disable tests or lower coverage to "make it pass".
- Commit binaries larger than 5 MB.

## Project Structure & Module Organization
`web/` contains the Next.js App Router (`app/`), shared `components/`, utility `lib/`, and static `public/`. Infrastructure lives in `infrastructure/` (CDK sources in `spaceport_cdk/`, Lambda code, container build contexts); scripts stay in `scripts/`, docs in `docs/`, and regression suites in `tests/`.

## Build, Test, and Development Commands
In `web/`, run `npm install`; `npm run dev` for the dev server, `npm run build` for the production bundle, and `npm run start` for local verification. Use `npm run cf:build` to mirror Cloudflare Pages and `npm run cf:preview` for a Wrangler preview. For CDK work, install deps with `pip install -r infrastructure/spaceport_cdk/requirements.txt`, then run `cdk synth` or `cdk deploy` there.

## Coding Style & Naming Conventions
Frontend code is TypeScript with two-space indentation, PascalCase components, and camelCase utilities; keep server and client components split and lint with `npx next lint`. Infrastructure Python follows PEP 8 with snake_case modules and docstrings; align new docs with existing names in `docs/`.

## Testing Guidelines
Run `python tests/run_beta_readiness_suite.py` for full regression (`--quick` for faster loops); targeted work should call the scripts in `tests/pipeline/`. Frontend smoke checks rely on Playwright MCP—verify the server is running before scripted tests.

## Commit & Pull Request Guidelines
Stick to the Conventional Commit prefixes in history (`feat:`, `fix:`, `chore:`). PRs target `development`, reference the driving task, describe behavior changes, detail exercised tests (Playwright MCP, beta readiness, manual), share screenshots or logs for UI updates, and wait for the preview to stabilize before review.
