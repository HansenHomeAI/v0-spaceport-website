#!/usr/bin/env python3
"""Build sequential first-portion benchmark ZIPs from a larger image archive."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import tempfile
import zipfile
from pathlib import Path
from typing import Iterable, List


IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png"}


def run_command(command: List[str]) -> None:
    subprocess.run(command, check=True)


def resolve_input_archive(input_path: str, workspace: Path) -> Path:
    if input_path.startswith("s3://"):
        local_path = workspace / Path(input_path).name
        run_command(["aws", "s3", "cp", input_path, str(local_path)])
        return local_path
    return Path(input_path).expanduser().resolve()


def upload_output_archive(local_path: Path, output_path: str) -> None:
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


def load_capture_records(image_dir: Path) -> List[dict[str, str]]:
    result = subprocess.run(
        [
            "exiftool",
            "-j",
            "-FileName",
            "-DateTimeOriginal",
            "-SubSecDateTimeOriginal",
            "-CreateDate",
            str(image_dir),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    records = json.loads(result.stdout or "[]")
    capture_records: List[dict[str, str]] = []
    for record in records:
        file_name = record.get("FileName")
        if not file_name:
            continue
        capture_records.append(
            {
                "file_name": file_name,
                "capture_time": (
                    record.get("SubSecDateTimeOriginal")
                    or record.get("DateTimeOriginal")
                    or record.get("CreateDate")
                    or ""
                ),
            }
        )
    return capture_records


def sort_capture_records(records: Iterable[dict[str, str]]) -> List[dict[str, str]]:
    def record_key(record: dict[str, str]) -> tuple[int, str, str]:
        capture_time = record.get("capture_time", "")
        file_name = record.get("file_name", "")
        if capture_time:
            return (0, capture_time, file_name.lower())
        return (1, file_name.lower(), "")

    return sorted(records, key=record_key)


def strip_gps_metadata(image_paths: List[Path]) -> None:
    if not image_paths:
        return
    run_command(
        [
            "exiftool",
            "-overwrite_original",
            "-gps:all=",
            *[str(path) for path in image_paths],
        ]
    )


def write_subset_archive(image_paths: List[Path], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for image_path in image_paths:
            archive.write(image_path, arcname=image_path.name)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, help="Local path or s3:// URI for the parent ZIP")
    parser.add_argument("--output", required=True, help="Local path or s3:// URI for the subset ZIP")
    parser.add_argument("--count", required=True, type=int, help="Number of first-sequence images to keep")
    parser.add_argument(
        "--strip-gps",
        action="store_true",
        help="Remove GPS EXIF from the output subset for no-GPS control benchmarks",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.count <= 0:
        raise ValueError("--count must be greater than zero")

    with tempfile.TemporaryDirectory(prefix="sfm_subset_") as temp_dir:
        workspace = Path(temp_dir)
        archive_path = resolve_input_archive(args.input, workspace)
        extracted_dir = workspace / "images"
        extracted_dir.mkdir(parents=True, exist_ok=True)
        extract_images(archive_path, extracted_dir)

        capture_records = sort_capture_records(load_capture_records(extracted_dir))
        selected_names = {record["file_name"] for record in capture_records[: args.count]}
        order_index = {
            record["file_name"]: index for index, record in enumerate(capture_records)
        }
        selected_paths = sorted(
            [path for path in extracted_dir.iterdir() if path.name in selected_names],
            key=lambda path: order_index[path.name],
        )
        if len(selected_paths) != min(args.count, len(capture_records)):
            raise RuntimeError("Failed to materialize the requested sequential subset")

        if args.strip_gps:
            strip_gps_metadata(selected_paths)

        local_output = workspace / "subset.zip"
        write_subset_archive(selected_paths, local_output)
        upload_output_archive(local_output, args.output)

        summary = {
            "input": args.input,
            "output": args.output,
            "requested_count": args.count,
            "selected_count": len(selected_paths),
            "subset_strategy": "first_portion_by_exif_datetime_else_filename",
            "strip_gps": args.strip_gps,
            "first_image": selected_paths[0].name if selected_paths else "",
            "last_image": selected_paths[-1].name if selected_paths else "",
        }
        print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
