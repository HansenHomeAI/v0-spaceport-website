#!/usr/bin/env python3
"""SageMaker Processing entrypoint for MD1 V18 LOD packaging and SOGS compression."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

from build_md1_lod_bundle import main as build_lod_main


INPUT_DIR = Path(os.environ.get("MD1_LOD_INPUT_DIR", "/opt/ml/processing/input"))
WORK_DIR = Path(os.environ.get("MD1_LOD_WORK_DIR", "/opt/ml/processing/work"))
OUTPUT_DIR = Path(os.environ.get("MD1_LOD_OUTPUT_DIR", "/opt/ml/processing/output"))
SKYBOX_FILE_NAME = "background_skybox.webp"


def find_source_ply() -> Path:
    candidates = sorted(INPUT_DIR.rglob("*.ply"))
    if not candidates:
        raise FileNotFoundError(f"no PLY files under {INPUT_DIR}")
    preferred = [path for path in candidates if path.name == "merged_splat.ply"]
    return preferred[0] if preferred else candidates[0]


def sha256_file(path: Path, chunk_size: int = 1024 * 1024) -> str:
    import hashlib

    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(chunk_size), b""):
            digest.update(chunk)
    return digest.hexdigest()


def run_sogs_compress(ply_file: Path, output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    cmd = ["sogs-compress", "--ply", str(ply_file), "--output-dir", str(output_dir)]
    print(f"[md1-lod] compressing {ply_file.name} -> {output_dir}", flush=True)
    subprocess.run(cmd, check=True, cwd=str(output_dir), timeout=7200)
    meta = output_dir / "meta.json"
    if not meta.exists():
        raise FileNotFoundError(f"SOGS compression did not write {meta}")


def collect_compressed_outputs() -> list[dict]:
    outputs: list[dict] = []
    for directory in sorted(OUTPUT_DIR.glob("compressed_*")):
        if not directory.is_dir():
            continue
        files = []
        for path in sorted(directory.iterdir()):
            if path.is_file():
                files.append(
                    {
                        "path": path.relative_to(OUTPUT_DIR).as_posix(),
                        "byteSize": path.stat().st_size,
                        "sha256": sha256_file(path),
                    }
                )
        outputs.append(
            {
                "directory": directory.name,
                "fileCount": len(files),
                "byteSize": sum(item["byteSize"] for item in files),
                "files": files,
            }
        )
    return outputs


def install_skybox_assets(production_manifest: dict) -> None:
    skybox_entry: str | None = None
    skybox_input = os.environ.get("MD1_SKYBOX_INPUT_PATH", "").strip()
    skybox_url = os.environ.get("MD1_SKYBOX_URL", "").strip()

    if skybox_input:
        source = Path(skybox_input)
        if source.exists():
            target = OUTPUT_DIR / SKYBOX_FILE_NAME
            shutil.copy2(source, target)
            skybox_entry = target.name
            production_manifest["skybox"] = {
                "path": skybox_entry,
                "byteSize": target.stat().st_size,
                "sha256": sha256_file(target),
            }
        else:
            print(f"[md1-lod] skybox input missing: {source}", flush=True)

    if not skybox_entry and skybox_url:
        skybox_entry = skybox_url
        production_manifest["skybox"] = {"url": skybox_url}

    if skybox_entry:
        bundle_config = {"skybox": skybox_entry}
        (OUTPUT_DIR / "spaceport_bundle.json").write_text(json.dumps(bundle_config, indent=2), encoding="utf-8")


def main() -> None:
    source_ply = find_source_ply()
    lod_dir = WORK_DIR / "lod"
    lod_dir.mkdir(parents=True, exist_ok=True)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    build_args = [
        "build_md1_lod_bundle.py",
        "--source-ply",
        str(source_ply),
        "--output-dir",
        str(lod_dir),
        "--lod-strides",
        os.environ.get("MD1_LOD_STRIDES", "1,4,16,64"),
        "--partition-mode",
        os.environ.get("MD1_LOD_PARTITION_MODE", "balanced-kd"),
        "--leaf-count",
        os.environ.get("MD1_LOD_LEAF_COUNT", "64"),
        "--grid-x",
        os.environ.get("MD1_LOD_GRID_X", "4"),
        "--grid-y",
        os.environ.get("MD1_LOD_GRID_Y", "4"),
        "--groups-per-lod",
        os.environ.get("MD1_LOD_GROUPS_PER_LOD", "32"),
        "--min-sogs-splats",
        os.environ.get("MD1_LOD_MIN_SOGS_SPLATS", "16"),
        "--source-artifact-uri",
        os.environ.get("MD1_SOURCE_ARTIFACT_URI", ""),
        "--source-ply-uri",
        os.environ.get("MD1_SOURCE_PLY_URI", ""),
        "--sfm-url",
        os.environ.get("MD1_SFM_URL", ""),
        "--bundle-s3-prefix",
        os.environ.get("MD1_BUNDLE_S3_PREFIX", ""),
        "--write-sha256",
    ]
    original_argv = sys.argv
    try:
        sys.argv = build_args
        build_lod_main()
    finally:
        sys.argv = original_argv

    for path in [lod_dir / "lod-meta.json", lod_dir / "production_manifest.json"]:
        shutil.copy2(path, OUTPUT_DIR / path.name)

    for ply_file in sorted((lod_dir / "chunks").glob("*.ply")):
        run_sogs_compress(ply_file, OUTPUT_DIR / f"compressed_{ply_file.stem}")

    production_manifest_path = OUTPUT_DIR / "production_manifest.json"
    production_manifest = json.loads(production_manifest_path.read_text(encoding="utf-8"))
    production_manifest["compressedOutputs"] = collect_compressed_outputs()
    production_manifest["compressedByteSize"] = sum(
        item["byteSize"] for item in production_manifest["compressedOutputs"]
    )
    install_skybox_assets(production_manifest)
    production_manifest_path.write_text(json.dumps(production_manifest, indent=2, sort_keys=True), encoding="utf-8")
    print("[md1-lod] complete", flush=True)


if __name__ == "__main__":
    main()
