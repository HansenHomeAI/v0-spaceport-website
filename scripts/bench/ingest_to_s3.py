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


def upload_to_s3(
    *,
    bucket: str,
    region: str,
    profile: str | None,
    raw_entries: list[tuple[Path, str]],
    manifest_path: Path,
    manifest_key: str,
) -> None:
    try:
        import boto3
        from botocore.exceptions import (
            ClientError,
            NoCredentialsError,
            PartialCredentialsError,
            ProfileNotFound,
        )
    except ModuleNotFoundError:
        raise SystemExit("upload error: boto3 is not installed. Install boto3 to use --upload.")

    try:
        session = boto3.Session(profile_name=profile, region_name=region)
        client = session.client("s3")

        for local_path, key in raw_entries:
            client.upload_file(str(local_path), bucket, key)
        client.upload_file(str(manifest_path), bucket, manifest_key)
    except ProfileNotFound:
        raise SystemExit(f"upload error: AWS profile not found: {profile}")
    except (NoCredentialsError, PartialCredentialsError):
        raise SystemExit("upload error: AWS credentials are missing or incomplete.")
    except ClientError as exc:
        code = str(exc.response.get("Error", {}).get("Code", ""))
        if code in {"AccessDenied", "403"}:
            raise SystemExit("upload error: S3 access denied (403). Check IAM permissions.")
        if code in {"NoSuchBucket", "404"}:
            raise SystemExit(f"upload error: S3 bucket not found: {bucket}")
        raise SystemExit(f"upload error: {exc}")


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

    pfx = normalized_prefix(args.prefix)
    manifest_key = f"{pfx}manifests/{args.dataset}/{args.scene}.manifest.json"

    normalized_root = Path(manifest["paths"]["normalized_scene"])
    file_records = manifest.get("reproducibility", {}).get("files", [])
    raw_entries: list[tuple[Path, str]] = []
    for item in file_records:
        rel_path = item["path"]
        local_path = normalized_root / rel_path
        if not local_path.exists():
            raise SystemExit(f"raw file missing for upload: {local_path}")
        raw_key = f"{pfx}raw/{args.dataset}/{args.scene}/{rel_path}"
        raw_entries.append((local_path, raw_key))

    local_manifest_copy = args.output_dir / "s3_dry_run" / manifest_key
    local_manifest_copy.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(manifest_path, local_manifest_copy)

    print(f"mode={'upload' if args.upload else 'dry-run'}")
    print(f"bucket={args.bucket}")
    print(f"region={args.region}")
    print(f"profile={args.profile or 'default'}")
    for _, key in raw_entries:
        print(f"would_write_raw=s3://{args.bucket}/{key}")
    print(f"would_write_manifest=s3://{args.bucket}/{manifest_key}")
    print(f"local_manifest_copy={local_manifest_copy}")

    if args.upload:
        upload_to_s3(
            bucket=args.bucket,
            region=args.region,
            profile=args.profile,
            raw_entries=raw_entries,
            manifest_path=manifest_path,
            manifest_key=manifest_key,
        )
        print("upload complete")


if __name__ == "__main__":
    main()
