# Agent Operating Procedures

## Branching & Isolation
- Start from the designated integration branch (default `development`) unless stated otherwise.
- Create a unique feature branch named `agent-<id>` for every task and keep all edits isolated there until validation succeeds.

## Planning & Execution Loop
1. Perform a brief structured analysis before coding covering objectives, risks, approach, and validation.
2. Implement the smallest viable change that satisfies the objectives while minimizing churn.
3. Push the branch and actively monitor the CI pipeline using the most reliable interface available (API ➜ official CLI ➜ other signals). Capture direct links to runs and artifacts.
4. Discover the branch or commit preview URL (deployment API ➜ provider CLI ➜ build output parsing). Treat the discovered URL as `BASE_URL`; if previews are unavailable, propose the smallest configuration change to enable them and pause for approval.
5. Run headless, deterministic end-to-end checks against `BASE_URL` using the playwright MCP, covering critical user flows including authentication.
6. If CI, deployment, or E2E checks fail, collect precise failure evidence (logs, artifacts), diagnose the root cause, and apply the smallest fix. Re-run the full validate cycle once (push ➜ monitor CI ➜ confirm preview ➜ run E2E). If the second attempt fails, stop with a clear diagnosis and recommended next steps—do not open a PR.
7. Only after CI is green, the preview is healthy, and E2E checks succeed, open a PR from the `agent-<id>` branch into the integration branch. Summarize the change, rationale, and validation evidence in the PR.

## Reporting & Safety
- Provide a final report that summarizes the work, includes links to the branch, CI runs, deployments/previews, and E2E results, and notes trade-offs or follow-ups.
- Handle secrets safely and consult maintainers before modifying CI/deployment credentials or configuration.
- Maintain least-change discipline: keep diffs tight, reversible, and consistent with existing conventions.

These procedures govern every task executed by agents within this repository.
