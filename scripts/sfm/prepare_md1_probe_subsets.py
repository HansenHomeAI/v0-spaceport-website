#!/usr/bin/env python3
"""Build neutral MD1 probe subset ZIPs and a manifest from a parent image archive."""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path
from typing import Dict, List


REPO_ROOT = Path(__file__).resolve().parents[2]
COLMAP_MODULE_PATH = REPO_ROOT / "infrastructure" / "containers" / "sfm" / "run_colmap_sfm.py"
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png"}


def load_colmap_module():
    spec = importlib.util.spec_from_file_location("prepare_md1_probe_subsets_colmap_module", COLMAP_MODULE_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load COLMAP module from {COLMAP_MODULE_PATH}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


run_colmap_sfm = load_colmap_module()


def run_command(command: List[str]) -> None:
    subprocess.run(command, check=True)


def run_json_command(command: List[str]) -> list[dict]:
    result = subprocess.run(command, check=True, capture_output=True, text=True)
    return json.loads(result.stdout or "[]")


def resolve_input_archive(input_path: str, workspace: Path) -> Path:
    if input_path.startswith("s3://"):
        local_path = workspace / Path(input_path).name
        run_command(["aws", "s3", "cp", "--no-progress", input_path, str(local_path)])
        return local_path
    return Path(input_path).expanduser().resolve()


def upload_output_file(local_path: Path, output_path: str) -> None:
    if output_path.startswith("s3://"):
        run_command(["aws", "s3", "cp", str(local_path), output_path])
        return
    destination = Path(output_path).expanduser().resolve()
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(local_path, destination)


def write_subset_archive_from_members(
    archive_path: Path,
    member_by_file_name: Dict[str, str],
    image_names: List[str],
    output_path: Path,
) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(archive_path, "r") as source_archive, zipfile.ZipFile(
        output_path,
        "w",
        compression=zipfile.ZIP_DEFLATED,
    ) as output_archive:
        for image_name in image_names:
            member_name = member_by_file_name.get(image_name)
            if not member_name:
                raise ValueError(f"Missing archive member for probe image {image_name}")
            output_archive.writestr(image_name, source_archive.read(member_name))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, help="Local path or s3:// URI for the parent ZIP")
    parser.add_argument("--manifest-output", required=True, help="Local path or s3:// URI for the probe manifest JSON")
    parser.add_argument(
        "--subset-output-prefix",
        required=True,
        help="Directory path or s3:// prefix where probe subset ZIPs should be written",
    )
    parser.add_argument(
        "--exif-batch-size",
        type=int,
        default=500,
        help="Number of images to stage locally per EXIF scan batch",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    with tempfile.TemporaryDirectory(prefix="sfm_md1_probe_subsets_") as temp_dir:
        workspace = Path(temp_dir)
        archive_path = resolve_input_archive(args.input, workspace)
        exif_batch_dir = workspace / "exif_batch"
        exif_batch_dir.mkdir(parents=True, exist_ok=True)

        previous_planner = os.environ.get("COLMAP_CHUNK_PLANNER")
        os.environ["COLMAP_CHUNK_PLANNER"] = "footprint_graph_v1"
        try:
            pipeline = run_colmap_sfm.ColmapPipeline(workspace / "input", workspace / "output")
        finally:
            if previous_planner is None:
                os.environ.pop("COLMAP_CHUNK_PLANNER", None)
            else:
                os.environ["COLMAP_CHUNK_PLANNER"] = previous_planner
        pipeline.images_dir = exif_batch_dir

        all_exif_records: Dict[str, Dict[str, float | str | None]] = {}
        member_by_file_name: Dict[str, str] = {}
        batch_members: List[tuple[str, str]] = []
        with zipfile.ZipFile(archive_path, "r") as archive:
            for member in archive.namelist():
                if Path(member).suffix.lower() not in IMAGE_EXTENSIONS:
                    continue
                file_name = Path(member).name
                if file_name in member_by_file_name:
                    raise ValueError(f"Archive contains duplicate image basename: {file_name}")
                member_by_file_name[file_name] = member
                batch_members.append((file_name, member))
                if len(batch_members) >= max(args.exif_batch_size, 1):
                    for staged_name, staged_member in batch_members:
                        target_path = exif_batch_dir / staged_name
                        with archive.open(staged_member) as source, open(target_path, "wb") as target:
                            shutil.copyfileobj(source, target)
                    batch_records = pipeline.load_exif_records()
                    all_exif_records.update(batch_records)
                    for staged_name, _ in batch_members:
                        (exif_batch_dir / staged_name).unlink(missing_ok=True)
                    batch_members = []
            if batch_members:
                for staged_name, staged_member in batch_members:
                    target_path = exif_batch_dir / staged_name
                    with archive.open(staged_member) as source, open(target_path, "wb") as target:
                        shutil.copyfileobj(source, target)
                batch_records = pipeline.load_exif_records()
                all_exif_records.update(batch_records)
                for staged_name, _ in batch_members:
                    (exif_batch_dir / staged_name).unlink(missing_ok=True)

        if not all_exif_records:
            raise ValueError(f"No geotagged images found in archive: {archive_path}")

        pipeline.apply_orientation_prior_sources(all_exif_records)
        pipeline.populate_local_coordinates(all_exif_records)
        pipeline.exif_records = all_exif_records
        pipeline.gps_image_count = len(pipeline.exif_records)
        pipeline.capture_ordered_names = [
            record["file_name"]
            for record in run_colmap_sfm.sort_capture_records(
                [
                    {
                        "file_name": str(record["file_name"]),
                        "capture_time": str(record.get("capture_time") or ""),
                    }
                    for record in pipeline.exif_records.values()
                ]
            )
        ]
        chunk_plans = pipeline.build_chunk_plans()

        manifest = {
            "input": args.input,
            "planner": pipeline.chunk_planner,
            "chunk_matcher_strategy": pipeline.chunk_matcher_strategy,
            "chunk_count": len(chunk_plans),
            "chunk_sizes": pipeline.chunk_sizes,
            "probe_subsets": {
                probe_name: {
                    "image_count": len(image_names),
                    "images": image_names,
                    "details": pipeline.probe_subset_details.get(probe_name, {}),
                }
                for probe_name, image_names in pipeline.probe_subsets.items()
            },
            "colmap_capabilities": pipeline.colmap_capabilities,
            "role_counts": pipeline.chunk_graph_probe_manifest.get("role_counts", {}),
        }

        local_manifest_path = workspace / "probe_manifest.json"
        local_manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
        upload_output_file(local_manifest_path, args.manifest_output)

        for probe_name, image_names in pipeline.probe_subsets.items():
            subset_zip_path = workspace / f"{probe_name}.zip"
            write_subset_archive_from_members(archive_path, member_by_file_name, image_names, subset_zip_path)
            destination = (
                args.subset_output_prefix.rstrip("/") + f"/{probe_name}.zip"
                if args.subset_output_prefix.startswith("s3://")
                else str(Path(args.subset_output_prefix).expanduser().resolve() / f"{probe_name}.zip")
            )
            upload_output_file(subset_zip_path, destination)
            subset_zip_path.unlink(missing_ok=True)

        print(json.dumps(manifest, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
