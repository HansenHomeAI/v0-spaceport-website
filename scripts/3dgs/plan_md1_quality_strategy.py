#!/usr/bin/env python3
"""Plan the next no-spend MD1 quality step from frozen review blockers."""

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


def promotion_decision(review_comparison: dict[str, Any]) -> dict[str, Any]:
    decision = review_comparison.get("promotion_decision")
    return decision if isinstance(decision, dict) else {}


def strategy_targets(strategy: dict[str, Any] | None) -> list[str]:
    if not strategy:
        return []
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
    return []


def planned_cost(strategy: dict[str, Any] | None) -> float | None:
    if not strategy:
        return None
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


def boundary_improvement_gaps(decision: dict[str, Any]) -> dict[str, Any] | None:
    per_bucket = decision.get("per_bucket") if isinstance(decision.get("per_bucket"), dict) else {}
    boundary = per_bucket.get("boundary") if isinstance(per_bucket.get("boundary"), dict) else {}
    deltas = boundary.get("delta") if isinstance(boundary.get("delta"), dict) else {}
    thresholds = decision.get("thresholds") if isinstance(decision.get("thresholds"), dict) else {}
    boundary_thresholds = thresholds.get("boundary") if isinstance(thresholds.get("boundary"), dict) else {}
    required = (
        boundary_thresholds.get("required_improvement")
        if isinstance(boundary_thresholds.get("required_improvement"), dict)
        else {}
    )
    if not deltas or not required:
        return None

    psnr_delta = float(deltas.get("psnr") or 0.0)
    ssim_delta = float(deltas.get("ssim") or 0.0)
    lpips_delta = float(deltas.get("lpips") or 0.0)
    psnr_required = float(required.get("psnr") or 0.0)
    ssim_required = float(required.get("ssim") or 0.0)
    lpips_required = float(required.get("lpips") or 0.0)

    return {
        "actual_delta": {
            "psnr": psnr_delta,
            "ssim": ssim_delta,
            "lpips": lpips_delta,
        },
        "required_improvement": {
            "psnr": psnr_required,
            "ssim": ssim_required,
            "lpips": lpips_required,
        },
        "remaining_gap": {
            "psnr": max(0.0, psnr_required - psnr_delta),
            "ssim": max(0.0, ssim_required - ssim_delta),
            "lpips": max(0.0, lpips_delta - lpips_required),
        },
        "passes_any_improvement_axis": (
            psnr_delta >= psnr_required
            or ssim_delta >= ssim_required
            or lpips_delta <= lpips_required
        ),
    }


def plan_quality_strategy(
    *,
    review_comparison: dict[str, Any],
    candidate_strategy: dict[str, Any] | None,
    max_estimated_usd: float = 0.0,
) -> dict[str, Any]:
    decision = promotion_decision(review_comparison)
    blockers = sorted(set(list_strings(decision.get("block_reasons"))))
    targets = strategy_targets(candidate_strategy)
    missing_targets = [reason for reason in blockers if reason not in targets]
    cost = planned_cost(candidate_strategy)
    boundary_gap = boundary_improvement_gaps(decision)
    submitted_jobs = candidate_strategy.get("submitted_jobs") if candidate_strategy else None
    no_full_14tile = candidate_strategy.get("no_full_14tile_training") if candidate_strategy else None

    candidate_strategy_ok = bool(candidate_strategy) and not missing_targets
    if max_estimated_usd > 0 and (cost is None or cost > max_estimated_usd):
        candidate_strategy_ok = False
    if submitted_jobs not in ([], None):
        candidate_strategy_ok = False
    if no_full_14tile is not True:
        candidate_strategy_ok = False

    recommendation = "hold_paid_retry"
    if not blockers:
        recommendation = "quality_blockers_clear"
    elif candidate_strategy_ok:
        recommendation = "candidate_strategy_targets_current_blockers"

    actions: list[dict[str, Any]] = []
    if "boundary_no_required_improvement" in blockers:
        actions.append(
            {
                "blocker": "boundary_no_required_improvement",
                "action": "produce_boundary_focused_no_spend_plan_before_paid_retry",
                "evidence_needed": [
                    "targeted_quality_blockers includes boundary_no_required_improvement",
                    "boundary frozen cameras and responsible tiles are listed",
                    "planned change can plausibly improve boundary PSNR/SSIM/LPIPS, not only tile density",
                    "max_estimated_usd remains capped before submit",
                ],
            }
        )

    if missing_targets:
        actions.append(
            {
                "blocker": "candidate_strategy_missing_current_blockers",
                "action": "do_not_submit_current_candidate_strategy",
                "missing_targeted_blockers": missing_targets,
            }
        )

    return {
        "checked_at": now_iso(),
        "promotion_decision_status": decision.get("status"),
        "current_quality_blockers": blockers,
        "candidate_strategy_present": bool(candidate_strategy),
        "candidate_targeted_quality_blockers": targets,
        "missing_targeted_blockers": missing_targets,
        "candidate_planned_cost_usd": cost,
        "max_estimated_usd": max_estimated_usd or None,
        "candidate_no_full_14tile_training": no_full_14tile,
        "candidate_submitted_jobs": submitted_jobs,
        "boundary_improvement_gap": boundary_gap,
        "recommendation": recommendation,
        "recommended_actions": actions,
        "paid_retry_recommended": recommendation == "candidate_strategy_targets_current_blockers",
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--review-comparison-json", required=True)
    parser.add_argument("--candidate-strategy-json", default="")
    parser.add_argument("--max-estimated-usd", type=float, default=0.0)
    parser.add_argument("--output-json", required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    candidate = load_json(args.candidate_strategy_json) if args.candidate_strategy_json else None
    report = plan_quality_strategy(
        review_comparison=load_json(args.review_comparison_json),
        candidate_strategy=candidate,
        max_estimated_usd=args.max_estimated_usd,
    )
    output_path = Path(args.output_json)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
