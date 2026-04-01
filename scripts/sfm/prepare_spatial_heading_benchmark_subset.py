#!/usr/bin/env python3
"""Build spatial-heading benchmark ZIPs from a larger image archive."""

from __future__ import annotations

import argparse
import json
import math
import shutil
import subprocess
import tempfile
import zipfile
from pathlib import Path
from typing import Iterable, List


IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png"}
EARTH_RADIUS_METERS = 6378137.0


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


def parse_optional_float(record: dict[str, object], keys: Iterable[str]) -> float | None:
    for key in keys:
        value = record.get(key)
        if value in (None, ""):
            continue
        try:
            return float(value)
        except (TypeError, ValueError):
            continue
    return None


def normalize_heading(angle_deg: float | None) -> float | None:
    if angle_deg is None:
        return None
    return float(angle_deg) % 360.0


def angular_distance_degrees(first_deg: float | None, second_deg: float | None) -> float:
    if first_deg is None or second_deg is None:
        return 90.0
    difference = abs(normalize_heading(first_deg) - normalize_heading(second_deg))
    return min(difference, 360.0 - difference)


def load_pose_records(image_dir: Path) -> List[dict[str, float | str | None]]:
    result = subprocess.run(
        [
            "exiftool",
            "-j",
            "-n",
            "-FileName",
            "-DateTimeOriginal",
            "-SubSecDateTimeOriginal",
            "-CreateDate",
            "-GPSLatitude",
            "-GPSLongitude",
            "-GPSAltitude",
            "-GPSImgDirection",
            "-GimbalYawDegree",
            "-FlightYawDegree",
            str(image_dir),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    records = json.loads(result.stdout or "[]")
    pose_records: List[dict[str, float | str | None]] = []
    for record in records:
        file_name = record.get("FileName")
        if not file_name or "GPSLatitude" not in record or "GPSLongitude" not in record:
            continue
        pose_records.append(
            {
                "file_name": file_name,
                "capture_time": (
                    record.get("SubSecDateTimeOriginal")
                    or record.get("DateTimeOriginal")
                    or record.get("CreateDate")
                    or ""
                ),
                "gps_latitude": float(record["GPSLatitude"]),
                "gps_longitude": float(record["GPSLongitude"]),
                "gps_altitude": float(record.get("GPSAltitude", 0.0)),
                "heading_deg": normalize_heading(
                    parse_optional_float(record, ["GimbalYawDegree", "GPSImgDirection", "FlightYawDegree"])
                ),
            }
        )
    if not pose_records:
        raise ValueError("No GPS-tagged images found in archive")
    reference_lat = float(pose_records[0]["gps_latitude"])
    reference_lon = float(pose_records[0]["gps_longitude"])
    cos_lat = math.cos(math.radians(reference_lat))
    for record in pose_records:
        latitude = float(record["gps_latitude"])
        longitude = float(record["gps_longitude"])
        delta_lat = math.radians(latitude - reference_lat)
        delta_lon = math.radians(longitude - reference_lon)
        record["local_x_m"] = EARTH_RADIUS_METERS * delta_lon * cos_lat
        record["local_y_m"] = EARTH_RADIUS_METERS * delta_lat
    return pose_records


def choose_seed_record(
    pose_records: List[dict[str, float | str | None]], seed_image: str
) -> dict[str, float | str | None]:
    if seed_image:
        for record in pose_records:
            if record["file_name"] == seed_image:
                return record
        raise ValueError(f"Seed image {seed_image} was not found in the archive")
    centroid_x = sum(float(record["local_x_m"]) for record in pose_records) / len(pose_records)
    centroid_y = sum(float(record["local_y_m"]) for record in pose_records) / len(pose_records)
    return min(
        pose_records,
        key=lambda record: math.hypot(
            float(record["local_x_m"]) - centroid_x,
            float(record["local_y_m"]) - centroid_y,
        ),
    )


def spatial_heading_score(
    record: dict[str, float | str | None],
    seed_record: dict[str, float | str | None],
    heading_weight: float,
) -> float:
    distance = math.hypot(
        float(record["local_x_m"]) - float(seed_record["local_x_m"]),
        float(record["local_y_m"]) - float(seed_record["local_y_m"]),
    )
    heading_factor = 1.0 + (
        heading_weight
        * angular_distance_degrees(record.get("heading_deg"), seed_record.get("heading_deg"))
        / 180.0
    )
    return distance * heading_factor


def select_spatial_heading_subset(
    pose_records: List[dict[str, float | str | None]],
    *,
    count: int,
    seed_image: str,
    heading_weight: float,
) -> List[dict[str, float | str | None]]:
    if count <= 0:
        raise ValueError("count must be greater than zero")
    seed_record = choose_seed_record(pose_records, seed_image)
    ordered_records = sorted(
        pose_records,
        key=lambda record: (
            spatial_heading_score(record, seed_record, heading_weight),
            str(record.get("capture_time", "")),
            str(record["file_name"]).lower(),
        ),
    )
    return ordered_records[: min(count, len(ordered_records))]


def write_subset_archive(image_paths: List[Path], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for image_path in image_paths:
            archive.write(image_path, arcname=image_path.name)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, help="Local path or s3:// URI for the parent ZIP")
    parser.add_argument("--output", required=True, help="Local path or s3:// URI for the subset ZIP")
    parser.add_argument("--count", required=True, type=int, help="Number of images to keep")
    parser.add_argument(
        "--seed-image",
        default="",
        help="Optional image basename to anchor the neighborhood around",
    )
    parser.add_argument(
        "--heading-weight",
        type=float,
        default=0.6,
        help="Weight applied to heading difference in the selection score",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    with tempfile.TemporaryDirectory(prefix="sfm_spatial_subset_") as temp_dir:
        workspace = Path(temp_dir)
        archive_path = resolve_input_archive(args.input, workspace)
        extracted_dir = workspace / "images"
        extracted_dir.mkdir(parents=True, exist_ok=True)
        extract_images(archive_path, extracted_dir)
        pose_records = load_pose_records(extracted_dir)
        selected_records = select_spatial_heading_subset(
            pose_records,
            count=args.count,
            seed_image=args.seed_image,
            heading_weight=args.heading_weight,
        )
        selected_names = {str(record["file_name"]) for record in selected_records}
        selected_paths = sorted(
            [path for path in extracted_dir.iterdir() if path.name in selected_names],
            key=lambda path: next(
                index
                for index, record in enumerate(selected_records)
                if record["file_name"] == path.name
            ),
        )
        local_output = workspace / "subset.zip"
        write_subset_archive(selected_paths, local_output)
        upload_output_archive(local_output, args.output)
        summary = {
            "input": args.input,
            "output": args.output,
            "requested_count": args.count,
            "selected_count": len(selected_paths),
            "subset_strategy": "spatial_heading_neighborhood_by_gps_and_view_direction",
            "seed_image": str(selected_records[0]["file_name"]) if selected_records else "",
            "heading_weight": args.heading_weight,
            "first_image": selected_paths[0].name if selected_paths else "",
            "last_image": selected_paths[-1].name if selected_paths else "",
        }
        print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
