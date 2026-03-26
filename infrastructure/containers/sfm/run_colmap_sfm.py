#!/usr/bin/env python3
import json
import math
import os
import shutil
import sqlite3
import subprocess
import tempfile
import time
import zipfile
from pathlib import Path

import exifread

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".tif", ".tiff", ".webp"}
VOCAB_URL = "https://demuc.de/colmap/vocab_tree_flickr100K_words256K.bin"
VOCAB_PATH = Path("/opt/colmap/vocab/vocab_tree_flickr100K_words256K.bin")


def run(cmd: list[str]) -> None:
    print(f"$ {' '.join(cmd)}", flush=True)
    subprocess.run(cmd, check=True)


def parse_exif_gps(image_path: Path):
    try:
        with image_path.open("rb") as f:
            tags = exifread.process_file(f, details=False)
        if "GPS GPSLatitude" not in tags or "GPS GPSLongitude" not in tags:
            return None

        def dms_to_deg(values, ref):
            deg = float(values.values[0].num) / float(values.values[0].den)
            minute = float(values.values[1].num) / float(values.values[1].den)
            sec = float(values.values[2].num) / float(values.values[2].den)
            out = deg + minute / 60.0 + sec / 3600.0
            return -out if str(ref) in ("S", "W") else out

        lat = dms_to_deg(tags["GPS GPSLatitude"], tags.get("GPS GPSLatitudeRef", "N"))
        lon = dms_to_deg(tags["GPS GPSLongitude"], tags.get("GPS GPSLongitudeRef", "E"))
        alt_tag = tags.get("GPS GPSAltitude")
        alt = float(alt_tag.values[0].num) / float(alt_tag.values[0].den) if alt_tag else 0.0
        return lat, lon, alt
    except Exception:
        return None


def haversine_meters(a, b):
    lat1, lon1 = math.radians(a[0]), math.radians(a[1])
    lat2, lon2 = math.radians(b[0]), math.radians(b[1])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    h = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    return 2 * 6371000 * math.asin(math.sqrt(h))


def extract_zip(input_dir: Path, workspace: Path) -> Path:
    zips = sorted(input_dir.glob("*.zip"))
    if not zips:
        raise RuntimeError(f"No zip found in {input_dir}")
    images_root = workspace / "images"
    images_root.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zips[0], "r") as zf:
        zf.extractall(images_root)
    return images_root


def gather_images(images_root: Path):
    return sorted([p for p in images_root.rglob("*") if p.is_file() and p.suffix.lower() in IMAGE_EXTS])


def ensure_vocab_tree():
    VOCAB_PATH.parent.mkdir(parents=True, exist_ok=True)
    if VOCAB_PATH.exists() and VOCAB_PATH.stat().st_size > 0:
        return
    run(["curl", "-fL", VOCAB_URL, "-o", str(VOCAB_PATH)])


def write_gps_match_list(images_root: Path, image_paths: list[Path], workspace: Path) -> Path | None:
    gps = {}
    for p in image_paths:
        coords = parse_exif_gps(p)
        if coords:
            gps[p.relative_to(images_root).as_posix()] = coords

    if len(gps) < 5:
        print("Insufficient EXIF GPS tags for GPS-prior matching; using vocab tree only", flush=True)
        return None

    match_list = workspace / "gps_match_list.txt"
    names = list(gps.keys())
    k = 30
    radius_m = 350.0

    with match_list.open("w") as f:
        for name in names:
            dists = []
            for other in names:
                if other == name:
                    continue
                d = haversine_meters(gps[name], gps[other])
                if d <= radius_m:
                    dists.append((d, other))
            dists.sort(key=lambda x: x[0])
            for _, other in dists[:k]:
                f.write(f"{name} {other}\n")

    if match_list.stat().st_size == 0:
        return None
    print(f"GPS-derived pair list written: {match_list}", flush=True)
    return match_list


def export_largest_sparse_model(workspace: Path, output_dir: Path):
    sparse_dir = workspace / "sparse"
    model_dirs = [d for d in sparse_dir.iterdir() if d.is_dir()]
    if not model_dirs:
        raise RuntimeError("COLMAP mapper produced no sparse models")

    def model_size(d: Path) -> int:
        pts = d / "points3D.bin"
        if pts.exists():
            return pts.stat().st_size
        txt = d / "points3D.txt"
        return txt.stat().st_size if txt.exists() else 0

    best = max(model_dirs, key=model_size)
    out_sparse = output_dir / "sparse" / "0"
    out_sparse.mkdir(parents=True, exist_ok=True)

    run([
        "colmap", "model_converter",
        "--input_path", str(best),
        "--output_path", str(out_sparse),
        "--output_type", "TXT",
    ])


def main(input_dir: Path, output_dir: Path):
    start = time.time()
    workspace = Path(tempfile.mkdtemp(prefix="colmap_"))
    try:
        images_root = extract_zip(input_dir, workspace)
        image_paths = gather_images(images_root)
        if len(image_paths) < 2:
            raise RuntimeError("Need at least two images for SfM")

        database_path = workspace / "database.db"
        sparse_path = workspace / "sparse"
        sparse_path.mkdir(parents=True, exist_ok=True)

        run([
            "colmap", "feature_extractor",
            "--database_path", str(database_path),
            "--image_path", str(images_root),
            "--ImageReader.camera_model", "OPENCV",
            "--ImageReader.single_camera", "1",
            "--SiftExtraction.use_gpu", "1",
            "--SiftExtraction.max_num_features", "8192",
        ])

        ensure_vocab_tree()
        gps_match_list = write_gps_match_list(images_root, image_paths, workspace)
        matcher_cmd = [
            "colmap", "vocab_tree_matcher",
            "--database_path", str(database_path),
            "--VocabTreeMatching.vocab_tree_path", str(VOCAB_PATH),
            "--SiftMatching.use_gpu", "1",
        ]
        if gps_match_list is not None:
            matcher_cmd.extend(["--VocabTreeMatching.match_list_path", str(gps_match_list)])
        run(matcher_cmd)

        run([
            "colmap", "mapper",
            "--database_path", str(database_path),
            "--image_path", str(images_root),
            "--output_path", str(sparse_path),
        ])

        output_dir.mkdir(parents=True, exist_ok=True)
        export_largest_sparse_model(workspace, output_dir)

        out_images = output_dir / "images"
        if out_images.exists():
            shutil.rmtree(out_images)
        shutil.copytree(images_root, out_images)
        shutil.copy2(database_path, output_dir / "database.db")

        metadata = {
            "pipeline": "COLMAP GPU SfM",
            "processing_time_seconds": round(time.time() - start, 2),
            "images_input": len(image_paths),
            "gps_priors_used": gps_match_list is not None,
            "vocab_tree_path": str(VOCAB_PATH),
            "timestamp_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        }
        with (output_dir / "sfm_metadata.json").open("w") as f:
            json.dump(metadata, f, indent=2)
    finally:
        shutil.rmtree(workspace, ignore_errors=True)


if __name__ == "__main__":
    input_dir = Path(os.environ.get("SFM_INPUT_DIR", "/opt/ml/processing/input"))
    output_dir = Path(os.environ.get("SFM_OUTPUT_DIR", "/opt/ml/processing/output"))
    main(input_dir, output_dir)
