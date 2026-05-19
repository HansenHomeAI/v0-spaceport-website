#!/usr/bin/env python3
"""Derive stable viewer camera poses from a COLMAP sparse model.

This produces camera poses that match our MD1 viewer query params:
  - camPos (viewer position)
  - camTarget (viewer target, derived from forward * distance)
  - camUp (viewer up vector)

The transform follows the same high-level normalization steps used by the
NerfStudio viewer:
  1) center poses by mean camera center
  2) orient so average up points +Z
  3) scale by max-abs (fits in [-1, 1])

Inputs can be a local file path or an S3 URI (s3://bucket/key).

Supported inputs:
  - COLMAP `images.txt` (includes image names, but can be very large because it
    embeds points2D data).
  - COLMAP `frames.txt` (compact, but requires `--image-names-s3-prefix` so we
    can map frame/data ids onto the corresponding image names).

S3 downloads and listings use the AWS CLI so the script stays dependency-light.
"""

from __future__ import annotations

import argparse
import json
import math
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


Vector3 = tuple[float, float, float]
Matrix3 = tuple[Vector3, Vector3, Vector3]
HOMEBREW_AWS = Path("/opt/homebrew/bin/aws")


def resolve_aws() -> str:
    return str(HOMEBREW_AWS) if HOMEBREW_AWS.exists() else "aws"


def dot(a: Vector3, b: Vector3) -> float:
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def cross(a: Vector3, b: Vector3) -> Vector3:
    return (
        a[1] * b[2] - a[2] * b[1],
        a[2] * b[0] - a[0] * b[2],
        a[0] * b[1] - a[1] * b[0],
    )


def norm(a: Vector3) -> float:
    return math.sqrt(dot(a, a))


def normalize(a: Vector3) -> Vector3:
    n = norm(a)
    if n <= 1e-12:
        return (0.0, 0.0, 0.0)
    return (a[0] / n, a[1] / n, a[2] / n)


def add(a: Vector3, b: Vector3) -> Vector3:
    return (a[0] + b[0], a[1] + b[1], a[2] + b[2])


def sub(a: Vector3, b: Vector3) -> Vector3:
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def mul(a: Vector3, scalar: float) -> Vector3:
    return (a[0] * scalar, a[1] * scalar, a[2] * scalar)


def mat_mul_vec(m: Matrix3, v: Vector3) -> Vector3:
    return (
        dot(m[0], v),
        dot(m[1], v),
        dot(m[2], v),
    )


def mat_transpose(m: Matrix3) -> Matrix3:
    return (
        (m[0][0], m[1][0], m[2][0]),
        (m[0][1], m[1][1], m[2][1]),
        (m[0][2], m[1][2], m[2][2]),
    )


def mat_add(a: Matrix3, b: Matrix3) -> Matrix3:
    return (
        (a[0][0] + b[0][0], a[0][1] + b[0][1], a[0][2] + b[0][2]),
        (a[1][0] + b[1][0], a[1][1] + b[1][1], a[1][2] + b[1][2]),
        (a[2][0] + b[2][0], a[2][1] + b[2][1], a[2][2] + b[2][2]),
    )


def mat_mul(a: Matrix3, b: Matrix3) -> Matrix3:
    bt = mat_transpose(b)
    return (
        (dot(a[0], bt[0]), dot(a[0], bt[1]), dot(a[0], bt[2])),
        (dot(a[1], bt[0]), dot(a[1], bt[1]), dot(a[1], bt[2])),
        (dot(a[2], bt[0]), dot(a[2], bt[1]), dot(a[2], bt[2])),
    )


def mat_scale(m: Matrix3, scalar: float) -> Matrix3:
    return (
        (m[0][0] * scalar, m[0][1] * scalar, m[0][2] * scalar),
        (m[1][0] * scalar, m[1][1] * scalar, m[1][2] * scalar),
        (m[2][0] * scalar, m[2][1] * scalar, m[2][2] * scalar),
    )


def identity() -> Matrix3:
    return (
        (1.0, 0.0, 0.0),
        (0.0, 1.0, 0.0),
        (0.0, 0.0, 1.0),
    )


def skew(v: Vector3) -> Matrix3:
    return (
        (0.0, -v[2], v[1]),
        (v[2], 0.0, -v[0]),
        (-v[1], v[0], 0.0),
    )


def rotation_between(a_raw: Vector3, b_raw: Vector3) -> Matrix3:
    """Rotation matrix that rotates a_raw onto b_raw (Rodrigues)."""
    a = normalize(a_raw)
    b = normalize(b_raw)
    v = cross(a, b)
    s = norm(v)
    c = dot(a, b)
    if s <= 1e-10:
        if c >= 0:
            return identity()
        # 180deg: pick an axis orthogonal to a
        axis = (1.0, 0.0, 0.0)
        if abs(dot(axis, a)) > 0.9:
            axis = (0.0, 1.0, 0.0)
        v = normalize(cross(a, axis))
        k = skew(v)
        # R = I + 2K^2 for 180 degrees
        return mat_add(identity(), mat_scale(mat_mul(k, k), 2.0))

    k = (v[0] / s, v[1] / s, v[2] / s)
    K = skew(k)
    K2 = mat_mul(K, K)
    # R = I + K*sin(theta) + K^2*(1-cos(theta))
    # where sin(theta)=s, cos(theta)=c for unit vectors
    term1 = mat_add(identity(), mat_scale(K, s))
    term2 = mat_scale(K2, (1.0 - c))
    return mat_add(term1, term2)


def quat_to_rotmat(qw: float, qx: float, qy: float, qz: float) -> Matrix3:
    """COLMAP qvec (qw,qx,qy,qz) to rotation matrix Rcw (world -> camera)."""
    # normalized quaternion -> rotation
    return (
        (
            1.0 - 2.0 * qy * qy - 2.0 * qz * qz,
            2.0 * qx * qy - 2.0 * qz * qw,
            2.0 * qx * qz + 2.0 * qy * qw,
        ),
        (
            2.0 * qx * qy + 2.0 * qz * qw,
            1.0 - 2.0 * qx * qx - 2.0 * qz * qz,
            2.0 * qy * qz - 2.0 * qx * qw,
        ),
        (
            2.0 * qx * qz - 2.0 * qy * qw,
            2.0 * qy * qz + 2.0 * qx * qw,
            1.0 - 2.0 * qx * qx - 2.0 * qy * qy,
        ),
    )


def camera_center_from_pose(Rcw: Matrix3, tvec: Vector3) -> Vector3:
    Rwc = mat_transpose(Rcw)
    return mul(mat_mul_vec(Rwc, tvec), -1.0)


def download_s3_uri(uri: str, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    aws = resolve_aws()
    subprocess.run(
        [aws, "s3", "cp", uri, str(destination)],
        check=True,
        stdout=subprocess.DEVNULL,
    )


def resolve_images_txt(path_or_s3: str) -> Path:
    if path_or_s3.startswith("s3://"):
        temp_dir = Path(tempfile.mkdtemp(prefix="colmap-images-txt-"))
        # Preserve the original leaf name so we can detect frames.txt vs images.txt.
        _, rest = path_or_s3.split("s3://", 1)
        _bucket, _, key = rest.partition("/")
        leaf = Path(key).name or "images.txt"
        destination = temp_dir / leaf
        download_s3_uri(path_or_s3, destination)
        return destination
    return Path(path_or_s3)


@dataclass(frozen=True)
class ParsedImage:
    image_id: int
    name: str
    qvec: tuple[float, float, float, float]
    tvec: Vector3


def parse_colmap_images_txt(path: Path) -> list[ParsedImage]:
    images: list[ParsedImage] = []
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    index = 0
    while index < len(lines):
        line = lines[index].strip()
        index += 1
        if not line or line.startswith("#"):
            continue
        parts = line.split()
        if len(parts) < 10:
            continue
        try:
            image_id = int(parts[0])
        except ValueError:
            continue
        q = tuple(float(value) for value in parts[1:5])
        t = (float(parts[5]), float(parts[6]), float(parts[7]))
        name = parts[9]
        images.append(ParsedImage(image_id=image_id, name=name, qvec=q, tvec=t))
        # Skip points2D line if present.
        if index < len(lines):
            index += 1
    return images


def parse_colmap_frames_txt(path: Path, image_names: list[str]) -> list[ParsedImage]:
    images: list[ParsedImage] = []
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    for raw in lines:
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split()
        if len(parts) < 13:
            continue
        try:
            frame_id = int(parts[0])
            # layout: frame_id rig_id qw qx qy qz tx ty tz num_data_ids SENSOR_TYPE SENSOR_ID DATA_ID
            q = tuple(float(value) for value in parts[2:6])
            t = (float(parts[6]), float(parts[7]), float(parts[8]))
        except ValueError:
            continue
        if frame_id <= 0 or frame_id > len(image_names):
            continue
        name = image_names[frame_id - 1]
        images.append(ParsedImage(image_id=frame_id, name=name, qvec=q, tvec=t))
    return images


def list_s3_image_names(prefix: str) -> list[str]:
    """List object base names under an S3 prefix, sorted lexicographically."""
    if not prefix.startswith("s3://"):
        raise ValueError("image-names-s3-prefix must be an s3:// URI")
    _, rest = prefix.split("s3://", 1)
    bucket, _, key_prefix = rest.partition("/")
    key_prefix = key_prefix.rstrip("/") + "/"

    aws = resolve_aws()
    token: str | None = None
    keys: list[str] = []
    while True:
        cmd = [
            aws,
            "s3api",
            "list-objects-v2",
            "--bucket",
            bucket,
            "--prefix",
            key_prefix,
            "--output",
            "json",
        ]
        if token:
            cmd += ["--continuation-token", token]
        result = subprocess.run(cmd, check=True, stdout=subprocess.PIPE, text=True).stdout
        payload = json.loads(result)
        for item in payload.get("Contents") or []:
            key = item.get("Key") or ""
            if not key or key.endswith("/"):
                continue
            keys.append(key.rsplit("/", 1)[-1])
        if not payload.get("IsTruncated"):
            break
        token = payload.get("NextContinuationToken")
        if not token:
            break
    return sorted(set(keys))


def mean_vector(values: Iterable[Vector3]) -> Vector3:
    total_x = total_y = total_z = 0.0
    count = 0
    for value in values:
        total_x += value[0]
        total_y += value[1]
        total_z += value[2]
        count += 1
    if count == 0:
        return (0.0, 0.0, 0.0)
    return (total_x / count, total_y / count, total_z / count)


def format_vector(value: Vector3) -> str:
    return ",".join(f"{entry:.6f}" for entry in value)


def derive_normalization(images: list[ParsedImage]) -> dict[str, object]:
    centers: list[Vector3] = []
    up_vectors: list[Vector3] = []

    for image in images:
        qw, qx, qy, qz = image.qvec
        Rcw = quat_to_rotmat(qw, qx, qy, qz)
        Rwc = mat_transpose(Rcw)
        center = camera_center_from_pose(Rcw, image.tvec)
        centers.append(center)
        # OpenCV camera up is -Y (since +Y points down in image coordinates).
        up_world = mat_mul_vec(Rwc, (0.0, -1.0, 0.0))
        up_vectors.append(normalize(up_world))

    center_mean = mean_vector(centers)
    avg_up = mean_vector(up_vectors)
    avg_up_norm = normalize(avg_up)
    orient = rotation_between(avg_up_norm, (0.0, 0.0, 1.0))

    max_abs = 0.0
    for center in centers:
        oriented = mat_mul_vec(orient, sub(center, center_mean))
        max_abs = max(max_abs, abs(oriented[0]), abs(oriented[1]), abs(oriented[2]))

    scale = 1.0 / max_abs if max_abs > 1e-12 else 1.0
    return {
        "center": [round(center_mean[0], 6), round(center_mean[1], 6), round(center_mean[2], 6)],
        "average_up": [round(avg_up[0], 6), round(avg_up[1], 6), round(avg_up[2], 6)],
        "max_abs_after_center_orient": round(max_abs, 6),
        "scale": round(scale, 12),
        "orient_row_major": [
            round(orient[0][0], 8),
            round(orient[0][1], 8),
            round(orient[0][2], 8),
            round(orient[1][0], 8),
            round(orient[1][1], 8),
            round(orient[1][2], 8),
            round(orient[2][0], 8),
            round(orient[2][1], 8),
            round(orient[2][2], 8),
        ],
    }


def derive_pose(
    image: ParsedImage,
    *,
    center: Vector3,
    orient: Matrix3,
    scale: float,
    distance: float,
) -> dict[str, object]:
    qw, qx, qy, qz = image.qvec
    Rcw = quat_to_rotmat(qw, qx, qy, qz)
    Rwc = mat_transpose(Rcw)

    camera_center = camera_center_from_pose(Rcw, image.tvec)
    cam_pos = mul(mat_mul_vec(orient, sub(camera_center, center)), scale)

    forward_world = mat_mul_vec(Rwc, (0.0, 0.0, 1.0))
    up_world = mat_mul_vec(Rwc, (0.0, -1.0, 0.0))

    forward_view = normalize(mat_mul_vec(orient, forward_world))
    up_view = normalize(mat_mul_vec(orient, up_world))

    cam_target = add(cam_pos, mul(forward_view, distance))
    return {
        "image_id": image.image_id,
        "name": image.name,
        "camPos": format_vector(cam_pos),
        "camTarget": format_vector(cam_target),
        "camUp": format_vector(up_view),
    }


def reshape_orient_row_major(values: list[float]) -> Matrix3:
    if len(values) != 9:
        raise ValueError("orient_row_major must be length 9")
    return (
        (float(values[0]), float(values[1]), float(values[2])),
        (float(values[3]), float(values[4]), float(values[5])),
        (float(values[6]), float(values[7]), float(values[8])),
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--images-txt",
        required=True,
        help="Path or S3 URI to COLMAP sparse/0/images.txt (or sparse/0/frames.txt)",
    )
    parser.add_argument(
        "--image-names-s3-prefix",
        default="",
        help="When --images-txt is frames.txt, list image names from this S3 prefix (s3://bucket/.../images)",
    )
    parser.add_argument("--output", required=True, help="Output JSON path")
    parser.add_argument(
        "--distance-to-target",
        type=float,
        default=0.3,
        help="Distance from camPos to camTarget in viewer units",
    )
    parser.add_argument(
        "--sample-count",
        type=int,
        default=6,
        help="Select N evenly-spaced images by image_id (0 = all)",
    )
    parser.add_argument(
        "--include-names",
        default="",
        help="Comma-separated list of image base names (e.g. DJI_01029.JPG) to include (overrides sampling)",
    )
    return parser.parse_args()


def choose_samples(images: list[ParsedImage], sample_count: int) -> list[ParsedImage]:
    ordered = sorted(images, key=lambda item: item.image_id)
    if sample_count <= 0 or sample_count >= len(ordered):
        return ordered
    if sample_count == 1:
        return [ordered[len(ordered) // 2]]
    picked: list[ParsedImage] = []
    for idx in range(sample_count):
        pos = round(idx * (len(ordered) - 1) / (sample_count - 1))
        picked.append(ordered[int(pos)])
    # de-dup if rounding collided
    seen: set[int] = set()
    unique: list[ParsedImage] = []
    for item in picked:
        if item.image_id in seen:
            continue
        seen.add(item.image_id)
        unique.append(item)
    return unique


def main() -> int:
    args = parse_args()
    images_path = resolve_images_txt(args.images_txt)
    # Frames.txt is compact but does not carry image names; map them from S3.
    if str(images_path).endswith("frames.txt"):
        if not args.image_names_s3_prefix.strip():
            raise RuntimeError("--image-names-s3-prefix is required when parsing frames.txt")
        image_names = list_s3_image_names(args.image_names_s3_prefix.strip())
        if not image_names:
            raise RuntimeError(f"no image names listed under {args.image_names_s3_prefix}")
        images = parse_colmap_frames_txt(images_path, image_names)
    else:
        images = parse_colmap_images_txt(images_path)
    if not images:
        raise RuntimeError(f"No images parsed from {images_path}")

    normalization = derive_normalization(images)
    center_list = normalization["center"]
    center = (float(center_list[0]), float(center_list[1]), float(center_list[2]))
    orient = reshape_orient_row_major([float(x) for x in normalization["orient_row_major"]])
    scale = float(normalization["scale"])

    if args.include_names.strip():
        wanted = {name.strip() for name in args.include_names.split(",") if name.strip()}
        selected = [image for image in images if image.name in wanted]
    else:
        selected = choose_samples(images, args.sample_count)

    poses = [derive_pose(image, center=center, orient=orient, scale=scale, distance=args.distance_to_target) for image in selected]
    payload = {
        "artifact_kind": "viewer_camera_pose_list",
        "schema_version": 1,
        "images_txt": str(args.images_txt),
        "image_count": len(images),
        "selected_count": len(poses),
        "normalization": normalization,
        "poses": poses,
    }
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(f"OK {output_path} selected={len(poses)} total={len(images)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
