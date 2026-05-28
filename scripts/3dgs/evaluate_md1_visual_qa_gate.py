#!/usr/bin/env python3
"""Gate tiled 3DGS visual QA outputs before promotion.

The quality review job produces camera-by-camera reference/render/diff panels.
This script turns those artifacts into a hard pass/fail decision so smoke
renders cannot be mistaken for production-ready splats.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from statistics import median
from typing import Any, Mapping, Sequence


REPO_ROOT = Path(__file__).resolve().parents[2]
GEOMETRY_REVIEW_DIR = REPO_ROOT / "infrastructure" / "containers" / "3dgs"
if str(GEOMETRY_REVIEW_DIR) not in sys.path:
    sys.path.insert(0, str(GEOMETRY_REVIEW_DIR))

from geometry_review import evaluate_v18_non_regression_decision  # noqa: E402


DEFAULT_BUCKETS = ("near_detail", "boundary", "horizon")
REQUIRED_ASSETS = (
    "reference_image",
    "merged_render",
    "merged_no_background_render",
    "diff_heatmap",
    "side_by_side_panel",
)
DEFAULT_MAX_HORIZON_FOREGROUND_ALPHA_MEAN = 0.98
DEFAULT_MAX_HORIZON_FOREGROUND_ALPHA_COVERAGE = 0.995
DEFAULT_MIN_HORIZON_FOREGROUND_LUMINANCE = 0.60
DEFAULT_MIN_HORIZON_FOREGROUND_BLUE_DOMINANCE = 0.35
DEFAULT_MIN_HORIZON_FOREGROUND_SATURATION = 0.12


def load_json(path: str | Path | None) -> dict[str, Any] | None:
    if not path:
        return None
    with open(path, "r", encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict):
        raise ValueError(f"Expected JSON object in {path}")
    return payload


def unique(items: Sequence[str]) -> list[str]:
    return list(dict.fromkeys(item for item in items if item))


def median_or_none(values: Sequence[Any]) -> float | None:
    numeric = []
    for value in values:
        if value is None:
            continue
        try:
            numeric.append(float(value))
        except (TypeError, ValueError):
            continue
    if not numeric:
        return None
    return float(median(numeric))


def float_or_none(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def metric_payload(metrics: Mapping[str, Any] | None) -> dict[str, float | None]:
    metrics = metrics if isinstance(metrics, Mapping) else {}
    return {
        "psnr": None if metrics.get("psnr") is None else float(metrics["psnr"]),
        "ssim": None if metrics.get("ssim") is None else float(metrics["ssim"]),
        "lpips": None if metrics.get("lpips") is None else float(metrics["lpips"]),
    }


def quality_manifest_path_from_visual(
    visual_manifest: Mapping[str, Any],
    visual_manifest_path: Path,
) -> Path | None:
    record = visual_manifest.get("quality_review_manifest")
    if not isinstance(record, Mapping):
        return None
    for key in ("path", "artifact_relative_path"):
        value = record.get(key)
        if not value:
            continue
        candidate = Path(str(value))
        if candidate.exists():
            return candidate
        sibling = visual_manifest_path.parent / candidate.name
        if sibling.exists():
            return sibling
        relative = visual_manifest_path.parent / candidate
        if relative.exists():
            return relative
    return None


def views_from_manifests(
    visual_manifest: Mapping[str, Any],
    quality_manifest: Mapping[str, Any] | None,
) -> list[Mapping[str, Any]]:
    quality_views = quality_manifest.get("views", []) if isinstance(quality_manifest, Mapping) else []
    if isinstance(quality_views, list) and quality_views:
        return [view for view in quality_views if isinstance(view, Mapping)]
    visual_views = visual_manifest.get("views", [])
    return [view for view in visual_views if isinstance(view, Mapping)] if isinstance(visual_views, list) else []


def bucket_medians_from_views(views: Sequence[Mapping[str, Any]]) -> dict[str, dict[str, float | None]]:
    medians: dict[str, dict[str, float | None]] = {}
    for bucket in DEFAULT_BUCKETS:
        bucket_views = [view for view in views if str(view.get("bucket") or "") == bucket]
        medians[bucket] = {
            "psnr": median_or_none([metric_payload(view.get("metrics")).get("psnr") for view in bucket_views]),
            "ssim": median_or_none([metric_payload(view.get("metrics")).get("ssim") for view in bucket_views]),
            "lpips": median_or_none([metric_payload(view.get("metrics")).get("lpips") for view in bucket_views]),
        }
    return medians


def asset_local_path(asset: Mapping[str, Any], asset_root: Path | None) -> Path | None:
    if not isinstance(asset, Mapping):
        return None
    relative = asset.get("artifact_relative_path")
    if asset_root is not None and relative:
        return asset_root / str(relative)
    path = asset.get("path")
    if path:
        return Path(str(path))
    return None


def evaluate_assets(
    visual_manifest: Mapping[str, Any],
    *,
    asset_root: Path | None,
    require_local_assets: bool,
) -> dict[str, Any]:
    missing_records: list[dict[str, str]] = []
    missing_files: list[dict[str, str]] = []
    checked_files = 0
    for view in visual_manifest.get("views", []):
        if not isinstance(view, Mapping):
            continue
        assets = view.get("assets", {})
        assets = assets if isinstance(assets, Mapping) else {}
        bucket = str(view.get("bucket") or "")
        image_name = str(view.get("image_name") or "")
        for asset_name in REQUIRED_ASSETS:
            asset = assets.get(asset_name)
            if not isinstance(asset, Mapping):
                missing_records.append({"bucket": bucket, "image_name": image_name, "asset": asset_name})
                continue
            path = asset_local_path(asset, asset_root)
            if path is None:
                missing_records.append({"bucket": bucket, "image_name": image_name, "asset": asset_name})
                continue
            if asset_root is not None or path.is_absolute():
                checked_files += 1
                if not path.exists():
                    missing_files.append(
                        {
                            "bucket": bucket,
                            "image_name": image_name,
                            "asset": asset_name,
                            "path": str(path),
                        }
                    )
    status = "ok"
    block_reasons: list[str] = []
    if missing_records:
        status = "blocked"
        block_reasons.append("visual_qa_asset_records_missing")
    if require_local_assets and missing_files:
        status = "blocked"
        block_reasons.append("visual_qa_local_assets_missing")
    return {
        "status": status,
        "checked_files": checked_files,
        "missing_record_count": len(missing_records),
        "missing_file_count": len(missing_files),
        "missing_records": missing_records[:25],
        "missing_files": missing_files[:25],
        "block_reasons": block_reasons,
    }


def evaluate_absolute_metrics(
    views: Sequence[Mapping[str, Any]],
    quality_manifest: Mapping[str, Any] | None,
    args: argparse.Namespace,
) -> dict[str, Any]:
    bucket_medians = (
        quality_manifest.get("bucket_medians")
        if isinstance(quality_manifest, Mapping) and isinstance(quality_manifest.get("bucket_medians"), Mapping)
        else bucket_medians_from_views(views)
    )
    block_reasons: list[str] = []
    per_bucket: dict[str, Any] = {}
    per_view_blocks: list[dict[str, Any]] = []

    for bucket in DEFAULT_BUCKETS:
        metrics = metric_payload((bucket_medians or {}).get(bucket))
        bucket_blocks: list[str] = []
        if metrics["psnr"] is None:
            bucket_blocks.append(f"{bucket}_median_psnr_missing")
        elif metrics["psnr"] < args.min_median_psnr:
            bucket_blocks.append(f"{bucket}_median_psnr_below_threshold")
        if metrics["ssim"] is None:
            bucket_blocks.append(f"{bucket}_median_ssim_missing")
        elif metrics["ssim"] < args.min_median_ssim:
            bucket_blocks.append(f"{bucket}_median_ssim_below_threshold")
        if metrics["lpips"] is None:
            bucket_blocks.append(f"{bucket}_median_lpips_missing")
        elif metrics["lpips"] > args.max_median_lpips:
            bucket_blocks.append(f"{bucket}_median_lpips_above_threshold")
        block_reasons.extend(bucket_blocks)
        per_bucket[bucket] = {
            "metrics": metrics,
            "thresholds": {
                "min_median_psnr": args.min_median_psnr,
                "min_median_ssim": args.min_median_ssim,
                "max_median_lpips": args.max_median_lpips,
            },
            "block_reasons": bucket_blocks,
        }

    for view in views:
        bucket = str(view.get("bucket") or "")
        image_name = str(view.get("image_name") or "")
        metrics = metric_payload(view.get("metrics"))
        difference_stats = view.get("difference_stats") if isinstance(view.get("difference_stats"), Mapping) else {}
        view_blocks: list[str] = []
        if metrics["psnr"] is None or metrics["psnr"] < args.min_single_psnr:
            view_blocks.append("single_view_psnr_below_threshold")
        if metrics["ssim"] is None or metrics["ssim"] < args.min_single_ssim:
            view_blocks.append("single_view_ssim_below_threshold")
        if metrics["lpips"] is None or metrics["lpips"] > args.max_single_lpips:
            view_blocks.append("single_view_lpips_above_threshold")
        mean_abs_error = difference_stats.get("mean_abs_rgb_error")
        if mean_abs_error is not None and float(mean_abs_error) > args.max_mean_abs_rgb_error:
            view_blocks.append("single_view_mean_abs_rgb_error_above_threshold")
        if view_blocks:
            block_reasons.extend(f"{bucket}_{reason}" if bucket else reason for reason in view_blocks)
            per_view_blocks.append(
                {
                    "bucket": bucket,
                    "image_name": image_name,
                    "metrics": metrics,
                    "difference_stats": dict(difference_stats),
                    "block_reasons": view_blocks,
                }
            )

    return {
        "status": "passed" if not block_reasons else "blocked",
        "block_reasons": unique(block_reasons),
        "per_bucket": per_bucket,
        "per_view_block_count": len(per_view_blocks),
        "per_view_blocks": per_view_blocks[:50],
    }


def evaluate_horizon_foreground_saturation(
    views: Sequence[Mapping[str, Any]],
    args: argparse.Namespace,
) -> dict[str, Any]:
    """Block horizon views where foreground splats fully cover sky-like pixels."""
    if getattr(args, "disable_horizon_foreground_gate", False):
        return {"status": "skipped", "block_reasons": [], "saturated_view_count": 0}

    saturated_views: list[dict[str, Any]] = []
    checked_views = 0
    for view in views:
        if str(view.get("bucket") or "") != "horizon":
            continue
        alpha_stats = view.get("merged_alpha_stats")
        sky_metrics = view.get("sky_metrics_no_background")
        if not isinstance(alpha_stats, Mapping) or not isinstance(sky_metrics, Mapping):
            continue
        checked_views += 1

        alpha_mean = float_or_none(alpha_stats.get("mean"))
        alpha_coverage = float_or_none(alpha_stats.get("coverage_gt_005"))
        luminance = float_or_none(sky_metrics.get("luminance"))
        blue_dominance = float_or_none(sky_metrics.get("blue_dominance"))
        saturation = float_or_none(sky_metrics.get("saturation"))
        has_opaque_foreground = (
            (alpha_mean is not None and alpha_mean >= args.max_horizon_foreground_alpha_mean)
            or (
                alpha_coverage is not None
                and alpha_coverage >= args.max_horizon_foreground_alpha_coverage
            )
        )
        has_sky_like_foreground = (
            luminance is not None
            and luminance >= args.min_horizon_foreground_luminance
            and (
                (blue_dominance is not None and blue_dominance >= args.min_horizon_foreground_blue_dominance)
                or (saturation is not None and saturation >= args.min_horizon_foreground_saturation)
            )
        )
        if has_opaque_foreground and has_sky_like_foreground:
            saturated_views.append(
                {
                    "bucket": "horizon",
                    "image_name": str(view.get("image_name") or ""),
                    "alpha_mean": alpha_mean,
                    "alpha_coverage_gt_005": alpha_coverage,
                    "foreground_sky_luminance": luminance,
                    "foreground_sky_blue_dominance": blue_dominance,
                    "foreground_sky_saturation": saturation,
                }
            )

    return {
        "status": "passed" if not saturated_views else "blocked",
        "block_reasons": ["horizon_foreground_saturation"] if saturated_views else [],
        "checked_horizon_view_count": checked_views,
        "saturated_view_count": len(saturated_views),
        "saturated_views": saturated_views[:25],
        "thresholds": {
            "max_horizon_foreground_alpha_mean": args.max_horizon_foreground_alpha_mean,
            "max_horizon_foreground_alpha_coverage": args.max_horizon_foreground_alpha_coverage,
            "min_horizon_foreground_luminance": args.min_horizon_foreground_luminance,
            "min_horizon_foreground_blue_dominance": args.min_horizon_foreground_blue_dominance,
            "min_horizon_foreground_saturation": args.min_horizon_foreground_saturation,
        },
    }


def evaluate_review_readiness(quality_manifest: Mapping[str, Any] | None) -> dict[str, Any]:
    if not isinstance(quality_manifest, Mapping):
        return {
            "status": "blocked",
            "block_reasons": ["quality_review_manifest_missing"],
        }
    block_reasons: list[str] = []
    promotion = quality_manifest.get("promotion_readiness")
    if isinstance(promotion, Mapping) and promotion.get("status") == "blocked":
        block_reasons.append("quality_review_promotion_readiness_blocked")
    render_sanity = quality_manifest.get("render_sanity") or (
        promotion.get("render_sanity") if isinstance(promotion, Mapping) else {}
    )
    if isinstance(render_sanity, Mapping) and render_sanity.get("status") == "blocked":
        block_reasons.append("quality_review_render_sanity_blocked")
    if isinstance(promotion, Mapping):
        if int(promotion.get("retain_all_tile_count") or 0) > 0:
            block_reasons.append("quality_review_retain_all_tile_count_gt_zero")
        if int(promotion.get("fallback_tile_count") or 0) > 0:
            block_reasons.append("quality_review_fallback_tile_count_gt_zero")
        if promotion.get("review_buckets_complete") is False:
            block_reasons.append("quality_review_buckets_incomplete")
    return {
        "status": "passed" if not block_reasons else "blocked",
        "block_reasons": block_reasons,
        "promotion_readiness": dict(promotion or {}) if isinstance(promotion, Mapping) else {},
        "render_sanity": dict(render_sanity or {}) if isinstance(render_sanity, Mapping) else {},
    }


def evaluate_ai_review(ai_review: Mapping[str, Any] | None) -> dict[str, Any]:
    if ai_review is None:
        return {"status": "skipped", "block_reasons": []}
    defects = ai_review.get("blocking_defects", [])
    if not isinstance(defects, list):
        defects = []
    decision = str(
        ai_review.get("promotion_decision")
        or ai_review.get("decision")
        or ai_review.get("status")
        or ""
    ).strip().lower()
    block_reasons: list[str] = []
    if defects:
        block_reasons.append("ai_review_blocking_defects")
    if decision and decision not in {"pass", "passed", "promote", "promoted", "approve", "approved"}:
        block_reasons.append("ai_review_decision_not_passing")
    return {
        "status": "passed" if not block_reasons else "blocked",
        "block_reasons": block_reasons,
        "blocking_defects": defects[:25],
        "decision": decision,
    }


def build_report(args: argparse.Namespace) -> dict[str, Any]:
    visual_path = Path(args.visual_qa_manifest)
    visual_manifest = load_json(visual_path) or {}
    quality_path = Path(args.quality_review_manifest) if args.quality_review_manifest else quality_manifest_path_from_visual(
        visual_manifest,
        visual_path,
    )
    quality_manifest = load_json(quality_path) if quality_path else None
    baseline_manifest = load_json(args.baseline_review_manifest)
    ai_review = load_json(args.ai_review_json)

    views = views_from_manifests(visual_manifest, quality_manifest)
    asset_root = Path(args.asset_root) if args.asset_root else None
    asset_check = evaluate_assets(
        visual_manifest,
        asset_root=asset_root,
        require_local_assets=bool(args.require_local_assets),
    )
    readiness = evaluate_review_readiness(quality_manifest)
    absolute = evaluate_absolute_metrics(views, quality_manifest, args)
    horizon_foreground = evaluate_horizon_foreground_saturation(views, args)
    ai_decision = evaluate_ai_review(ai_review)

    baseline_decision = None
    if baseline_manifest is not None and quality_manifest is not None:
        baseline_decision = evaluate_v18_non_regression_decision(
            v18_manifest=baseline_manifest,
            candidate_manifest=quality_manifest,
        )

    block_reasons: list[str] = []
    for section in (asset_check, readiness, absolute, horizon_foreground, ai_decision, baseline_decision or {}):
        block_reasons.extend(section.get("block_reasons", []))

    report = {
        "version": "1.0.0",
        "status": "passed" if not block_reasons else "blocked",
        "block_reasons": unique(block_reasons),
        "inputs": {
            "visual_qa_manifest": str(visual_path),
            "quality_review_manifest": str(quality_path) if quality_path else None,
            "baseline_review_manifest": args.baseline_review_manifest,
            "ai_review_json": args.ai_review_json,
            "asset_root": str(asset_root) if asset_root else None,
        },
        "view_count": len(views),
        "panel_count": int(visual_manifest.get("panel_count") or 0),
        "bucket_counts": dict(visual_manifest.get("bucket_counts") or {}),
        "asset_check": asset_check,
        "review_readiness": readiness,
        "absolute_metric_gate": absolute,
        "horizon_foreground_gate": horizon_foreground,
        "ai_review_gate": ai_decision,
        "baseline_non_regression": baseline_decision,
    }
    return report


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--visual-qa-manifest", required=True, help="Path to visual_qa_manifest.json")
    parser.add_argument("--quality-review-manifest", help="Optional path to quality_review_manifest.json")
    parser.add_argument("--baseline-review-manifest", help="Optional V18/baseline quality_review_manifest.json")
    parser.add_argument("--asset-root", help="Root directory containing extracted visual QA assets")
    parser.add_argument(
        "--require-local-assets",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Require visual QA asset files to exist under --asset-root or absolute paths.",
    )
    parser.add_argument("--ai-review-json", help="Optional human/AI visual review verdict JSON")
    parser.add_argument("--output-json", help="Optional path to write the gate report")
    parser.add_argument("--min-median-psnr", type=float, default=18.0)
    parser.add_argument("--min-median-ssim", type=float, default=0.55)
    parser.add_argument("--max-median-lpips", type=float, default=0.55)
    parser.add_argument("--min-single-psnr", type=float, default=14.0)
    parser.add_argument("--min-single-ssim", type=float, default=0.45)
    parser.add_argument("--max-single-lpips", type=float, default=0.75)
    parser.add_argument("--max-mean-abs-rgb-error", type=float, default=0.22)
    parser.add_argument(
        "--max-horizon-foreground-alpha-mean",
        type=float,
        default=DEFAULT_MAX_HORIZON_FOREGROUND_ALPHA_MEAN,
    )
    parser.add_argument(
        "--max-horizon-foreground-alpha-coverage",
        type=float,
        default=DEFAULT_MAX_HORIZON_FOREGROUND_ALPHA_COVERAGE,
    )
    parser.add_argument(
        "--min-horizon-foreground-luminance",
        type=float,
        default=DEFAULT_MIN_HORIZON_FOREGROUND_LUMINANCE,
    )
    parser.add_argument(
        "--min-horizon-foreground-blue-dominance",
        type=float,
        default=DEFAULT_MIN_HORIZON_FOREGROUND_BLUE_DOMINANCE,
    )
    parser.add_argument(
        "--min-horizon-foreground-saturation",
        type=float,
        default=DEFAULT_MIN_HORIZON_FOREGROUND_SATURATION,
    )
    parser.add_argument(
        "--disable-horizon-foreground-gate",
        action="store_true",
        help="Skip the explicit horizon foreground opacity/sky-color blocker.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    report = build_report(args)
    output = json.dumps(report, indent=2, sort_keys=True)
    if args.output_json:
        output_path = Path(args.output_json)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(output + "\n", encoding="utf-8")
    print(output)
    return 0 if report["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
