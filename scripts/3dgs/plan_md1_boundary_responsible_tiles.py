#!/usr/bin/env python3
"""Plan the no-spend MD1 boundary-camera responsible tile strategy."""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence


BOUNDARY_BLOCKER = "boundary_no_required_improvement"
REVIEW_BUCKET_KEYS = (
    ("near_detail_camera_ids", "near_detail"),
    ("boundary_camera_ids", "boundary"),
    ("horizon_camera_ids", "horizon"),
)


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_json(path: str | Path) -> dict[str, Any]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Expected JSON object at {path}")
    return payload


def write_json(path: str | Path, payload: Mapping[str, Any]) -> None:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def list_strings(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value if str(item)]


def ordered_unique(items: Sequence[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        normalized = Path(str(item).lstrip("./")).name
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        result.append(normalized)
    return result


def promotion_decision(review_comparison: Mapping[str, Any]) -> dict[str, Any]:
    decision = review_comparison.get("promotion_decision")
    return dict(decision) if isinstance(decision, Mapping) else {}


def review_image_names_by_bucket(review_comparison: Mapping[str, Any]) -> dict[str, list[str]]:
    camera_manifest = review_comparison.get("camera_manifest")
    explicit = camera_manifest.get("review_image_names_by_bucket") if isinstance(camera_manifest, Mapping) else None
    if not isinstance(explicit, Mapping):
        explicit = review_comparison.get("review_image_names_by_bucket")
    if not isinstance(explicit, Mapping):
        explicit = {}

    result: dict[str, list[str]] = {}
    for bucket_key, bucket_label in REVIEW_BUCKET_KEYS:
        raw = explicit.get(bucket_key, explicit.get(bucket_label, []))
        result[bucket_key] = ordered_unique([str(item) for item in raw]) if isinstance(raw, list) else []
    return result


def camera_manifest_boundary_context(review_comparison: Mapping[str, Any]) -> dict[str, list[str]]:
    camera_manifest = review_comparison.get("camera_manifest")
    views = camera_manifest.get("views") if isinstance(camera_manifest, Mapping) else []
    result: dict[str, list[str]] = {}
    if not isinstance(views, list):
        return result
    for view in views:
        if not isinstance(view, Mapping) or str(view.get("bucket")) != "boundary":
            continue
        image_name = Path(str(view.get("image_name") or "")).name
        if not image_name:
            continue
        result[image_name] = ordered_unique(list_strings(view.get("boundary_context_tile_ids")))
    return result


def tiles_by_id(tile_manifest: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for tile in tile_manifest.get("tiles", []):
        if not isinstance(tile, Mapping):
            continue
        tile_id = str(tile.get("tile_id") or "").strip()
        if tile_id:
            result[tile_id] = dict(tile)
    return result


def support_roles_by_image(tile_manifest: Mapping[str, Any]) -> dict[str, dict[str, list[str]]]:
    by_image: dict[str, dict[str, list[str]]] = {}
    role_fields = (
        ("base", "base_camera_ids"),
        ("border", "border_camera_ids"),
        ("context", "context_camera_ids"),
        ("image", "image_names"),
    )
    for tile in tile_manifest.get("tiles", []):
        if not isinstance(tile, Mapping):
            continue
        tile_id = str(tile.get("tile_id") or "").strip()
        if not tile_id:
            continue
        for role, field in role_fields:
            raw = tile.get(field, [])
            if not isinstance(raw, list):
                continue
            for image_name in ordered_unique([str(item) for item in raw]):
                roles = by_image.setdefault(image_name, {}).setdefault(tile_id, [])
                if role not in roles:
                    roles.append(role)
    return by_image


def view_bucket_counts(tile: Mapping[str, Any], view_buckets: Mapping[str, Any] | None) -> dict[str, int]:
    if not view_buckets:
        return {}
    image_names = set(ordered_unique([str(item) for item in tile.get("image_names", []) if str(item)]))
    counts: dict[str, int] = {}
    for bucket_key, bucket_label in REVIEW_BUCKET_KEYS:
        bucket_images = view_buckets.get(bucket_key, []) if isinstance(view_buckets, Mapping) else []
        if isinstance(bucket_images, list):
            counts[bucket_label] = sum(1 for image_name in ordered_unique([str(item) for item in bucket_images]) if image_name in image_names)
    return counts


def strategy_targets(strategy: Mapping[str, Any] | None) -> list[str]:
    if not strategy:
        return []
    direct = list_strings(strategy.get("targeted_quality_blockers"))
    if not direct:
        direct = list_strings(strategy.get("targeted_quality_block_reasons"))
    nested = strategy.get("quality_strategy")
    if isinstance(nested, Mapping):
        direct.extend(list_strings(nested.get("targeted_quality_blockers")))
        direct.extend(list_strings(nested.get("targeted_quality_block_reasons")))
    return sorted(set(direct))


def candidate_tile_ids(strategy: Mapping[str, Any] | None) -> list[str]:
    if not strategy:
        return []
    values = list_strings(strategy.get("selected_tile_ids"))
    values.extend(list_strings(strategy.get("tile_ids")))
    for key in ("planned_tiles", "training_jobs", "post_leaf_preflight_gates"):
        raw = strategy.get(key)
        if isinstance(raw, list):
            for item in raw:
                if isinstance(item, Mapping) and item.get("tile_id"):
                    values.append(str(item["tile_id"]))
                elif isinstance(item, str):
                    values.append(item)
    return ordered_unique(values)


def boundary_gap(decision: Mapping[str, Any]) -> dict[str, Any] | None:
    per_bucket = decision.get("per_bucket") if isinstance(decision.get("per_bucket"), Mapping) else {}
    boundary = per_bucket.get("boundary") if isinstance(per_bucket.get("boundary"), Mapping) else {}
    deltas = boundary.get("delta") if isinstance(boundary.get("delta"), Mapping) else {}
    thresholds = decision.get("thresholds") if isinstance(decision.get("thresholds"), Mapping) else {}
    required = {}
    if isinstance(thresholds.get("boundary"), Mapping):
        required = thresholds["boundary"].get("required_improvement") or {}
    if not isinstance(required, Mapping) or not deltas:
        return None
    psnr_delta = float(deltas.get("psnr") or 0.0)
    ssim_delta = float(deltas.get("ssim") or 0.0)
    lpips_delta = float(deltas.get("lpips") or 0.0)
    psnr_required = float(required.get("psnr") or 0.0)
    ssim_required = float(required.get("ssim") or 0.0)
    lpips_required = float(required.get("lpips") or 0.0)
    return {
        "actual_delta": {"psnr": psnr_delta, "ssim": ssim_delta, "lpips": lpips_delta},
        "required_improvement": {"psnr": psnr_required, "ssim": ssim_required, "lpips": lpips_required},
        "remaining_gap": {
            "psnr": max(0.0, psnr_required - psnr_delta),
            "ssim": max(0.0, ssim_required - ssim_delta),
            "lpips": max(0.0, lpips_delta - lpips_required),
        },
    }


def tile_density_summary(tile_id: str, density_context: Mapping[str, Any] | None) -> dict[str, Any] | None:
    if not density_context:
        return None
    comparison = density_context.get("tile_density_context_comparison")
    if not isinstance(comparison, Mapping):
        return None
    tile = comparison.get(tile_id)
    if not isinstance(tile, Mapping):
        return None
    summary: dict[str, Any] = {}
    for key in (
        "standard_to_v18_retained_ratio",
        "hard_to_v18_retained_ratio",
        "r5_serial_leaf_remaining_to_v18_retained_ratio",
        "standard_retained_gap_vs_v18",
        "hard_retained_gap_vs_v18",
    ):
        if key in tile:
            summary[key] = tile[key]
    for variant in ("standard_v18color", "hard_repair"):
        source = tile.get(variant)
        if isinstance(source, Mapping):
            summary[variant] = {
                key: source.get(key)
                for key in (
                    "retained_gaussians",
                    "retained_context_count",
                    "retained_overlap_count",
                    "selected_image_count",
                    "max_iterations",
                    "context_preserve_enabled",
                    "view_bucket_counts",
                )
                if key in source
            }
    return summary or None


def plan_boundary_responsible_tiles(
    *,
    review_comparison: Mapping[str, Any],
    tile_manifest: Mapping[str, Any],
    view_buckets: Mapping[str, Any] | None = None,
    quality_strategy: Mapping[str, Any] | None = None,
    candidate_strategy: Mapping[str, Any] | None = None,
    density_context: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    decision = promotion_decision(review_comparison)
    blockers = sorted(set(list_strings(decision.get("block_reasons"))))
    images_by_bucket = review_image_names_by_bucket(review_comparison)
    boundary_images = images_by_bucket.get("boundary_camera_ids", [])
    embedded_boundary_context = camera_manifest_boundary_context(review_comparison)
    support_by_image = support_roles_by_image(tile_manifest)
    tile_lookup = tiles_by_id(tile_manifest)

    role_counts_by_tile: dict[str, Counter[str]] = defaultdict(Counter)
    primary_counts: Counter[str] = Counter()
    support_counts: Counter[str] = Counter()
    per_camera: list[dict[str, Any]] = []

    for image_name in boundary_images:
        roles_by_tile = support_by_image.get(Path(image_name).name, {})
        support_tile_ids = sorted(roles_by_tile)
        embedded_primary = embedded_boundary_context.get(Path(image_name).name, [])
        primary_tile_ids = [tile_id for tile_id in embedded_primary if tile_id in support_tile_ids]
        if not primary_tile_ids:
            primary_tile_ids = [
                tile_id
                for tile_id in support_tile_ids
                if "base" in roles_by_tile.get(tile_id, []) or "image" in roles_by_tile.get(tile_id, [])
            ]
        primary_tile_ids = ordered_unique(primary_tile_ids)
        for tile_id in support_tile_ids:
            support_counts[tile_id] += 1
            for role in roles_by_tile[tile_id]:
                role_counts_by_tile[tile_id][role] += 1
        primary_counts.update(primary_tile_ids)
        per_camera.append(
            {
                "image_name": image_name,
                "embedded_boundary_context_tile_ids": embedded_primary,
                "primary_responsible_tile_ids": primary_tile_ids,
                "support_tile_ids": support_tile_ids,
                "support_roles_by_tile": {tile_id: roles_by_tile[tile_id] for tile_id in support_tile_ids},
            }
        )

    primary_responsible_tiles = sorted(primary_counts)
    support_tiles = sorted(support_counts)
    ranked_tiles: list[dict[str, Any]] = []
    for tile_id in sorted(set(primary_responsible_tiles + support_tiles)):
        tile = tile_lookup.get(tile_id, {})
        ranked_tiles.append(
            {
                "tile_id": tile_id,
                "primary_boundary_camera_count": primary_counts.get(tile_id, 0),
                "support_boundary_camera_count": support_counts.get(tile_id, 0),
                "support_role_counts": dict(sorted(role_counts_by_tile[tile_id].items())),
                "selected_image_count": tile.get("selected_image_count"),
                "view_bucket_counts": view_bucket_counts(tile, view_buckets),
                "neighbor_tile_ids": list_strings(tile.get("neighbor_tile_ids")),
                "density_context_summary": tile_density_summary(tile_id, density_context),
            }
        )
    ranked_tiles.sort(
        key=lambda row: (
            -int(row["primary_boundary_camera_count"]),
            -int(row["support_boundary_camera_count"]),
            str(row["tile_id"]),
        )
    )

    candidate_targets = strategy_targets(candidate_strategy)
    candidate_tiles = candidate_tile_ids(candidate_strategy)
    missing_candidate_targets = [reason for reason in blockers if reason not in candidate_targets]
    missing_primary_tiles = [tile_id for tile_id in primary_responsible_tiles if candidate_tiles and tile_id not in candidate_tiles]

    blocked_reasons: list[str] = []
    if BOUNDARY_BLOCKER in blockers and missing_candidate_targets:
        blocked_reasons.append("candidate_strategy_does_not_target_boundary_blocker")
    if missing_primary_tiles:
        blocked_reasons.append("candidate_strategy_omits_primary_boundary_tiles")
    if BOUNDARY_BLOCKER in blockers and not boundary_images:
        blocked_reasons.append("boundary_frozen_cameras_missing")

    recommendation = "hold_paid_retry"
    next_step = "dry_run_paired_boundary_tile_strategy"
    if BOUNDARY_BLOCKER not in blockers:
        recommendation = "boundary_blocker_clear"
        next_step = "continue_promotion_gate"
    elif blocked_reasons:
        recommendation = "hold_paid_retry"
    else:
        recommendation = "candidate_strategy_targets_boundary_context"

    return {
        "checked_at": now_iso(),
        "current_quality_blockers": blockers,
        "boundary_improvement_gap": boundary_gap(decision),
        "quality_strategy_reference": quality_strategy,
        "boundary_frozen_cameras": boundary_images,
        "per_boundary_camera": per_camera,
        "primary_responsible_tile_ids": primary_responsible_tiles,
        "support_tile_ids": support_tiles,
        "ranked_responsible_tiles": ranked_tiles,
        "candidate_strategy_targeted_quality_blockers": candidate_targets,
        "candidate_strategy_tile_ids": candidate_tiles,
        "candidate_strategy_block_reasons": blocked_reasons,
        "recommendation": recommendation,
        "paid_retry_recommended": recommendation == "candidate_strategy_targets_boundary_context",
        "proposed_no_spend_next_step": {
            "action": next_step,
            "tile_scope": primary_responsible_tiles,
            "context_support_tile_ids": [tile_id for tile_id in support_tiles if tile_id not in primary_responsible_tiles],
            "rationale": (
                "The frozen boundary cameras are jointly supported by the primary boundary tiles; "
                "a single-tile density retry cannot plausibly move the boundary PSNR/SSIM/LPIPS gate enough."
            ),
        },
        "paid_retry_requirements_before_submit": [
            "targeted_quality_blockers must include boundary_no_required_improvement",
            "selected tiles must include every primary_responsible_tile_id",
            "strategy must name the boundary frozen cameras and expected metric axis",
            "leaf preflight density/reference gates must pass before any merge or review spend",
            "no full 14-tile training before R0/R1/R2/R3 evidence gates pass",
        ],
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--review-comparison-json", required=True)
    parser.add_argument("--tile-manifest-json", required=True)
    parser.add_argument("--view-buckets-json", default="")
    parser.add_argument("--quality-strategy-json", default="")
    parser.add_argument("--candidate-strategy-json", default="")
    parser.add_argument("--density-context-json", default="")
    parser.add_argument("--output-json", required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    report = plan_boundary_responsible_tiles(
        review_comparison=load_json(args.review_comparison_json),
        tile_manifest=load_json(args.tile_manifest_json),
        view_buckets=load_json(args.view_buckets_json) if args.view_buckets_json else None,
        quality_strategy=load_json(args.quality_strategy_json) if args.quality_strategy_json else None,
        candidate_strategy=load_json(args.candidate_strategy_json) if args.candidate_strategy_json else None,
        density_context=load_json(args.density_context_json) if args.density_context_json else None,
    )
    write_json(args.output_json, report)
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
