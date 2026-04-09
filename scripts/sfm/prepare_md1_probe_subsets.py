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


def resolve_input_archive(input_path: str, workspace: Path) -> Path:
    if input_path.startswith("s3://"):
        local_path = workspace / Path(input_path).name
        run_command(["aws", "s3", "cp", input_path, str(local_path)])
        return local_path
    return Path(input_path).expanduser().resolve()


def upload_output_file(local_path: Path, output_path: str) -> None:
    if output_path.startswith("s3://"):
        run_command(["aws", "s3", "cp", str(local_path), output_path])
        return
    destination = Path(output_path).expanduser().resolve()
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(local_path, destination)


def extract_images(archive_path: Path, extract_dir: Path) -> List[Path]:
    extracted_paths: List[Path] = []
    seen_names: set[str] = set()
    with zipfile.ZipFile(archive_path, "r") as archive:
        for member in archive.namelist():
            if Path(member).suffix.lower() not in IMAGE_EXTENSIONS:
                continue
            file_name = Path(member).name
            if file_name in seen_names:
                raise ValueError(f"Archive contains duplicate image basename: {file_name}")
            seen_names.add(file_name)
            target_path = extract_dir / file_name
            with archive.open(member) as source, open(target_path, "wb") as target:
                shutil.copyfileobj(source, target)
            extracted_paths.append(target_path)
    if not extracted_paths:
        raise ValueError(f"No images found in archive: {archive_path}")
    return extracted_paths


def write_subset_archive(image_paths: List[Path], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for image_path in image_paths:
            archive.write(image_path, arcname=image_path.name)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, help="Local path or s3:// URI for the parent ZIP")
    parser.add_argument("--manifest-output", required=True, help="Local path or s3:// URI for the probe manifest JSON")
    parser.add_argument(
        "--subset-output-prefix",
        required=True,
        help="Directory path or s3:// prefix where probe subset ZIPs should be written",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    with tempfile.TemporaryDirectory(prefix="sfm_md1_probe_subsets_") as temp_dir:
        workspace = Path(temp_dir)
        archive_path = resolve_input_archive(args.input, workspace)
        extracted_dir = workspace / "images"
        extracted_dir.mkdir(parents=True, exist_ok=True)
        extract_images(archive_path, extracted_dir)

        previous_planner = os.environ.get("COLMAP_CHUNK_PLANNER")
        os.environ["COLMAP_CHUNK_PLANNER"] = "footprint_graph_v1"
        try:
            pipeline = run_colmap_sfm.ColmapPipeline(workspace / "input", workspace / "output")
        finally:
            if previous_planner is None:
                os.environ.pop("COLMAP_CHUNK_PLANNER", None)
            else:
                os.environ["COLMAP_CHUNK_PLANNER"] = previous_planner
        pipeline.images_dir = extracted_dir
        pipeline.exif_records = pipeline.load_exif_records()
        pipeline.gps_image_count = len(pipeline.exif_records)
        pipeline.prepare_capture_ordered_image_list()
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
            subset_paths = [
                extracted_dir / image_name
                for image_name in image_names
                if (extracted_dir / image_name).exists()
            ]
            subset_zip_path = workspace / f"{probe_name}.zip"
            write_subset_archive(subset_paths, subset_zip_path)
            destination = (
                args.subset_output_prefix.rstrip("/") + f"/{probe_name}.zip"
                if args.subset_output_prefix.startswith("s3://")
                else str(Path(args.subset_output_prefix).expanduser().resolve() / f"{probe_name}.zip")
            )
            upload_output_file(subset_zip_path, destination)

        print(json.dumps(manifest, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
