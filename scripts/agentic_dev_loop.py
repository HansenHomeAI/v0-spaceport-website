#!/usr/bin/env python3
"""Harness the Codex CLI to execute the Agentic Dev Loop SOP."""
from __future__ import annotations

import argparse
import datetime as _dt
import os
import re
import shlex
import shutil
import subprocess
import sys
import textwrap
from pathlib import Path
from typing import Iterable, Optional

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BRANCH = "development"
DEFAULT_CODEX_COMMAND = os.environ.get("CODEX_CLI_COMMAND", "codex")
DEFAULT_PLAYWRIGHT_MCP_TASK = os.environ.get(
    "PLAYWRIGHT_MCP_BASELINE_TASK",
    "playwright-mcp baseline --output .agentic/playwright-baseline",
)


def _slugify(text: str, *, max_length: int = 30) -> str:
    cleaned = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    if not cleaned:
        cleaned = "objective"
    if len(cleaned) > max_length:
        cleaned = cleaned[:max_length].rstrip("-")
    return cleaned or "objective"


def generate_branch_name(objective: str) -> str:
    timestamp = _dt.datetime.utcnow().strftime("%Y%m%d%H%M%S")
    suffix = _slugify(objective, max_length=18)
    return f"agent-{timestamp}-{suffix}"


def ensure_codex_available(command: str) -> Optional[str]:
    executable = shlex.split(command)[0]
    return shutil.which(executable)


def build_instruction_block(
    *,
    objective: str,
    branch_name: str,
    playwright_task: str,
    repo_root: Path,
) -> str:
    sop = textwrap.dedent(
        f"""
        You are Codex CLI executing the Spaceport Agentic Dev Loop SOP. Operate autonomously while
        respecting all safeguards.

        ## Primary Objective
        {objective.strip()}

        ## Repository & Deployment Context
        - Repository root: {repo_root}
        - Integration branch: {DEFAULT_BRANCH}
        - Frontend app: Next.js project in `web/`
        - Deployments: GitHub Actions workflow "Deploy Next.js to Cloudflare Pages" pushes to Cloudflare Pages
          projects (`development` → preview, `main` → production).
        - Cloudflare deploy path must be `.vercel/output/static` to expose `_worker.js`.
        - Additional workflows: `build-containers.yml`, `cdk-deploy.yml` (AWS infrastructure). Monitor for regressions.

        ## Guardrails
        - Always work from a unique feature branch (`{branch_name}`) forked from `{DEFAULT_BRANCH}`.
        - Do not modify or rotate secrets. Pause and request maintainer approval for any secret change.
        - Apply smallest viable fixes; avoid refactors unless necessary for the objective.
        - If a deployment or CI cycle fails twice, halt and provide a written diagnosis.

        ## Required Loop
        1. Checkout `{DEFAULT_BRANCH}`, fetch, and create `{branch_name}`.
        2. Capture the current state:
           - Install dependencies as needed (`npm ci` in `web/`).
           - Build locally if helpful (`npm run build`).
           - Trigger preview deployment by pushing `{branch_name}`.
        3. Monitor GitHub Actions:
           - Use `gh run watch --branch {branch_name}` for `Deploy Next.js to Cloudflare Pages`.
           - Record run URLs and surface any failing jobs (`build-containers`, `cdk-deploy`).
        4. Discover the Cloudflare preview URL:
           - Prefer workflow outputs (hash + alias URLs).
           - Otherwise query `wrangler pages deployment list --project-name <preview-project>` and resolve latest deployment.
        5. With `BASE_URL` set to the preview URL, execute baseline end-to-end checks via Playwright MCP:
           - Run `{playwright_task} --base-url "$BASE_URL"` (adjust task if baseline scripts change).
           - Archive results in `.agentic/playwright-baseline` and summarize pass/fail status.
        6. Analyse failures and plan the minimum fix. Document the hypothesis before editing files.
        7. Implement the fix, run unit/integration tests as needed (`npm test`, targeted Python suites under `tests/`).
        8. Commit with a clear message, push, redeploy, and repeat validation (CI ➜ preview ➜ Playwright MCP).
        9. Once CI is green, preview is healthy, and tests pass, open a PR targeting `{DEFAULT_BRANCH}` including:
           - Summary of changes and rationale.
           - Links to CI runs, deployment previews, and test artifacts.

        ## Evidence & Logging Expectations
        - Maintain `notes/agentic/{branch_name}.md` (create if absent) capturing investigation notes.
        - Store links to GitHub Action runs, Cloudflare deployment IDs, and MCP outputs.
        - Surface blockers early; request human support if secrets or credentials are missing.

        Execute iteratively until the objective is met or a blocking issue is identified.
        """
    ).strip()
    return sop


def launch_codex(
    command: str,
    instructions: str,
    *,
    dry_run: bool,
    transcript_path: Optional[Path] = None,
) -> int:
    if dry_run:
        print(instructions)
        if transcript_path:
            transcript_path.write_text(instructions)
        return 0

    if transcript_path:
        transcript_path.write_text(instructions)

    process = subprocess.run(
        shlex.split(command),
        input=instructions,
        text=True,
        check=False,
    )
    return process.returncode


def parse_args(argv: Optional[Iterable[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Bootstrap the Spaceport Agentic Dev Loop by feeding a structured prompt into the Codex CLI."
        )
    )
    parser.add_argument(
        "objective",
        nargs="?",
        help="Desired outcome for this troubleshooting session. If omitted, you will be prompted interactively.",
    )
    parser.add_argument(
        "--branch-name",
        dest="branch_name",
        help="Override the generated agent branch name.",
    )
    parser.add_argument(
        "--codex-command",
        dest="codex_command",
        default=DEFAULT_CODEX_COMMAND,
        help="Codex CLI command to execute (default: %(default)s).",
    )
    parser.add_argument(
        "--playwright-task",
        dest="playwright_task",
        default=DEFAULT_PLAYWRIGHT_MCP_TASK,
        help="Command Codex should run via Playwright MCP for baseline capture.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the generated instructions without invoking the Codex CLI.",
    )
    parser.add_argument(
        "--transcript",
        dest="transcript",
        type=Path,
        help="Optional path to store the rendered instructions for auditing.",
    )
    return parser.parse_args(argv)


def main(argv: Optional[Iterable[str]] = None) -> int:
    args = parse_args(argv)

    objective = args.objective
    if not objective:
        try:
            objective = input("Describe the desired outcome for this session:\n> ").strip()
        except KeyboardInterrupt:
            print("\nAborted.", file=sys.stderr)
            return 130
    if not objective:
        print("An objective is required to start the Agentic Dev Loop.", file=sys.stderr)
        return 1

    branch_name = args.branch_name or generate_branch_name(objective)

    instructions = build_instruction_block(
        objective=objective,
        branch_name=branch_name,
        playwright_task=args.playwright_task,
        repo_root=REPO_ROOT,
    )

    transcript_path = args.transcript
    if transcript_path and not transcript_path.is_absolute():
        transcript_path = REPO_ROOT / transcript_path
        transcript_path.parent.mkdir(parents=True, exist_ok=True)

    codex_exists = ensure_codex_available(args.codex_command)
    if not codex_exists and not args.dry_run:
        print(
            textwrap.dedent(
                f"""
                Codex CLI command '{args.codex_command}' was not found on PATH.\n"
                "Use --dry-run to review the prompt or set CODEX_CLI_COMMAND to the correct executable."
                """
            ).strip(),
            file=sys.stderr,
        )
        return 127

    exit_code = launch_codex(
        args.codex_command,
        instructions,
        dry_run=args.dry_run,
        transcript_path=transcript_path,
    )

    if exit_code == 0:
        summary = textwrap.dedent(
            f"""
            Launched Codex CLI with branch '{branch_name}'.
            Track your working notes in notes/agentic/{branch_name}.md and proceed through the SOP.
            """
        ).strip()
        print(summary)
    else:
        print(f"Codex CLI exited with status {exit_code}.", file=sys.stderr)

    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
