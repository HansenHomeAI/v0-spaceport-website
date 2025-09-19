# Repository Guidelines

## Agentic Dev Loop SOP
1. **Branch**: from `development` create `agent-12345678-task-name` (unique eight-digit ID plus slug, e.g. `agent-74120953-update-web-copy`).
2. **Baseline**: deploy, monitor GitHub Actions until the Cloudflare preview is green, and capture failing logs (run `gh run watch/logs` locally before touching the API—no debug cycle is complete until the live preview succeeds).
3. **Test**: start Playwright MCP with `python3 scripts/playwright-mcp-manager.py ensure`, record a baseline run, and expand coverage when gaps appear.
4. **Iterate**: apply the smallest fix, redeploy, watch the live preview build/logs, and rerun the baseline until everything passes.
5. **Wrap**: open a `development` PR only after preview and tests are green; escalate secret or production-config work.

## Guardrails (Never Do)
- Modify `main` or production configuration.
- Change secrets or add deploy targets.
- Disable tests or drop coverage to "make it pass".
- Commit binaries larger than 5 MB.

## Project Structure & Module Organization
`web/` holds the Next.js App Router (`app/`), shared `components/`, helpers in `lib/`, and static `public/`. `infrastructure/` covers CDK stacks, Lambda code, and container contexts; `scripts/` hosts automation; `tests/` contains regression suites.

## Build, Test, and Development Commands
Inside `web/`: run `npm install`, `npm run dev`, `npm run build`, `npm run start`, and `npm run cf:build`/`npm run cf:preview` for Cloudflare builds. For CDK use `pip install -r infrastructure/spaceport_cdk/requirements.txt` followed by `cdk synth` or `cdk deploy`. Environment tip: surface `NEXT_PUBLIC_FEEDBACK_API_URL` (Feedback API output) alongside the existing public API URLs.

## Coding Style & Naming Conventions
Frontend: TypeScript, two-space indent, PascalCase components, camelCase utilities, `npx next lint` before committing, and keep server/client modules split. Infrastructure Python follows PEP 8 (snake_case, docstrings).

## Testing Guidelines
Run `python3 tests/run_beta_readiness_suite.py` for full regression (`--quick` for faster loops); targeted work should call the scripts in `tests/pipeline/`. For MCP frontend coverage ensure Node 18+ and run `npx playwright install` once, start the server with `python3 scripts/playwright-mcp-manager.py ensure` (honours `PLAYWRIGHT_MCP_PORT`/`PLAYWRIGHT_MCP_COMMAND`) or launch `npx @playwright/mcp@latest --headless`. After `browser_navigate`, read the YAML snapshot for refs (e.g. `textbox "Email" [ref=e35]`) before driving `browser_fill_form`, `browser_click`, `browser_wait_for`, or `browser_handle_dialog`, and log arguments plus console output each step. Use `npx @wong2/mcp-cli npx @playwright/mcp@latest` for STDIO probes or script the SSE endpoint with `@modelcontextprotocol/sdk`—`scripts/run_waitlist_flow.mjs` is a template that can be retargeted via its URL argument or `PLAYWRIGHT_MCP_SSE_URL`. Supplement MCP telemetry with the local CLIs you already have (`gh`, `aws`, `wrangler`, `git`, etc.) before falling back to raw APIs.

## Commit & Pull Request Guidelines
Stick to the Conventional Commit prefixes in history (`feat:`, `fix:`, `chore:`). PRs target `development`, reference the driving task, describe behavior changes, detail exercised tests (Playwright MCP, beta readiness, manual), share screenshots or logs for UI updates, and wait for the preview to stabilize before review.
