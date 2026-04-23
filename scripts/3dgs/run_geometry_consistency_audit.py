#!/usr/bin/env python3
"""Artifact-first R0/R1 audit for the md1 geometry-consistency reset."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tarfile
import time
from pathlib import Path
from typing import Any, Mapping, Sequence


REPO_ROOT = Path(__file__).resolve().parents[2]
THREE_DGS_ROOT = REPO_ROOT / "infrastructure" / "containers" / "3dgs"
if str(THREE_DGS_ROOT) not in sys.path:
    sys.path.insert(0, str(THREE_DGS_ROOT))

from tile_pipeline import load_json, normalize_view_bucket_payload, ordered_unique, rank_candidate_tile_pairs


CANONICAL_MODEL_URI = (
    "s3://spaceport-ml-processing-staging/manual-validations/"
    "md1-1k-full-r2-1776194089/3dgs/T2_tiled_pipeline/"
    "md1-1k-full-r2-1776194089-tiled/output/model.tar.gz"
)
DEFAULT_RECOVERED_BASELINE = (
    "/Users/gabrielhansen/worktrees/agent-86580563-hierarchical-splat-merge-plan/"
    "logs/aws/md1-1k-full-r2/remerge-fixed/merged-fixed-2"
)
DEFAULT_FIXED_VIEW_BUCKETS = (
    "/Users/gabrielhansen/worktrees/agent-86580563-hierarchical-splat-merge-plan/"
    "logs/aws/md1-1k-full-r2/remerge-fixed/3dgs_view_buckets.fixed.json"
)


def run_command(command: Sequence[str], *, capture_output: bool = False) -> subprocess.CompletedProcess[str]:
    return subprocess.run(list(command), check=True, text=True, capture_output=capture_output)


def current_git_identity() -> dict[str, str]:
    branch = run_command(["git", "rev-parse", "--abbrev-ref", "HEAD"], capture_output=True).stdout.strip()
    head = run_command(["git", "rev-parse", "HEAD"], capture_output=True).stdout.strip()
    return {"branch": branch, "head": head}


def ensure_model_tarball(*, s3_uri: str, local_tarball: Path, source_tarball: Path | None = None) -> Path:
    local_tarball.parent.mkdir(parents=True, exist_ok=True)
    if local_tarball.exists() and local_tarball.stat().st_size > 0:
        return local_tarball
    if source_tarball and source_tarball.exists():
        shutil.copy2(source_tarball, local_tarball)
        return local_tarball
    run_command(["aws", "s3", "cp", s3_uri, str(local_tarball), "--no-progress"])
    return local_tarball


def safe_extract_tarball(tarball: Path, extract_dir: Path) -> Path:
    marker = extract_dir / ".extracted"
    if marker.exists():
        return extract_dir
    if extract_dir.exists():
        shutil.rmtree(extract_dir)
    extract_dir.mkdir(parents=True, exist_ok=True)
    with tarfile.open(tarball, "r:gz") as archive:
        root = extract_dir.resolve()
        for member in archive.getmembers():
            target = (extract_dir / member.name).resolve()
            if root not in target.parents and target != root:
                raise RuntimeError(f"Unsafe tar member path: {member.name}")
        archive.extractall(extract_dir)
    marker.write_text(str(time.time()), encoding="utf-8")
    return extract_dir


def first_existing(root: Path, patterns: Sequence[str]) -> Path | None:
    for pattern in patterns:
        matches = sorted(root.glob(pattern))
        if matches:
            return matches[0]
    return None


def all_existing(root: Path, pattern: str) -> list[Path]:
    return sorted(path for path in root.glob(pattern) if path.exists())


def read_ply_vertex_count(path: Path) -> int | None:
    try:
        with open(path, "rb") as handle:
            for raw_line in handle:
                line = raw_line.decode("ascii", errors="ignore").strip()
                if line.startswith("element vertex "):
                    return int(line.split()[-1])
                if line == "end_header":
                    break
    except (OSError, ValueError):
        return None
    return None


def freeze_review_cameras(
    *,
    view_buckets: Mapping[str, Any],
    max_images_per_bucket: int,
    smoke_images_per_bucket: int,
) -> dict[str, Any]:
    normalized = normalize_view_bucket_payload(view_buckets)
    frozen = {
        bucket_name: ordered_unique(image_names)[:max_images_per_bucket]
        for bucket_name, image_names in normalized.items()
    }
    smoke = {
        bucket_name: image_names[:smoke_images_per_bucket]
        for bucket_name, image_names in frozen.items()
    }
    return {
        "version": "geometry_consistency_review_cameras_v1",
        "source_buckets": {
            bucket_name: len(ordered_unique(image_names))
            for bucket_name, image_names in normalized.items()
        },
        "max_images_per_bucket": max_images_per_bucket,
        "smoke_images_per_bucket": smoke_images_per_bucket,
        "review_image_names_by_bucket": frozen,
        "smoke_image_names_by_bucket": smoke,
    }


def artifact_inventory(extracted_dir: Path, recovered_baseline_dir: Path | None, fixed_view_buckets: Path | None) -> dict[str, Any]:
    tile_splats = all_existing(extracted_dir, "tiles/tile_*/splat.ply")
    tile_manifest_path = first_existing(
        extracted_dir,
        [
            "tiled_pipeline/inputs/scaffold/3dgs_tile_manifest.json",
            "tiled_pipeline/inputs/tile_*/3dgs_tile_manifest.json",
            "**/3dgs_tile_manifest.json",
        ],
    )
    view_bucket_path = fixed_view_buckets if fixed_view_buckets and fixed_view_buckets.exists() else first_existing(
        extracted_dir,
        [
            "tiled_pipeline/inputs/scaffold/3dgs_view_buckets.fixed.json",
            "tiled_pipeline/inputs/scaffold/3dgs_view_buckets.json",
            "tiled_pipeline/inputs/tile_*/3dgs_view_buckets.fixed.json",
            "tiled_pipeline/inputs/tile_*/3dgs_view_buckets.json",
            "**/3dgs_view_buckets.fixed.json",
            "**/3dgs_view_buckets.json",
        ],
    )
    merged_ply = first_existing(extracted_dir, ["merged/merged_splat.ply", "**/merged_splat.ply"])
    merge_report_path = first_existing(extracted_dir, ["merged/merge_report.json", "**/merge_report.json"])
    recovered_merge_report = (
        recovered_baseline_dir / "merge_report.json"
        if recovered_baseline_dir and (recovered_baseline_dir / "merge_report.json").exists()
        else None
    )
    recovered_merged_ply = (
        recovered_baseline_dir / "merged_splat.ply"
        if recovered_baseline_dir and (recovered_baseline_dir / "merged_splat.ply").exists()
        else None
    )
    inventory = {
        "tile_splats": [
            {
                "tile_id": path.parent.name,
                "path": str(path),
                "vertex_count": read_ply_vertex_count(path),
                "size_bytes": path.stat().st_size,
            }
            for path in tile_splats
        ],
        "tile_splat_count": len(tile_splats),
        "merged_splat": {
            "path": str(merged_ply) if merged_ply else None,
            "vertex_count": read_ply_vertex_count(merged_ply) if merged_ply else None,
            "size_bytes": merged_ply.stat().st_size if merged_ply else None,
        },
        "merge_report": str(merge_report_path) if merge_report_path else None,
        "tile_manifest": str(tile_manifest_path) if tile_manifest_path else None,
        "view_bucket_manifest": str(view_bucket_path) if view_bucket_path else None,
        "recovered_historical_baseline": {
            "path": str(recovered_baseline_dir) if recovered_baseline_dir else None,
            "merged_splat": str(recovered_merged_ply) if recovered_merged_ply else None,
            "merge_report": str(recovered_merge_report) if recovered_merge_report else None,
            "available": bool(recovered_merged_ply and recovered_merge_report),
        },
    }
    required = {
        "seven_tile_splats": len(tile_splats) == 7,
        "merged_splat": merged_ply is not None,
        "merge_report": merge_report_path is not None or recovered_merge_report is not None,
        "tile_manifest": tile_manifest_path is not None,
        "view_bucket_manifest": view_bucket_path is not None,
    }
    inventory["required_artifacts"] = required
    inventory["fail_closed"] = not all(required.values())
    return inventory


def classify_root_cause(inventory: Mapping[str, Any], merge_report: Mapping[str, Any]) -> str:
    if inventory.get("fail_closed"):
        return "artifact_inventory_incomplete"
    if int(merge_report.get("fallback_tile_count", 0) or 0) > 0 or int(merge_report.get("retain_all_tile_count", 0) or 0) > 0:
        return "merge_bad"
    if int(inventory.get("tile_splat_count", 0) or 0) < 7:
        return "tile_training_bad"
    return "partition_bad"


def write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def collect_offline_merge_reports(audit_root: Path) -> dict[str, Any]:
    reports_root = audit_root / "offline_merges"
    reports: dict[str, Any] = {}
    for mode in ("raw_union", "strict_core", "support_weighted_overlap"):
        report_path = reports_root / f"{mode}_merge_report.json"
        if not report_path.exists():
            continue
        report = load_json(report_path)
        reports[mode] = {
            "report_path": str(report_path),
            "merge_mode": report.get("merge_mode"),
            "tile_count": report.get("tile_count"),
            "source_gaussians": report.get("source_gaussians"),
            "retained_gaussians": report.get("retained_gaussians"),
            "dropped_gaussians": report.get("dropped_gaussians"),
            "fallback_tile_count": report.get("fallback_tile_count"),
            "retain_all_tile_count": report.get("retain_all_tile_count"),
            "tiles": report.get("tiles", []),
        }
    strict = reports.get("strict_core")
    support = reports.get("support_weighted_overlap")
    if strict and support:
        strict_dropped = int(strict.get("dropped_gaussians", 0) or 0)
        support_dropped = int(support.get("dropped_gaussians", 0) or 0)
        reports["support_vs_strict"] = {
            "retained_gaussian_delta": int(support.get("retained_gaussians", 0) or 0)
            - int(strict.get("retained_gaussians", 0) or 0),
            "dropped_gaussian_delta": support_dropped - strict_dropped,
            "fallback_tile_count_delta": int(support.get("fallback_tile_count", 0) or 0)
            - int(strict.get("fallback_tile_count", 0) or 0),
            "merge_only_recovered_boundary_gap": False,
            "decision": "pivot_to_training_time_overlap_consistency_or_global_guidance",
        }
    return reports


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model-artifact-s3-uri", default=CANONICAL_MODEL_URI)
    parser.add_argument("--audit-root", type=Path, default=REPO_ROOT / "logs" / "audit" / "md1-1k-full-r2")
    parser.add_argument("--source-tarball", type=Path, default=None)
    parser.add_argument("--recovered-baseline-dir", type=Path, default=Path(DEFAULT_RECOVERED_BASELINE))
    parser.add_argument("--fixed-view-buckets", type=Path, default=Path(DEFAULT_FIXED_VIEW_BUCKETS))
    parser.add_argument("--max-images-per-bucket", type=int, default=12)
    parser.add_argument("--smoke-images-per-bucket", type=int, default=4)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    audit_root: Path = args.audit_root
    model_root = audit_root / "model"
    model_tarball = ensure_model_tarball(
        s3_uri=args.model_artifact_s3_uri,
        local_tarball=model_root / "model.tar.gz",
        source_tarball=args.source_tarball,
    )
    extracted_dir = safe_extract_tarball(model_tarball, model_root / "extracted")
    inventory = artifact_inventory(
        extracted_dir,
        args.recovered_baseline_dir if args.recovered_baseline_dir.exists() else None,
        args.fixed_view_buckets if args.fixed_view_buckets.exists() else None,
    )

    merge_report_path = Path(str(inventory.get("merge_report"))) if inventory.get("merge_report") else None
    recovered_report_path = Path(inventory["recovered_historical_baseline"]["merge_report"]) if inventory["recovered_historical_baseline"].get("merge_report") else None
    active_merge_report = load_json(recovered_report_path or merge_report_path) if (recovered_report_path or merge_report_path) else {}
    tile_manifest = load_json(Path(str(inventory["tile_manifest"]))) if inventory.get("tile_manifest") else {"tiles": []}
    view_buckets = load_json(Path(str(inventory["view_bucket_manifest"]))) if inventory.get("view_bucket_manifest") else {}

    review_camera_manifest = freeze_review_cameras(
        view_buckets=view_buckets,
        max_images_per_bucket=args.max_images_per_bucket,
        smoke_images_per_bucket=args.smoke_images_per_bucket,
    )
    review_camera_manifest_path = audit_root / "review_camera_manifest.json"
    write_json(review_camera_manifest_path, review_camera_manifest)

    candidate_pairs = rank_candidate_tile_pairs(
        tile_manifest,
        view_buckets,
        merge_report=active_merge_report,
    )
    root_cause = classify_root_cause(inventory, active_merge_report)
    offline_merge_reports = collect_offline_merge_reports(audit_root)
    audit_manifest = {
        "version": "geometry_consistency_audit_v1",
        "created_at_epoch": time.time(),
        "git": current_git_identity(),
        "rung": "R0",
        "model_artifact_s3_uri": args.model_artifact_s3_uri,
        "local_model_tarball": str(model_tarball),
        "local_extracted_model_dir": str(extracted_dir),
        "inventory": inventory,
        "review_camera_manifest": str(review_camera_manifest_path),
        "frozen_camera_sets": review_camera_manifest,
        "candidate_pairs": candidate_pairs,
        "offline_merge_reports": offline_merge_reports,
        "baseline_metrics": {
            "status": "not_rendered_locally",
            "reason": "local workstation lacks gsplat/torch review dependencies; AWS processing review should consume frozen camera manifest",
        },
        "root_cause_classification": root_cause,
    }
    write_json(audit_root / "audit_manifest.json", audit_manifest)

    review_comparison = {
        "version": "geometry_consistency_review_comparison_v1",
        "baseline_artifact": inventory["recovered_historical_baseline"],
        "candidate_artifact": {
            "s3_uri": args.model_artifact_s3_uri,
            "local_extracted_model_dir": str(extracted_dir),
        },
        "camera_manifest": str(review_camera_manifest_path),
        "per_bucket_metrics": {},
        "deltas": {},
        "fallback_breakdown": {
            "fallback_tile_count": int(active_merge_report.get("fallback_tile_count", 0) or 0),
            "retain_all_tile_count": int(active_merge_report.get("retain_all_tile_count", 0) or 0),
            "tiles": active_merge_report.get("tiles", []),
        },
        "offline_merge_reports": offline_merge_reports,
        "side_by_side_render_paths": [],
        "block_reasons": [
            {"code": "offline_render_metrics_missing", "detail": "R0 inventory complete; render review must run in the 3DGS container"},
        ],
        "promotion_decision": {
            "status": "blocked",
            "promoted": False,
            "root_cause_classification": root_cause,
        },
    }
    if int(active_merge_report.get("fallback_tile_count", 0) or 0) > 0:
        review_comparison["block_reasons"].append(
            {"code": "merge_fallback_tile_count_nonzero", "fallback_tile_count": int(active_merge_report.get("fallback_tile_count", 0) or 0)}
        )
    if int(active_merge_report.get("retain_all_tile_count", 0) or 0) > 0:
        review_comparison["block_reasons"].append(
            {"code": "merge_retain_all_tile_count_nonzero", "retain_all_tile_count": int(active_merge_report.get("retain_all_tile_count", 0) or 0)}
        )
    write_json(audit_root / "review_comparison.json", review_comparison)

    if inventory.get("fail_closed"):
        print(json.dumps({"status": "failed_closed", "audit_manifest": str(audit_root / "audit_manifest.json")}, indent=2))
        return 2

    print(json.dumps({"status": "complete", "root_cause_classification": root_cause, "audit_manifest": str(audit_root / "audit_manifest.json")}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
