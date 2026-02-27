#!/usr/bin/env python3
"""Dry-run wrapper for benchmark ingestion to S3 key layout.

Default behavior performs no AWS calls and prints the keys that would be written.
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", required=True, help="Dataset key (e.g., mipnerf360).")
    parser.add_argument("--scene", required=True, help="Scene name (e.g., garden).")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("benchmarks/sota_local"),
        help="Local output root.",
    )
    parser.add_argument("--bucket", default="spaceport-ml-benchmarks", help="Target S3 bucket name.")
    parser.add_argument("--prefix", default="", help="Optional S3 prefix (for example: dev/benchmarks).")
    parser.add_argument("--region", default="us-east-1", help="AWS region for upload mode.")
    parser.add_argument("--profile", default=None, help="AWS profile for upload mode.")
    parser.add_argument(
        "--previous-manifest",
        type=Path,
        default=None,
        help="Optional prior manifest for local drift checks.",
    )

    parser.add_argument("--source-url", default=None, help="Source URL/path passed to ingest_dataset.py.")
    parser.add_argument("--license-url", default="TBD_LICENSE_URL", help="License URL passed to ingest_dataset.py.")
    parser.add_argument(
        "--expected-image-dirs",
        nargs="+",
        default=["images_2", "images_4"],
        help="Expected normalized image directories.",
    )

    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--dry-run", action="store_true", help="Print planned S3 keys only (default).")
    mode.add_argument("--upload", action="store_true", help="Enable upload mode (stub; no AWS call yet).")

    args = parser.parse_args()
    if not args.upload:
        args.dry_run = True
    return args


def normalized_prefix(prefix: str) -> str:
    clean = prefix.strip("/")
    return f"{clean}/" if clean else ""


def run_ingest_dataset(args: argparse.Namespace, manifest_path: Path) -> None:
    if manifest_path.exists():
        return
    if not args.source_url:
        raise SystemExit(
            f"Manifest not found at {manifest_path}. Provide --source-url to generate it via ingest_dataset.py."
        )

    script_path = Path(__file__).with_name("ingest_dataset.py")
    command = [
        sys.executable,
        str(script_path),
        "--dataset",
        args.dataset,
        "--scene",
        args.scene,
        "--source-url",
        args.source_url,
        "--license-url",
        args.license_url,
        "--output-dir",
        str(args.output_dir),
        "--expected-image-dirs",
        *args.expected_image_dirs,
    ]
    subprocess.run(command, check=True)


def compare_manifests(previous: dict, current: dict, dataset: str, scene: str) -> list[str]:
    mismatches: list[str] = []
    if previous.get("dataset") != dataset or previous.get("scene") != scene:
        mismatches.append(
            "identity mismatch "
            f"(previous={previous.get('dataset')}/{previous.get('scene')} current={dataset}/{scene})"
        )

    prev_rep = previous.get("reproducibility", {})
    curr_rep = current.get("reproducibility", {})

    if prev_rep.get("total_files") != curr_rep.get("total_files"):
        mismatches.append(
            f"total_files mismatch (previous={prev_rep.get('total_files')} current={curr_rep.get('total_files')})"
        )

    prev_files = {item["path"]: item.get("sha256") for item in prev_rep.get("files", [])}
    curr_files = {item["path"]: item.get("sha256") for item in curr_rep.get("files", [])}

    if sorted(prev_files.keys()) != sorted(curr_files.keys()):
        prev_only = sorted(set(prev_files.keys()) - set(curr_files.keys()))
        curr_only = sorted(set(curr_files.keys()) - set(prev_files.keys()))
        mismatches.append(
            "file list mismatch "
            f"(previous_only={prev_only[:5]} current_only={curr_only[:5]})"
        )

    for path in sorted(set(prev_files.keys()) & set(curr_files.keys())):
        if prev_files[path] != curr_files[path]:
            mismatches.append(f"checksum mismatch ({path})")
            break

    prev_dirs = prev_rep.get("image_dirs", {})
    curr_dirs = curr_rep.get("image_dirs", {})
    if prev_dirs != curr_dirs:
        mismatches.append("resolution/count mismatch (reproducibility.image_dirs)")

    return mismatches


def main() -> None:
    args = parse_args()
    args.output_dir = args.output_dir.resolve()

    manifest_path = args.output_dir / "manifests" / args.dataset / f"{args.scene}.manifest.json"
    run_ingest_dataset(args, manifest_path)

    if not manifest_path.exists():
        raise SystemExit(f"Expected manifest not found: {manifest_path}")

    with manifest_path.open("r", encoding="utf-8") as handle:
        manifest = json.load(handle)

    if args.previous_manifest:
        previous_manifest_path = args.previous_manifest.resolve()
        with previous_manifest_path.open("r", encoding="utf-8") as handle:
            previous_manifest = json.load(handle)
        mismatches = compare_manifests(previous_manifest, manifest, args.dataset, args.scene)
        if mismatches:
            for mismatch in mismatches:
                print(f"drift: {mismatch}")
            raise SystemExit(2)

    raw_download_path = Path(manifest["paths"]["raw_download"])
    source_name = raw_download_path.name

    pfx = normalized_prefix(args.prefix)
    raw_key = f"{pfx}raw/{args.dataset}/{args.scene}/{source_name}"
    manifest_key = f"{pfx}manifests/{args.dataset}/{args.scene}.manifest.json"

    local_manifest_copy = args.output_dir / "s3_dry_run" / manifest_key
    local_manifest_copy.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(manifest_path, local_manifest_copy)

    print(f"mode={'upload' if args.upload else 'dry-run'}")
    print(f"bucket={args.bucket}")
    print(f"region={args.region}")
    print(f"profile={args.profile or 'default'}")
    print(f"would_write_raw=s3://{args.bucket}/{raw_key}")
    print(f"would_write_manifest=s3://{args.bucket}/{manifest_key}")
    print(f"local_manifest_copy={local_manifest_copy}")

    if args.upload:
        raise SystemExit("--upload requested, but AWS upload is not implemented yet (stub only).")


if __name__ == "__main__":
    main()
