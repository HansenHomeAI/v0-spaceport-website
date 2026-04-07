#!/usr/bin/env python3
"""Build prior-aware chunk plans and optional chunk-focused subset ZIPs from a larger image archive."""

from __future__ import annotations

import argparse
import importlib.util
import json
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path
from typing import Iterable, List, Sequence


REPO_ROOT = Path(__file__).resolve().parents[2]
COLMAP_MODULE_PATH = REPO_ROOT / "infrastructure" / "containers" / "sfm" / "run_colmap_sfm.py"
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png"}


def load_colmap_module():
    spec = importlib.util.spec_from_file_location("prepare_prior_chunk_subset_colmap_module", COLMAP_MODULE_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load COLMAP module from {COLMAP_MODULE_PATH}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


run_colmap_sfm = load_colmap_module()


def run_command(command: Sequence[str]) -> None:
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
            suffix = Path(member).suffix.lower()
            if suffix not in IMAGE_EXTENSIONS:
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


def parse_chunk_indexes(values: Iterable[int]) -> List[int]:
    return sorted(set(int(value) for value in values))


def resolve_selected_chunk_plans(chunk_plans, selected_chunk_indexes: Sequence[int]):
    if not selected_chunk_indexes:
        return list(chunk_plans)
    selected = [chunk_plan for chunk_plan in chunk_plans if chunk_plan.index in set(selected_chunk_indexes)]
    if not selected:
        raise ValueError(f"Requested chunk indexes {list(selected_chunk_indexes)} but no chunk plans matched")
    return selected


def build_retry_context_group_indices(
    *,
    chunk_plan,
    chunk_group_count: int,
    retry_group_context: int,
) -> List[int]:
    if not getattr(chunk_plan, "core_group_indices", None):
        return []
    start_index = max(0, min(chunk_plan.core_group_indices) - retry_group_context)
    end_index = min(chunk_group_count - 1, max(chunk_plan.core_group_indices) + retry_group_context)
    return list(range(start_index, end_index + 1))


def collect_selected_image_names(
    *,
    chunk_groups,
    selected_chunk_plans,
    retry_group_context: int,
    include_retry_context: bool,
) -> List[str]:
    selected_names: set[str] = set()
    for chunk_plan in selected_chunk_plans:
        selected_names.update(chunk_plan.image_names)
        if not include_retry_context:
            continue
        for group_index in build_retry_context_group_indices(
            chunk_plan=chunk_plan,
            chunk_group_count=len(chunk_groups),
            retry_group_context=retry_group_context,
        ):
            selected_names.update(chunk_groups[group_index].image_names)
    return sorted(selected_names)


def build_chunk_summary(chunk_plan, *, retry_context_group_indices: Sequence[int]) -> dict[str, object]:
    return {
        "index": chunk_plan.index,
        "core_image_count": len(chunk_plan.core_names),
        "image_count": len(chunk_plan.image_names),
        "overlap_image_count": len(chunk_plan.overlap_names),
        "core_group_indices": list(getattr(chunk_plan, "core_group_indices", [])),
        "group_indices": list(getattr(chunk_plan, "group_indices", [])),
        "overlap_group_indices": list(getattr(chunk_plan, "overlap_group_indices", [])),
        "segment_indices": list(getattr(chunk_plan, "segment_indices", [])),
        "retry_context_group_indices": list(retry_context_group_indices),
        "core_names": list(chunk_plan.core_names),
        "image_names": list(chunk_plan.image_names),
        "overlap_names": list(chunk_plan.overlap_names),
    }


def write_subset_archive(image_paths: Sequence[Path], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for image_path in image_paths:
            archive.write(image_path, arcname=image_path.name)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, help="Local path or s3:// URI for the parent ZIP")
    parser.add_argument(
        "--plan-json-output",
        default="",
        help="Optional local path or s3:// URI for the generated chunk-plan JSON",
    )
    parser.add_argument(
        "--subset-output",
        default="",
        help="Optional local path or s3:// URI for the selected chunk subset ZIP",
    )
    parser.add_argument(
        "--chunk-index",
        type=int,
        action="append",
        default=[],
        help="Repeatable chunk index selector for the subset ZIP",
    )
    parser.add_argument(
        "--retry-group-context",
        type=int,
        default=-1,
        help="Optional retry-context expansion override. Defaults to the pipeline setting.",
    )
    parser.add_argument(
        "--skip-retry-context",
        action="store_true",
        help="Do not include retry-context capture groups around the selected chunks in the subset ZIP",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if not args.plan_json_output and not args.subset_output:
        raise SystemExit("At least one of --plan-json-output or --subset-output is required")

    with tempfile.TemporaryDirectory(prefix="sfm_prior_chunk_subset_") as temp_dir:
        workspace = Path(temp_dir)
        archive_path = resolve_input_archive(args.input, workspace)
        extracted_dir = workspace / "images"
        extracted_dir.mkdir(parents=True, exist_ok=True)
        extract_images(archive_path, extracted_dir)

        pipeline = run_colmap_sfm.ColmapPipeline(workspace / "input", workspace / "output")
        pipeline.images_dir = extracted_dir
        pipeline.exif_records = pipeline.load_exif_records()
        pipeline.gps_image_count = len(pipeline.exif_records)
        pipeline.prepare_capture_ordered_image_list()
        chunk_plans = pipeline.build_spatial_heading_chunks()
        selected_chunk_indexes = parse_chunk_indexes(args.chunk_index)
        selected_chunk_plans = resolve_selected_chunk_plans(chunk_plans, selected_chunk_indexes)
        retry_group_context = (
            args.retry_group_context
            if args.retry_group_context >= 0
            else pipeline.chunk_retry_group_context
        )

        plan_summary = {
            "input": args.input,
            "chunk_count": len(chunk_plans),
            "chunk_sizes": pipeline.chunk_sizes,
            "chunk_overlap_image_count": pipeline.chunk_overlap_image_count,
            "chunk_group_count": pipeline.chunk_group_count,
            "chunk_segment_count": pipeline.chunk_segment_count,
            "selected_chunk_indexes": [chunk_plan.index for chunk_plan in selected_chunk_plans],
            "retry_group_context": retry_group_context,
            "chunk_plans": [
                build_chunk_summary(
                    chunk_plan,
                    retry_context_group_indices=build_retry_context_group_indices(
                        chunk_plan=chunk_plan,
                        chunk_group_count=len(pipeline.chunk_groups),
                        retry_group_context=retry_group_context,
                    ),
                )
                for chunk_plan in chunk_plans
            ],
        }

        if args.plan_json_output:
            local_plan_path = workspace / "chunk_plan.json"
            local_plan_path.write_text(json.dumps(plan_summary, indent=2) + "\n", encoding="utf-8")
            upload_output_file(local_plan_path, args.plan_json_output)

        if args.subset_output:
            selected_names = collect_selected_image_names(
                chunk_groups=pipeline.chunk_groups,
                selected_chunk_plans=selected_chunk_plans,
                retry_group_context=retry_group_context,
                include_retry_context=not args.skip_retry_context,
            )
            selected_paths = sorted(
                [path for path in extracted_dir.iterdir() if path.name in set(selected_names)],
                key=lambda path: pipeline.capture_ordered_names.index(path.name),
            )
            local_subset_path = workspace / "subset.zip"
            write_subset_archive(selected_paths, local_subset_path)
            upload_output_file(local_subset_path, args.subset_output)
            plan_summary["subset_image_count"] = len(selected_paths)
            plan_summary["subset_images"] = [path.name for path in selected_paths]

        print(json.dumps(plan_summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
