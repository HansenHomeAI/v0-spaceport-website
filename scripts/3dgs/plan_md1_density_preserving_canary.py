#!/usr/bin/env python3
"""Build a no-spend MD1 full-scene density-preserving canary plan."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PASSING_STATUSES = {"passed", "pass", "promoted", "accepted", "ok"}


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def load_json(path: str | Path) -> dict[str, Any]:
    with Path(path).open(encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict):
        raise ValueError(f"expected JSON object in {path}")
    return payload


def status_is_passing(value: object) -> bool:
    return str(value or "").strip().lower() in PASSING_STATUSES


def normalize_context_density_manifest(payload: dict[str, Any]) -> dict[str, dict[str, Any]]:
    entries = payload.get("context_density_tiles") or payload.get("context_density_entries") or payload.get("tiles") or payload
    if isinstance(entries, dict):
        values = entries.values()
    elif isinstance(entries, list):
        values = entries
    else:
        raise ValueError("context density manifest must contain a dict or list of tile entries")

    by_tile: dict[str, dict[str, Any]] = {}
    for raw in values:
        if not isinstance(raw, dict):
            continue
        tile_id = str(raw.get("tile_id") or "").strip()
        if tile_id:
            by_tile[tile_id] = dict(raw)
    return by_tile


def normalize_reference_tiles(reference_merge_report: dict[str, Any]) -> dict[str, dict[str, Any]]:
    tiles = reference_merge_report.get("tiles")
    if not isinstance(tiles, list):
        raise ValueError("reference merge report must contain tiles[]")
    by_tile: dict[str, dict[str, Any]] = {}
    for raw in tiles:
        if not isinstance(raw, dict):
            continue
        tile_id = str(raw.get("tile_id") or "").strip()
        if tile_id:
            by_tile[tile_id] = dict(raw)
    return by_tile


def candidate_merge_report(payload: dict[str, Any]) -> dict[str, Any]:
    if isinstance(payload.get("merge_report"), dict):
        return payload["merge_report"]
    if isinstance(payload.get("merge"), dict) and isinstance(payload["merge"].get("tiles"), list):
        return payload["merge"]
    if isinstance(payload.get("merge_report"), str):
        return load_json(payload["merge_report"])
    if isinstance(payload.get("tiles"), list):
        return payload
    raise ValueError("candidate summary must contain merge_report or merge tiles")


def normalize_candidate_plan(payload: dict[str, Any]) -> dict[str, dict[str, Any]]:
    merge_plan = payload.get("merge_plan") if isinstance(payload.get("merge_plan"), dict) else {}
    plan_tiles = merge_plan.get("tiles") if isinstance(merge_plan, dict) else []
    by_tile: dict[str, dict[str, Any]] = {}
    if isinstance(plan_tiles, list):
        for raw in plan_tiles:
            if not isinstance(raw, dict):
                continue
            tile_id = str(raw.get("tile_id") or "").strip()
            if tile_id:
                by_tile[tile_id] = dict(raw)
    return by_tile


def ratio(numerator: object, denominator: object) -> float | None:
    try:
        den = float(denominator)
        if den <= 0:
            return None
        return float(numerator) / den
    except (TypeError, ValueError):
        return None


def context_entry_density_ratio(context_entry: dict[str, Any]) -> float | None:
    retained = (
        context_entry.get("retained_gaussians")
        or context_entry.get("context_retained_gaussians")
        or context_entry.get("dense_retained_gaussians")
    )
    reference = (
        context_entry.get("reference_retained_gaussians")
        or context_entry.get("v18_retained_gaussians")
        or context_entry.get("target_retained_gaussians")
    )
    return ratio(retained, reference)


@dataclass
class TileDecision:
    tile_id: str
    reference_retained_gaussians: int
    candidate_retained_gaussians: int | None
    candidate_retained_ratio: float | None
    candidate_quality_status: str | None
    candidate_status: str
    selected_source: str
    selected_stage_type: str
    selected_artifact_uri: str | None
    context_density_ratio: float | None
    retrain_required_if_no_v18_rollback: bool
    reasons: list[str]


def build_plan(
    *,
    reference_merge_report: dict[str, Any],
    candidate_summary: dict[str, Any],
    context_density_manifest: dict[str, Any],
    candidate_label: str,
    min_retained_ratio: float,
    min_context_density_ratio: float,
) -> dict[str, Any]:
    reference_tiles = normalize_reference_tiles(reference_merge_report)
    candidate_report = candidate_merge_report(candidate_summary)
    candidate_tiles = normalize_reference_tiles(candidate_report)
    candidate_plan_tiles = normalize_candidate_plan(candidate_summary)
    context_entries = normalize_context_density_manifest(context_density_manifest)

    decisions: list[TileDecision] = []
    for tile_id in sorted(reference_tiles):
        reference = reference_tiles[tile_id]
        reference_retained = int(reference.get("retained_gaussians") or 0)
        candidate = candidate_tiles.get(tile_id)
        candidate_retained = int(candidate.get("retained_gaussians")) if candidate else None
        candidate_ratio = ratio(candidate_retained, reference_retained) if candidate else None
        reasons: list[str] = []

        candidate_status = "missing"
        if candidate:
            candidate_status = "density_pass" if candidate_ratio is not None and candidate_ratio >= min_retained_ratio else "density_fail"
            if candidate_status == "density_fail":
                reasons.append("candidate_retained_ratio_below_threshold")
        else:
            reasons.append("candidate_tile_missing")

        plan_entry = candidate_plan_tiles.get(tile_id, {})
        candidate_stage_type = str(plan_entry.get("stage_type") or "candidate_tile")
        if candidate_stage_type == "context_density_tile":
            candidate_quality_status = str(
                plan_entry.get("quality_gate_status")
                or plan_entry.get("quality_status")
                or plan_entry.get("promotion_status")
                or "context_density_trusted"
            ).strip()
            candidate_quality_ok = True
        else:
            candidate_quality_status = str(
                plan_entry.get("v18_non_regression_status")
                or plan_entry.get("fullscene_quality_status")
                or plan_entry.get("candidate_review_status")
                or ""
            ).strip()
            candidate_quality_ok = status_is_passing(candidate_quality_status)
        candidate_quality_status = candidate_quality_status or None
        if candidate_status == "density_pass" and not candidate_quality_ok:
            candidate_status = "quality_unproven"
            reasons.append("candidate_quality_status_not_passing")

        if candidate_status == "density_pass":
            selected_source = "candidate"
            selected_stage_type = candidate_stage_type
            selected_artifact_uri = plan_entry.get("artifact_uri")
            context_ratio = None
            retrain_required = False
        else:
            context_entry = context_entries.get(tile_id)
            context_ratio = context_entry_density_ratio(context_entry or {})
            context_status_ok = bool(context_entry) and status_is_passing(
                context_entry.get("context_density_status")
                or context_entry.get("quality_gate_status")
                or context_entry.get("status")
            )
            context_ratio_ok = context_ratio is not None and context_ratio >= min_context_density_ratio
            if context_status_ok and context_ratio_ok:
                selected_source = "context_density_rollback"
                selected_stage_type = "context_density_tile"
                selected_artifact_uri = str(
                    context_entry.get("artifact_s3_uri")
                    or context_entry.get("source_artifact_uri")
                    or ""
                ) or None
                retrain_required = True
            else:
                selected_source = "retrain_required"
                selected_stage_type = "train"
                selected_artifact_uri = None
                retrain_required = True
                if not context_entry:
                    reasons.append("missing_context_density_fallback")
                elif not context_status_ok:
                    reasons.append("context_density_status_not_passing")
                elif not context_ratio_ok:
                    reasons.append("context_density_ratio_below_threshold")

        decisions.append(
            TileDecision(
                tile_id=tile_id,
                reference_retained_gaussians=reference_retained,
                candidate_retained_gaussians=candidate_retained,
                candidate_retained_ratio=candidate_ratio,
                candidate_quality_status=candidate_quality_status,
                candidate_status=candidate_status,
                selected_source=selected_source,
                selected_stage_type=selected_stage_type,
                selected_artifact_uri=selected_artifact_uri,
                context_density_ratio=context_ratio,
                retrain_required_if_no_v18_rollback=retrain_required,
                reasons=reasons,
            )
        )

    selected_counts: dict[str, int] = {}
    for decision in decisions:
        selected_counts[decision.selected_source] = selected_counts.get(decision.selected_source, 0) + 1

    missing_dense_fallback = [d.tile_id for d in decisions if d.selected_source == "retrain_required"]
    fallback_tiles = [d.tile_id for d in decisions if d.selected_source == "context_density_rollback"]
    candidate_density_fail_tiles = [
        d.tile_id for d in decisions if d.candidate_status in {"missing", "density_fail", "quality_unproven"}
    ]

    if missing_dense_fallback:
        status = "blocked_missing_dense_fallback"
        canary_submit_allowed = False
    elif fallback_tiles:
        status = "full_scene_canary_ready_with_v18_rollback"
        canary_submit_allowed = True
    else:
        status = "candidate_passes_density_gate"
        canary_submit_allowed = True

    return {
        "generated_at": utc_now(),
        "candidate_label": candidate_label,
        "density_thresholds": {
            "min_retained_ratio": min_retained_ratio,
            "min_context_density_ratio": min_context_density_ratio,
        },
        "status": status,
        "canary_submit_allowed": canary_submit_allowed,
        "training_jobs_to_submit": 0 if canary_submit_allowed else len(missing_dense_fallback),
        "no_full_14tile_training": True,
        "summary": {
            "reference_tile_count": len(reference_tiles),
            "candidate_tile_count": len(candidate_tiles),
            "selected_source_counts": selected_counts,
            "candidate_density_fail_or_missing_tile_ids": candidate_density_fail_tiles,
            "v18_rollback_tile_ids": fallback_tiles,
            "retrain_required_tile_ids": missing_dense_fallback,
        },
        "tile_plan": [asdict(decision) for decision in decisions],
        "decision": {
            "production_quality_status": (
                "not_a_new_cheaper_candidate_until_v18_rollback_tile_count_is_zero"
                if fallback_tiles
                else "candidate_density_gate_clear"
            ),
            "next_unblocked_step": (
                "Run only no-spend merge/preflight/review for this full-scene rollback canary, or target bounded "
                "paid retraining at candidate_density_fail_or_missing_tile_ids; do not submit a full 14-tile run."
            ),
        },
    }


def cache_status_for_decision(decision: dict[str, Any]) -> str:
    if decision.get("selected_stage_type") == "context_density_tile":
        return "context_density_hit"
    if decision.get("selected_source") == "candidate":
        return "hit"
    return str(decision.get("selected_source") or "")


def build_benchmark_summary_from_plan(
    *,
    plan: dict[str, Any],
    base_summary: dict[str, Any] | None = None,
    experiment_id: str = "",
) -> dict[str, Any]:
    base_summary = dict(base_summary or {})
    selected_tile_ids = [str(tile["tile_id"]) for tile in plan.get("tile_plan", []) if tile.get("tile_id")]
    stages = []
    for tile in plan.get("tile_plan", []):
        tile_id = str(tile.get("tile_id") or "").strip()
        artifact_uri = str(tile.get("selected_artifact_uri") or "").strip()
        stage_type = str(tile.get("selected_stage_type") or "").strip()
        if not tile_id or not artifact_uri or stage_type == "train":
            continue
        stages.append(
            {
                "stage_name": f"T0_{tile_id}",
                "stage_type": stage_type,
                "tile_id": tile_id,
                "source_artifact_uri": artifact_uri,
                "model_artifact_s3_uri": artifact_uri,
                "cache_status": cache_status_for_decision(tile),
                "quality_gate_status": "passed",
                "candidate_label": plan.get("candidate_label"),
                "candidate_status": tile.get("candidate_status"),
                "candidate_quality_status": tile.get("candidate_quality_status"),
                "selected_source": tile.get("selected_source"),
                "candidate_retained_ratio": tile.get("candidate_retained_ratio"),
                "context_density_ratio": tile.get("context_density_ratio"),
                "reference_retained_gaussians": tile.get("reference_retained_gaussians"),
                "candidate_retained_gaussians": tile.get("candidate_retained_gaussians"),
            }
        )

    summary = {
        **base_summary,
        "experiment_id": experiment_id or f"{plan.get('candidate_label', 'candidate')}-fullscene-rollback-canary",
        "selected_tile_ids": selected_tile_ids,
        "stages": stages,
        "submitted_jobs": [],
        "completed_jobs": [],
        "training_jobs_to_submit": 0,
        "cost_estimate": {"estimated_usd": 0.0, "training_stage_count": 0},
        "density_preserving_canary": {
            "generated_at": plan.get("generated_at"),
            "status": plan.get("status"),
            "candidate_label": plan.get("candidate_label"),
            "summary": plan.get("summary"),
            "decision": plan.get("decision"),
            "no_full_14tile_training": True,
        },
    }
    summary["source_density_preserving_canary_json"] = base_summary.get("source_density_preserving_canary_json")
    summary["merge_mode"] = summary.get("merge_mode") or "support_weighted_overlap"
    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reference-merge-report-json", required=True)
    parser.add_argument("--candidate-remote-merge-summary-json", required=True)
    parser.add_argument("--context-density-manifest-json", required=True)
    parser.add_argument("--candidate-label", default="candidate")
    parser.add_argument("--min-retained-ratio", type=float, default=0.95)
    parser.add_argument("--min-context-density-ratio", type=float, default=0.95)
    parser.add_argument("--output-json", required=True)
    parser.add_argument("--base-summary-json", default="")
    parser.add_argument("--summary-output-json", default="")
    parser.add_argument("--experiment-id", default="")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    plan = build_plan(
        reference_merge_report=load_json(args.reference_merge_report_json),
        candidate_summary=load_json(args.candidate_remote_merge_summary_json),
        context_density_manifest=load_json(args.context_density_manifest_json),
        candidate_label=args.candidate_label,
        min_retained_ratio=args.min_retained_ratio,
        min_context_density_ratio=args.min_context_density_ratio,
    )
    output_path = Path(args.output_json)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(plan, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    summary_path = None
    if args.summary_output_json:
        base_summary = load_json(args.base_summary_json) if args.base_summary_json else {}
        base_summary["source_density_preserving_canary_json"] = str(output_path)
        summary = build_benchmark_summary_from_plan(
            plan=plan,
            base_summary=base_summary,
            experiment_id=args.experiment_id,
        )
        summary_path = Path(args.summary_output_json)
        summary_path.parent.mkdir(parents=True, exist_ok=True)
        summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "output_json": str(output_path),
                "summary_output_json": str(summary_path) if summary_path else None,
                "status": plan["status"],
                "summary": plan["summary"],
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
