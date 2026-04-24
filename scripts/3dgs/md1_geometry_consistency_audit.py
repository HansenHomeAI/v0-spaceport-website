#!/usr/bin/env python3
"""Run the offline R0/R1 geometry-first audit for the md1 1k tiled artifact."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import tarfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping


REPO_ROOT = Path(__file__).resolve().parents[2]
THREE_DGS_ROOT = REPO_ROOT / "infrastructure" / "containers" / "3dgs"
if str(THREE_DGS_ROOT) not in sys.path:
    sys.path.insert(0, str(THREE_DGS_ROOT))

from geometry_review import (  # noqa: E402
    build_review_comparison,
    classify_root_cause,
    freeze_review_camera_manifest,
    inventory_extracted_model,
)
from tile_pipeline import load_json, merge_tile_outputs, rank_candidate_tile_pairs, rank_candidate_tile_triples  # noqa: E402


CANONICAL_MODEL_URI = (
    "s3://spaceport-ml-processing-staging/manual-validations/"
    "md1-1k-full-r2-1776194089/3dgs/T2_tiled_pipeline/"
    "md1-1k-full-r2-1776194089-tiled/output/model.tar.gz"
)
HISTORICAL_RECOVERED_MERGE = Path(
    "/Users/gabrielhansen/worktrees/agent-86580563-hierarchical-splat-merge-plan/"
    "logs/aws/md1-1k-full-r2/remerge-fixed/merged-fixed-2"
)


def run_command(command: list[str]) -> None:
    subprocess.run(command, check=True, text=True)


def ensure_model_tarball(model_uri: str, model_tarball: Path) -> None:
    if model_tarball.exists() and model_tarball.stat().st_size > 0:
        return
    model_tarball.parent.mkdir(parents=True, exist_ok=True)
    run_command(["aws", "s3", "cp", model_uri, str(model_tarball)])


def extract_model_tarball(model_tarball: Path, extracted_dir: Path) -> Path:
    marker = extracted_dir / ".extract_complete"
    if marker.exists():
        return extracted_dir
    if extracted_dir.exists():
        shutil.rmtree(extracted_dir)
    extracted_dir.mkdir(parents=True, exist_ok=True)
    with tarfile.open(model_tarball, "r:gz") as archive:
        for member in archive.getmembers():
            member_path = Path(member.name)
            if member_path.is_absolute() or ".." in member_path.parts or member.issym() or member.islnk():
                raise RuntimeError(f"Refusing unsafe tar member: {member.name}")
        archive.extractall(extracted_dir)
    marker.write_text(datetime.now(timezone.utc).isoformat(), encoding="utf-8")
    return extracted_dir


def load_inventory_manifests(inventory: Mapping[str, Any]) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    if not inventory.get("complete"):
        missing = [key for key, ok in inventory.get("required", {}).items() if not ok]
        raise RuntimeError(f"R0 inventory failed closed; missing required assets: {', '.join(missing)}")
    tile_manifest = load_json(str(inventory["tile_manifest"]))
    view_buckets = load_json(str(inventory["view_bucket_manifest"]))
    merge_report = load_json(str(inventory["merge_report"]))
    return tile_manifest, view_buckets, merge_report


def build_metric_unavailable_manifest(
    *,
    model_artifact: str,
    merge_report: Mapping[str, Any],
    camera_manifest_path: Path,
) -> dict[str, Any]:
    return {
        "version": "1.0.0",
        "model_artifact": model_artifact,
        "merge_report": dict(merge_report),
        "review_camera_manifest": str(camera_manifest_path),
        "bucket_medians": {
            "near_detail": {"psnr": None, "ssim": None, "lpips": None},
            "boundary": {"psnr": None, "ssim": None, "lpips": None},
            "horizon": {"psnr": None, "ssim": None, "lpips": None},
        },
        "sky_bucket_medians": {
            "near_detail": {"score": None},
            "boundary": {"score": None},
            "horizon": {"score": None},
        },
        "views": [],
        "promotion_readiness": {
            "status": "blocked",
            "notes": ["render metrics not produced by offline inventory audit"],
        },
    }


def choose_baseline_artifact(extracted_dir: Path) -> dict[str, Any]:
    recovered_report = HISTORICAL_RECOVERED_MERGE / "merge_report.json"
    recovered_splat = HISTORICAL_RECOVERED_MERGE / "merged_splat.ply"
    if recovered_report.exists() and recovered_splat.exists():
        return {
            "source": "historical_recovered_local_merge",
            "path": str(HISTORICAL_RECOVERED_MERGE),
            "merge_report": load_json(recovered_report),
        }
    merge_report = extracted_dir / "merged" / "merge_report.json"
    return {
        "source": "canonical_s3_tarball",
        "path": str(extracted_dir / "merged"),
        "merge_report": load_json(merge_report),
    }


def run_offline_merge_comparisons(
    *,
    tile_manifest: Mapping[str, Any],
    extracted_dir: Path,
    merge_root: Path,
) -> dict[str, Any]:
    tile_output_dirs = {
        str(tile["tile_id"]): extracted_dir / "tiles" / str(tile["tile_id"])
        for tile in tile_manifest.get("tiles", [])
    }
    reports: dict[str, Any] = {}
    for merge_mode in ("raw_union", "strict_core", "support_weighted_overlap"):
        output_dir = merge_root / merge_mode
        report = merge_tile_outputs(
            tile_manifest=tile_manifest,
            tile_output_dirs=tile_output_dirs,
            output_dir=output_dir,
            merge_mode=merge_mode,
        )
        reports[merge_mode] = {
            "report_path": str(output_dir / "merge_report.json"),
            "merged_ply": report.get("merged_ply"),
            "tile_count": report.get("tile_count"),
            "source_gaussians": report.get("source_gaussians"),
            "retained_gaussians": report.get("retained_gaussians"),
            "fallback_tile_count": report.get("fallback_tile_count"),
            "retain_all_tile_count": report.get("retain_all_tile_count"),
            "fallback_reasons": report.get("fallback_reasons", []),
        }
    strict_retained = float(reports["strict_core"].get("retained_gaussians") or 0.0)
    support_retained = float(reports["support_weighted_overlap"].get("retained_gaussians") or 0.0)
    return {
        "merge_root": str(merge_root),
        "reports": reports,
        "retained_delta_vs_strict_core": int(support_retained - strict_retained),
        "render_metrics_required": True,
        "promotion_note": (
            "R1 cannot promote on retention statistics alone; render LPIPS/SSIM/PSNR comparison "
            "must recover at least 50% of the strict_core boundary LPIPS gap."
        ),
    }


def write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model-uri", default=CANONICAL_MODEL_URI)
    parser.add_argument(
        "--audit-root",
        type=Path,
        default=REPO_ROOT / "logs" / "audit" / "md1-1k-full-r2",
    )
    parser.add_argument("--skip-download", action="store_true")
    parser.add_argument("--skip-offline-merges", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    audit_root: Path = args.audit_root
    model_dir = audit_root / "model"
    model_tarball = model_dir / "model.tar.gz"
    extracted_dir = model_dir / "extracted"
    if not args.skip_download:
        ensure_model_tarball(args.model_uri, model_tarball)
    extract_model_tarball(model_tarball, extracted_dir)

    inventory = inventory_extracted_model(extracted_dir)
    tile_manifest, view_buckets, merge_report = load_inventory_manifests(inventory)
    camera_manifest = freeze_review_camera_manifest(view_buckets, images_per_bucket=12, smoke_images_per_bucket=4)
    camera_manifest_path = audit_root / "review_camera_manifest.json"
    write_json(camera_manifest_path, camera_manifest)

    candidate_pairs = rank_candidate_tile_pairs(
        tile_manifest,
        view_buckets,
        merge_report=merge_report,
    )
    candidate_triples = rank_candidate_tile_triples(
        tile_manifest,
        view_buckets,
        merge_report=merge_report,
    )
    offline_merge_comparisons = None
    if not args.skip_offline_merges:
        offline_merge_comparisons = run_offline_merge_comparisons(
            tile_manifest=tile_manifest,
            extracted_dir=extracted_dir,
            merge_root=audit_root / "offline_merges",
        )
    baseline = choose_baseline_artifact(extracted_dir)
    candidate_artifact = args.model_uri
    candidate_merge_report = merge_report
    if offline_merge_comparisons:
        support_weighted_report_path = Path(
            offline_merge_comparisons["reports"]["support_weighted_overlap"]["report_path"]
        )
        if support_weighted_report_path.exists():
            candidate_artifact = str(support_weighted_report_path.parent)
            candidate_merge_report = load_json(support_weighted_report_path)
    candidate_manifest = build_metric_unavailable_manifest(
        model_artifact=candidate_artifact,
        merge_report=candidate_merge_report,
        camera_manifest_path=camera_manifest_path,
    )
    baseline_manifest = build_metric_unavailable_manifest(
        model_artifact=baseline["path"],
        merge_report=baseline["merge_report"],
        camera_manifest_path=camera_manifest_path,
    )
    comparison = build_review_comparison(
        baseline_manifest=baseline_manifest,
        candidate_manifest=candidate_manifest,
        baseline_artifact=baseline["path"],
        candidate_artifact=candidate_artifact,
        camera_manifest=camera_manifest,
    )
    classification_merge_report = (
        baseline["merge_report"]
        if int(baseline["merge_report"].get("fallback_tile_count", 0) or 0) > 0
        or int(baseline["merge_report"].get("retain_all_tile_count", 0) or 0) > 0
        else merge_report
    )
    root_cause = classify_root_cause(
        inventory=inventory,
        merge_report=classification_merge_report,
        candidate_pairs=candidate_pairs,
        review_comparison=comparison,
    )
    audit_manifest = {
        "version": "1.0.0",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "rung": "R0_artifact_first_diagnosis",
        "model_uri": args.model_uri,
        "model_tarball": str(model_tarball),
        "extracted_model_dir": str(extracted_dir),
        "inventory": inventory,
        "baseline_artifact": baseline,
        "frozen_review_camera_manifest": str(camera_manifest_path),
        "frozen_camera_sets": camera_manifest,
        "candidate_pairs": candidate_pairs,
        "candidate_triples": candidate_triples,
        "offline_merge_comparisons": offline_merge_comparisons,
        "baseline_metrics": baseline_manifest["bucket_medians"],
        "candidate_metrics": candidate_manifest["bucket_medians"],
        "root_cause_classification": root_cause,
        "next_unblocked_step": (
            "R1 offline merge arbitration: compare raw_union, strict_core, and "
            "support_weighted_overlap with render metrics before any new AWS training"
        ),
    }
    write_json(audit_root / "audit_manifest.json", audit_manifest)
    write_json(audit_root / "review_comparison.json", comparison)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
