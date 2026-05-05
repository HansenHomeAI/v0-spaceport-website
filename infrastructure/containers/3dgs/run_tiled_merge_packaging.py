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

from tile_pipeline import load_json, merge_tile_outputs


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
        metadata_candidates = [
            f"tiles/{tile_plan.get('tile_id')}/training_metadata.json",
            "training_metadata.json",
        ]
        selection_candidates = [
            f"tiles/{tile_plan.get('tile_id')}/training_selection.json",
            "training_selection.json",
        ]
        for member_name in metadata_candidates:
            if safe_extract_member(archive, member_name, output_tile_dir / "training_metadata.json"):
                break
        for member_name in selection_candidates:
            if safe_extract_member(archive, member_name, output_tile_dir / "training_selection.json"):
                break

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

    return {
        "tile_id": tile_plan.get("tile_id"),
        "artifact_uri": tile_plan.get("artifact_uri"),
        "artifact_input_name": tile_plan.get("artifact_input_name"),
        "selected_member": selected_member,
        "selected_size_bytes": selected_size,
        "tile_output_dir": str(output_tile_dir),
    }


def build_tarball(source_dir: Path, tarball_path: Path) -> None:
    if tarball_path.exists():
        tarball_path.unlink()
    with tarfile.open(tarball_path, "w:gz") as archive:
        for path in sorted(source_dir.rglob("*")):
            if path == tarball_path:
                continue
            archive.add(path, arcname=path.relative_to(source_dir))


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

    if work_root.exists():
        shutil.rmtree(work_root)
    if output_root.exists():
        shutil.rmtree(output_root)
    work_root.mkdir(parents=True, exist_ok=True)
    output_root.mkdir(parents=True, exist_ok=True)

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

    (output_root / "3dgs_tile_manifest.json").write_text(json.dumps(selected_manifest, indent=2), encoding="utf-8")
    if view_buckets:
        (output_root / "3dgs_view_buckets.json").write_text(json.dumps(view_buckets, indent=2), encoding="utf-8")
    merge_report = merge_tile_outputs(
        tile_manifest=selected_manifest,
        tile_output_dirs=extracted_tiles,
        output_dir=output_root / "merged",
        merge_mode=merge_mode,
    )
    summary = {
        "created_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "training_completed": True,
        "training_mode": "remote_no_training_tiled_merge",
        "merge_mode": merge_mode,
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
