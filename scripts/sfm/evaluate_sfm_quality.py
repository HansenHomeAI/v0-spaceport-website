#!/usr/bin/env python3
"""Build a deterministic SfM quality report from COLMAP/viewer artifacts."""

from __future__ import annotations

import argparse
import json
import math
import statistics
from pathlib import Path
from typing import Any, Iterable


def load_json(path: str | None) -> dict[str, Any]:
    if not path:
        return {}
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def arg_value(args: argparse.Namespace, name: str, default: Any) -> Any:
    return getattr(args, name, default)


def quantile(values: list[float], q: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    index = min(max(math.ceil(q * len(ordered)) - 1, 0), len(ordered) - 1)
    return round(ordered[index], 4)


def summarize(values: Iterable[float]) -> dict[str, float | int | None]:
    numbers = [float(value) for value in values if value is not None and math.isfinite(float(value))]
    if not numbers:
        return {"count": 0, "min": None, "p10": None, "median": None, "p90": None, "p95": None, "p99": None, "max": None}
    return {
        "count": len(numbers),
        "min": round(min(numbers), 4),
        "p10": quantile(numbers, 0.10),
        "median": round(statistics.median(numbers), 4),
        "p90": quantile(numbers, 0.90),
        "p95": quantile(numbers, 0.95),
        "p99": quantile(numbers, 0.99),
        "max": round(max(numbers), 4),
    }


def parse_points3d(points_path: Path) -> dict[str, Any]:
    errors: list[float] = []
    track_lengths: list[int] = []
    coords: list[tuple[float, float, float]] = []
    if not points_path.exists():
        return {}
    with points_path.open("r", encoding="utf-8", errors="replace") as handle:
        for line in handle:
            if not line.strip() or line.startswith("#"):
                continue
            parts = line.split()
            if len(parts) < 8:
                continue
            coords.append((float(parts[1]), float(parts[2]), float(parts[3])))
            errors.append(float(parts[7]))
            track_lengths.append(max((len(parts) - 8) // 2, 0))
    return {
        "source": str(points_path),
        "exact_point_count": len(errors),
        "reprojection_error": summarize(errors),
        "track_length": summarize(track_lengths),
        "low_track_ratio": round(sum(1 for length in track_lengths if length <= 2) / len(track_lengths), 4)
        if track_lengths
        else None,
        "high_error_ratio": round(sum(1 for error in errors if error > 10.0) / len(errors), 4)
        if errors
        else None,
        "bounds": bounds(coords),
    }


def parse_images(images_path: Path) -> dict[str, Any]:
    registered = 0
    names: list[str] = []
    if not images_path.exists():
        return {}
    with images_path.open("r", encoding="utf-8", errors="replace") as handle:
        expect_points_line = False
        for line in handle:
            if not line.strip() or line.startswith("#"):
                continue
            if expect_points_line:
                expect_points_line = False
                continue
            parts = line.split()
            if len(parts) >= 10:
                registered += 1
                names.append(parts[9])
                expect_points_line = True
    return {"source": str(images_path), "registered_image_count": registered, "sample_names": names[:8]}


def bounds(coords: list[tuple[float, float, float]]) -> dict[str, Any]:
    if not coords:
        return {}
    axes = list(zip(*coords))
    return {
        axis: {
            "min": round(min(values), 4),
            "max": round(max(values), 4),
            "span": round(max(values) - min(values), 4),
        }
        for axis, values in zip(("x", "y", "z"), axes)
    }


def viewer_stats(payload: dict[str, Any]) -> dict[str, Any]:
    if not payload:
        return {}
    cameras = payload.get("cameras") or []
    positions = payload.get("positions") or []
    point_coords = [
        (float(positions[index]), float(positions[index + 1]), float(positions[index + 2]))
        for index in range(0, max(len(positions) - 2, 0), 3)
    ]
    up_y = [float((camera.get("up") or [0, 0, 0])[1]) for camera in cameras if camera.get("up")]
    step_lengths: list[float] = []
    ordered_cameras = sorted(cameras, key=lambda camera: int(camera.get("imageId") or 0))
    for left, right in zip(ordered_cameras, ordered_cameras[1:]):
        left_pos = left.get("position") or []
        right_pos = right.get("position") or []
        if len(left_pos) == 3 and len(right_pos) == 3:
            step_lengths.append(
                math.sqrt(sum((float(a) - float(b)) ** 2 for a, b in zip(left_pos, right_pos)))
            )
    errors = payload.get("pointErrors") or []
    tracks = payload.get("pointTrackLengths") or []
    return {
        "source_registered_images": payload.get("registeredImageCount"),
        "exact_point_count": payload.get("exactPointCount"),
        "sampled_point_count": payload.get("sampledPointCount"),
        "chunk_count": payload.get("chunkCount"),
        "sample_bounds": bounds(point_coords),
        "sample_reprojection_error": summarize(errors),
        "sample_track_length": summarize(tracks),
        "sample_low_track_ratio": round(sum(1 for length in tracks if int(length) <= 2) / len(tracks), 4)
        if tracks
        else None,
        "sample_high_error_ratio": round(sum(1 for error in errors if float(error) > 10.0) / len(errors), 4)
        if errors
        else None,
        "camera_up_y": summarize(up_y),
        "camera_step_length": summarize(step_lengths),
    }


def metric_at(payload: dict[str, Any], metric: str, stat: str) -> float | None:
    metrics = payload.get("metrics") if isinstance(payload.get("metrics"), dict) else payload
    if not isinstance(metrics, dict):
        return None
    metric_payload = metrics.get(metric)
    if isinstance(metric_payload, dict):
        value = metric_payload.get(stat)
    else:
        value = metrics.get(f"{metric}_{stat}") or metrics.get(metric)
    if value is None:
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def render_metric_stats(payload: dict[str, Any]) -> dict[str, Any]:
    if not payload:
        return {}

    baseline = payload.get("baseline_metrics") or payload.get("baseline") or {}
    holdout_count = int(payload.get("holdout_count") or payload.get("validation_images") or payload.get("sample_count") or 0)
    successful_count = int(payload.get("successful_render_count") or payload.get("successful_count") or 0)
    if not successful_count and payload.get("final_validation_psnr") is not None:
        successful_count = holdout_count

    psnr_median = metric_at(payload, "psnr", "median")
    if psnr_median is None and payload.get("final_validation_psnr") is not None:
        psnr_median = float(payload["final_validation_psnr"])
    stats = {
        "artifact_kind": payload.get("artifact_kind"),
        "decision": payload.get("decision"),
        "holdout_count": holdout_count,
        "successful_render_count": successful_count,
        "success_ratio": round(successful_count / holdout_count, 4) if holdout_count else None,
        "psnr_median": psnr_median,
        "psnr_p10": metric_at(payload, "psnr", "p10"),
        "ssim_median": metric_at(payload, "ssim", "median"),
        "ssim_p10": metric_at(payload, "ssim", "p10"),
        "lpips_median": metric_at(payload, "lpips", "median"),
        "lpips_p90": metric_at(payload, "lpips", "p90"),
        "blockers": payload.get("blockers") or payload.get("promotion_blockers") or [],
        "proof_panels": payload.get("proof_panels") or payload.get("proof_panel_manifest"),
    }
    stats["baseline"] = {
        "psnr_median": metric_at(baseline, "psnr", "median"),
        "ssim_median": metric_at(baseline, "ssim", "median"),
        "lpips_median": metric_at(baseline, "lpips", "median"),
    }
    return stats


def visual_review_stats(payload: dict[str, Any]) -> dict[str, Any]:
    if not payload:
        return {}
    findings = payload.get("findings") or []
    blocking_from_findings = sum(
        1 for finding in findings if str(finding.get("severity", "")).lower() in {"blocker", "critical", "fail"}
    )
    warning_from_findings = sum(
        1 for finding in findings if str(finding.get("severity", "")).lower() in {"warning", "warn"}
    )
    panel_count = int(payload.get("panel_count") or len(payload.get("panels") or []) or 0)
    reviewed_count = int(payload.get("reviewed_panel_count") or payload.get("reviewed_count") or panel_count)
    blocking_count = int(payload.get("blocking_defect_count") or blocking_from_findings)
    warning_count = int(payload.get("warning_defect_count") or warning_from_findings)
    return {
        "artifact_kind": payload.get("artifact_kind"),
        "decision": payload.get("decision"),
        "panel_count": panel_count,
        "reviewed_panel_count": reviewed_count,
        "blocking_defect_count": blocking_count,
        "warning_defect_count": warning_count,
        "findings": findings[:20],
        "proof_panel_manifest": payload.get("proof_panel_manifest"),
    }


def merge_stats(sfm_metadata: dict[str, Any], reducer_metadata: dict[str, Any]) -> dict[str, Any]:
    if reducer_metadata.get("artifact_kind") in {"sfm_reducer_canary_report", "sfm_fanout_reducer_report"}:
        transforms = (reducer_metadata.get("fallback") or {}).get("transforms") or []
        shared_counts = [int(item.get("shared_registered_images") or 0) for item in transforms]
        leaf_count = int(reducer_metadata.get("leaf_count") or 0)
        passed = reducer_metadata.get("decision") == "pass"
        blockers = reducer_metadata.get("promotion_blockers") or reducer_metadata.get("blockers") or []
        return {
            "leaf_count": leaf_count,
            "passed_leaf_count": reducer_metadata.get("passed_leaf_count", leaf_count if passed else 0),
            "failed_leaf_count": reducer_metadata.get("failed_leaf_count", 0 if passed else leaf_count),
            "merged_component_count": reducer_metadata.get("merged_component_count", 1 if passed else 0),
            "expected_component_count": reducer_metadata.get("expected_component_count", 1),
            "promotion_blockers": blockers,
            "pre_merge_retention_ratio": min(reducer_metadata.get("leaf_retention_ratios") or [0.0]),
            "final_merged_registered_images": reducer_metadata.get("merged_registered_images"),
            "merge_node_count": len(transforms),
            "shared_registered_images": summarize(shared_counts),
            "cross_edge_count": summarize([]),
            "weak_merge_nodes": [
                {
                    "sequence": item.get("leaf_index"),
                    "shared_registered_image_count": item.get("shared_registered_images"),
                    "cross_edge_count": None,
                    "left_stage": "anchor_leaf",
                    "right_stage": f"leaf_{item.get('leaf_index')}",
                }
                for item in transforms
                if int(item.get("shared_registered_images") or 0) < 10
            ],
        }
    proof = sfm_metadata.get("chunk_merge_proof") or {}
    nodes = proof.get("merge_nodes") or []
    shared_counts = [int(node.get("shared_registered_image_count") or 0) for node in nodes]
    cross_edges = [int(node.get("cross_edge_count") or 0) for node in nodes]
    return {
        "leaf_count": reducer_metadata.get("leaf_count"),
        "passed_leaf_count": reducer_metadata.get("passed_leaf_count"),
        "failed_leaf_count": reducer_metadata.get("failed_leaf_count"),
        "merged_component_count": reducer_metadata.get("merged_component_count"),
        "expected_component_count": reducer_metadata.get("expected_component_count"),
        "promotion_blockers": reducer_metadata.get("promotion_blockers") or [],
        "pre_merge_retention_ratio": proof.get("pre_merge_retention_ratio"),
        "final_merged_registered_images": proof.get("final_merged_registered_images"),
        "merge_node_count": len(nodes),
        "shared_registered_images": summarize(shared_counts),
        "cross_edge_count": summarize(cross_edges),
        "weak_merge_nodes": [
            {
                "sequence": node.get("sequence"),
                "shared_registered_image_count": node.get("shared_registered_image_count"),
                "cross_edge_count": node.get("cross_edge_count"),
                "left_stage": node.get("left_stage"),
                "right_stage": node.get("right_stage"),
            }
            for node in nodes
            if int(node.get("shared_registered_image_count") or 0) < 10
        ],
    }


def add_gate(gates: list[dict[str, Any]], name: str, status: str, evidence: str) -> None:
    gates.append({"gate": name, "status": status, "evidence": evidence})


def add_heldout_render_gate(gates: list[dict[str, Any]], stats: dict[str, Any], args: argparse.Namespace) -> None:
    if not stats:
        add_gate(
            gates,
            "heldout_render_metrics",
            "not_run",
            "requires downstream splat renders from held-out source cameras",
        )
        return

    failures: list[str] = []
    blockers = stats.get("blockers") or []
    if blockers:
        failures.append(f"blockers={blockers}")
    if str(stats.get("decision") or "").lower() in {"fail", "do_not_promote"}:
        failures.append(f"decision={stats.get('decision')}")

    holdout_count = int(stats.get("holdout_count") or 0)
    success_ratio = stats.get("success_ratio")
    if holdout_count < arg_value(args, "min_heldout_render_count", 8):
        failures.append(f"holdout_count={holdout_count}")
    if success_ratio is None or float(success_ratio) < arg_value(args, "min_heldout_success_ratio", 0.95):
        failures.append(f"success_ratio={success_ratio}")

    required_metrics = ("psnr_median", "ssim_median", "lpips_median")
    missing = [name for name in required_metrics if stats.get(name) is None]
    if missing:
        failures.append(f"missing_metrics={missing}")
    if stats.get("psnr_median") is not None and float(stats["psnr_median"]) < arg_value(args, "min_heldout_psnr_median", 22.0):
        failures.append(f"psnr_median={stats['psnr_median']}")
    if stats.get("ssim_median") is not None and float(stats["ssim_median"]) < arg_value(args, "min_heldout_ssim_median", 0.70):
        failures.append(f"ssim_median={stats['ssim_median']}")
    if stats.get("lpips_median") is not None and float(stats["lpips_median"]) > arg_value(args, "max_heldout_lpips_median", 0.35):
        failures.append(f"lpips_median={stats['lpips_median']}")

    baseline = stats.get("baseline") or {}
    if baseline.get("psnr_median") is not None and stats.get("psnr_median") is not None:
        delta = float(stats["psnr_median"]) - float(baseline["psnr_median"])
        if delta < -arg_value(args, "max_psnr_regression", 1.0):
            failures.append(f"psnr_regression={round(delta, 4)}")
    if baseline.get("ssim_median") is not None and stats.get("ssim_median") is not None:
        delta = float(stats["ssim_median"]) - float(baseline["ssim_median"])
        if delta < -arg_value(args, "max_ssim_regression", 0.03):
            failures.append(f"ssim_regression={round(delta, 4)}")
    if baseline.get("lpips_median") is not None and stats.get("lpips_median") is not None:
        delta = float(stats["lpips_median"]) - float(baseline["lpips_median"])
        if delta > arg_value(args, "max_lpips_regression", 0.03):
            failures.append(f"lpips_regression={round(delta, 4)}")

    add_gate(
        gates,
        "heldout_render_metrics",
        "fail" if failures else "pass",
        "render_metrics="
        + json.dumps(
            {
                "holdout_count": holdout_count,
                "success_ratio": success_ratio,
                "psnr_median": stats.get("psnr_median"),
                "ssim_median": stats.get("ssim_median"),
                "lpips_median": stats.get("lpips_median"),
                "failures": failures,
            },
            sort_keys=True,
        ),
    )


def add_ai_visual_gate(gates: list[dict[str, Any]], stats: dict[str, Any], args: argparse.Namespace) -> None:
    if not stats:
        add_gate(
            gates,
            "ai_visual_review",
            "not_run",
            "requires fixed side-by-side render proof panels",
        )
        return

    panel_count = int(stats.get("panel_count") or 0)
    reviewed_count = int(stats.get("reviewed_panel_count") or 0)
    blockers = int(stats.get("blocking_defect_count") or 0)
    warnings = int(stats.get("warning_defect_count") or 0)
    failures: list[str] = []
    if panel_count < arg_value(args, "min_visual_review_panels", 6):
        failures.append(f"panel_count={panel_count}")
    if reviewed_count < panel_count:
        failures.append(f"reviewed_panel_count={reviewed_count}")
    if blockers:
        failures.append(f"blocking_defect_count={blockers}")
    if str(stats.get("decision") or "").lower() in {"fail", "do_not_promote"}:
        failures.append(f"decision={stats.get('decision')}")

    status = "fail" if failures else "warning" if warnings else "pass"
    add_gate(
        gates,
        "ai_visual_review",
        status,
        f"panels={panel_count}, reviewed={reviewed_count}, blocking={blockers}, warnings={warnings}, failures={failures}",
    )


def build_report(args: argparse.Namespace) -> dict[str, Any]:
    sfm_metadata = load_json(args.sfm_metadata)
    reducer_metadata = load_json(args.reducer_metadata)
    viewer_payload = load_json(args.viewer_api_json)
    heldout_render_payload = load_json(arg_value(args, "heldout_render_json", ""))
    ai_visual_payload = load_json(arg_value(args, "ai_visual_review_json", ""))
    sparse_dir = Path(args.sparse_dir) if args.sparse_dir else None

    sparse_images = parse_images(sparse_dir / "images.txt") if sparse_dir else {}
    sparse_points = parse_points3d(sparse_dir / "points3D.txt") if sparse_dir else {}
    viewer = viewer_stats(viewer_payload)
    merge = merge_stats(sfm_metadata, reducer_metadata)
    heldout_render = render_metric_stats(heldout_render_payload)
    ai_visual_review = visual_review_stats(ai_visual_payload)

    registered = (
        sparse_images.get("registered_image_count")
        or viewer.get("source_registered_images")
        or sfm_metadata.get("images_registered")
    )
    points = (
        sparse_points.get("exact_point_count")
        or viewer.get("exact_point_count")
        or sfm_metadata.get("points_3d")
    )
    total = args.expected_images or sfm_metadata.get("dataset_image_count") or registered
    registered_ratio = float(registered or 0) / float(total or 1)

    gates: list[dict[str, Any]] = []
    add_gate(
        gates,
        "registration_coverage",
        "pass" if registered_ratio >= args.min_registered_ratio else "fail",
        f"{registered}/{total} registered ({registered_ratio:.4f})",
    )
    add_gate(
        gates,
        "point_count",
        "pass" if int(points or 0) >= args.min_points else "fail",
        f"{points} points, minimum {args.min_points}",
    )
    blockers = merge.get("promotion_blockers") or []
    add_gate(
        gates,
        "reducer_blockers",
        "pass" if not blockers else "fail",
        f"promotion_blockers={blockers}",
    )
    add_gate(
        gates,
        "single_component",
        "pass" if merge.get("merged_component_count") == merge.get("expected_component_count") == 1 else "fail",
        f"merged={merge.get('merged_component_count')} expected={merge.get('expected_component_count')}",
    )
    retention = merge.get("pre_merge_retention_ratio")
    add_gate(
        gates,
        "merge_retention",
        "pass" if retention is None or float(retention) >= 0.98 else "fail",
        f"pre_merge_retention_ratio={retention}",
    )
    weak_nodes = merge.get("weak_merge_nodes") or []
    add_gate(
        gates,
        "seam_overlap",
        "warning" if weak_nodes else "pass",
        f"{len(weak_nodes)} merge nodes have <10 shared registered images",
    )
    error_p95 = (
        (sparse_points.get("reprojection_error") or {}).get("p95")
        or (viewer.get("sample_reprojection_error") or {}).get("p95")
    )
    add_gate(
        gates,
        "reprojection_error_sample",
        "pass" if error_p95 is not None and float(error_p95) <= arg_value(args, "max_reprojection_error_p95", 8.0) else "warning",
        f"p95={error_p95}, max={arg_value(args, 'max_reprojection_error_p95', 8.0)}",
    )
    up_y_median = (viewer.get("camera_up_y") or {}).get("median")
    add_gate(
        gates,
        "viewer_axis_sanity",
        "pass" if up_y_median is None or float(up_y_median) > 0.0 else "fail",
        f"median camera up.y={up_y_median}",
    )
    add_heldout_render_gate(gates, heldout_render, args)
    add_ai_visual_gate(gates, ai_visual_review, args)

    statuses = {gate["status"] for gate in gates}
    decision = "do_not_promote" if "fail" in statuses else "needs_more_proof" if statuses & {"warning", "not_run"} else "promote"
    next_required_gates = [
        "render held-out images from the splat and compute PSNR/SSIM/LPIPS",
        "generate fixed proof panels and run AI visual defect review",
    ]
    if reducer_metadata.get("artifact_kind") != "sfm_fanout_reducer_report" or blockers:
        next_required_gates.append("prove reducer ingest from independent leaf prefixes before full fanout")
    return {
        "schema_version": 1,
        "artifact_kind": "sfm_quality_report",
        "decision": decision,
        "inputs": {
            "sparse_dir": args.sparse_dir,
            "viewer_api_json": args.viewer_api_json,
            "sfm_metadata": args.sfm_metadata,
            "reducer_metadata": args.reducer_metadata,
            "heldout_render_json": arg_value(args, "heldout_render_json", ""),
            "ai_visual_review_json": arg_value(args, "ai_visual_review_json", ""),
        },
        "summary": {
            "registered_images": registered,
            "expected_images": total,
            "registered_ratio": round(registered_ratio, 4),
            "points": points,
        },
        "gates": gates,
        "sparse_images": sparse_images,
        "sparse_points": sparse_points,
        "viewer": viewer,
        "merge": merge,
        "heldout_render": heldout_render,
        "ai_visual_review": ai_visual_review,
        "next_required_gates": next_required_gates,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sparse-dir", default="")
    parser.add_argument("--viewer-api-json", default="")
    parser.add_argument("--sfm-metadata", default="")
    parser.add_argument("--reducer-metadata", default="")
    parser.add_argument("--heldout-render-json", default="")
    parser.add_argument("--ai-visual-review-json", default="")
    parser.add_argument("--expected-images", type=int, default=0)
    parser.add_argument("--min-registered-ratio", type=float, default=0.98)
    parser.add_argument("--min-points", type=int, default=1000)
    parser.add_argument("--max-reprojection-error-p95", type=float, default=8.0)
    parser.add_argument("--min-heldout-render-count", type=int, default=8)
    parser.add_argument("--min-heldout-success-ratio", type=float, default=0.95)
    parser.add_argument("--min-heldout-psnr-median", type=float, default=22.0)
    parser.add_argument("--min-heldout-ssim-median", type=float, default=0.70)
    parser.add_argument("--max-heldout-lpips-median", type=float, default=0.35)
    parser.add_argument("--max-psnr-regression", type=float, default=1.0)
    parser.add_argument("--max-ssim-regression", type=float, default=0.03)
    parser.add_argument("--max-lpips-regression", type=float, default=0.03)
    parser.add_argument("--min-visual-review-panels", type=int, default=6)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    report = build_report(args)
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as handle:
        json.dump(report, handle, indent=2)
        handle.write("\n")
    print(json.dumps({"decision": report["decision"], "output": str(output_path)}, indent=2))
    return 1 if report["decision"] == "do_not_promote" else 0


if __name__ == "__main__":
    raise SystemExit(main())
