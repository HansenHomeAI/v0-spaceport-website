#!/usr/bin/env python3
"""Block MD1 merge/review spend until all required leaf gates pass."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def load_json(path: str) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


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


def targeted_quality_blockers(strategy: dict[str, Any]) -> list[str]:
    labels = list_strings(strategy.get("targeted_quality_blockers"))
    labels.extend(list_strings(strategy.get("targeted_quality_block_reasons")))
    labels.extend(env_labels(strategy, "TARGETED_QUALITY_BLOCKERS"))
    labels.extend(env_labels(strategy, "TARGETED_QUALITY_BLOCK_REASONS"))
    return ordered_unique(labels)


def context_tile_ids(strategy: dict[str, Any]) -> list[str]:
    labels = list_strings(strategy.get("context_support_tile_ids"))
    labels.extend(list_strings(strategy.get("boundary_context_tile_ids")))
    labels.extend(list_strings(strategy.get("horizon_context_tile_ids")))
    labels.extend(list_strings(strategy.get("context_tile_ids")))
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


def leaf_gate_by_tile(leaf_gates: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for leaf_gate in leaf_gates:
        tile_id = str(leaf_gate.get("tile_id") or leaf_gate.get("expected_tile_id") or "")
        if tile_id:
            result[tile_id] = leaf_gate
    return result


def evaluate_gate(
    *,
    strategy: dict[str, Any],
    required_tile_ids: list[str],
    required_context_tile_ids: list[str],
    required_targeted_blockers: list[str],
    leaf_gates: list[dict[str, Any]],
) -> dict[str, Any]:
    block_reasons: list[str] = []
    selected_tiles = ordered_unique(list_strings(strategy.get("selected_tile_ids")))
    emitted_leaf_gate_tiles = post_leaf_gate_tile_ids(strategy)
    targeted_blockers = targeted_quality_blockers(strategy)
    context_tiles = context_tile_ids(strategy)
    leaf_by_tile = leaf_gate_by_tile(leaf_gates)
    passing_leaf_tiles = sorted(
        tile_id for tile_id, leaf_gate in leaf_by_tile.items() if leaf_gate.get("decision") == "merge_review_allowed"
    )

    submitted_jobs = strategy.get("submitted_jobs")
    if submitted_jobs not in ([], None):
        block_reasons.append("strategy_has_submitted_jobs")

    for blocker in required_targeted_blockers:
        if blocker not in targeted_blockers:
            block_reasons.append(f"targeted_blocker_missing:{blocker}")

    for tile_id in required_tile_ids:
        leaf_gate = leaf_by_tile.get(tile_id)
        has_passing_prior_leaf = bool(leaf_gate and leaf_gate.get("decision") == "merge_review_allowed")
        if tile_id not in selected_tiles and not has_passing_prior_leaf:
            block_reasons.append(f"required_tile_not_selected:{tile_id}")
        if tile_id in selected_tiles and tile_id not in emitted_leaf_gate_tiles:
            block_reasons.append(f"post_leaf_gate_missing:{tile_id}")
        if not leaf_gate:
            block_reasons.append(f"leaf_gate_summary_missing:{tile_id}")
            continue
        if leaf_gate.get("decision") != "merge_review_allowed":
            block_reasons.append(f"leaf_gate_not_allowed:{tile_id}")
        expected_tile_id = str(leaf_gate.get("expected_tile_id") or tile_id)
        actual_tile_id = str(leaf_gate.get("tile_id") or "")
        if actual_tile_id and actual_tile_id != expected_tile_id:
            block_reasons.append(f"leaf_gate_tile_mismatch:{tile_id}")

    for tile_id in required_context_tile_ids:
        if tile_id not in context_tiles:
            block_reasons.append(f"context_support_tile_missing:{tile_id}")

    return {
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "decision": "merge_review_allowed" if not block_reasons else "merge_review_blocked",
        "block_reasons": block_reasons,
        "required_tile_ids": required_tile_ids,
        "selected_tile_ids": selected_tiles,
        "required_context_tile_ids": required_context_tile_ids,
        "context_support_tile_ids": context_tiles,
        "required_targeted_blockers": required_targeted_blockers,
        "targeted_quality_blockers": targeted_blockers,
        "post_leaf_preflight_gate_tile_ids": emitted_leaf_gate_tiles,
        "leaf_gate_summary_tile_ids": sorted(leaf_by_tile),
        "passing_prior_or_current_leaf_tile_ids": passing_leaf_tiles,
        "submitted_jobs": submitted_jobs,
        "next_required_action": (
            "merge/review may proceed"
            if not block_reasons
            else "run each required leaf proof, run its emitted preflight/enforce gate, and provide passing leaf gate summaries before merge/review spend"
        ),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--strategy-json", required=True)
    parser.add_argument("--required-tile-id", action="append", default=[])
    parser.add_argument("--context-tile-id", action="append", default=[])
    parser.add_argument("--targeted-quality-blocker", action="append", default=[])
    parser.add_argument("--leaf-gate-json", action="append", default=[])
    parser.add_argument("--summary-json-output", required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    summary = evaluate_gate(
        strategy=load_json(args.strategy_json),
        required_tile_ids=args.required_tile_id,
        required_context_tile_ids=args.context_tile_id,
        required_targeted_blockers=args.targeted_quality_blocker,
        leaf_gates=[load_json(path) for path in args.leaf_gate_json],
    )
    output_path = Path(args.summary_json_output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))
    return 0 if summary["decision"] == "merge_review_allowed" else 2


if __name__ == "__main__":
    raise SystemExit(main())
