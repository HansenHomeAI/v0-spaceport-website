#!/usr/bin/env python3
"""Geometry-first review helpers for tiled 3DGS artifacts."""

from __future__ import annotations

from pathlib import Path
from statistics import median
from typing import Any, Mapping, Sequence


REVIEW_BUCKETS = (
    ("near_detail_camera_ids", "near_detail"),
    ("boundary_camera_ids", "boundary"),
    ("horizon_camera_ids", "horizon"),
)

PROMOTION_THRESHOLDS = {
    "near_detail": {
        "psnr_min_delta": -1.0,
        "ssim_min_delta": -0.015,
        "lpips_max_delta": 0.035,
    },
    "boundary": {
        "psnr_min_delta": -1.0,
        "ssim_min_delta": -0.015,
        "lpips_max_delta": 0.035,
        "required_improvement": {
            "psnr": 0.5,
            "ssim": 0.01,
            "lpips": -0.025,
        },
    },
    "horizon": {
        "psnr_min_delta": -0.75,
        "ssim_min_delta": -0.012,
        "lpips_max_delta": 0.03,
        "sky_score_min_ratio": 0.90,
    },
}


def ordered_unique(items: Sequence[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        normalized = Path(str(item).lstrip("./")).name
        if normalized in seen:
            continue
        seen.add(normalized)
        result.append(normalized)
    return result


def median_or_none(values: Sequence[float | None]) -> float | None:
    filtered = [float(value) for value in values if value is not None]
    if not filtered:
        return None
    return float(median(filtered))


def normalize_bucket_payload(view_buckets: Mapping[str, Any] | None) -> dict[str, list[str]]:
    payload = view_buckets if isinstance(view_buckets, Mapping) else {}
    return {
        bucket_key: ordered_unique(payload.get(bucket_key, payload.get(bucket_label, [])))
        for bucket_key, bucket_label in REVIEW_BUCKETS
    }


def freeze_review_camera_manifest(
    view_buckets: Mapping[str, Any] | None,
    *,
    images_per_bucket: int = 12,
    smoke_images_per_bucket: int = 4,
) -> dict[str, Any]:
    normalized = normalize_bucket_payload(view_buckets)
    frozen: dict[str, list[str]] = {}
    smoke: dict[str, list[str]] = {}
    for bucket_key, bucket_label in REVIEW_BUCKETS:
        selected = normalized[bucket_key][: max(0, images_per_bucket)]
        frozen[bucket_label] = selected
        smoke[bucket_label] = selected[: max(0, smoke_images_per_bucket)]
    return {
        "version": "1.0.0",
        "selection": "deterministic_ordered_manifest_first_n",
        "images_per_bucket": images_per_bucket,
        "smoke_images_per_bucket": smoke_images_per_bucket,
        "buckets": frozen,
        "smoke_buckets": smoke,
    }


def metric_delta(
    baseline_bucket_metrics: Mapping[str, Any] | None,
    candidate_bucket_metrics: Mapping[str, Any] | None,
) -> dict[str, float | None]:
    baseline = baseline_bucket_metrics or {}
    candidate = candidate_bucket_metrics or {}
    deltas: dict[str, float | None] = {}
    for metric in ("psnr", "ssim", "lpips"):
        before = baseline.get(metric)
        after = candidate.get(metric)
        deltas[metric] = None if before is None or after is None else float(after) - float(before)
    return deltas


def _has_required_metrics(metrics: Mapping[str, Any] | None) -> bool:
    if not isinstance(metrics, Mapping):
        return False
    return all(metrics.get(metric) is not None for metric in ("psnr", "ssim", "lpips"))


def _bucket_count_from_manifest(manifest: Mapping[str, Any] | None, bucket_label: str) -> int | None:
    if not isinstance(manifest, Mapping):
        return None
    for key in ("actual_bucket_counts", "expected_bucket_counts", "requested_bucket_counts"):
        counts = manifest.get(key)
        if isinstance(counts, Mapping) and counts.get(bucket_label) is not None:
            return int(counts[bucket_label])
    views = manifest.get("views")
    if not isinstance(views, Sequence) or isinstance(views, (str, bytes)):
        return None
    names = {
        str(view.get("image_name") or view.get("camera_id") or "")
        for view in views
        if isinstance(view, Mapping) and view.get("bucket") == bucket_label
    }
    names.discard("")
    return len(names)


def _bucket_camera_names(manifest: Mapping[str, Any] | None, bucket_key: str, bucket_label: str) -> list[str]:
    if not isinstance(manifest, Mapping):
        return []
    explicit = manifest.get("review_image_names_by_bucket")
    if isinstance(explicit, Mapping):
        values = explicit.get(bucket_key, explicit.get(bucket_label, []))
        if isinstance(values, Sequence) and not isinstance(values, (str, bytes)):
            return ordered_unique([str(value) for value in values])
    views = manifest.get("views")
    if isinstance(views, Sequence) and not isinstance(views, (str, bytes)):
        names = []
        for view in views:
            if not isinstance(view, Mapping) or view.get("bucket") != bucket_label:
                continue
            name = str(view.get("image_name") or view.get("camera_id") or "")
            if name:
                names.append(name)
        return ordered_unique(names)
    return []


def review_camera_coverage(
    baseline_manifest: Mapping[str, Any] | None,
    candidate_manifest: Mapping[str, Any],
) -> dict[str, Any]:
    per_bucket: dict[str, Any] = {}
    block_reasons: list[str] = []
    for bucket_key, bucket_label in REVIEW_BUCKETS:
        baseline_count = _bucket_count_from_manifest(baseline_manifest, bucket_label)
        candidate_count = _bucket_count_from_manifest(candidate_manifest, bucket_label)
        baseline_names = _bucket_camera_names(baseline_manifest, bucket_key, bucket_label)
        candidate_names = _bucket_camera_names(candidate_manifest, bucket_key, bucket_label)
        bucket_blocks: list[str] = []
        if baseline_manifest is not None:
            if baseline_names and candidate_names and baseline_names != candidate_names:
                bucket_blocks.append(f"{bucket_label}_camera_set_mismatch")
            elif (
                baseline_count is not None
                and candidate_count is not None
                and int(baseline_count) != int(candidate_count)
            ):
                bucket_blocks.append(f"{bucket_label}_camera_count_mismatch")
        block_reasons.extend(bucket_blocks)
        per_bucket[bucket_label] = {
            "baseline_count": baseline_count,
            "candidate_count": candidate_count,
            "baseline_cameras": baseline_names,
            "candidate_cameras": candidate_names,
            "block_reasons": bucket_blocks,
        }
    return {
        "status": "ok" if not block_reasons else "blocked",
        "block_reasons": list(dict.fromkeys(block_reasons)),
        "per_bucket": per_bucket,
    }


def evaluate_promotion_decision(
    *,
    baseline_manifest: Mapping[str, Any] | None,
    candidate_manifest: Mapping[str, Any],
    merge_report: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    baseline_buckets = (baseline_manifest or {}).get("bucket_medians", {})
    candidate_buckets = candidate_manifest.get("bucket_medians", {})
    baseline_sky = (baseline_manifest or {}).get("sky_bucket_medians", {})
    candidate_sky = candidate_manifest.get("sky_bucket_medians", {})
    effective_merge_report = merge_report or candidate_manifest.get("merge_report", {})

    block_reasons: list[str] = []
    warnings: list[str] = []
    per_bucket: dict[str, Any] = {}

    fallback_tile_count = int(effective_merge_report.get("fallback_tile_count", 0) or 0)
    retain_all_tile_count = int(effective_merge_report.get("retain_all_tile_count", 0) or 0)
    merge_mode = str(effective_merge_report.get("merge_mode", "") or "")
    if fallback_tile_count > 0:
        block_reasons.append("merge_fallback_tile_count_gt_zero")
    if retain_all_tile_count > 0:
        block_reasons.append("merge_retain_all_tile_count_gt_zero")
    if merge_mode == "raw_union":
        block_reasons.append("diagnostic_raw_union_not_promotable")
    render_sanity = candidate_manifest.get("render_sanity") or (
        candidate_manifest.get("promotion_readiness", {}).get("render_sanity")
        if isinstance(candidate_manifest.get("promotion_readiness"), Mapping)
        else {}
    )
    if isinstance(render_sanity, Mapping) and render_sanity.get("status") == "blocked":
        block_reasons.append("candidate_render_sanity_blocked")

    camera_coverage = review_camera_coverage(baseline_manifest, candidate_manifest)
    for _bucket_key, bucket_label in REVIEW_BUCKETS:
        baseline_metrics = baseline_buckets.get(bucket_label)
        candidate_metrics = candidate_buckets.get(bucket_label)
        deltas = metric_delta(baseline_metrics, candidate_metrics)
        bucket_blocks: list[str] = list(
            (camera_coverage.get("per_bucket", {}).get(bucket_label, {}) or {}).get("block_reasons", [])
        )
        if not _has_required_metrics(candidate_metrics):
            bucket_blocks.append(f"{bucket_label}_candidate_metrics_missing")
        if baseline_manifest is None or not _has_required_metrics(baseline_metrics):
            bucket_blocks.append(f"{bucket_label}_baseline_metrics_missing")

        thresholds = PROMOTION_THRESHOLDS[bucket_label]
        if not bucket_blocks:
            if deltas["psnr"] is not None and deltas["psnr"] < thresholds["psnr_min_delta"]:
                bucket_blocks.append(f"{bucket_label}_psnr_regression")
            if deltas["ssim"] is not None and deltas["ssim"] < thresholds["ssim_min_delta"]:
                bucket_blocks.append(f"{bucket_label}_ssim_regression")
            if deltas["lpips"] is not None and deltas["lpips"] > thresholds["lpips_max_delta"]:
                bucket_blocks.append(f"{bucket_label}_lpips_regression")

            if bucket_label == "boundary":
                required = thresholds["required_improvement"]
                improved = (
                    (deltas["psnr"] is not None and deltas["psnr"] >= required["psnr"])
                    or (deltas["ssim"] is not None and deltas["ssim"] >= required["ssim"])
                    or (deltas["lpips"] is not None and deltas["lpips"] <= required["lpips"])
                )
                if not improved:
                    bucket_blocks.append("boundary_no_required_improvement")
            if bucket_label == "horizon":
                baseline_sky_score = (baseline_sky.get(bucket_label) or {}).get("score")
                candidate_sky_score = (candidate_sky.get(bucket_label) or {}).get("score")
                if baseline_sky_score is not None and candidate_sky_score is not None:
                    if float(candidate_sky_score) < float(baseline_sky_score) * thresholds["sky_score_min_ratio"]:
                        bucket_blocks.append("horizon_sky_score_regression")
                else:
                    warnings.append("horizon_sky_score_unavailable")

        block_reasons.extend(bucket_blocks)
        per_bucket[bucket_label] = {
            "baseline": dict(baseline_metrics or {}),
            "candidate": dict(candidate_metrics or {}),
            "delta": deltas,
            "block_reasons": bucket_blocks,
        }

    unique_block_reasons = list(dict.fromkeys(block_reasons))
    return {
        "status": "promoted" if not unique_block_reasons else "blocked",
        "block_reasons": unique_block_reasons,
        "warnings": list(dict.fromkeys(warnings)),
        "merge_mode": merge_mode,
        "fallback_tile_count": fallback_tile_count,
        "retain_all_tile_count": retain_all_tile_count,
        "per_bucket": per_bucket,
        "thresholds": PROMOTION_THRESHOLDS,
        "camera_coverage": camera_coverage,
    }


def build_review_comparison(
    *,
    baseline_manifest: Mapping[str, Any] | None,
    candidate_manifest: Mapping[str, Any],
    baseline_artifact: str | None = None,
    candidate_artifact: str | None = None,
    camera_manifest: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    candidate_merge_report = candidate_manifest.get("merge_report", {})
    baseline_merge_report = (baseline_manifest or {}).get("merge_report", {})
    camera_coverage = review_camera_coverage(baseline_manifest, candidate_manifest)
    decision = evaluate_promotion_decision(
        baseline_manifest=baseline_manifest,
        candidate_manifest=candidate_manifest,
        merge_report=candidate_merge_report,
    )
    side_by_side_paths: list[dict[str, Any]] = []
    for view in candidate_manifest.get("views", []):
        if not isinstance(view, Mapping):
            continue
        side_by_side_paths.append(
            {
                "bucket": view.get("bucket"),
                "image_name": view.get("image_name"),
                "reference_image": view.get("reference_image"),
                "candidate_render": view.get("merged_render"),
                "candidate_no_background_render": view.get("merged_no_background_render"),
                "boundary_composite": view.get("boundary_composite"),
                "tile_renders": view.get("boundary_tile_renders", []),
            }
        )
    return {
        "version": "1.0.0",
        "baseline_artifact": baseline_artifact,
        "candidate_artifact": candidate_artifact,
        "camera_manifest": dict(camera_manifest or {}),
        "camera_coverage": camera_coverage,
        "per_bucket": decision["per_bucket"],
        "fallback_breakdown": {
            "baseline": {
                "merge_mode": baseline_merge_report.get("merge_mode"),
                "fallback_tile_count": int(baseline_merge_report.get("fallback_tile_count", 0) or 0),
                "retain_all_tile_count": int(baseline_merge_report.get("retain_all_tile_count", 0) or 0),
                "source_gaussians": baseline_merge_report.get("source_gaussians"),
                "retained_gaussians": baseline_merge_report.get("retained_gaussians"),
                "fallback_reasons": baseline_merge_report.get("fallback_reasons", []),
            },
            "candidate": {
                "merge_mode": candidate_merge_report.get("merge_mode"),
                "fallback_tile_count": int(candidate_merge_report.get("fallback_tile_count", 0) or 0),
                "retain_all_tile_count": int(candidate_merge_report.get("retain_all_tile_count", 0) or 0),
                "source_gaussians": candidate_merge_report.get("source_gaussians"),
                "retained_gaussians": candidate_merge_report.get("retained_gaussians"),
                "fallback_reasons": candidate_merge_report.get("fallback_reasons", []),
            },
        },
        "side_by_side_render_paths": side_by_side_paths,
        "promotion_decision": decision,
    }


def inventory_extracted_model(model_dir: Path) -> dict[str, Any]:
    tile_splats = sorted(str(path.relative_to(model_dir)) for path in (model_dir / "tiles").glob("tile_*/splat.ply"))
    manifest_candidates = [
        model_dir / "3dgs_tile_manifest.json",
        model_dir / "tiled_pipeline" / "inputs" / "scaffold" / "3dgs_tile_manifest.json",
        *sorted((model_dir / "tiled_pipeline" / "inputs").glob("tile_*/3dgs_tile_manifest.json")),
    ]
    view_bucket_candidates = [
        model_dir / "3dgs_view_buckets.fixed.json",
        model_dir / "3dgs_view_buckets.json",
        model_dir / "tiled_pipeline" / "inputs" / "scaffold" / "3dgs_view_buckets.fixed.json",
        model_dir / "tiled_pipeline" / "inputs" / "scaffold" / "3dgs_view_buckets.json",
        *sorted((model_dir / "tiled_pipeline" / "inputs").glob("tile_*/3dgs_view_buckets.fixed.json")),
        *sorted((model_dir / "tiled_pipeline" / "inputs").glob("tile_*/3dgs_view_buckets.json")),
    ]
    tile_manifest = next((path for path in manifest_candidates if path.exists()), None)
    view_bucket_manifest = next((path for path in view_bucket_candidates if path.exists()), None)
    merge_report = model_dir / "merged" / "merge_report.json"
    merged_splat = model_dir / "merged" / "merged_splat.ply"
    required = {
        "seven_tile_splats": len(tile_splats) >= 7,
        "merged_splat": merged_splat.exists(),
        "merge_report": merge_report.exists(),
        "tile_manifest": tile_manifest is not None,
        "view_bucket_manifest": view_bucket_manifest is not None,
    }
    return {
        "model_dir": str(model_dir),
        "tile_splat_count": len(tile_splats),
        "tile_splats": tile_splats,
        "merged_splat": str(merged_splat) if merged_splat.exists() else None,
        "merge_report": str(merge_report) if merge_report.exists() else None,
        "tile_manifest": str(tile_manifest) if tile_manifest else None,
        "view_bucket_manifest": str(view_bucket_manifest) if view_bucket_manifest else None,
        "required": required,
        "complete": all(required.values()),
    }


def classify_root_cause(
    *,
    inventory: Mapping[str, Any],
    merge_report: Mapping[str, Any] | None = None,
    candidate_pairs: Sequence[Mapping[str, Any]] | None = None,
    review_comparison: Mapping[str, Any] | None = None,
) -> str:
    required = inventory.get("required", {})
    if not inventory.get("complete", False):
        if not required.get("seven_tile_splats", False):
            return "tile_training_bad"
        if not required.get("tile_manifest", False) or not required.get("view_bucket_manifest", False):
            return "partition_bad"
        return "merge_bad"

    report = merge_report or {}
    if int(report.get("retain_all_tile_count", 0) or 0) > 0 or int(report.get("fallback_tile_count", 0) or 0) > 0:
        return "merge_bad"

    if review_comparison:
        reasons = set(
            (review_comparison.get("promotion_decision") or {}).get("block_reasons", [])
        )
        actionable_reasons = {
            str(reason)
            for reason in reasons
            if not str(reason).endswith("_metrics_missing")
        }
        if any(reason.startswith("horizon_") for reason in actionable_reasons):
            return "far_field_bad"
        if any(reason.startswith("near_detail_") for reason in actionable_reasons):
            return "tile_training_bad"

    if candidate_pairs is not None and not any(pair.get("eligible") for pair in candidate_pairs):
        return "partition_bad"

    return "base_geometry_bad"
