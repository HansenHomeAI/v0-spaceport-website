#!/usr/bin/env python3
"""Build a spatially coherent image subset ZIP from an existing COLMAP handoff.

The script reads COLMAP sparse/0/images.txt, selects a contiguous camera-center
neighborhood, and streams the selected images from S3 into a ZIP uploaded to S3.
It avoids local full-dataset staging so large image sets can be prepared on
machines with limited free disk.
"""

from __future__ import annotations

import argparse
import json
import math
import shutil
import subprocess
import sys
import zipfile
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import BinaryIO, Iterable, List, Sequence


@dataclass(frozen=True)
class ImagePose:
    image_id: int
    name: str
    qvec: tuple[float, float, float, float]
    tvec: tuple[float, float, float]
    center: tuple[float, float, float]


def parse_s3_uri(uri: str) -> tuple[str, str]:
    if not uri.startswith("s3://"):
        raise ValueError(f"Expected s3:// URI, got {uri}")
    bucket_and_key = uri[5:]
    bucket, _, key = bucket_and_key.partition("/")
    if not bucket or not key:
        raise ValueError(f"Expected s3://bucket/key URI, got {uri}")
    return bucket, key.rstrip("/")


def s3_join(prefix: str, *parts: str) -> str:
    return "/".join([prefix.rstrip("/"), *(part.strip("/") for part in parts if part)])


def run_capture(command: Sequence[str]) -> str:
    result = subprocess.run(command, check=True, text=True, capture_output=True)
    return result.stdout


def stream_s3_text(s3_uri: str) -> Iterable[str]:
    process = subprocess.Popen(
        ["aws", "s3", "cp", s3_uri, "-"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1024 * 1024,
    )
    assert process.stdout is not None
    assert process.stderr is not None
    try:
        for line in process.stdout:
            yield line
    finally:
        process.stdout.close()
    return_code = process.wait()
    stderr = process.stderr.read()
    if return_code != 0:
        raise RuntimeError(f"Failed to stream {s3_uri}: {stderr.strip()}")


def quaternion_to_rotation_matrix(qvec: tuple[float, float, float, float]) -> list[list[float]]:
    qw, qx, qy, qz = qvec
    return [
        [
            1.0 - 2.0 * qy * qy - 2.0 * qz * qz,
            2.0 * qx * qy - 2.0 * qz * qw,
            2.0 * qx * qz + 2.0 * qy * qw,
        ],
        [
            2.0 * qx * qy + 2.0 * qz * qw,
            1.0 - 2.0 * qx * qx - 2.0 * qz * qz,
            2.0 * qy * qz - 2.0 * qx * qw,
        ],
        [
            2.0 * qx * qz - 2.0 * qy * qw,
            2.0 * qy * qz + 2.0 * qx * qw,
            1.0 - 2.0 * qx * qx - 2.0 * qy * qy,
        ],
    ]


def camera_center_from_colmap(
    qvec: tuple[float, float, float, float],
    tvec: tuple[float, float, float],
) -> tuple[float, float, float]:
    rotation = quaternion_to_rotation_matrix(qvec)
    # COLMAP stores world-to-camera transform. Camera center is -R^T t.
    return tuple(
        -sum(rotation[row][col] * tvec[row] for row in range(3))
        for col in range(3)
    )


def parse_colmap_images_text(images_txt_uri: str) -> list[ImagePose]:
    records: list[ImagePose] = []
    read_image_line = True
    for raw_line in stream_s3_text(images_txt_uri):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if read_image_line:
            parts = line.split()
            if len(parts) < 10:
                raise ValueError(f"Malformed COLMAP image line: {line[:200]}")
            image_id = int(parts[0])
            qvec = tuple(float(value) for value in parts[1:5])
            tvec = tuple(float(value) for value in parts[5:8])
            name = parts[9]
            records.append(
                ImagePose(
                    image_id=image_id,
                    name=name,
                    qvec=qvec,  # type: ignore[arg-type]
                    tvec=tvec,  # type: ignore[arg-type]
                    center=camera_center_from_colmap(qvec, tvec),  # type: ignore[arg-type]
                )
            )
        read_image_line = not read_image_line
    if not records:
        raise ValueError(f"No image records found in {images_txt_uri}")
    return records


def distance_xy(first: ImagePose, second: ImagePose) -> float:
    return math.hypot(first.center[0] - second.center[0], first.center[1] - second.center[1])


def choose_densest_spatial_subset(records: Sequence[ImagePose], count: int) -> tuple[ImagePose, list[ImagePose]]:
    if count <= 0:
        raise ValueError("count must be greater than zero")
    if count > len(records):
        raise ValueError(f"count {count} exceeds available records {len(records)}")
    best_seed: ImagePose | None = None
    best_ordered: list[ImagePose] | None = None
    best_score: tuple[float, float, str] | None = None
    for seed in records:
        ordered = sorted(records, key=lambda record: (distance_xy(seed, record), record.name))
        selected = ordered[:count]
        kth_radius = distance_xy(seed, selected[-1])
        mean_radius = sum(distance_xy(seed, record) for record in selected) / len(selected)
        score = (kth_radius, mean_radius, seed.name)
        if best_score is None or score < best_score:
            best_seed = seed
            best_ordered = selected
            best_score = score
    assert best_seed is not None and best_ordered is not None
    return best_seed, sorted(best_ordered, key=lambda record: record.name)


def build_subset_summary(
    *,
    source_colmap_uri: str,
    source_images_uri: str,
    output_zip_uri: str,
    target_count: int,
    records: Sequence[ImagePose],
    selected: Sequence[ImagePose],
    seed: ImagePose,
) -> dict[str, object]:
    xs = [record.center[0] for record in selected]
    ys = [record.center[1] for record in selected]
    zs = [record.center[2] for record in selected]
    radii = [distance_xy(seed, record) for record in selected]
    selected_names = [record.name for record in selected]
    return {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "dataset": "MD1-Shrunk",
        "selection_strategy": "densest_colmap_camera_center_neighborhood_xy",
        "source_colmap_uri": source_colmap_uri,
        "source_images_uri": source_images_uri,
        "output_zip_uri": output_zip_uri,
        "target_count": target_count,
        "source_registered_images": len(records),
        "selected_count": len(selected),
        "seed": {
            "image_id": seed.image_id,
            "name": seed.name,
            "center": list(seed.center),
        },
        "xy_radius_max": max(radii),
        "xy_radius_mean": sum(radii) / len(radii),
        "bounds": {
            "min_x": min(xs),
            "max_x": max(xs),
            "min_y": min(ys),
            "max_y": max(ys),
            "min_z": min(zs),
            "max_z": max(zs),
        },
        "first_selected_name": selected_names[0],
        "last_selected_name": selected_names[-1],
        "selected_names": selected_names,
    }


def copy_s3_object_to_zip_entry(source_uri: str, target: BinaryIO) -> int:
    process = subprocess.Popen(
        ["aws", "s3", "cp", source_uri, "-"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        bufsize=1024 * 1024,
    )
    assert process.stdout is not None
    assert process.stderr is not None
    bytes_written = 0
    with process.stdout:
        while True:
            chunk = process.stdout.read(1024 * 1024)
            if not chunk:
                break
            target.write(chunk)
            bytes_written += len(chunk)
    stderr = process.stderr.read().decode("utf-8", errors="replace")
    return_code = process.wait()
    if return_code != 0:
        raise RuntimeError(f"Failed to read {source_uri}: {stderr.strip()}")
    return bytes_written


def upload_zip_from_s3_images(
    *,
    source_images_uri: str,
    output_zip_uri: str,
    selected: Sequence[ImagePose],
    compression: int,
) -> dict[str, object]:
    upload = subprocess.Popen(
        ["aws", "s3", "cp", "-", output_zip_uri],
        stdin=subprocess.PIPE,
        stderr=subprocess.PIPE,
        bufsize=1024 * 1024,
    )
    assert upload.stdin is not None
    assert upload.stderr is not None
    bytes_by_name: dict[str, int] = {}
    try:
        with upload.stdin:
            with zipfile.ZipFile(upload.stdin, mode="w", compression=compression, allowZip64=True) as archive:
                for index, record in enumerate(selected, start=1):
                    source_uri = s3_join(source_images_uri, record.name)
                    info = zipfile.ZipInfo(filename=record.name)
                    info.compress_type = compression
                    with archive.open(info, mode="w", force_zip64=True) as entry:
                        bytes_by_name[record.name] = copy_s3_object_to_zip_entry(source_uri, entry)
                    if index == 1 or index % 50 == 0 or index == len(selected):
                        print(
                            f"zipped {index}/{len(selected)} {record.name} "
                            f"({bytes_by_name[record.name]} bytes)",
                            file=sys.stderr,
                            flush=True,
                        )
    except Exception:
        upload.kill()
        upload.wait()
        raise
    stderr = upload.stderr.read().decode("utf-8", errors="replace")
    return_code = upload.wait()
    if return_code != 0:
        raise RuntimeError(f"Failed to upload {output_zip_uri}: {stderr.strip()}")
    return {
        "uploaded_zip_uri": output_zip_uri,
        "selected_object_count": len(selected),
        "selected_source_bytes": sum(bytes_by_name.values()),
        "aws_cli_stderr": stderr.strip(),
    }


def write_manifest(path: Path, manifest: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def upload_manifest(path: Path, manifest_s3_uri: str) -> None:
    subprocess.run(["aws", "s3", "cp", str(path), manifest_s3_uri], check=True)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-colmap-uri", required=True, help="S3 URI ending at the COLMAP root")
    parser.add_argument("--output-zip-uri", required=True, help="S3 URI for the generated ZIP")
    parser.add_argument("--target-count", required=True, type=int, help="Number of images to select")
    parser.add_argument("--manifest-output", required=True, help="Local JSON manifest path")
    parser.add_argument("--manifest-s3-uri", default="", help="Optional S3 URI for the manifest JSON")
    parser.add_argument(
        "--write-zip",
        action="store_true",
        help="Actually stream and upload the ZIP. Without this, only writes the selection manifest.",
    )
    parser.add_argument(
        "--deflate",
        action="store_true",
        help="Use ZIP_DEFLATED. Default is ZIP_STORED because JPEGs are already compressed.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    source_colmap_uri = args.source_colmap_uri.rstrip("/")
    source_images_uri = s3_join(source_colmap_uri, "images")
    images_txt_uri = s3_join(source_colmap_uri, "sparse/0/images.txt")
    records = parse_colmap_images_text(images_txt_uri)
    seed, selected = choose_densest_spatial_subset(records, args.target_count)
    manifest = build_subset_summary(
        source_colmap_uri=source_colmap_uri,
        source_images_uri=source_images_uri,
        output_zip_uri=args.output_zip_uri,
        target_count=args.target_count,
        records=records,
        selected=selected,
        seed=seed,
    )
    manifest_path = Path(args.manifest_output)
    write_manifest(manifest_path, manifest)
    if args.manifest_s3_uri:
        upload_manifest(manifest_path, args.manifest_s3_uri)
    if args.write_zip:
        compression = zipfile.ZIP_DEFLATED if args.deflate else zipfile.ZIP_STORED
        upload_summary = upload_zip_from_s3_images(
            source_images_uri=source_images_uri,
            output_zip_uri=args.output_zip_uri,
            selected=selected,
            compression=compression,
        )
        manifest["zip_upload"] = upload_summary
        write_manifest(manifest_path, manifest)
        if args.manifest_s3_uri:
            upload_manifest(manifest_path, args.manifest_s3_uri)
    print(json.dumps({key: manifest[key] for key in manifest if key != "selected_names"}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
