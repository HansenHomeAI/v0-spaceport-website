#!/usr/bin/env python3
"""Build a no-training MD1 merge summary from passed leaf preflight gates."""

from __future__ import annotations

import argparse
import copy
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PASSING_LEAF_PREFLIGHT_DECISIONS = {
    "leaf_preflight_passed",
    "leaf_preflight_passed_cache_candidate",
}


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def load_json(path: str | Path) -> dict[str, Any]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"expected JSON object in {path}")
    return payload


def as_list(value: object) -> list[Any]:
    return value if isinstance(value, list) else []


def ordered_unique(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        cleaned = str(value).strip()
        if cleaned and cleaned not in seen:
            seen.add(cleaned)
            result.append(cleaned)
    return result


def string_value(payload: dict[str, Any], *keys: str) -> str:
    for key in keys:
        value = payload.get(key)
        if value is not None and str(value).strip():
            return str(value).strip()
    return ""


def nested_dict(payload: dict[str, Any], key: str) -> dict[str, Any]:
    value = payload.get(key)
    return value if isinstance(value, dict) else {}


@dataclass(frozen=True)
class PassedLeaf:
    tile_id: str
    artifact_uri: str
    preflight_json: str
    gate_json: str
    splat_vertex_count: int | None
    selected_image_count: int | None
    reference_splat_count: int | None
    observed_reference_splat_ratio: float | None


def validate_passed_leaf(
    *,
    preflight: dict[str, Any],
    gate: dict[str, Any],
    preflight_json: str,
    gate_json: str,
) -> PassedLeaf:
    block_reasons: list[str] = []
    preflight_decision = string_value(preflight, "decision")
    gate_decision = string_value(gate, "decision")

    if preflight_decision not in PASSING_LEAF_PREFLIGHT_DECISIONS:
        block_reasons.append("leaf_preflight_not_passing")
    if as_list(preflight.get("block_reasons")):
        block_reasons.append("leaf_preflight_has_block_reasons")
    if gate_decision != "merge_review_allowed":
        block_reasons.append("leaf_gate_not_merge_review_allowed")
    if as_list(gate.get("block_reasons")):
        block_reasons.append("leaf_gate_has_block_reasons")

    preflight_tile_id = string_value(preflight, "tile_id", "expected_tile_id")
    gate_tile_id = string_value(gate, "expected_tile_id", "tile_id")
    if not preflight_tile_id:
        block_reasons.append("leaf_preflight_missing_tile_id")
    if not gate_tile_id:
        block_reasons.append("leaf_gate_missing_tile_id")
    if preflight_tile_id and gate_tile_id and preflight_tile_id != gate_tile_id:
        block_reasons.append("leaf_tile_id_mismatch")

    artifact_uri = string_value(preflight, "artifact_uri", "artifact_s3_uri")
    if not artifact_uri:
        block_reasons.append("leaf_preflight_missing_artifact_uri")

    if block_reasons:
        raise ValueError(
            f"leaf preflight/gate did not pass for {preflight_json} + {gate_json}: {', '.join(block_reasons)}"
        )

    training_selection = nested_dict(preflight, "training_selection")
    splat_reference_guard = nested_dict(gate, "splat_reference_guard")

    return PassedLeaf(
        tile_id=preflight_tile_id,
        artifact_uri=artifact_uri,
        preflight_json=preflight_json,
        gate_json=gate_json,
        splat_vertex_count=preflight.get("splat_vertex_count"),
        selected_image_count=(
            preflight.get("selected_image_count")
            or preflight.get("selected_image_count_actual")
            or gate.get("selected_image_count")
            or training_selection.get("selected_image_count")
        ),
        reference_splat_count=preflight.get("reference_splat_count")
        or splat_reference_guard.get("reference_splat_count"),
        observed_reference_splat_ratio=preflight.get("observed_reference_splat_ratio")
        or splat_reference_guard.get("observed_reference_ratio"),
    )


def build_leaf_reuse_summary(
    *,
    base_summary: dict[str, Any],
    base_summary_json: str,
    passed_leaves: list[PassedLeaf],
    candidate_label: str,
    experiment_id: str,
    targeted_quality_blockers: list[str] | None = None,
    context_tile_ids: list[str] | None = None,
) -> dict[str, Any]:
    summary = copy.deepcopy(base_summary)
    leaves_by_tile = {leaf.tile_id: leaf for leaf in passed_leaves}
    if len(leaves_by_tile) != len(passed_leaves):
        raise ValueError("duplicate leaf tile ids")

    stages = summary.get("stages")
    if not isinstance(stages, list):
        raise ValueError("base summary must contain stages[]")

    replaced: list[dict[str, Any]] = []
    for stage in stages:
        if not isinstance(stage, dict):
            continue
        tile_id = string_value(stage, "tile_id")
        leaf = leaves_by_tile.get(tile_id)
        if not leaf:
            continue
        previous_artifact_uri = string_value(stage, "source_artifact_uri", "model_artifact_s3_uri")
        stage["stage_name"] = f"T0_{tile_id}_validated_leaf_reuse"
        stage["stage_type"] = "train"
        stage["source_artifact_uri"] = leaf.artifact_uri
        stage["model_artifact_s3_uri"] = leaf.artifact_uri
        stage["cache_status"] = "validated_leaf_reuse"
        stage["quality_gate_status"] = "leaf_gate_passed_merge_review_allowed"
        stage["candidate_label"] = candidate_label
        stage["candidate_status"] = "leaf_preflight_passed"
        stage["selected_source"] = "validated_leaf_reuse"
        stage["source_leaf_preflight_json"] = leaf.preflight_json
        stage["source_leaf_gate_json"] = leaf.gate_json
        stage["splat_vertex_count"] = leaf.splat_vertex_count
        stage["selected_image_count"] = leaf.selected_image_count
        stage["reference_splat_count"] = leaf.reference_splat_count
        stage["observed_reference_splat_ratio"] = leaf.observed_reference_splat_ratio
        replaced.append(
            {
                "tile_id": tile_id,
                "previous_artifact_uri": previous_artifact_uri,
                "artifact_uri": leaf.artifact_uri,
                "leaf_preflight_json": leaf.preflight_json,
                "leaf_gate_json": leaf.gate_json,
                "splat_vertex_count": leaf.splat_vertex_count,
                "selected_image_count": leaf.selected_image_count,
            }
        )

    missing = sorted(set(leaves_by_tile) - {entry["tile_id"] for entry in replaced})
    if missing:
        raise ValueError(f"leaf tiles missing from base summary stages: {', '.join(missing)}")

    summary["candidate_label"] = candidate_label
    summary["experiment_id"] = experiment_id or f"{candidate_label}-leaf-reuse-merge"
    summary["submitted_jobs"] = []
    summary["completed_jobs"] = []
    summary["training_jobs_to_submit"] = 0
    summary["cost_estimate"] = {"estimated_usd": 0.0, "training_stage_count": 0}
    summary["no_full_14tile_training"] = True
    if targeted_quality_blockers:
        summary["targeted_quality_blockers"] = ordered_unique(targeted_quality_blockers)
    if context_tile_ids:
        summary["context_support_tile_ids"] = ordered_unique(context_tile_ids)
        summary["reuse_context_tile_ids"] = ordered_unique(context_tile_ids)

    existing_post_leaf_gates = [
        gate
        for gate in as_list(summary.get("post_leaf_preflight_gates"))
        if isinstance(gate, dict) and string_value(gate, "tile_id") not in leaves_by_tile
    ]
    summary["post_leaf_preflight_gates"] = existing_post_leaf_gates + [
        {
            "tile_id": leaf.tile_id,
            "artifact_uri": leaf.artifact_uri,
            "preflight_summary_json": leaf.preflight_json,
            "gate_summary_json": leaf.gate_json,
            "splat_vertex_count": leaf.splat_vertex_count,
            "selected_image_count": leaf.selected_image_count,
            "reference_splat_count": leaf.reference_splat_count,
            "observed_reference_splat_ratio": leaf.observed_reference_splat_ratio,
            "merge_review_allowed_only_if": "leaf_gate_json decision is merge_review_allowed",
        }
        for leaf in passed_leaves
    ]
    summary["source_leaf_reuse_base_summary_json"] = base_summary_json
    summary["source_leaf_preflight_jsons"] = [leaf.preflight_json for leaf in passed_leaves]
    summary["source_leaf_gate_jsons"] = [leaf.gate_json for leaf in passed_leaves]
    summary["leaf_reuse_merge"] = {
        "generated_at": utc_now(),
        "base_summary_json": base_summary_json,
        "candidate_label": candidate_label,
        "experiment_id": summary["experiment_id"],
        "replaced_tile_ids": [entry["tile_id"] for entry in replaced],
        "replaced_artifacts": replaced,
        "targeted_quality_blockers": ordered_unique(targeted_quality_blockers or []),
        "context_tile_ids": ordered_unique(context_tile_ids or []),
        "submitted_jobs": [],
        "training_jobs_to_submit": 0,
        "no_full_14tile_training": True,
        "decision": "remote_merge_plan_allowed_after_local_json_and_artifact_validation",
        "next_unblocked_step": "Generate local no-training remote merge plan/payload, then submit at most one bounded processing merge after review.",
    }
    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-summary-json", required=True)
    parser.add_argument("--leaf-preflight-json", action="append", required=True)
    parser.add_argument("--leaf-gate-json", action="append", required=True)
    parser.add_argument("--candidate-label", required=True)
    parser.add_argument("--experiment-id", default="")
    parser.add_argument("--targeted-quality-blocker", action="append", default=[])
    parser.add_argument("--context-tile-id", action="append", default=[])
    parser.add_argument("--output-json", required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if len(args.leaf_preflight_json) != len(args.leaf_gate_json):
        raise RuntimeError("--leaf-preflight-json and --leaf-gate-json counts must match")

    leaves = [
        validate_passed_leaf(
            preflight=load_json(preflight_json),
            gate=load_json(gate_json),
            preflight_json=preflight_json,
            gate_json=gate_json,
        )
        for preflight_json, gate_json in zip(args.leaf_preflight_json, args.leaf_gate_json)
    ]
    summary = build_leaf_reuse_summary(
        base_summary=load_json(args.base_summary_json),
        base_summary_json=args.base_summary_json,
        passed_leaves=leaves,
        candidate_label=args.candidate_label,
        experiment_id=args.experiment_id,
        targeted_quality_blockers=args.targeted_quality_blocker,
        context_tile_ids=args.context_tile_id,
    )
    output_path = Path(args.output_json)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "output_json": str(output_path),
                "candidate_label": summary["candidate_label"],
                "experiment_id": summary["experiment_id"],
                "replaced_tile_ids": summary["leaf_reuse_merge"]["replaced_tile_ids"],
                "training_jobs_to_submit": summary["training_jobs_to_submit"],
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
