#!/usr/bin/env python3
"""Download and normalize a benchmark scene, then emit reproducibility manifest JSON.

Phase 1 stub: local-only output, no AWS dependencies.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import shutil
import tarfile
import urllib.parse
import urllib.request
import zipfile
from pathlib import Path
from typing import Dict, List, Optional, Tuple

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff", ".webp"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", required=True, help="Dataset key (e.g., mipnerf360).")
    parser.add_argument("--scene", required=True, help="Scene name (e.g., garden).")
    parser.add_argument("--source-url", required=True, help="HTTP(S), file:// URL, or local path.")
    parser.add_argument("--license-url", default="TBD_LICENSE_URL", help="Source license URL.")
    parser.add_argument(
        "--expected-image-dirs",
        nargs="+",
        default=["images_2", "images_4"],
        help="Expected normalized image directories.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("benchmarks/sota_local"),
        help="Local output root for downloads, normalized data, and manifests.",
    )
    return parser.parse_args()


def ensure_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def is_archive(path: Path) -> bool:
    return path.suffix.lower() in {".zip", ".tar", ".gz", ".tgz", ".bz2", ".xz"}


def download_or_copy(source_url: str, destination_dir: Path) -> Path:
    ensure_dir(destination_dir)
    parsed = urllib.parse.urlparse(source_url)

    if parsed.scheme in {"http", "https"}:
        filename = Path(parsed.path).name or "source.bin"
        destination = destination_dir / filename
        urllib.request.urlretrieve(source_url, destination)
        return destination

    if parsed.scheme == "file":
        local_path = Path(urllib.request.url2pathname(parsed.path)).expanduser().resolve()
    elif parsed.scheme == "":
        local_path = Path(source_url).expanduser().resolve()
    else:
        raise ValueError(f"Unsupported source-url scheme: {parsed.scheme}")

    if not local_path.exists():
        raise FileNotFoundError(f"Source path does not exist: {local_path}")

    destination = destination_dir / local_path.name
    if local_path.is_dir():
        if destination.exists():
            shutil.rmtree(destination)
        shutil.copytree(local_path, destination)
    else:
        shutil.copy2(local_path, destination)
    return destination


def extract_if_needed(download_path: Path, extract_dir: Path) -> Path:
    ensure_dir(extract_dir)
    if download_path.is_dir():
        return download_path

    lower_name = download_path.name.lower()
    if zipfile.is_zipfile(download_path):
        with zipfile.ZipFile(download_path, "r") as archive:
            archive.extractall(extract_dir)
        return pick_root(extract_dir)

    if tarfile.is_tarfile(download_path):
        with tarfile.open(download_path, "r:*") as archive:
            archive.extractall(extract_dir)
        return pick_root(extract_dir)

    if is_archive(download_path):
        raise ValueError(f"Archive extension not supported by stdlib handlers: {download_path}")

    # Single non-archive file input; treat parent as root payload.
    single_file_root = extract_dir / "payload"
    ensure_dir(single_file_root)
    shutil.copy2(download_path, single_file_root / download_path.name)
    return single_file_root


def pick_root(path: Path) -> Path:
    children = [child for child in path.iterdir() if child.name != "__MACOSX"]
    if len(children) == 1 and children[0].is_dir():
        return children[0]
    return path


def normalize_scene(source_root: Path, normalized_dir: Path, expected_image_dirs: List[str]) -> None:
    if normalized_dir.exists():
        shutil.rmtree(normalized_dir)
    shutil.copytree(source_root, normalized_dir)

    fallback_images = normalized_dir / "images"
    for image_dir in expected_image_dirs:
        target = normalized_dir / image_dir
        if target.exists():
            continue
        if fallback_images.exists() and fallback_images.is_dir():
            shutil.copytree(fallback_images, target)
        else:
            target.mkdir(parents=True, exist_ok=True)


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def parse_png_size(header: bytes) -> Optional[Tuple[int, int]]:
    if len(header) < 24 or header[:8] != b"\x89PNG\r\n\x1a\n":
        return None
    width = int.from_bytes(header[16:20], "big")
    height = int.from_bytes(header[20:24], "big")
    return width, height


def parse_jpeg_size(data: bytes) -> Optional[Tuple[int, int]]:
    if len(data) < 4 or data[0:2] != b"\xff\xd8":
        return None
    i = 2
    while i + 9 < len(data):
        if data[i] != 0xFF:
            i += 1
            continue
        marker = data[i + 1]
        i += 2
        if marker in {0xD8, 0xD9}:
            continue
        if i + 2 > len(data):
            break
        segment_len = int.from_bytes(data[i:i + 2], "big")
        if segment_len < 2 or i + segment_len > len(data):
            break
        if marker in {0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7, 0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF}:
            if i + 7 >= len(data):
                break
            height = int.from_bytes(data[i + 3:i + 5], "big")
            width = int.from_bytes(data[i + 5:i + 7], "big")
            return width, height
        i += segment_len
    return None


def image_size(path: Path) -> Optional[Tuple[int, int]]:
    with path.open("rb") as handle:
        header = handle.read(65536)
    png_size = parse_png_size(header)
    if png_size:
        return png_size
    return parse_jpeg_size(header)


def build_manifest(
    dataset: str,
    scene: str,
    source_url: str,
    license_url: str,
    expected_image_dirs: List[str],
    download_path: Path,
    normalized_dir: Path,
) -> Dict[str, object]:
    file_records = []
    total_bytes = 0

    for file_path in sorted(path for path in normalized_dir.rglob("*") if path.is_file()):
        rel = file_path.relative_to(normalized_dir).as_posix()
        size_bytes = file_path.stat().st_size
        checksum = file_sha256(file_path)
        file_records.append({"path": rel, "sha256": checksum, "size_bytes": size_bytes})
        total_bytes += size_bytes

    scene_digest = hashlib.sha256()
    for record in file_records:
        scene_digest.update(record["path"].encode("utf-8"))
        scene_digest.update(record["sha256"].encode("utf-8"))

    image_dir_stats: Dict[str, object] = {}
    for image_dir in expected_image_dirs:
        base = normalized_dir / image_dir
        histogram: Dict[Tuple[int, int], int] = {}
        count = 0
        if base.exists():
            for image_path in sorted(p for p in base.rglob("*") if p.is_file() and p.suffix.lower() in IMAGE_EXTENSIONS):
                count += 1
                size = image_size(image_path)
                if size:
                    histogram[size] = histogram.get(size, 0) + 1
        resolutions = [
            {"width": width, "height": height, "count": qty}
            for (width, height), qty in sorted(histogram.items())
        ]
        image_dir_stats[image_dir] = {"count": count, "resolutions": resolutions}

    timestamp = dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    return {
        "schema_version": "1.0.0",
        "dataset": dataset,
        "scene": scene,
        "source_url": source_url,
        "license_url": license_url,
        "download_timestamp": timestamp,
        "expected_image_dirs": expected_image_dirs,
        "paths": {
            "raw_download": str(download_path),
            "normalized_scene": str(normalized_dir),
        },
        "reproducibility": {
            "scene_sha256": scene_digest.hexdigest(),
            "total_files": len(file_records),
            "total_bytes": total_bytes,
            "files": file_records,
            "image_dirs": image_dir_stats,
        },
    }


def main() -> None:
    args = parse_args()
    output_dir = args.output_dir.resolve()

    download_dir = ensure_dir(output_dir / "downloads" / args.dataset / args.scene)
    extract_dir = ensure_dir(output_dir / "extract" / args.dataset / args.scene)
    normalized_dir = output_dir / "normalized" / args.dataset / args.scene
    manifest_dir = ensure_dir(output_dir / "manifests" / args.dataset)

    download_path = download_or_copy(args.source_url, download_dir)
    source_root = extract_if_needed(download_path, extract_dir)
    normalize_scene(source_root, normalized_dir, args.expected_image_dirs)

    manifest = build_manifest(
        dataset=args.dataset,
        scene=args.scene,
        source_url=args.source_url,
        license_url=args.license_url,
        expected_image_dirs=args.expected_image_dirs,
        download_path=download_path,
        normalized_dir=normalized_dir,
    )

    manifest_path = manifest_dir / f"{args.scene}.manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"Manifest written: {manifest_path}")


if __name__ == "__main__":
    main()
