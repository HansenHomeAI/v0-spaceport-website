#!/usr/bin/env python3
"""Extract only visual QA assets from an MD1 quality-review artifact."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import tarfile
import tempfile
from pathlib import Path
from typing import Any


ROOT_MANIFESTS = {
    "quality_review_manifest.json",
    "review_comparison.json",
    "review_camera_manifest.json",
    "visual_qa_manifest.json",
}
VISUAL_REVIEW_PREFIXES = (
    "quality_review/reference/",
    "quality_review/merged/",
    "quality_review/merged_no_background/",
    "quality_review/diff_heatmaps/",
    "quality_review/visual_panels/",
    "quality_review/boundary_composites/",
    "quality_review/tiles/",
)
VISUAL_SUFFIXES = {".json", ".png", ".jpg", ".jpeg", ".webp"}


def is_safe_member_name(name: str) -> bool:
    path = Path(name)
    return not path.is_absolute() and ".." not in path.parts


def is_visual_qa_member(name: str) -> bool:
    if not is_safe_member_name(name):
        raise RuntimeError(f"Refusing unsafe tar member: {name}")
    if name in ROOT_MANIFESTS:
        return True
    if not name.startswith(VISUAL_REVIEW_PREFIXES):
        return False
    return Path(name).suffix.lower() in VISUAL_SUFFIXES


def download_s3_artifact(artifact_uri: str, work_dir: Path) -> Path:
    local_path = work_dir / "model.tar.gz"
    subprocess.run(["aws", "s3", "cp", artifact_uri, str(local_path)], check=True)
    return local_path


def resolve_artifact_path(artifact: str, work_dir: Path) -> Path:
    if artifact.startswith("s3://"):
        return download_s3_artifact(artifact, work_dir)
    artifact_path = Path(artifact)
    if not artifact_path.exists():
        raise FileNotFoundError(f"Artifact does not exist: {artifact}")
    return artifact_path


def extract_visual_qa_bundle(*, artifact: str, output_dir: Path) -> dict[str, Any]:
    if output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(prefix="md1-visual-qa-") as tmp:
        artifact_path = resolve_artifact_path(artifact, Path(tmp))
        extracted_files: list[str] = []
        skipped_files: list[str] = []
        with tarfile.open(artifact_path, "r:gz") as archive:
            for member in archive.getmembers():
                if member.isdir():
                    continue
                if member.issym() or member.islnk():
                    raise RuntimeError(f"Refusing unsafe tar link member: {member.name}")
                if not is_visual_qa_member(member.name):
                    skipped_files.append(member.name)
                    continue
                target = output_dir / member.name
                target.parent.mkdir(parents=True, exist_ok=True)
                source = archive.extractfile(member)
                if source is None:
                    skipped_files.append(member.name)
                    continue
                with source, open(target, "wb") as handle:
                    shutil.copyfileobj(source, handle)
                extracted_files.append(member.name)

    summary = {
        "artifact": artifact,
        "output_dir": str(output_dir),
        "extracted_count": len(extracted_files),
        "skipped_count": len(skipped_files),
        "extracted_files": extracted_files,
        "skipped_files_sample": skipped_files[:50],
        "visual_qa_manifest": str(output_dir / "visual_qa_manifest.json")
        if (output_dir / "visual_qa_manifest.json").exists()
        else None,
        "quality_review_manifest": str(output_dir / "quality_review_manifest.json")
        if (output_dir / "quality_review_manifest.json").exists()
        else None,
    }
    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifact", required=True, help="Local model.tar.gz path or s3:// artifact URI")
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--summary-json-output", type=Path)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    summary = extract_visual_qa_bundle(artifact=args.artifact, output_dir=args.output_dir)
    if args.summary_json_output:
        args.summary_json_output.parent.mkdir(parents=True, exist_ok=True)
        args.summary_json_output.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
