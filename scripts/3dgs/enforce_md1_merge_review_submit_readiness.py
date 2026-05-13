#!/usr/bin/env python3
"""Gate MD1 no-training merge/review spend against exact-head, cost, and QA plans."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def load_json(path: str) -> dict[str, Any]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"expected JSON object in {path}")
    return payload


def parse_json_list(value: str) -> list[Any]:
    parsed = json.loads(value)
    if not isinstance(parsed, list):
        raise ValueError(f"expected JSON list, got {type(parsed).__name__}")
    return parsed


def list_strings(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value if str(item)]


def ordered_unique(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value and value not in seen:
            seen.add(value)
            result.append(value)
    return result


def nested_dict(payload: dict[str, Any], key: str) -> dict[str, Any]:
    value = payload.get(key)
    return value if isinstance(value, dict) else {}


def numeric_value(payload: dict[str, Any], key: str) -> float | None:
    value = payload.get(key)
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def processing_runtime_seconds(payload: dict[str, Any]) -> int | None:
    stopping = nested_dict(payload, "StoppingCondition")
    value = stopping.get("MaxRuntimeInSeconds")
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def payload_input_names(payload: dict[str, Any]) -> list[str]:
    inputs = payload.get("ProcessingInputs")
    if not isinstance(inputs, list):
        return []
    return ordered_unique(
        [str(item.get("InputName") or "") for item in inputs if isinstance(item, dict) and item.get("InputName")]
    )


def merge_plan_tile_ids(merge_plan: dict[str, Any]) -> list[str]:
    tile_ids = list_strings(merge_plan.get("selected_tile_ids"))
    if tile_ids:
        return ordered_unique(tile_ids)
    tiles = merge_plan.get("tiles")
    if not isinstance(tiles, list):
        return []
    return ordered_unique([str(tile.get("tile_id") or "") for tile in tiles if isinstance(tile, dict)])


def summary_selected_tile_ids(summary: dict[str, Any]) -> list[str]:
    tile_ids = list_strings(summary.get("selected_tile_ids"))
    if tile_ids:
        return ordered_unique(tile_ids)
    stages = summary.get("stages")
    if not isinstance(stages, list):
        return []
    return ordered_unique([str(stage.get("tile_id") or "") for stage in stages if isinstance(stage, dict)])


def has_required_visual_qa_plan(plan: dict[str, Any]) -> bool:
    visual = nested_dict(plan, "visual_qa_plan")
    return all(
        [
            visual.get("required") is True,
            visual.get("extract_only_visual_assets") is True,
            visual.get("evaluate_gate_required") is True,
            visual.get("ai_assisted_review_manifest_required") is True,
        ]
    )


def has_required_viewer_smoke_plan(plan: dict[str, Any]) -> bool:
    viewer = nested_dict(plan, "viewer_smoke_plan")
    checks = set(list_strings(viewer.get("checks")))
    return all(
        [
            viewer.get("required") is True,
            viewer.get("post_review_or_compressed_artifact_required") is True,
            viewer.get("no_local_model_weight_bloat") is True,
            {"nonblank_canvas", "camera_navigation", "serious_console_errors"}.issubset(checks),
        ]
    )


def has_required_v18_review_plan(plan: dict[str, Any], max_review_estimated_usd: float, max_review_runtime_seconds: int) -> bool:
    review = nested_dict(plan, "review_plan")
    estimated = numeric_value(review, "max_estimated_usd")
    runtime = numeric_value(review, "max_runtime_seconds")
    return all(
        [
            review.get("required") is True,
            review.get("v18_non_regression_required") is True,
            str(review.get("v18_review_manifest_s3_uri") or "").startswith("s3://"),
            str(review.get("candidate_model_artifact_s3_uri") or "").startswith("s3://"),
            estimated is not None and estimated <= max_review_estimated_usd,
            runtime is not None and runtime <= max_review_runtime_seconds,
        ]
    )


def evaluate_gate(
    *,
    leaf_reuse_summary: dict[str, Any],
    merge_plan: dict[str, Any],
    payload: dict[str, Any],
    merge_review_gate: dict[str, Any],
    readiness_plan: dict[str, Any],
    required_tile_ids: list[str],
    exact_head: str,
    git_head: str,
    workflow_conclusion: str,
    training_jobs_in_progress: list[Any],
    processing_jobs_in_progress: list[Any],
    max_merge_estimated_usd: float,
    max_merge_runtime_seconds: int,
    max_review_estimated_usd: float,
    max_review_runtime_seconds: int,
) -> dict[str, Any]:
    block_reasons: list[str] = []
    required_tiles = ordered_unique(required_tile_ids)
    summary_tiles = summary_selected_tile_ids(leaf_reuse_summary)
    plan_tiles = merge_plan_tile_ids(merge_plan)
    runtime = processing_runtime_seconds(payload)
    merge = nested_dict(readiness_plan, "merge_plan")
    merge_estimated = numeric_value(merge, "max_estimated_usd")
    merge_runtime = numeric_value(merge, "max_runtime_seconds")

    if git_head != exact_head:
        block_reasons.append("git_head_not_exact_head")
    if workflow_conclusion != "success":
        block_reasons.append("exact_head_workflow_not_green")
    if training_jobs_in_progress:
        block_reasons.append("training_jobs_in_progress")
    if processing_jobs_in_progress:
        block_reasons.append("processing_jobs_in_progress")
    if leaf_reuse_summary.get("submitted_jobs") not in ([], None):
        block_reasons.append("leaf_reuse_summary_has_submitted_jobs")
    if int(leaf_reuse_summary.get("training_jobs_to_submit") or 0) != 0:
        block_reasons.append("leaf_reuse_summary_has_training_jobs_to_submit")
    if len(summary_tiles) >= 14:
        block_reasons.append("full_14tile_scope_not_allowed")
    if merge_review_gate.get("decision") != "merge_review_allowed":
        block_reasons.append("merge_review_gate_not_allowed")
    for tile_id in required_tiles:
        if tile_id not in summary_tiles:
            block_reasons.append(f"required_tile_missing_from_leaf_reuse_summary:{tile_id}")
        if tile_id not in plan_tiles:
            block_reasons.append(f"required_tile_missing_from_merge_plan:{tile_id}")
    if set(summary_tiles) != set(plan_tiles):
        block_reasons.append("merge_plan_tiles_do_not_match_leaf_reuse_summary")
    if "merge-plan" not in payload_input_names(payload):
        block_reasons.append("payload_missing_merge_plan_input")
    if "tile-selection" not in payload_input_names(payload):
        block_reasons.append("payload_missing_tile_selection_input")
    if runtime is None:
        block_reasons.append("payload_runtime_missing")
    elif runtime > max_merge_runtime_seconds:
        block_reasons.append("payload_runtime_above_cap")
    if merge.get("required") is not True:
        block_reasons.append("merge_plan_required_flag_missing")
    if merge.get("no_training") is not True:
        block_reasons.append("merge_plan_not_marked_no_training")
    if merge_estimated is None:
        block_reasons.append("merge_estimated_usd_missing")
    elif merge_estimated > max_merge_estimated_usd:
        block_reasons.append("merge_estimated_usd_above_cap")
    if merge_runtime is None:
        block_reasons.append("merge_runtime_missing")
    elif merge_runtime > max_merge_runtime_seconds:
        block_reasons.append("merge_runtime_above_cap")
    if not has_required_v18_review_plan(readiness_plan, max_review_estimated_usd, max_review_runtime_seconds):
        block_reasons.append("v18_review_plan_missing_or_over_cap")
    if not has_required_visual_qa_plan(readiness_plan):
        block_reasons.append("visual_qa_plan_missing")
    if not has_required_viewer_smoke_plan(readiness_plan):
        block_reasons.append("viewer_smoke_plan_missing")

    return {
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "decision": "merge_review_submit_allowed" if not block_reasons else "merge_review_submit_blocked",
        "block_reasons": block_reasons,
        "exact_head": exact_head,
        "git_head": git_head,
        "workflow_conclusion": workflow_conclusion,
        "training_jobs_in_progress": training_jobs_in_progress,
        "processing_jobs_in_progress": processing_jobs_in_progress,
        "required_tile_ids": required_tiles,
        "leaf_reuse_summary_tile_ids": summary_tiles,
        "merge_plan_tile_ids": plan_tiles,
        "merge_review_gate_decision": merge_review_gate.get("decision"),
        "payload_input_names": payload_input_names(payload),
        "payload_max_runtime_seconds": runtime,
        "max_merge_estimated_usd": max_merge_estimated_usd,
        "max_merge_runtime_seconds": max_merge_runtime_seconds,
        "max_review_estimated_usd": max_review_estimated_usd,
        "max_review_runtime_seconds": max_review_runtime_seconds,
        "next_required_action": (
            "submit at most one bounded no-training merge/preflight, then one bounded V18/visual QA review only if merge preflight passes"
            if not block_reasons
            else "fix every merge/review readiness blocker before any paid merge or review"
        ),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--leaf-reuse-summary-json", required=True)
    parser.add_argument("--merge-plan-json", required=True)
    parser.add_argument("--payload-json", required=True)
    parser.add_argument("--merge-review-gate-json", required=True)
    parser.add_argument("--readiness-plan-json", required=True)
    parser.add_argument("--required-tile-id", action="append", default=[])
    parser.add_argument("--exact-head", required=True)
    parser.add_argument("--git-head", required=True)
    parser.add_argument("--workflow-conclusion", required=True)
    parser.add_argument("--training-jobs-json", default="[]")
    parser.add_argument("--processing-jobs-json", default="[]")
    parser.add_argument("--max-merge-estimated-usd", type=float, required=True)
    parser.add_argument("--max-merge-runtime-seconds", type=int, required=True)
    parser.add_argument("--max-review-estimated-usd", type=float, required=True)
    parser.add_argument("--max-review-runtime-seconds", type=int, required=True)
    parser.add_argument("--summary-json-output", required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    summary = evaluate_gate(
        leaf_reuse_summary=load_json(args.leaf_reuse_summary_json),
        merge_plan=load_json(args.merge_plan_json),
        payload=load_json(args.payload_json),
        merge_review_gate=load_json(args.merge_review_gate_json),
        readiness_plan=load_json(args.readiness_plan_json),
        required_tile_ids=args.required_tile_id,
        exact_head=args.exact_head,
        git_head=args.git_head,
        workflow_conclusion=args.workflow_conclusion,
        training_jobs_in_progress=parse_json_list(args.training_jobs_json),
        processing_jobs_in_progress=parse_json_list(args.processing_jobs_json),
        max_merge_estimated_usd=args.max_merge_estimated_usd,
        max_merge_runtime_seconds=args.max_merge_runtime_seconds,
        max_review_estimated_usd=args.max_review_estimated_usd,
        max_review_runtime_seconds=args.max_review_runtime_seconds,
    )
    output_path = Path(args.summary_json_output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))
    return 0 if summary["decision"] == "merge_review_submit_allowed" else 2


if __name__ == "__main__":
    raise SystemExit(main())
