#!/usr/bin/env python3
"""Run NDVS benchmark scenes and enforce promotion gates in one command."""

from __future__ import annotations

import argparse
import json
import os
import shlex
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Tuple


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("benchmarks/ndvs/benchmark_config.json"),
        help="Path to NDVS benchmark config JSON.",
    )
    parser.add_argument(
        "--subset",
        default="control9",
        help="Subset key from benchmark config.",
    )
    parser.add_argument(
        "--gate",
        default="progress",
        help="Gate key from benchmark config.",
    )
    parser.add_argument(
        "--method-name",
        required=True,
        help="Method name expected in NDVS results rows.",
    )
    parser.add_argument(
        "--results-json",
        type=Path,
        default=None,
        help="Existing NDVS result rows JSON path. Required unless --eval-command is provided.",
    )
    parser.add_argument(
        "--run-command-template",
        default=os.environ.get("NDVS_RUN_COMMAND_TEMPLATE", ""),
        help=(
            "Optional shell command template to execute each scene. "
            "Placeholders: {dataset}, {scene}, {scene_token}, {method}, {output_dir}."
        ),
    )
    parser.add_argument(
        "--eval-command",
        default=os.environ.get("NDVS_EVAL_COMMAND", ""),
        help=(
            "Optional shell command to generate results JSON if --results-json is not provided. "
            "Placeholders: {method}, {subset}, {output_dir}."
        ),
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("logs/ndvs") / datetime.now(tz=timezone.utc).strftime("%Y%m%dT%H%M%SZ"),
        help="Directory for orchestration logs and scorecards.",
    )
    parser.add_argument(
        "--orientation-failures",
        type=int,
        default=0,
        help="Orientation validation failures for this run (fed into gate checks).",
    )
    parser.add_argument(
        "--scorecard-output",
        type=Path,
        default=None,
        help="Optional scorecard output path. Defaults to <output-dir>/scorecard.json.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print commands without executing them.",
    )
    return parser.parse_args()


def load_json(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def parse_scene_token(token: str) -> Tuple[str, str]:
    dataset, scene = token.split("/", 1)
    return dataset, scene


def run_shell(command: str, dry_run: bool) -> None:
    print(f"[cmd] {command}")
    if dry_run:
        return
    subprocess.run(command, shell=True, check=True)


def invoke_scorecard(
    args: argparse.Namespace,
    results_json: Path,
    scorecard_output: Path,
) -> int:
    cmd: List[str] = [
        "python3",
        "scripts/benchmarks/ndvs_scorecard.py",
        "--config",
        str(args.config),
        "--results-json",
        str(results_json),
        "--method-name",
        args.method_name,
        "--subset",
        args.subset,
        "--gate",
        args.gate,
        "--orientation-failures",
        str(args.orientation_failures),
        "--strict-scenes",
        "--fail-on-gate",
        "--output-json",
        str(scorecard_output),
    ]
    print("[scorecard] " + shlex.join(cmd))
    if args.dry_run:
        return 0
    completed = subprocess.run(cmd, check=False)
    return completed.returncode


def main() -> int:
    args = parse_args()
    config = load_json(args.config)

    scene_tokens = config.get("scene_subsets", {}).get(args.subset)
    if not scene_tokens:
        raise KeyError(f"Unknown subset '{args.subset}' in {args.config}")

    args.output_dir.mkdir(parents=True, exist_ok=True)
    scorecard_output = args.scorecard_output or (args.output_dir / "scorecard.json")

    if args.run_command_template:
        print(f"Running NDVS scene commands for subset '{args.subset}'...")
        for token in scene_tokens:
            dataset, scene = parse_scene_token(token)
            command = args.run_command_template.format(
                dataset=dataset,
                scene=scene,
                scene_token=token,
                method=args.method_name,
                output_dir=args.output_dir,
            )
            run_shell(command, args.dry_run)
    else:
        print("No run command template provided; skipping scene execution step.")

    results_json = args.results_json
    if results_json is None:
        if args.dry_run and not args.eval_command:
            results_json = args.output_dir / "ndvs_results.json"
            print("Dry-run mode: skipping results JSON requirement.")
        elif not args.eval_command:
            raise ValueError("--results-json is required when --eval-command is not provided.")
        else:
            eval_command = args.eval_command.format(
                method=args.method_name,
                subset=args.subset,
                output_dir=args.output_dir,
            )
            run_shell(eval_command, args.dry_run)
            # Convention: eval command writes this file.
            results_json = args.output_dir / "ndvs_results.json"

    if not args.dry_run and not results_json.exists():
        raise FileNotFoundError(f"NDVS results JSON not found: {results_json}")

    gate_code = invoke_scorecard(args, results_json, scorecard_output)
    if gate_code != 0:
        print(f"Gate enforcement failed with exit code {gate_code}.")
        return gate_code

    print(f"NDVS benchmark run completed. Scorecard: {scorecard_output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
