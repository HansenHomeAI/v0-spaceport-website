#!/usr/bin/env python3
"""Gate MD1 paid leaf-only proof submission against cost and live-state controls."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def load_json(path: str) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def parse_json_list(value: str) -> list[Any]:
    parsed = json.loads(value)
    if not isinstance(parsed, list):
        raise ValueError(f"expected JSON list, got {type(parsed).__name__}")
    return parsed


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


def ordered_unique(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value and value not in seen:
            seen.add(value)
            result.append(value)
    return result


def cost_estimate(strategy: dict[str, Any]) -> float | None:
    if isinstance(strategy.get("cost_estimate"), dict):
        value = strategy["cost_estimate"].get("estimated_usd")
        if value is not None:
            return float(value)
    if strategy.get("estimated_usd") is not None:
        return float(strategy["estimated_usd"])
    return None


def quality_gate_decision(quality_gate: dict[str, Any]) -> str | None:
    decision = quality_gate.get("decision")
    if isinstance(decision, str) and decision:
        return decision
    candidate_gate = quality_gate.get("candidate_objective_gate")
    if isinstance(candidate_gate, dict):
        nested_decision = candidate_gate.get("decision")
        if isinstance(nested_decision, str) and nested_decision:
            return nested_decision
    return None


def env_labels(strategy: dict[str, Any], key: str) -> list[str]:
    labels: list[str] = []
    stages = strategy.get("stages")
    if isinstance(stages, list):
        for stage in stages:
            if not isinstance(stage, dict):
                continue
            env = stage.get("environment")
            if isinstance(env, dict):
                labels.extend(split_label_list(env.get(key)))
    return ordered_unique(labels)


def targeted_blockers(strategy: dict[str, Any]) -> list[str]:
    labels = list_strings(strategy.get("targeted_quality_blockers"))
    labels.extend(list_strings(strategy.get("targeted_quality_block_reasons")))
    labels.extend(env_labels(strategy, "TARGETED_QUALITY_BLOCKERS"))
    labels.extend(env_labels(strategy, "TARGETED_QUALITY_BLOCK_REASONS"))
    return ordered_unique(labels)


def context_tile_ids(strategy: dict[str, Any]) -> list[str]:
    labels = list_strings(strategy.get("context_support_tile_ids"))
    labels.extend(list_strings(strategy.get("boundary_context_tile_ids")))
    labels.extend(list_strings(strategy.get("horizon_context_tile_ids")))
    labels.extend(list_strings(strategy.get("reuse_context_tile_ids")))
    labels.extend(env_labels(strategy, "BOUNDARY_CONTEXT_TILE_IDS"))
    labels.extend(env_labels(strategy, "HORIZON_CONTEXT_TILE_IDS"))
    labels.extend(env_labels(strategy, "CONTEXT_SUPPORT_TILE_IDS"))
    return ordered_unique(labels)


def post_leaf_gate_tile_ids(strategy: dict[str, Any]) -> list[str]:
    gates = strategy.get("post_leaf_preflight_gates")
    if not isinstance(gates, list):
        return []
    return ordered_unique(
        [str(gate.get("tile_id") or "") for gate in gates if isinstance(gate, dict) and gate.get("tile_id")]
    )


def stage_tile_ids(strategy: dict[str, Any]) -> list[str]:
    stages = strategy.get("stages")
    if not isinstance(stages, list):
        return []
    result: list[str] = []
    for stage in stages:
        if not isinstance(stage, dict):
            continue
        tile_id = str(stage.get("tile_id") or "")
        if not tile_id and isinstance(stage.get("environment"), dict):
            tile_id = str(stage["environment"].get("TILE_ID") or "")
        if tile_id:
            result.append(tile_id)
    return ordered_unique(result)


def leaf_gate_by_tile(leaf_gates: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for leaf_gate in leaf_gates:
        tile_id = str(leaf_gate.get("tile_id") or leaf_gate.get("expected_tile_id") or "")
        if tile_id:
            result[tile_id] = leaf_gate
    return result


def passing_leaf_tile_ids(leaf_gates: list[dict[str, Any]]) -> list[str]:
    return sorted(
        tile_id
        for tile_id, leaf_gate in leaf_gate_by_tile(leaf_gates).items()
        if leaf_gate.get("decision") == "merge_review_allowed"
    )


def merge_review_blocks_only_missing_leaf_summaries(
    merge_review_gate: dict[str, Any],
    missing_tile_ids: list[str],
) -> bool:
    if merge_review_gate.get("decision") != "merge_review_blocked":
        return False
    expected = {f"leaf_gate_summary_missing:{tile_id}" for tile_id in missing_tile_ids}
    actual = set(list_strings(merge_review_gate.get("block_reasons")))
    return actual == expected


def evaluate_gate(
    *,
    strategy: dict[str, Any],
    quality_gate: dict[str, Any],
    merge_review_gate: dict[str, Any],
    required_tile_ids: list[str],
    required_context_tile_ids: list[str],
    required_targeted_blockers: list[str],
    exact_head: str,
    git_head: str,
    workflow_conclusion: str,
    training_jobs_in_progress: list[Any],
    processing_jobs_in_progress: list[Any],
    max_estimated_usd: float,
    v18_review_manifest_s3_uri: str = "",
    prior_leaf_gates: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    block_reasons: list[str] = []
    selected_tiles = ordered_unique(list_strings(strategy.get("selected_tile_ids")))
    stage_tiles = stage_tile_ids(strategy)
    prior_leaf_gates = prior_leaf_gates or []
    passing_prior_tiles = passing_leaf_tile_ids(prior_leaf_gates)
    covered_required_tiles = ordered_unique(selected_tiles + passing_prior_tiles)
    missing_leaf_summary_tiles = [tile_id for tile_id in required_tile_ids if tile_id not in passing_prior_tiles]
    cost = cost_estimate(strategy)

    if git_head != exact_head:
        block_reasons.append("git_head_not_exact_head")
    if workflow_conclusion != "success":
        block_reasons.append("exact_head_workflow_not_green")
    if training_jobs_in_progress:
        block_reasons.append("training_jobs_in_progress")
    if processing_jobs_in_progress:
        block_reasons.append("processing_jobs_in_progress")
    if strategy.get("submitted_jobs") not in ([], None):
        block_reasons.append("strategy_not_dry_run")
    strategy_v18_review_manifest = str(strategy.get("v18_review_manifest_s3_uri") or "").strip()
    expected_v18_review_manifest = (v18_review_manifest_s3_uri or strategy_v18_review_manifest).strip()
    if not expected_v18_review_manifest:
        block_reasons.append("v18_review_manifest_missing")
    elif strategy_v18_review_manifest != expected_v18_review_manifest:
        block_reasons.append("strategy_v18_review_manifest_mismatch")
    if len(selected_tiles) >= 14:
        block_reasons.append("full_14tile_scope_not_allowed")
    if not selected_tiles:
        block_reasons.append("selected_tiles_missing")
    for tile_id in required_tile_ids:
        if tile_id not in covered_required_tiles:
            block_reasons.append(f"required_tile_not_selected_or_prior_passing:{tile_id}")
    if set(stage_tiles) != set(selected_tiles):
        block_reasons.append("stage_tiles_do_not_match_selected_leaf_scope")
    if cost is None:
        block_reasons.append("estimated_usd_missing")
    elif cost > max_estimated_usd:
        block_reasons.append("estimated_usd_above_cap")

    quality_decision = quality_gate_decision(quality_gate)
    if quality_decision != "paid_retry_allowed":
        block_reasons.append("quality_strategy_gate_not_allowed")
    if not merge_review_blocks_only_missing_leaf_summaries(merge_review_gate, missing_leaf_summary_tiles):
        block_reasons.append("merge_review_gate_not_blocked_only_on_leaf_summaries")

    emitted_leaf_gates = post_leaf_gate_tile_ids(strategy)
    target_labels = targeted_blockers(strategy)
    context_tiles = context_tile_ids(strategy)
    for tile_id in selected_tiles:
        if tile_id not in emitted_leaf_gates:
            block_reasons.append(f"post_leaf_gate_missing:{tile_id}")
    for tile_id in required_context_tile_ids:
        if tile_id not in context_tiles:
            block_reasons.append(f"context_support_tile_missing:{tile_id}")
    for blocker in required_targeted_blockers:
        if blocker not in target_labels:
            block_reasons.append(f"targeted_blocker_missing:{blocker}")

    return {
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "decision": "leaf_submit_allowed" if not block_reasons else "leaf_submit_blocked",
        "block_reasons": block_reasons,
        "exact_head": exact_head,
        "git_head": git_head,
        "workflow_conclusion": workflow_conclusion,
        "v18_review_manifest_s3_uri": strategy_v18_review_manifest,
        "expected_v18_review_manifest_s3_uri": expected_v18_review_manifest or None,
        "training_jobs_in_progress": training_jobs_in_progress,
        "processing_jobs_in_progress": processing_jobs_in_progress,
        "required_tile_ids": required_tile_ids,
        "selected_tile_ids": selected_tiles,
        "stage_tile_ids": stage_tiles,
        "prior_leaf_gate_tile_ids": sorted(leaf_gate_by_tile(prior_leaf_gates)),
        "passing_prior_leaf_tile_ids": passing_prior_tiles,
        "covered_required_tile_ids": covered_required_tiles,
        "merge_review_missing_leaf_summary_tile_ids": missing_leaf_summary_tiles,
        "required_context_tile_ids": required_context_tile_ids,
        "context_support_tile_ids": context_tiles,
        "required_targeted_blockers": required_targeted_blockers,
        "targeted_quality_blockers": target_labels,
        "post_leaf_preflight_gate_tile_ids": emitted_leaf_gates,
        "quality_strategy_decision": quality_decision,
        "merge_review_gate_decision": merge_review_gate.get("decision"),
        "estimated_usd": cost,
        "max_estimated_usd": max_estimated_usd,
        "submitted_jobs": strategy.get("submitted_jobs"),
        "next_required_action": (
            "submit leaf-only fanout with --skip-merge/--skip-review and run emitted post_leaf_preflight_gates"
            if not block_reasons
            else "fix every readiness blocker before submitting paid leaf proof"
        ),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--strategy-json", required=True)
    parser.add_argument("--quality-gate-json", required=True)
    parser.add_argument("--merge-review-gate-json", required=True)
    parser.add_argument("--required-tile-id", action="append", default=[])
    parser.add_argument("--context-tile-id", action="append", default=[])
    parser.add_argument("--targeted-quality-blocker", action="append", default=[])
    parser.add_argument("--exact-head", required=True)
    parser.add_argument("--git-head", required=True)
    parser.add_argument("--workflow-conclusion", required=True)
    parser.add_argument("--v18-review-manifest-s3-uri", default="")
    parser.add_argument("--prior-leaf-gate-json", action="append", default=[])
    parser.add_argument("--training-jobs-json", default="[]")
    parser.add_argument("--processing-jobs-json", default="[]")
    parser.add_argument("--max-estimated-usd", type=float, required=True)
    parser.add_argument("--summary-json-output", required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    summary = evaluate_gate(
        strategy=load_json(args.strategy_json),
        quality_gate=load_json(args.quality_gate_json),
        merge_review_gate=load_json(args.merge_review_gate_json),
        required_tile_ids=args.required_tile_id,
        required_context_tile_ids=args.context_tile_id,
        required_targeted_blockers=args.targeted_quality_blocker,
        exact_head=args.exact_head,
        git_head=args.git_head,
        workflow_conclusion=args.workflow_conclusion,
        v18_review_manifest_s3_uri=args.v18_review_manifest_s3_uri,
        prior_leaf_gates=[load_json(path) for path in args.prior_leaf_gate_json],
        training_jobs_in_progress=parse_json_list(args.training_jobs_json),
        processing_jobs_in_progress=parse_json_list(args.processing_jobs_json),
        max_estimated_usd=args.max_estimated_usd,
    )
    output_path = Path(args.summary_json_output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))
    return 0 if summary["decision"] == "leaf_submit_allowed" else 2


if __name__ == "__main__":
    raise SystemExit(main())
