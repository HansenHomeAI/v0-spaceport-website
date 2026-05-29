#!/usr/bin/env python3
"""Package a no-training tiled 3DGS merge from mounted SageMaker Processing inputs."""

from __future__ import annotations

import json
import os
import shutil
import tarfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from tile_pipeline import bounds_available, load_json, merge_tile_outputs


TILE_SIDECAR_CANDIDATES = {
    "training_metadata.json": ("training_metadata.json",),
    "training_selection.json": ("training_selection.json",),
    "export_manifest.json": ("export_manifest.json",),
    "stage_summary.json": ("stage_summary.json",),
    "background_skybox.webp": ("background_skybox.webp",),
    "background_manifest.json": ("background_manifest.json",),
    "floater_pruning_summary.json": ("floater_pruning_summary.json",),
}

SIDECAR_BOUNDS_DISABLED_VALUES = {"", "0", "false", "no", "off"}
SIDECAR_BOUNDS_CORE_MODE = "scaffold_filter_as_core"
SIDECAR_BOUNDS_CORE_AND_OVERLAP_MODE = "scaffold_filter_as_core_and_overlap"
SUPPORTED_SIDECAR_BOUNDS_MODES = {
    SIDECAR_BOUNDS_CORE_MODE,
    SIDECAR_BOUNDS_CORE_AND_OVERLAP_MODE,
}


def safe_extract_member(archive: tarfile.TarFile, member_name: str, target_path: Path) -> bool:
    try:
        member = archive.getmember(member_name)
    except KeyError:
        return False
    if not member.isfile() or Path(member.name).is_absolute() or ".." in Path(member.name).parts:
        raise RuntimeError(f"Refusing unsafe artifact member: {member.name}")
    extracted = archive.extractfile(member)
    if extracted is None:
        return False
    target_path.parent.mkdir(parents=True, exist_ok=True)
    with extracted, open(target_path, "wb") as output:
        shutil.copyfileobj(extracted, output)
    return True


def find_tarball(input_dir: Path) -> Path:
    if input_dir.is_file() and input_dir.name.endswith(".tar.gz"):
        return input_dir
    candidates = sorted(path for path in input_dir.rglob("*.tar.gz") if path.is_file())
    if not candidates:
        raise FileNotFoundError(f"No .tar.gz artifact found under {input_dir}")
    return candidates[0]


def load_json_if_present(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return load_json(path)
    except (OSError, json.JSONDecodeError):
        return {}


def sidecar_scaffold_filter_bounds(tile_dir: Path) -> tuple[dict[str, float] | None, dict[str, Any]]:
    """Return resolved SfM-authority bounds recorded by the leaf, if trustworthy."""

    selection = load_json_if_present(tile_dir / "training_selection.json")
    scaffold = selection.get("scaffold_initialization")
    if not isinstance(scaffold, dict):
        return None, {"status": "not_available", "reason": "missing_scaffold_initialization"}

    bounds = scaffold.get("scaffold_filter_bounds")
    if not bounds_available(bounds):
        return None, {"status": "not_available", "reason": "missing_or_degenerate_scaffold_filter_bounds"}

    resolution = selection.get("tile_manifest_resolution")
    refresh = resolution.get("ownership_bounds_refresh") if isinstance(resolution, dict) else None
    refresh_status = str((refresh or {}).get("status", "")).strip().lower() if isinstance(refresh, dict) else ""
    if refresh_status != "refreshed":
        return None, {
            "status": "not_available",
            "reason": "tile_manifest_bounds_not_refreshed",
            "ownership_bounds_refresh": refresh or None,
        }

    return (
        {key: float(bounds[key]) for key in ("min_x", "max_x", "min_y", "max_y", "min_z", "max_z")},
        {
            "status": "available",
            "source": "training_selection.scaffold_initialization.scaffold_filter_bounds",
            "ownership_bounds_refresh": refresh,
            "source_filter_retention_ratio": scaffold.get("source_filter_retention_ratio"),
            "source_filtered_gaussian_count": scaffold.get("source_filtered_gaussian_count"),
            "source_gaussian_count": scaffold.get("source_gaussian_count"),
        },
    )


def apply_sidecar_merge_bounds(
    tile_manifest: dict[str, Any],
    tile_output_dirs: dict[str, Path],
    *,
    enabled: bool = True,
    mode: str = SIDECAR_BOUNDS_CORE_MODE,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Align merge ownership bounds with the bounds a leaf actually used for SfM-authority init."""

    normalized_mode = (mode or SIDECAR_BOUNDS_CORE_MODE).strip().lower()
    if normalized_mode not in SUPPORTED_SIDECAR_BOUNDS_MODES:
        raise ValueError(
            f"Unsupported MERGE_SIDECAR_BOUNDS_MODE={mode}; "
            f"expected one of {', '.join(sorted(SUPPORTED_SIDECAR_BOUNDS_MODES))}"
        )

    manifest = {**tile_manifest}
    updated_tiles: list[dict[str, Any]] = []
    tile_reports: list[dict[str, Any]] = []
    applied_count = 0

    for tile in tile_manifest.get("tiles", []):
        tile_entry = dict(tile)
        tile_id = str(tile_entry.get("tile_id", "")).strip()
        tile_dir = tile_output_dirs.get(tile_id)
        report: dict[str, Any] = {
            "tile_id": tile_id,
            "enabled": enabled,
            "applied": False,
            "mode": normalized_mode,
        }
        if enabled and tile_id and tile_dir is not None:
            sidecar_bounds, sidecar_report = sidecar_scaffold_filter_bounds(tile_dir)
            report.update(sidecar_report)
            if sidecar_bounds is not None:
                original_core_bounds = tile_entry.get("core_bounds")
                original_overlap_bounds = tile_entry.get("overlap_bounds")
                tile_entry["core_bounds"] = sidecar_bounds
                if normalized_mode == SIDECAR_BOUNDS_CORE_AND_OVERLAP_MODE:
                    tile_entry["overlap_bounds"] = sidecar_bounds
                strategies = (
                    dict(tile_entry.get("bounds_strategy", {}))
                    if isinstance(tile_entry.get("bounds_strategy"), dict)
                    else {}
                )
                strategies["core"] = "resolved_scaffold_filter_bounds"
                if normalized_mode == SIDECAR_BOUNDS_CORE_AND_OVERLAP_MODE:
                    strategies["overlap"] = "resolved_scaffold_filter_bounds"
                tile_entry["bounds_strategy"] = strategies
                tile_entry["ownership_bounds_available"] = True
                tile_entry["merge_sidecar_bounds"] = {
                    "source": report["source"],
                    "mode": normalized_mode,
                    "original_core_bounds": original_core_bounds,
                    "original_overlap_bounds": original_overlap_bounds,
                    "applied_core_bounds": sidecar_bounds,
                }
                report["applied"] = True
                report["applied_core_bounds"] = sidecar_bounds
                applied_count += 1
        elif not enabled:
            report["status"] = "disabled"
        else:
            report["status"] = "not_available"
            report["reason"] = "missing_tile_output_dir"

        updated_tiles.append(tile_entry)
        tile_reports.append(report)

    summary = {
        "enabled": enabled,
        "mode": normalized_mode,
        "applied_tile_count": applied_count,
        "tile_count": len(updated_tiles),
        "tiles": tile_reports,
    }
    manifest["tiles"] = updated_tiles
    manifest["merge_sidecar_bounds"] = summary
    return manifest, summary


def extract_tile_from_artifact(tile_plan: dict[str, Any], artifact_root: Path, output_tile_dir: Path) -> dict[str, Any]:
    tarball = find_tarball(artifact_root)
    member_candidates = [str(value) for value in tile_plan.get("candidate_members", []) if value]
    if not member_candidates:
        raise RuntimeError(f"Tile {tile_plan.get('tile_id')} has no candidate splat members")

    selected_member = ""
    selected_size = 0
    with tarfile.open(tarball, "r:gz") as archive:
        for member_name in member_candidates:
            if safe_extract_member(archive, member_name, output_tile_dir / "splat.ply"):
                selected_member = member_name
                selected_size = int((output_tile_dir / "splat.ply").stat().st_size)
                break
        if not selected_member:
            raise RuntimeError(
                f"Artifact {tarball} did not contain any candidate splat member for {tile_plan.get('tile_id')}: "
                f"{member_candidates}"
            )
        tile_id = str(tile_plan.get("tile_id"))
        for output_name, fallback_names in TILE_SIDECAR_CANDIDATES.items():
            for member_name in (f"tiles/{tile_id}/{output_name}", *fallback_names):
                if safe_extract_member(archive, member_name, output_tile_dir / output_name):
                    break
            else:
                continue

    if not (output_tile_dir / "training_metadata.json").exists():
        (output_tile_dir / "training_metadata.json").write_text(
            json.dumps(
                {
                    "training_mode": str(tile_plan.get("stage_type") or "cached_tile"),
                    "tile_id": tile_plan.get("tile_id"),
                    "source_artifact_uri": tile_plan.get("artifact_uri"),
                    "source_member": selected_member,
                },
                indent=2,
            ),
            encoding="utf-8",
        )
    if not (output_tile_dir / "training_selection.json").exists():
        (output_tile_dir / "training_selection.json").write_text(
            json.dumps(
                {
                    "training_mode": str(tile_plan.get("stage_type") or "cached_tile"),
                    "tile_id": tile_plan.get("tile_id"),
                    "source_artifact_uri": tile_plan.get("artifact_uri"),
                    "source_member": selected_member,
                },
                indent=2,
            ),
            encoding="utf-8",
        )
    if not (output_tile_dir / "export_manifest.json").exists():
        (output_tile_dir / "export_manifest.json").write_text(
            json.dumps(
                {
                    "tile_id": tile_plan.get("tile_id"),
                    "splat_ply": "splat.ply",
                    "source_artifact_uri": tile_plan.get("artifact_uri"),
                    "source_member": selected_member,
                    "foreground_coordinate_frame": "planner",
                    "planner_transform_applied": True,
                },
                indent=2,
            ),
            encoding="utf-8",
        )
    if not (output_tile_dir / "stage_summary.json").exists():
        (output_tile_dir / "stage_summary.json").write_text(
            json.dumps(
                {
                    "tile_id": tile_plan.get("tile_id"),
                    "stage_type": tile_plan.get("stage_type"),
                    "source_artifact_uri": tile_plan.get("artifact_uri"),
                    "source_member": selected_member,
                    "splat_size_bytes": selected_size,
                    "stage_elapsed_seconds": 0,
                },
                indent=2,
            ),
            encoding="utf-8",
        )

    return {
        "tile_id": tile_plan.get("tile_id"),
        "artifact_uri": tile_plan.get("artifact_uri"),
        "artifact_input_name": tile_plan.get("artifact_input_name"),
        "selected_member": selected_member,
        "selected_size_bytes": selected_size,
        "tile_output_dir": str(output_tile_dir),
    }


def tile_only_manifest(tile_manifest: dict[str, Any], tile_id: str) -> dict[str, Any]:
    return {
        **tile_manifest,
        "tiles": [tile for tile in tile_manifest.get("tiles", []) if str(tile.get("tile_id")) == tile_id],
    }


def write_required_tile_inputs(
    *, output_root: Path, tile_plan: dict[str, Any], tile_manifest: dict[str, Any], view_buckets: dict[str, Any]
) -> None:
    tile_id = str(tile_plan["tile_id"])
    tile_input_dir = output_root / "tiled_pipeline" / "inputs" / tile_id
    tile_input_dir.mkdir(parents=True, exist_ok=True)
    (tile_input_dir / "3dgs_tile_manifest.json").write_text(
        json.dumps(tile_only_manifest(tile_manifest, tile_id), indent=2),
        encoding="utf-8",
    )
    (tile_input_dir / "3dgs_view_buckets.json").write_text(
        json.dumps(view_buckets, indent=2),
        encoding="utf-8",
    )
    if isinstance(tile_manifest.get("sfm_seam_graph"), dict):
        (tile_input_dir / "3dgs_seam_graph.json").write_text(
            json.dumps(tile_manifest["sfm_seam_graph"], indent=2),
            encoding="utf-8",
        )
    (tile_input_dir / "scaffold_init_metadata.json").write_text(
        json.dumps(
            {
                "tile_id": tile_id,
                "scaffold_inheritance_mode": "remote_no_training_reuse",
                "scaffold_source_artifact": tile_plan.get("artifact_uri"),
                "source_member_candidates": tile_plan.get("candidate_members", []),
            },
            indent=2,
        ),
        encoding="utf-8",
    )


def build_tarball(source_dir: Path, tarball_path: Path) -> None:
    if tarball_path.exists():
        tarball_path.unlink()
    with tarfile.open(tarball_path, "w:gz") as archive:
        for path in sorted(source_dir.rglob("*")):
            if path == tarball_path:
                continue
            archive.add(path, arcname=path.relative_to(source_dir))


def reset_directory_contents(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)
    for child in path.iterdir():
        if child.is_dir() and not child.is_symlink():
            shutil.rmtree(child)
        else:
            child.unlink()


def parse_csv_values(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


def main() -> int:
    merge_plan_path = Path(os.environ.get("MERGE_PLAN_PATH", "/opt/ml/processing/input/merge-plan/merge_plan.json"))
    tile_manifest_path = Path(
        os.environ.get("TILE_MANIFEST_PATH", "/opt/ml/processing/input/tile-selection/3dgs_tile_manifest.json")
    )
    view_bucket_path = Path(
        os.environ.get("VIEW_BUCKET_MANIFEST_PATH", "/opt/ml/processing/input/tile-selection/3dgs_view_buckets.json")
    )
    output_root = Path(os.environ.get("OUTPUT_DIR", "/opt/ml/processing/output/artifact"))
    work_root = Path(os.environ.get("WORK_DIR", "/opt/ml/processing/tmp/tiled-merge"))
    merge_mode = os.environ.get("MERGE_MODE", "support_weighted_overlap")
    background_source_tile_id = os.environ.get("BACKGROUND_SOURCE_TILE_ID", "").strip()
    protected_overlap_tile_ids = parse_csv_values(os.environ.get("MERGE_PROTECTED_OVERLAP_TILE_IDS", ""))
    protected_overlap_mode = os.environ.get("MERGE_PROTECTED_OVERLAP_MODE", "").strip()

    if work_root.exists():
        shutil.rmtree(work_root)
    work_root.mkdir(parents=True, exist_ok=True)
    reset_directory_contents(output_root)

    merge_plan = load_json(merge_plan_path)
    tile_manifest = load_json(tile_manifest_path)
    view_buckets = load_json(view_bucket_path) if view_bucket_path.exists() else {}
    selected_tiles = {str(tile["tile_id"]) for tile in merge_plan.get("tiles", [])}
    selected_manifest = {
        **tile_manifest,
        "tiles": [tile for tile in tile_manifest.get("tiles", []) if str(tile.get("tile_id")) in selected_tiles],
    }

    tile_root = output_root / "tiles"
    extracted_tiles: dict[str, Path] = {}
    extraction_records = []
    for tile_plan in merge_plan.get("tiles", []):
        tile_id = str(tile_plan["tile_id"])
        artifact_input_name = str(tile_plan["artifact_input_name"])
        artifact_root = Path(f"/opt/ml/processing/input/artifacts/{artifact_input_name}")
        output_tile_dir = tile_root / tile_id
        record = extract_tile_from_artifact(tile_plan, artifact_root, output_tile_dir)
        extraction_records.append(record)
        extracted_tiles[tile_id] = output_tile_dir

    sidecar_bounds_enabled = os.environ.get("MERGE_APPLY_SIDECAR_BOUNDS", "true").strip().lower()
    selected_manifest, sidecar_bounds_summary = apply_sidecar_merge_bounds(
        selected_manifest,
        extracted_tiles,
        enabled=sidecar_bounds_enabled not in SIDECAR_BOUNDS_DISABLED_VALUES,
        mode=os.environ.get("MERGE_SIDECAR_BOUNDS_MODE", SIDECAR_BOUNDS_CORE_MODE),
    )

    for tile_plan in merge_plan.get("tiles", []):
        write_required_tile_inputs(
            output_root=output_root,
            tile_plan=tile_plan,
            tile_manifest=selected_manifest,
            view_buckets=view_buckets,
        )

    (output_root / "3dgs_tile_manifest.json").write_text(json.dumps(selected_manifest, indent=2), encoding="utf-8")
    if view_buckets:
        (output_root / "3dgs_view_buckets.json").write_text(json.dumps(view_buckets, indent=2), encoding="utf-8")
    if isinstance(selected_manifest.get("sfm_seam_graph"), dict):
        (output_root / "3dgs_seam_graph.json").write_text(
            json.dumps(selected_manifest["sfm_seam_graph"], indent=2),
            encoding="utf-8",
        )
    merge_report = merge_tile_outputs(
        tile_manifest=selected_manifest,
        tile_output_dirs=extracted_tiles,
        output_dir=output_root / "merged",
        merge_mode=merge_mode,
        background_source_tile_id=background_source_tile_id,
        protected_overlap_tile_ids=protected_overlap_tile_ids,
        protected_overlap_mode=protected_overlap_mode,
    )
    summary = {
        "created_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "training_completed": True,
        "training_mode": "remote_no_training_tiled_merge",
        "merge_mode": merge_mode,
        "background_source_tile_id": background_source_tile_id or None,
        "protected_overlap_tile_ids": protected_overlap_tile_ids,
        "protected_overlap_mode": protected_overlap_mode or None,
        "merge_sidecar_bounds": sidecar_bounds_summary,
        "merge_plan": merge_plan,
        "extracted_tiles": extraction_records,
        "merge_report": merge_report,
        "model_artifact": "model.tar.gz",
    }
    (output_root / "training_metadata.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    (output_root / "tiled_pipeline_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    (output_root / "remote_merge_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    build_tarball(output_root, output_root / "model.tar.gz")
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
