#!/usr/bin/env python3
"""Validate an MD1 paid-retry strategy against the current quality blockers."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def load_json(path: str) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def list_strings(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value if str(item)]


def split_label_list(value: Any) -> list[str]:
    if isinstance(value, list):
        return list_strings(value)
    if not isinstance(value, str):
        return []
    result: list[str] = []
    for item in value.replace(";", ",").split(","):
        cleaned = item.strip()
        if cleaned:
            result.append(cleaned)
    return result


def quality_blockers(readiness_report: dict[str, Any]) -> list[str]:
    gate = readiness_report.get("quality_gate") if isinstance(readiness_report.get("quality_gate"), dict) else {}
    blockers = list_strings(gate.get("block_reasons"))
    if blockers:
        return sorted(set(blockers))

    decision = (
        readiness_report.get("promotion_decision")
        if isinstance(readiness_report.get("promotion_decision"), dict)
        else {}
    )
    return sorted(set(list_strings(decision.get("block_reasons"))))


def targeted_blockers(strategy: dict[str, Any]) -> list[str]:
    direct = list_strings(strategy.get("targeted_quality_blockers"))
    if direct:
        return sorted(set(direct))

    direct = list_strings(strategy.get("targeted_quality_block_reasons"))
    if direct:
        return sorted(set(direct))

    nested = strategy.get("quality_strategy")
    if isinstance(nested, dict):
        return sorted(
            set(
                list_strings(nested.get("targeted_quality_blockers"))
                + list_strings(nested.get("targeted_quality_block_reasons"))
            )
        )
    stage_targets: list[str] = []
    stages = strategy.get("stages")
    if isinstance(stages, list):
        for stage in stages:
            if not isinstance(stage, dict):
                continue
            env = stage.get("environment")
            if isinstance(env, dict):
                stage_targets.extend(split_label_list(env.get("TARGETED_QUALITY_BLOCKERS")))
                stage_targets.extend(split_label_list(env.get("TARGETED_QUALITY_BLOCK_REASONS")))
    return sorted(set(stage_targets))


def estimated_usd(strategy: dict[str, Any]) -> float | None:
    cost = strategy.get("planned_cost_estimate")
    if not isinstance(cost, dict):
        cost = strategy.get("cost_estimate")
    if not isinstance(cost, dict):
        return None
    for key in ("estimated_usd", "worst_case_usd"):
        if cost.get(key) is not None:
            try:
                return float(cost[key])
            except (TypeError, ValueError):
                return None
    return None


def no_full_14tile_training_confirmed(strategy: dict[str, Any]) -> bool:
    if strategy.get("no_full_14tile_training") is True:
        return True
    if strategy.get("full_14tile_training_launched") is False:
        return True
    selected_tile_ids = strategy.get("selected_tile_ids")
    if isinstance(selected_tile_ids, list):
        normalized = [str(tile_id) for tile_id in selected_tile_ids if str(tile_id)]
        if 0 < len(set(normalized)) < 14:
            return True
    return False


def evaluate_gate(
    *,
    readiness_report: dict[str, Any],
    strategy: dict[str, Any],
    max_estimated_usd: float = 0.0,
    require_no_full_14tile: bool = True,
    require_dry_run: bool = True,
) -> dict[str, Any]:
    block_reasons: list[str] = []
    warnings: list[str] = []
    current_blockers = quality_blockers(readiness_report)
    targets = targeted_blockers(strategy)
    promotion_ready = readiness_report.get("promotion_ready") is True

    missing_targets = [reason for reason in current_blockers if reason not in targets]
    if current_blockers and not targets:
        block_reasons.append("quality_strategy_missing_targeted_blockers")
    elif missing_targets:
        block_reasons.append("quality_strategy_does_not_target_current_blockers")

    no_full_14tile = no_full_14tile_training_confirmed(strategy)
    if require_no_full_14tile and not no_full_14tile:
        block_reasons.append("no_full_14tile_training_not_confirmed")

    submitted_jobs = strategy.get("submitted_jobs")
    if require_dry_run and submitted_jobs not in ([], None):
        block_reasons.append("strategy_already_submitted_jobs")

    cost = estimated_usd(strategy)
    if max_estimated_usd > 0:
        if cost is None:
            block_reasons.append("strategy_missing_cost_estimate")
        elif cost > max_estimated_usd:
            block_reasons.append("strategy_estimated_cost_above_cap")
    elif cost is None:
        warnings.append("strategy_missing_cost_estimate")

    if promotion_ready:
        block_reasons = [
            reason
            for reason in block_reasons
            if reason
            not in {
                "quality_strategy_missing_targeted_blockers",
                "quality_strategy_does_not_target_current_blockers",
            }
        ]

    return {
        "checked_at": now_iso(),
        "decision": "paid_retry_allowed" if not block_reasons else "paid_retry_blocked",
        "promotion_ready": promotion_ready,
        "current_quality_blockers": current_blockers,
        "targeted_quality_blockers": targets,
        "missing_targeted_blockers": missing_targets,
        "block_reasons": block_reasons,
        "warnings": warnings,
        "max_estimated_usd": max_estimated_usd or None,
        "estimated_usd": cost,
        "require_no_full_14tile": require_no_full_14tile,
        "require_dry_run": require_dry_run,
        "no_full_14tile_training": no_full_14tile,
        "submitted_jobs": submitted_jobs,
        "next_required_action": (
            "paid retry may proceed through its own leaf/preflight gates"
            if not block_reasons
            else "add an explicit no-spend quality strategy that targets every current frozen-quality blocker before paid retry"
        ),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--readiness-report-json", required=True)
    parser.add_argument("--strategy-json", required=True)
    parser.add_argument("--max-estimated-usd", type=float, default=0.0)
    parser.add_argument("--allow-full-14tile", action="store_true")
    parser.add_argument("--allow-submitted-jobs", action="store_true")
    parser.add_argument("--summary-json-output", required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    summary = evaluate_gate(
        readiness_report=load_json(args.readiness_report_json),
        strategy=load_json(args.strategy_json),
        max_estimated_usd=args.max_estimated_usd,
        require_no_full_14tile=not args.allow_full_14tile,
        require_dry_run=not args.allow_submitted_jobs,
    )
    output_path = Path(args.summary_json_output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))
    return 0 if summary["decision"] == "paid_retry_allowed" else 2


if __name__ == "__main__":
    raise SystemExit(main())
