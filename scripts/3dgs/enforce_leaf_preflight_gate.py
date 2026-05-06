#!/usr/bin/env python3
"""Validate a leaf-artifact preflight summary before allowing merge/review spend."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def load_json(path: str) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def scaffold_is_filtered(scaffold: Any) -> bool:
    if not isinstance(scaffold, dict):
        return False
    mode = str(scaffold.get("scaffold_inheritance_mode") or "")
    filtered_path = str(scaffold.get("filtered_point_cloud") or "")
    inherited_count = int(scaffold.get("inherited_gaussian_count") or 0)
    fallback_used = bool(scaffold.get("fallback_used"))
    return bool(filtered_path) and "filtered" in mode and inherited_count > 0 and not fallback_used


def hard_max_splat_count(gate: dict[str, Any]) -> int:
    direct = gate.get("hard_max_splat_count")
    if direct is not None:
        return int(direct)
    nested = gate.get("required_leaf_preflight_gate") or {}
    if isinstance(nested, dict) and nested.get("hard_max_splat_count") is not None:
        return int(nested["hard_max_splat_count"])
    return 0


def expected_pass_decision(gate: dict[str, Any]) -> str:
    nested = gate.get("required_leaf_preflight_gate") or {}
    if isinstance(nested, dict) and nested.get("pass_decision"):
        return str(nested["pass_decision"])
    return "leaf_preflight_passed_cache_candidate"


def resolve_tile_gate(gate: dict[str, Any], tile_id: str) -> dict[str, Any]:
    gates = gate.get("post_leaf_preflight_gates")
    if not isinstance(gates, list) or not gates:
        return gate
    if tile_id:
        for candidate in gates:
            if isinstance(candidate, dict) and str(candidate.get("tile_id") or "") == tile_id:
                return candidate
    if len(gates) == 1 and isinstance(gates[0], dict):
        return gates[0]
    return gate


def evaluate_gate(
    *,
    preflight: dict[str, Any],
    gate: dict[str, Any],
    expected_tile_id: str = "",
    expected_selected_image_count: int = 0,
    require_filtered_scaffold: bool = False,
) -> dict[str, Any]:
    block_reasons: list[str] = []
    warnings: list[str] = []

    gate = resolve_tile_gate(gate, expected_tile_id)
    expected_decision = expected_pass_decision(gate)
    actual_decision = str(preflight.get("decision") or "")
    if actual_decision != expected_decision:
        block_reasons.append("leaf_preflight_decision_not_pass")

    missing_paths = (preflight.get("required_paths") or {}).get("missing") or []
    if missing_paths:
        block_reasons.append("leaf_required_paths_missing")

    if (preflight.get("training_metadata") or {}).get("training_completed") is not True:
        block_reasons.append("training_metadata_not_completed")

    actual_tile_id = str(preflight.get("tile_id") or (preflight.get("training_selection") or {}).get("tile_id") or "")
    if expected_tile_id and actual_tile_id != expected_tile_id:
        block_reasons.append("tile_id_mismatch")

    selection = preflight.get("training_selection") or {}
    selected_count = int(selection.get("selected_image_count") or 0)
    if expected_selected_image_count > 0 and selected_count != expected_selected_image_count:
        block_reasons.append("selected_image_count_mismatch")

    reference_guard = preflight.get("splat_reference_guard") or {}
    if reference_guard.get("enabled") is True and reference_guard.get("status") != "ok":
        block_reasons.append(str(reference_guard.get("block_reason") or "splat_reference_guard_not_ok"))

    splat_count = preflight.get("splat_vertex_count")
    if splat_count is None:
        block_reasons.append("splat_vertex_count_missing")
    else:
        splat_count = int(splat_count)
        max_splats = hard_max_splat_count(gate)
        if max_splats > 0 and splat_count > max_splats:
            block_reasons.append("splat_vertex_count_above_hard_max")

    scaffold = selection.get("scaffold_initialization")
    if require_filtered_scaffold and not scaffold_is_filtered(scaffold):
        block_reasons.append("filtered_scaffold_initialization_missing")
    elif scaffold and not scaffold_is_filtered(scaffold):
        warnings.append("scaffold_initialization_present_but_not_filtered")

    return {
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "preflight_artifact_uri": preflight.get("artifact_uri"),
        "preflight_job_name": preflight.get("job_name"),
        "tile_id": actual_tile_id,
        "expected_tile_id": expected_tile_id or None,
        "decision": "merge_review_allowed" if not block_reasons else "merge_review_blocked",
        "block_reasons": block_reasons,
        "warnings": warnings,
        "leaf_preflight_decision": actual_decision,
        "expected_leaf_preflight_decision": expected_decision,
        "splat_vertex_count": splat_count,
        "hard_max_splat_count": hard_max_splat_count(gate) or None,
        "splat_reference_guard": reference_guard,
        "selected_image_count": selected_count,
        "expected_selected_image_count": expected_selected_image_count or None,
        "filtered_scaffold_required": require_filtered_scaffold,
        "filtered_scaffold_ok": scaffold_is_filtered(scaffold),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--preflight-json", required=True)
    parser.add_argument("--gate-json", required=True)
    parser.add_argument("--expected-tile-id", default="")
    parser.add_argument("--expected-selected-image-count", type=int, default=0)
    parser.add_argument("--require-filtered-scaffold", action="store_true")
    parser.add_argument("--summary-json-output", required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    summary = evaluate_gate(
        preflight=load_json(args.preflight_json),
        gate=load_json(args.gate_json),
        expected_tile_id=args.expected_tile_id,
        expected_selected_image_count=args.expected_selected_image_count,
        require_filtered_scaffold=args.require_filtered_scaffold,
    )
    output_path = Path(args.summary_json_output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))
    return 0 if summary["decision"] == "merge_review_allowed" else 2


if __name__ == "__main__":
    raise SystemExit(main())
