#!/usr/bin/env python3
"""Stream-check one leaf 3DGS training artifact without extracting large PLYs."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import tarfile
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator
from urllib.parse import urlparse


REQUIRED_LEAF_PATHS = (
    "splat.ply",
    "training_metadata.json",
    "training_selection.json",
    "export_manifest.json",
    "background_manifest.json",
    "background_skybox.webp",
    "floater_pruning_summary.json",
)


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


def stream_sha256(artifact_uri: str) -> str:
    digest = hashlib.sha256()
    with artifact_stream(artifact_uri) as handle:
        while True:
            chunk = handle.read(1024 * 1024)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def safe_output_path(output_dir: Path, member_name: str) -> Path:
    relative = Path(member_name)
    if relative.is_absolute() or ".." in relative.parts:
        raise ValueError(f"Unsafe tar member path: {member_name}")
    return output_dir / relative


def parse_ply_header(source: object) -> tuple[list[str], int | None]:
    header: list[str] = []
    vertex_count: int | None = None
    while True:
        raw_line = source.readline()
        if not raw_line:
            break
        line = raw_line.decode("utf-8", errors="replace").rstrip("\n")
        header.append(line)
        if line.startswith("element vertex "):
            try:
                vertex_count = int(line.split()[-1])
            except ValueError:
                vertex_count = None
        if line == "end_header":
            break
    return header, vertex_count


def load_json_if_present(output_dir: Path, member_name: str) -> dict:
    path = output_dir / member_name
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def stream_inventory(artifact_uri: str, output_dir: Path) -> dict:
    output_dir.mkdir(parents=True, exist_ok=True)
    inventory: list[dict[str, object]] = []
    present: set[str] = set()
    ply_header: list[str] = []
    splat_vertex_count: int | None = None
    splat_ply_size_bytes = 0

    with artifact_stream(artifact_uri) as handle:
        with tarfile.open(fileobj=handle, mode="r|gz") as archive:
            for member in archive:
                if not member.isfile():
                    continue
                inventory.append({"name": member.name, "size": int(member.size), "type": "file"})
                if member.name in REQUIRED_LEAF_PATHS:
                    present.add(member.name)
                source = archive.extractfile(member)
                if source is None:
                    continue
                if member.name.endswith(".json"):
                    target = safe_output_path(output_dir, member.name)
                    target.parent.mkdir(parents=True, exist_ok=True)
                    with source, open(target, "wb") as destination:
                        while True:
                            chunk = source.read(1024 * 1024)
                            if not chunk:
                                break
                            destination.write(chunk)
                elif member.name == "splat.ply":
                    splat_ply_size_bytes = int(member.size)
                    with source:
                        ply_header, splat_vertex_count = parse_ply_header(source)

    missing = [path for path in REQUIRED_LEAF_PATHS if path not in present]
    return {
        "inventory": inventory,
        "required_paths": {"present": sorted(present), "missing": missing},
        "splat_ply_size_bytes": splat_ply_size_bytes,
        "splat_ply_header": ply_header,
        "splat_vertex_count": splat_vertex_count,
    }


def build_summary(*, artifact_uri: str, output_dir: Path, tile_id: str, job_name: str) -> dict:
    head = artifact_head(artifact_uri)
    sha256 = stream_sha256(artifact_uri)
    inventory = stream_inventory(artifact_uri, output_dir)
    metadata = load_json_if_present(output_dir, "training_metadata.json")
    selection = load_json_if_present(output_dir, "training_selection.json")
    export = load_json_if_present(output_dir, "export_manifest.json")
    floater = load_json_if_present(output_dir, "floater_pruning_summary.json")
    background_manifest = load_json_if_present(output_dir, "background_manifest.json")

    block_reasons: list[str] = []
    if inventory["required_paths"]["missing"]:
        block_reasons.append("leaf_required_paths_missing")
    if metadata.get("training_completed") is not True:
        block_reasons.append("training_metadata_not_completed")
    if inventory.get("splat_vertex_count") is None:
        block_reasons.append("splat_vertex_count_missing")
    elif int(inventory["splat_vertex_count"]) <= 0:
        block_reasons.append("splat_vertex_count_zero")

    return {
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "artifact_uri": artifact_uri,
        "artifact_head_object": head,
        "local_size_bytes": head.get("ContentLength"),
        "sha256": sha256,
        "job_name": job_name,
        "tile_id": tile_id,
        "preflight_type": "leaf_tile_artifact",
        "inventory": inventory["inventory"],
        "required_paths": inventory["required_paths"],
        "training_metadata": {
            "training_completed": metadata.get("training_completed"),
            "training_mode": metadata.get("training_mode"),
            "model_variant": metadata.get("model_variant"),
            "max_iterations": metadata.get("max_iterations"),
            "sh_degree": metadata.get("sh_degree"),
            "downscale_factor": metadata.get("downscale_factor"),
            "enable_bg_model": metadata.get("enable_bg_model"),
            "enable_alpha_loss": metadata.get("enable_alpha_loss"),
            "enable_robust_mask": metadata.get("enable_robust_mask"),
        },
        "training_selection": {
            "tile_id": selection.get("tile_id"),
            "selected_image_count": selection.get("selected_image_count"),
            "max_selected_images": selection.get("max_selected_images"),
            "view_bucket_counts": selection.get("view_bucket_counts"),
            "scaffold_initialization": selection.get("scaffold_initialization"),
        },
        "export_manifest": {
            "ply": export.get("ply"),
            "planner_transform_applied": export.get("planner_transform_applied"),
            "foreground_coordinate_frame": export.get("foreground_coordinate_frame"),
        },
        "floater_pruning_summary": floater,
        "background_manifest_keys": sorted(background_manifest.keys()),
        "splat_ply_size_bytes": inventory["splat_ply_size_bytes"],
        "splat_ply_header": inventory["splat_ply_header"],
        "splat_vertex_count": inventory["splat_vertex_count"],
        "block_reasons": block_reasons,
        "decision": "leaf_preflight_passed_cache_candidate" if not block_reasons else "leaf_preflight_blocked",
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifact-uri", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--tile-id", required=True)
    parser.add_argument("--job-name", default="")
    parser.add_argument("--summary-json-output", required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    output_dir = Path(args.output_dir)
    summary = build_summary(
        artifact_uri=args.artifact_uri,
        output_dir=output_dir,
        tile_id=args.tile_id,
        job_name=args.job_name,
    )
    summary_path = Path(args.summary_json_output)
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))
    return 0 if not summary["block_reasons"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
