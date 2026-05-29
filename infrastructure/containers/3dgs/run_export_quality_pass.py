#!/usr/bin/env python3
"""
Run the no-retrain skybox export and floater-pruning pass from an existing model artifact.
"""

from __future__ import annotations

import json
import logging
import os
import shutil
import tarfile
from pathlib import Path

import yaml

from train_nerfstudio_production import NerfStudioTrainer


logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def find_model_artifact(model_input_dir: Path) -> Path:
    if model_input_dir.is_file():
        return model_input_dir

    candidates = sorted(model_input_dir.rglob("model.tar.gz"))
    if not candidates:
        raise FileNotFoundError(f"No model.tar.gz found under {model_input_dir}")
    return candidates[0]


def extract_model_artifact(model_tarball: Path, extract_dir: Path) -> Path:
    if extract_dir.exists():
        shutil.rmtree(extract_dir)
    extract_dir.mkdir(parents=True, exist_ok=True)

    with tarfile.open(model_tarball, "r:gz") as tar:
        dest_root = extract_dir.resolve()
        for member in tar.getmembers():
            member_path = (extract_dir / member.name).resolve()
            if not str(member_path).startswith(str(dest_root)):
                raise RuntimeError(f"Refusing unsafe artifact member: {member.name}")
        tar.extractall(extract_dir)
    return extract_dir


def patch_config_data_path(source_config: Path, data_dir: Path, patched_config_path: Path) -> Path:
    with open(source_config, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    config["data"] = str(data_dir)
    patched_config_path.parent.mkdir(parents=True, exist_ok=True)
    with open(patched_config_path, "w", encoding="utf-8") as f:
        yaml.safe_dump(config, f, sort_keys=False)
    return patched_config_path


def build_model_tarball(source_dir: Path, tarball_path: Path) -> Path:
    """Package export-quality-pass output so downstream cached tile merge can reuse it."""
    if tarball_path.exists():
        tarball_path.unlink()

    source_root = source_dir.resolve()
    with tarfile.open(tarball_path, "w:gz") as archive:
        for path in sorted(source_dir.rglob("*")):
            resolved_path = path.resolve()
            if resolved_path == tarball_path.resolve() or not path.is_file():
                continue
            if not str(resolved_path).startswith(str(source_root)):
                raise RuntimeError(f"Refusing to package path outside output dir: {path}")
            archive.add(path, arcname=path.relative_to(source_dir))
    return tarball_path


def main() -> None:
    model_input_dir = Path(os.environ.get("MODEL_INPUT_DIR", "/opt/ml/processing/input/model"))
    colmap_input_dir = Path(os.environ.get("COLMAP_INPUT_DIR", "/opt/ml/processing/input/colmap"))
    output_dir = Path(os.environ.get("OUTPUT_DIR", "/opt/ml/processing/output"))
    temp_dir = Path("/tmp/no_retrain_quality_pass")
    config_path = Path("/opt/ml/code/nerfstudio_config.yaml")

    logger.info("🚀 Starting no-retrain export quality pass")
    logger.info(f"📦 Model input: {model_input_dir}")
    logger.info(f"📁 COLMAP input: {colmap_input_dir}")
    logger.info(f"📁 Output dir: {output_dir}")

    model_tarball = find_model_artifact(model_input_dir)
    extracted_model_dir = extract_model_artifact(model_tarball, temp_dir / "model")
    source_configs = sorted(extracted_model_dir.rglob("config.yml"))
    if not source_configs:
        raise FileNotFoundError(f"No config.yml found in extracted model artifact {model_tarball}")
    source_config = source_configs[0]

    trainer = NerfStudioTrainer(str(config_path))
    trainer.input_dir = colmap_input_dir
    trainer.output_dir = output_dir
    trainer.temp_dir = temp_dir / "work"
    trainer.output_dir.mkdir(parents=True, exist_ok=True)
    trainer.temp_dir.mkdir(parents=True, exist_ok=True)

    if not trainer.validate_input_data():
        raise RuntimeError("COLMAP validation/conversion failed for export-only quality pass")

    patched_config_path = patch_config_data_path(
        source_config=source_config,
        data_dir=trainer.input_dir,
        patched_config_path=temp_dir / "patched" / "config.yml",
    )
    logger.info(f"📄 Patched config for export: {patched_config_path}")

    if not trainer.export_trained_model(source_config=patched_config_path):
        raise RuntimeError("Model export failed during no-retrain quality pass")

    metadata = trainer.generate_training_metadata()
    trainer.cleanup_temp_files()

    packaged_model_artifact = output_dir / "model.tar.gz"
    summary = {
        "model_artifact": str(model_tarball),
        "packaged_model_artifact": str(packaged_model_artifact),
        "patched_config": str(patched_config_path),
        "training_metadata": metadata,
    }
    summary_path = output_dir / "export_quality_pass_summary.json"
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    build_model_tarball(output_dir, packaged_model_artifact)
    logger.info(f"📦 Packaged no-retrain model artifact: {packaged_model_artifact}")
    logger.info(f"✅ No-retrain export quality pass complete: {summary_path}")


if __name__ == "__main__":
    main()
