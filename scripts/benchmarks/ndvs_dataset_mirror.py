#!/usr/bin/env python3
"""Mirror paper-aligned NDVS benchmark datasets into S3 with manifests."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import urllib.request
import zipfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Set

IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".JPG", ".JPEG", ".PNG"}


@dataclass
class DatasetOutput:
    dataset_name: str
    local_path: Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("benchmarks/ndvs/benchmark_config.json"),
        help="Path to NDVS benchmark config JSON.",
    )
    parser.add_argument(
        "--workdir",
        type=Path,
        default=Path("/tmp/ndvs-dataset-mirror"),
        help="Working directory for archives/raw/normalized data.",
    )
    parser.add_argument(
        "--bucket",
        default=None,
        help="S3 bucket name for uploads (required unless --skip-upload).",
    )
    parser.add_argument(
        "--prefix",
        default="ndvs-benchmarks",
        help="S3 prefix under bucket.",
    )
    parser.add_argument(
        "--datasets",
        default=None,
        help="Comma-separated dataset keys from config (default: all).",
    )
    parser.add_argument(
        "--skip-download",
        action="store_true",
        help="Assume archives are already present in workdir/archives.",
    )
    parser.add_argument(
        "--skip-upload",
        action="store_true",
        help="Generate normalized data and manifests only; skip S3 upload.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print planned operations without mutating files.",
    )
    return parser.parse_args()


def load_json(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def ensure_dir(path: Path, dry_run: bool) -> None:
    if dry_run:
        return
    path.mkdir(parents=True, exist_ok=True)


def download_file(url: str, dest: Path, dry_run: bool) -> None:
    if dest.exists():
        print(f"[download] exists: {dest}")
        return
    print(f"[download] {url} -> {dest}")
    if dry_run:
        return
    dest.parent.mkdir(parents=True, exist_ok=True)
    urllib.request.urlretrieve(url, dest)


def extract_zip(archive: Path, output_dir: Path, dry_run: bool) -> None:
    print(f"[extract] {archive} -> {output_dir}")
    if dry_run:
        return
    output_dir.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(archive, "r") as handle:
        handle.extractall(output_dir)


def list_image_files(path: Path) -> List[Path]:
    return sorted(
        [
            candidate
            for candidate in path.iterdir()
            if candidate.is_file() and candidate.suffix in IMAGE_SUFFIXES
        ],
        key=lambda p: p.name.lower(),
    )


def rename_images_stable(images_dir: Path, dry_run: bool) -> None:
    files = list_image_files(images_dir)
    if not files:
        return
    tmp_paths: List[Path] = []
    for index, src in enumerate(files, start=1):
        tmp = src.with_name(f"__tmp__{index:08d}{src.suffix.lower()}")
        print(f"[rename:tmp] {src.name} -> {tmp.name}")
        if not dry_run:
            src.rename(tmp)
        tmp_paths.append(tmp)

    for index, src in enumerate(tmp_paths, start=1):
        dst = images_dir / f"{index:08d}{src.suffix.lower()}"
        print(f"[rename:final] {src.name} -> {dst.name}")
        if not dry_run:
            src.rename(dst)


def clean_extra_image_dirs(scene_dir: Path, keep_dir_name: str, dry_run: bool) -> None:
    for candidate in scene_dir.glob("images*"):
        if candidate.name == keep_dir_name:
            continue
        if candidate.is_dir():
            print(f"[cleanup] remove {candidate}")
            if not dry_run:
                shutil.rmtree(candidate)


def hash_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while True:
            chunk = handle.read(1024 * 1024)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def hash_tree(path: Path) -> str:
    digest = hashlib.sha256()
    for file_path in sorted([p for p in path.rglob("*") if p.is_file()]):
        relative = file_path.relative_to(path).as_posix()
        digest.update(relative.encode("utf-8"))
        digest.update(hash_file(file_path).encode("utf-8"))
    return digest.hexdigest()


def copytree(src: Path, dst: Path, dry_run: bool) -> None:
    print(f"[copy] {src} -> {dst}")
    if dry_run:
        return
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(src, dst)


def normalize_mipnerf360(
    dataset_cfg: Dict[str, Any],
    raw_root: Path,
    normalized_root: Path,
    dry_run: bool,
) -> List[DatasetOutput]:
    dataset_name = "mipnerf360"
    output_root = normalized_root / dataset_name
    ensure_dir(output_root, dry_run)

    for scene_cfg in dataset_cfg["scenes"]:
        scene = scene_cfg["name"]
        scene_src = raw_root / scene
        scene_dst = output_root / scene
        if not scene_src.exists():
            if dry_run:
                print(f"[dry-run] missing scene source: {scene_src}")
                continue
            raise FileNotFoundError(f"Missing scene source: {scene_src}")
        copytree(scene_src, scene_dst, dry_run)

        selected_dir = scene_cfg.get("image_folder", "images")
        selected_path = scene_dst / selected_dir
        images_path = scene_dst / "images"

        if selected_dir != "images":
            if not selected_path.exists():
                raise FileNotFoundError(f"Missing selected image folder: {selected_path}")
            if images_path.exists() and not dry_run:
                shutil.rmtree(images_path)
            print(f"[normalize] {scene}: {selected_dir} -> images")
            if not dry_run:
                selected_path.rename(images_path)

        clean_extra_image_dirs(scene_dst, "images", dry_run)
        poses_bounds = scene_dst / "poses_bounds.npy"
        if poses_bounds.exists():
            print(f"[cleanup] remove {poses_bounds}")
            if not dry_run:
                poses_bounds.unlink()
        rename_images_stable(scene_dst / "images", dry_run)

    return [DatasetOutput(dataset_name=dataset_name, local_path=output_root)]


def normalize_tandt_db(
    dataset_cfg: Dict[str, Any],
    raw_root: Path,
    normalized_root: Path,
    dry_run: bool,
) -> List[DatasetOutput]:
    outputs: List[DatasetOutput] = []
    for export_cfg in dataset_cfg["exports"]:
        dataset_name = export_cfg["dataset_name"]
        source_root = raw_root / export_cfg["source_root"]
        output_root = normalized_root / dataset_name
        ensure_dir(output_root, dry_run)
        if not source_root.exists():
            raise FileNotFoundError(f"Missing source root: {source_root}")

        for scene in export_cfg["scenes"]:
            scene_src = source_root / scene
            scene_dst = output_root / scene
            if not scene_src.exists():
                if dry_run:
                    print(f"[dry-run] missing scene source: {scene_src}")
                    continue
                raise FileNotFoundError(f"Missing scene source: {scene_src}")
            copytree(scene_src, scene_dst, dry_run)
            images_path = scene_dst / "images"
            if not images_path.exists():
                if dry_run:
                    print(f"[dry-run] missing images directory: {images_path}")
                    continue
                raise FileNotFoundError(f"Missing images directory: {images_path}")
            rename_images_stable(images_path, dry_run)

        outputs.append(DatasetOutput(dataset_name=dataset_name, local_path=output_root))
    return outputs


def normalize_zipnerf(
    dataset_cfg: Dict[str, Any],
    raw_root: Path,
    normalized_root: Path,
    dry_run: bool,
) -> List[DatasetOutput]:
    dataset_name = "zipnerf"
    output_root = normalized_root / dataset_name
    ensure_dir(output_root, dry_run)

    for scene_cfg in dataset_cfg["scenes"]:
        scene = scene_cfg["name"]
        selected_dir = scene_cfg.get("image_folder", "images")
        scene_src = raw_root / scene
        scene_dst = output_root / scene
        if not scene_src.exists():
            if dry_run:
                print(f"[dry-run] missing scene source: {scene_src}")
                continue
            raise FileNotFoundError(f"Missing scene source: {scene_src}")
        copytree(scene_src, scene_dst, dry_run)

        selected_path = scene_dst / selected_dir
        images_path = scene_dst / "images"
        if selected_dir != "images":
            if not selected_path.exists():
                raise FileNotFoundError(f"Missing selected image folder: {selected_path}")
            if images_path.exists() and not dry_run:
                shutil.rmtree(images_path)
            print(f"[normalize] {scene}: {selected_dir} -> images")
            if not dry_run:
                selected_path.rename(images_path)
        clean_extra_image_dirs(scene_dst, "images", dry_run)
        rename_images_stable(scene_dst / "images", dry_run)

    return [DatasetOutput(dataset_name=dataset_name, local_path=output_root)]


def build_manifest(dataset_name: str, root_path: Path) -> Dict[str, Any]:
    scenes: List[Dict[str, Any]] = []
    for scene_dir in sorted([path for path in root_path.iterdir() if path.is_dir()], key=lambda p: p.name):
        images_dir = scene_dir / "images"
        image_files = list_image_files(images_dir) if images_dir.exists() else []
        scenes.append(
            {
                "scene_name": scene_dir.name,
                "relative_path": scene_dir.relative_to(root_path.parent).as_posix(),
                "image_count": len(image_files),
                "scene_sha256": hash_tree(scene_dir),
            }
        )

    return {
        "dataset_name": dataset_name,
        "generated_at": datetime.now(tz=timezone.utc).isoformat(),
        "scene_count": len(scenes),
        "scenes": scenes,
        "dataset_sha256": hash_tree(root_path),
    }


def run_aws_sync(local_path: Path, s3_uri: str, dry_run: bool) -> None:
    cmd = ["aws", "s3", "sync", str(local_path), s3_uri, "--delete"]
    print(f"[upload] {' '.join(cmd)}")
    if dry_run:
        return
    subprocess.run(cmd, check=True)


def run_aws_cp(local_file: Path, s3_uri: str, dry_run: bool) -> None:
    cmd = ["aws", "s3", "cp", str(local_file), s3_uri]
    print(f"[upload] {' '.join(cmd)}")
    if dry_run:
        return
    subprocess.run(cmd, check=True)


def should_include(name: str, allowlist: Optional[Set[str]]) -> bool:
    if not allowlist:
        return True
    return name in allowlist


def main() -> int:
    args = parse_args()
    config = load_json(args.config)
    allowlist = set(args.datasets.split(",")) if args.datasets else None

    archives_dir = args.workdir / "archives"
    raw_dir = args.workdir / "raw"
    normalized_dir = args.workdir / "normalized"
    manifests_dir = args.workdir / "manifests"

    ensure_dir(archives_dir, args.dry_run)
    ensure_dir(raw_dir, args.dry_run)
    ensure_dir(normalized_dir, args.dry_run)
    ensure_dir(manifests_dir, args.dry_run)

    outputs: List[DatasetOutput] = []

    for dataset_cfg in config["datasets"]:
        dataset_key = dataset_cfg["name"]
        if not should_include(dataset_key, allowlist):
            continue

        print(f"\n=== Processing dataset config: {dataset_key} ===")
        dataset_raw_dir = raw_dir / dataset_key
        ensure_dir(dataset_raw_dir, args.dry_run)

        for archive_cfg in dataset_cfg.get("source_archives", []):
            archive_file = archives_dir / archive_cfg["filename"]
            if not args.skip_download:
                download_file(archive_cfg["url"], archive_file, args.dry_run)
            if not archive_file.exists() and not args.dry_run:
                raise FileNotFoundError(f"Archive missing and skip-download set: {archive_file}")
            if archive_file.exists() or args.dry_run:
                extract_zip(archive_file, dataset_raw_dir, args.dry_run)

        scene_layout = dataset_cfg["scene_layout"]
        if scene_layout == "mipnerf360":
            outputs.extend(normalize_mipnerf360(dataset_cfg, dataset_raw_dir, normalized_dir, args.dry_run))
        elif scene_layout == "tandt_db":
            outputs.extend(normalize_tandt_db(dataset_cfg, dataset_raw_dir, normalized_dir, args.dry_run))
        elif scene_layout == "zipnerf":
            outputs.extend(normalize_zipnerf(dataset_cfg, dataset_raw_dir, normalized_dir, args.dry_run))
        else:
            raise ValueError(f"Unsupported scene_layout: {scene_layout}")

    manifest_index: Dict[str, Any] = {
        "generated_at": datetime.now(tz=timezone.utc).isoformat(),
        "config_version": config.get("version"),
        "datasets": [],
    }

    for output in outputs:
        if args.dry_run:
            manifest = {
                "dataset_name": output.dataset_name,
                "generated_at": datetime.now(tz=timezone.utc).isoformat(),
                "scene_count": 0,
                "scenes": [],
                "dataset_sha256": "dry-run",
            }
        else:
            manifest = build_manifest(output.dataset_name, output.local_path)

        manifest_file = manifests_dir / f"{output.dataset_name}.manifest.json"
        print(f"[manifest] write {manifest_file}")
        if not args.dry_run:
            manifest_file.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        manifest_index["datasets"].append(
            {
                "dataset_name": output.dataset_name,
                "local_path": str(output.local_path),
                "manifest_file": str(manifest_file),
            }
        )

    index_file = manifests_dir / "index.json"
    print(f"[manifest] write {index_file}")
    if not args.dry_run:
        index_file.write_text(json.dumps(manifest_index, indent=2), encoding="utf-8")

    if not args.skip_upload:
        if not args.bucket:
            raise ValueError("--bucket is required unless --skip-upload is set.")
        for output in outputs:
            destination = f"s3://{args.bucket}/{args.prefix}/datasets/{output.dataset_name}"
            run_aws_sync(output.local_path, destination, args.dry_run)
        for manifest_file in [*manifests_dir.glob("*.json")]:
            destination = f"s3://{args.bucket}/{args.prefix}/manifests/{manifest_file.name}"
            run_aws_cp(manifest_file, destination, args.dry_run)

    print("\nDataset mirror run complete.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
