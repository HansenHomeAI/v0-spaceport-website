#!/usr/bin/env bash
set -euo pipefail

# Re-enters Codex with a tiny resume prompt unless STATE.md says BLOCKED.
while :; do
  if [[ -f STATE.md ]] && grep -q '^BLOCKED:' STATE.md; then
    echo "Blocked. See STATE.md" >&2
    exit 1
  fi

  # Nudge prompt keeps it acting without summaries.
  codex <<'PROMPT'
Resume continuous development cycle per Autonomy Contract:
- Read STATE.md if present and resume.
- Apply smallest fix, push branch, watch CI until preview is green, resolve exact PREVIEW_URL.
- Run Playwright MCP against PREVIEW_URL. If failing, plan next smallest fix and continue.
- Write long logs to logs/ and keep output within 120 lines. Do not pause unless BLOCKED (then write STATE.md).
PROMPT

  # Small delay to avoid hammering if the model returns super fast.
  sleep 2

done
