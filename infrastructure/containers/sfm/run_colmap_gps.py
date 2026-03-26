#!/usr/bin/env python3
"""Run COLMAP SfM for SageMaker, with GPU SIFT + vocab-tree matching."""

from __future__ import annotations

import json
import math
import os
import shutil
import subprocess
import sys
import tempfile
import time
import zipfile
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

from PIL import Image
from PIL.ExifTags import GPSTAGS, TAGS

IMAGE_EXTS = {".jpg", ".jpeg", ".png"}


def run_cmd(cmd: List[str]) -> None:
    print(f"▶ {' '.join(cmd)}", flush=True)
    proc = subprocess.run(cmd, check=False)
    if proc.returncode != 0:
        raise RuntimeError(f"Command failed ({proc.returncode}): {' '.join(cmd)}")


def iter_images(root: Path) -> Iterable[Path]:
    for p in sorted(root.rglob("*")):
        if p.is_file() and p.suffix.lower() in IMAGE_EXTS:
            yield p


def extract_images(input_dir: Path, images_dir: Path) -> int:
    images_dir.mkdir(parents=True, exist_ok=True)
    zip_files = sorted(input_dir.glob("*.zip"))
    count = 0

    if zip_files:
        zip_path = zip_files[0]
        print(f"📦 Extracting {zip_path}")
        with zipfile.ZipFile(zip_path, "r") as zf:
            for member in zf.namelist():
                if Path(member).suffix.lower() in IMAGE_EXTS:
                    dst = images_dir / Path(member).name
                    with zf.open(member) as src, open(dst, "wb") as out:
                        out.write(src.read())
                    count += 1
    else:
        for src in iter_images(input_dir):
            shutil.copy2(src, images_dir / src.name)
            count += 1

    return count


def _to_float(v) -> float:
    try:
        return float(v)
    except Exception:
        n = getattr(v, "numerator", None)
        d = getattr(v, "denominator", None)
        if n is not None and d not in (None, 0):
            return float(n) / float(d)
        if isinstance(v, (tuple, list)) and len(v) == 2:
            return float(v[0]) / float(v[1])
        raise


def _dms_to_deg(vals) -> float:
    deg = _to_float(vals[0])
    minutes = _to_float(vals[1])
    seconds = _to_float(vals[2])
    return deg + (minutes / 60.0) + (seconds / 3600.0)


def read_gps(path: Path) -> Optional[Tuple[float, float]]:
    try:
        exif = Image.open(path).getexif()
        gps_raw = None
        for tag_id, value in exif.items():
            if TAGS.get(tag_id, tag_id) == "GPSInfo":
                gps_raw = value
                break
        if not gps_raw:
            return None

        gps = {GPSTAGS.get(k, k): v for k, v in gps_raw.items()}
        if "GPSLatitude" not in gps or "GPSLongitude" not in gps:
            return None

        lat = _dms_to_deg(gps["GPSLatitude"])
        lon = _dms_to_deg(gps["GPSLongitude"])
        if gps.get("GPSLatitudeRef", "N") == "S":
            lat = -lat
        if gps.get("GPSLongitudeRef", "E") == "W":
            lon = -lon
        return lat, lon
    except Exception:
        return None


def haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6371000.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi, dlambda = math.radians(lat2 - lat1), math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return 2 * r * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def build_gps_match_list(images_dir: Path, out_path: Path, max_neighbors: int = 40) -> Tuple[int, int]:
    gps_points: Dict[str, Tuple[float, float]] = {}
    for img in sorted(images_dir.iterdir()):
        if img.suffix.lower() not in IMAGE_EXTS:
            continue
        coords = read_gps(img)
        if coords:
            gps_points[img.name] = coords

    if len(gps_points) < 2:
        return 0, len(gps_points)

    names = list(gps_points.keys())
    pairs = set()

    for i, name in enumerate(names):
        lat1, lon1 = gps_points[name]
        nbrs = []
        for j, other in enumerate(names):
            if i == j:
                continue
            lat2, lon2 = gps_points[other]
            nbrs.append((haversine_m(lat1, lon1, lat2, lon2), other))
        nbrs.sort(key=lambda x: x[0])
        for _, other in nbrs[:max_neighbors]:
            a, b = sorted([name, other])
            pairs.add((a, b))

    with open(out_path, "w") as f:
        for a, b in sorted(pairs):
            f.write(f"{a} {b}\n")

    return len(pairs), len(gps_points)


def find_best_model(model_root: Path) -> Path:
    model_dirs = [p for p in model_root.iterdir() if p.is_dir()]
    if not model_dirs:
        raise RuntimeError("COLMAP mapper produced no sparse models")

    best = None
    best_points = -1
    for d in sorted(model_dirs):
        points_file = d / "points3D.bin"
        if points_file.exists():
            size = points_file.stat().st_size
            if size > best_points:
                best_points = size
                best = d
    if best is None:
        best = sorted(model_dirs)[0]
    return best


def read_txt_point_count(points_file: Path) -> int:
    count = 0
    with open(points_file, "r") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#"):
                count += 1
    return count


def write_metadata(output_dir: Path, started: float, image_count: int, gps_images: int, gps_pairs: int, points: int) -> None:
    metadata = {
        "pipeline": "COLMAP GPU Vocabulary Tree",
        "processing_time_seconds": round(time.time() - started, 2),
        "images_registered": image_count,
        "gps_images_detected": gps_images,
        "gps_pairs_generated": gps_pairs,
        "points_3d": points,
        "gpu_enabled": True,
        "matching_mode": "gps_vocab_tree" if gps_pairs > 0 else "vocab_tree_only",
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime()),
    }
    with open(output_dir / "sfm_metadata.json", "w") as f:
        json.dump(metadata, f, indent=2)


def main() -> int:
    if len(sys.argv) != 3:
        print("Usage: run_colmap_gps.py <input_dir> <output_dir>")
        return 2

    started = time.time()
    input_dir = Path(sys.argv[1])
    output_dir = Path(sys.argv[2])
    output_dir.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(prefix="colmap_") as tmp:
        work = Path(tmp)
        images_dir = work / "images"
        database_path = work / "database.db"
        sparse_root = work / "sparse"
        sparse_root.mkdir(parents=True, exist_ok=True)

        image_count = extract_images(input_dir, images_dir)
        if image_count == 0:
            raise RuntimeError("No input images found")
        print(f"📷 Images extracted: {image_count}")

        sift_max = os.environ.get("SIFT_MAX_NUM_FEATURES", "8192")
        run_cmd([
            "colmap", "feature_extractor",
            "--database_path", str(database_path),
            "--image_path", str(images_dir),
            "--ImageReader.single_camera", "1",
            "--SiftExtraction.use_gpu", "1",
            "--SiftExtraction.max_num_features", sift_max,
        ])

        vocab_tree = Path(os.environ.get("COLMAP_VOCAB_TREE", "/opt/ml/code/vocab_tree_flickr100K_words32K.bin"))
        if not vocab_tree.exists():
            raise RuntimeError(f"Vocabulary tree not found at {vocab_tree}")

        match_list = work / "gps_pairs.txt"
        gps_pairs, gps_images = build_gps_match_list(images_dir, match_list)

        matcher_cmd = [
            "colmap", "vocab_tree_matcher",
            "--database_path", str(database_path),
            "--VocabTreeMatching.vocab_tree_path", str(vocab_tree),
            "--SiftMatching.use_gpu", "1",
        ]
        if gps_pairs > 0:
            matcher_cmd += ["--VocabTreeMatching.match_list_path", str(match_list)]
            print(f"🛰️ GPS-guided matching enabled (gps_images={gps_images}, pairs={gps_pairs})")
        else:
            matcher_cmd += ["--VocabTreeMatching.num_images", os.environ.get("VOCAB_TREE_NUM_IMAGES", "100")]
            print("⚠️ No usable EXIF GPS metadata; using pure vocab-tree matching")
        run_cmd(matcher_cmd)

        run_cmd([
            "colmap", "mapper",
            "--database_path", str(database_path),
            "--image_path", str(images_dir),
            "--output_path", str(sparse_root),
        ])

        best_model = find_best_model(sparse_root)
        output_sparse = output_dir / "sparse" / "0"
        output_sparse.mkdir(parents=True, exist_ok=True)

        run_cmd([
            "colmap", "model_converter",
            "--input_path", str(best_model),
            "--output_path", str(output_sparse),
            "--output_type", "TXT",
        ])

        # Keep legacy OpenSfM-compatible side path for zero downstream changes.
        colmap_export = output_dir / "colmap_export"
        colmap_export.mkdir(parents=True, exist_ok=True)
        for filename in ("cameras.txt", "images.txt", "points3D.txt"):
            shutil.copy2(output_sparse / filename, colmap_export / filename)

        output_images = output_dir / "images"
        if output_images.exists():
            shutil.rmtree(output_images)
        shutil.copytree(images_dir, output_images)

        shutil.copy2(database_path, output_dir / "database.db")

        points = read_txt_point_count(output_sparse / "points3D.txt")
        if points < 1:
            raise RuntimeError("COLMAP produced zero 3D points")

        write_metadata(output_dir, started, image_count, gps_images, gps_pairs, points)
        print(f"✅ COLMAP completed with {points} sparse points")

    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:
        print(f"❌ Fatal error: {exc}")
        sys.exit(1)
