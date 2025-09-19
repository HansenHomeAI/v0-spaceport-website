# Agentic Dev Loop SOP

For each task, create a unique agent-{id} branch. Deploy it and monitor GitHub Actions for failures, waiting for a successful live preview. Run baseline tests via Playwright MCP (and generate additional ones if useful) to capture the current state. Analyze results and logs, plan minimal fixes, commit, and redeploy. If deployment fails, debug with Git CLI, AWS CLI, Playwright MCP, and Wrangler CLI as needed. Re-run tests, compare outcomes, and iterate until all tests pass and the desired behavior is reached. Only then open a PR into the development branch. Stop before changing secrets, require manual approval for that.

## Guardrails (Never Do)

- Touch main or production config.
- Rotate/edit secrets or add new deploy targets.
- Disable tests or lower coverage to "make it pass".
- Commit large binary assets (>5MB) to the repo.
