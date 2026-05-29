#!/usr/bin/env python3
"""Enforce that a leaf artifact preflight is safe to reuse before merge/review spend."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Mapping


PASS_DECISION = "leaf_preflight_passed_cache_candidate"


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def nested(payload: Mapping[str, Any], *keys: str) -> Any:
    value: Any = payload
    for key in keys:
        if not isinstance(value, Mapping):
            return None
        value = value.get(key)
    return value


def build_report(args: argparse.Namespace) -> dict[str, Any]:
    preflight_path = Path(args.preflight_json)
    preflight = load_json(preflight_path)
    gate_json_path = str(args.gate_json or "").strip()
    gate_json_exists = bool(gate_json_path) and gate_json_path != "<benchmark-summary-json>" and Path(gate_json_path).exists()

    block_reasons: list[str] = []
    warnings: list[str] = []

    decision = str(preflight.get("decision") or "")
    if decision != PASS_DECISION:
        block_reasons.append("leaf_preflight_decision_not_passed")

    preflight_blocks = preflight.get("block_reasons") or []
    if preflight_blocks:
        block_reasons.append("leaf_preflight_has_block_reasons")

    expected_tile_id = str(args.expected_tile_id or "").strip()
    observed_tile_id = str(preflight.get("tile_id") or nested(preflight, "training_selection", "tile_id") or "")
    if expected_tile_id and observed_tile_id != expected_tile_id:
        block_reasons.append("leaf_tile_id_mismatch")

    required_missing = nested(preflight, "required_paths", "missing")
    if required_missing:
        block_reasons.append("leaf_required_paths_missing")

    if nested(preflight, "training_metadata", "training_completed") is not True:
        block_reasons.append("leaf_training_metadata_not_completed")

    splat_vertex_count = preflight.get("splat_vertex_count")
    if not isinstance(splat_vertex_count, int) or splat_vertex_count <= 0:
        block_reasons.append("leaf_splat_vertex_count_invalid")

    reference_status = str(nested(preflight, "splat_reference_guard", "status") or "not_configured")
    if reference_status not in {"ok", "not_configured"}:
        block_reasons.append("leaf_splat_reference_guard_blocked")

    expected_selected = int(args.expected_selected_image_count or 0)
    observed_selected = nested(preflight, "training_selection", "selected_image_count")
    if expected_selected > 0 and observed_selected != expected_selected:
        block_reasons.append("leaf_selected_image_count_mismatch")

    scaffold = nested(preflight, "training_selection", "scaffold_initialization") or {}
    if args.require_filtered_scaffold:
        if not isinstance(scaffold, Mapping):
            block_reasons.append("leaf_scaffold_initialization_missing")
        else:
            if scaffold.get("fallback_used") is True:
                block_reasons.append("leaf_scaffold_fallback_used")
            if scaffold.get("scaffold_filter_selective") is not True:
                block_reasons.append("leaf_scaffold_filter_not_selective")
            filtered_count = scaffold.get("source_filtered_gaussian_count")
            inherited_count = scaffold.get("inherited_gaussian_count")
            if not isinstance(filtered_count, int) or filtered_count <= 0:
                block_reasons.append("leaf_filtered_scaffold_count_invalid")
            if not isinstance(inherited_count, int) or inherited_count <= 0:
                block_reasons.append("leaf_inherited_scaffold_count_invalid")

    if gate_json_path and gate_json_path != "<benchmark-summary-json>" and not gate_json_exists:
        warnings.append("gate_json_path_not_found")

    return {
        "status": "passed" if not block_reasons else "blocked",
        "pass_decision": PASS_DECISION,
        "preflight_json": str(preflight_path),
        "gate_json": gate_json_path or None,
        "gate_json_exists": gate_json_exists,
        "expected_tile_id": expected_tile_id or None,
        "observed_tile_id": observed_tile_id or None,
        "expected_selected_image_count": expected_selected or None,
        "observed_selected_image_count": observed_selected,
        "require_filtered_scaffold": bool(args.require_filtered_scaffold),
        "splat_vertex_count": splat_vertex_count,
        "splat_reference_guard": preflight.get("splat_reference_guard"),
        "scaffold_initialization": scaffold if isinstance(scaffold, Mapping) else None,
        "preflight_block_reasons": preflight_blocks,
        "block_reasons": block_reasons,
        "warnings": warnings,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--preflight-json", required=True)
    parser.add_argument("--gate-json", default="")
    parser.add_argument("--expected-tile-id", required=True)
    parser.add_argument("--expected-selected-image-count", type=int, default=0)
    parser.add_argument("--require-filtered-scaffold", action="store_true")
    parser.add_argument("--summary-json-output", required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    report = build_report(args)
    output_path = Path(args.summary_json_output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0 if report["status"] == "passed" else 2


if __name__ == "__main__":
    raise SystemExit(main())
