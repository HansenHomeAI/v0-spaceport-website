#!/usr/bin/env python3
"""Stream-check a tiled 3DGS model artifact without extracting large PLY files."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tarfile
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator
from urllib.parse import urlparse


def parse_s3_uri(uri: str) -> tuple[str, str]:
    parsed = urlparse(uri)
    if parsed.scheme != "s3" or not parsed.netloc or not parsed.path.lstrip("/"):
        raise ValueError(f"Expected s3://bucket/key URI, got: {uri}")
    return parsed.netloc, parsed.path.lstrip("/")


def run_json(args: list[str]) -> dict:
    result = subprocess.run(args, check=True, text=True, capture_output=True)
    return json.loads(result.stdout)


def artifact_head(artifact_uri: str) -> dict:
    if artifact_uri.startswith("s3://"):
        bucket, key = parse_s3_uri(artifact_uri)
        return run_json(["aws", "s3api", "head-object", "--bucket", bucket, "--key", key])
    path = Path(artifact_uri)
    stat = path.stat()
    return {
        "ContentLength": stat.st_size,
        "LastModified": datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat(),
        "ETag": None,
    }


@contextmanager
def artifact_stream(artifact_uri: str) -> Iterator[object]:
    if artifact_uri.startswith("s3://"):
        process = subprocess.Popen(["aws", "s3", "cp", artifact_uri, "-"], stdout=subprocess.PIPE)
        if process.stdout is None:
            raise RuntimeError("aws s3 cp did not expose stdout")
        try:
            yield process.stdout
        finally:
            process.stdout.close()
            return_code = process.wait()
            if return_code != 0:
                raise RuntimeError(f"aws s3 cp failed for {artifact_uri} with exit code {return_code}")
        return

    with open(artifact_uri, "rb") as handle:
        yield handle


def safe_output_path(output_dir: Path, member_name: str) -> Path:
    relative = Path(member_name)
    if relative.is_absolute() or ".." in relative.parts:
        raise ValueError(f"Unsafe tar member path: {member_name}")
    return output_dir / relative


def required_paths(tile_ids: list[str]) -> list[str]:
    required = [
        "merged/merge_report.json",
        "merged/merged_splat.ply",
        "tiled_pipeline_summary.json",
        "training_metadata.json",
    ]
    for tile_id in tile_ids:
        required.extend(
            [
                f"tiles/{tile_id}/splat.ply",
                f"tiles/{tile_id}/export_manifest.json",
                f"tiles/{tile_id}/stage_summary.json",
                f"tiles/{tile_id}/training_metadata.json",
                f"tiles/{tile_id}/training_selection.json",
                f"tiled_pipeline/inputs/{tile_id}/3dgs_tile_manifest.json",
                f"tiled_pipeline/inputs/{tile_id}/3dgs_view_buckets.json",
                f"tiled_pipeline/inputs/{tile_id}/scaffold_init_metadata.json",
            ]
        )
    return required


def should_extract(member_name: str) -> bool:
    return member_name.endswith(".json")


def load_json_if_present(path: Path) -> dict:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def stream_inventory(artifact_uri: str, output_dir: Path, tile_ids: list[str]) -> dict:
    output_dir.mkdir(parents=True, exist_ok=True)
    required = set(required_paths(tile_ids))
    inventory: list[str] = []
    sizes: dict[str, int] = {}
    extracted: list[str] = []

    with artifact_stream(artifact_uri) as handle:
        with tarfile.open(fileobj=handle, mode="r|gz") as archive:
            for member in archive:
                name = member.name
                if not member.isfile():
                    continue
                inventory.append(name)
                sizes[name] = int(member.size)
                if should_extract(name):
                    target = safe_output_path(output_dir, name)
                    target.parent.mkdir(parents=True, exist_ok=True)
                    source = archive.extractfile(member)
                    if source is None:
                        continue
                    with source, open(target, "wb") as destination:
                        while True:
                            chunk = source.read(1024 * 1024)
                            if not chunk:
                                break
                            destination.write(chunk)
                    extracted.append(name)

    filtered = [
        name
        for name in inventory
        if name in required
        or name.endswith(".json")
        or name.endswith(".ply")
        or name.endswith(".webp")
    ]
    (output_dir / "artifact_inventory_filtered.txt").write_text(
        "\n".join(sorted(filtered)) + "\n",
        encoding="utf-8",
    )
    present = sorted(required.intersection(inventory))
    missing = sorted(required.difference(inventory))
    return {
        "inventory_count": len(inventory),
        "artifact_inventory_filtered_path": "artifact_inventory_filtered.txt",
        "artifact_required_paths": {"present": present, "missing": missing},
        "sizes": sizes,
        "extracted_json_members": sorted(extracted),
    }


def tile_summary(output_dir: Path, tile_id: str, sizes: dict[str, int], merge_report: dict) -> dict:
    metadata = load_json_if_present(output_dir / "tiles" / tile_id / "training_metadata.json")
    selection = load_json_if_present(output_dir / "tiles" / tile_id / "training_selection.json")
    stage = load_json_if_present(output_dir / "tiles" / tile_id / "stage_summary.json")
    export = load_json_if_present(output_dir / "tiles" / tile_id / "export_manifest.json")
    scaffold = load_json_if_present(output_dir / "tiled_pipeline" / "inputs" / tile_id / "scaffold_init_metadata.json")
    tile_reports = merge_report.get("tile_reports") or merge_report.get("tiles") or {}
    merge_tile = tile_reports.get(tile_id, {}) if isinstance(tile_reports, dict) else {}
    return {
        "file_size_mb": sizes.get(f"tiles/{tile_id}/splat.ply", 0) / (1024 * 1024),
        "training_completed": metadata.get("training_completed"),
        "training_mode": metadata.get("training_mode") or selection.get("training_mode"),
        "model_variant": metadata.get("model_variant") or selection.get("model_variant"),
        "max_iterations": metadata.get("max_iterations") or selection.get("max_iterations"),
        "sh_degree": metadata.get("sh_degree") or selection.get("sh_degree"),
        "selected_image_count": selection.get("selected_image_count"),
        "view_bucket_counts": selection.get("view_bucket_counts"),
        "stage_elapsed_seconds": stage.get("stage_elapsed_seconds"),
        "remaining_gaussians": stage.get("remaining_gaussians"),
        "foreground_coordinate_frame": export.get("foreground_coordinate_frame"),
        "planner_transform_applied": export.get("planner_transform_applied"),
        "scaffold_source_artifact": scaffold.get("scaffold_source_artifact"),
        "scaffold_inheritance_mode": scaffold.get("scaffold_inheritance_mode"),
        "inherited_gaussian_count": scaffold.get("inherited_gaussian_count"),
        "merge_fallback_used": merge_tile.get("fallback_used"),
        "merge_fallback_reason": merge_tile.get("fallback_reason"),
        "merge_retained_gaussians": merge_tile.get("retained_gaussians"),
        "merge_dropped_gaussians": merge_tile.get("dropped_gaussians"),
    }


def build_summary(
    *,
    artifact_uri: str,
    output_dir: Path,
    tile_ids: list[str],
    rung: str,
    candidate_label: str,
    job_name: str,
) -> dict:
    head = artifact_head(artifact_uri)
    inventory = stream_inventory(artifact_uri, output_dir, tile_ids)
    merge_report = load_json_if_present(output_dir / "merged" / "merge_report.json")
    pipeline = load_json_if_present(output_dir / "tiled_pipeline_summary.json")
    training_metadata = load_json_if_present(output_dir / "training_metadata.json")

    fallback_tile_count = int(merge_report.get("fallback_tile_count", 0) or 0)
    retain_all_tile_count = int(merge_report.get("retain_all_tile_count", 0) or 0)
    block_reasons = []
    if inventory["artifact_required_paths"]["missing"]:
        block_reasons.append("artifact_required_paths_missing")
    if fallback_tile_count > 0:
        block_reasons.append("merge_fallback_tile_count_gt_zero")
    if retain_all_tile_count > 0:
        block_reasons.append("merge_retain_all_tile_count_gt_zero")

    decision = "preflight_passed_run_frozen_smoke_review" if not block_reasons else "preflight_blocked"
    return {
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "rung": rung,
        "candidate_label": candidate_label,
        "job_name": job_name,
        "artifact_s3_uri": artifact_uri if artifact_uri.startswith("s3://") else None,
        "artifact_uri": artifact_uri,
        "artifact_head_object": head,
        "artifact_complete": not inventory["artifact_required_paths"]["missing"],
        "artifact_inventory_filtered_path": inventory["artifact_inventory_filtered_path"],
        "artifact_required_paths": inventory["artifact_required_paths"],
        "block_reasons": block_reasons,
        "decision": decision,
        "next_unblocked_step": (
            "run frozen-camera smoke review against the R1 strict_core baseline before any R5 spend"
            if decision == "preflight_passed_run_frozen_smoke_review"
            else "fix artifact completeness or merge fallback before review/promotion"
        ),
        "merge": {
            "merge_mode": merge_report.get("merge_mode"),
            "tile_count": merge_report.get("tile_count"),
            "source_gaussians": merge_report.get("source_gaussians"),
            "retained_gaussians": merge_report.get("retained_gaussians"),
            "dropped_gaussians": merge_report.get("dropped_gaussians"),
            "fallback_tile_count": fallback_tile_count,
            "retain_all_tile_count": retain_all_tile_count,
            "fallback_reasons": merge_report.get("fallback_reasons") or [],
            "background_asset": merge_report.get("background_asset"),
        },
        "pipeline": {
            "mode": pipeline.get("mode"),
            "selected_tile_ids": pipeline.get("selected_tile_ids"),
            "include_scaffold": pipeline.get("include_scaffold"),
            "include_merge": pipeline.get("include_merge"),
            "tile_manifest_resolution": pipeline.get("tile_manifest_resolution"),
        },
        "root_training_metadata": {
            "training_completed": training_metadata.get("training_completed"),
            "training_mode": training_metadata.get("training_mode"),
            "model_variant": training_metadata.get("model_variant"),
            "max_iterations": training_metadata.get("max_iterations"),
            "downscale_factor": training_metadata.get("downscale_factor"),
            "enable_bg_model": training_metadata.get("enable_bg_model"),
            "sh_degree": training_metadata.get("sh_degree"),
        },
        "tiles": {
            tile_id: tile_summary(output_dir, tile_id, inventory["sizes"], merge_report)
            for tile_id in tile_ids
        },
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("--artifact-uri", required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--tile-ids", required=True, help="Comma-separated tile ids to require.")
    parser.add_argument("--rung", default="R4")
    parser.add_argument("--candidate-label", default="candidate")
    parser.add_argument("--job-name", default="")
    parser.add_argument("--summary-json-output", type=Path, default=None)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    tile_ids = [tile.strip() for tile in args.tile_ids.split(",") if tile.strip()]
    if not tile_ids:
        raise ValueError("--tile-ids must include at least one tile id")
    summary = build_summary(
        artifact_uri=args.artifact_uri,
        output_dir=args.output_dir,
        tile_ids=tile_ids,
        rung=args.rung,
        candidate_label=args.candidate_label,
        job_name=args.job_name,
    )
    output_path = args.summary_json_output or (args.output_dir / "preflight_summary.json")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0 if not summary["block_reasons"] else 2


if __name__ == "__main__":
    sys.exit(main())
