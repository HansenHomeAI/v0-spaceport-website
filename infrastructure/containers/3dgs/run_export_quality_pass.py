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
from typing import Any, Optional, TYPE_CHECKING

import numpy as np
import yaml

from projected_skybox import ProjectedSkyboxSettings, build_projected_photo_skybox

if TYPE_CHECKING:
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


def find_first_path(root: Path, pattern: str) -> Optional[Path]:
    matches = sorted(root.rglob(pattern))
    return matches[0] if matches else None


def load_json_if_exists(path: Optional[Path]) -> Optional[dict[str, Any]]:
    if path is None or not path.exists():
        return None
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def build_projected_settings(trainer: NerfStudioTrainer) -> ProjectedSkyboxSettings:
    skybox_settings = trainer.config.get("output", {}).get("background_skybox", {})
    semantic_mask_settings = trainer.get_semantic_mask_settings()
    return ProjectedSkyboxSettings(
        enabled=bool(skybox_settings.get("enable_projected_photo_skybox", True)),
        composition_mode=str(skybox_settings.get("composition_mode", "projected_photo_low_frequency")),
        world_up_source=str(skybox_settings.get("world_up_source", "colmap_pose_consensus")),
        min_sky_mask_ratio=float(skybox_settings.get("min_sky_mask_ratio", 0.01)),
        min_observations_per_pixel=int(skybox_settings.get("min_observations_per_pixel", 1)),
        blend_edge_feather_px=int(skybox_settings.get("blend_edge_feather_px", 24)),
        low_frequency_fill=bool(skybox_settings.get("low_frequency_fill", True)),
        training_mask_mode=str(semantic_mask_settings.training_mask_mode),
        projection_max_long_side=int(skybox_settings.get("projection_max_long_side", 1024)),
        projection_mask_mode=str(skybox_settings.get("projection_mask_mode", "semantic_horizon_fill")),
        projection_confidence_threshold=float(skybox_settings.get("projection_confidence_threshold", 0.25)),
        projection_horizon_smoothing_px=int(skybox_settings.get("projection_horizon_smoothing_px", 31)),
        photometric_alignment_strength=float(skybox_settings.get("photometric_alignment_strength", 0.65)),
        base_saturation_scale=float(skybox_settings.get("base_saturation_scale", 0.78)),
        detail_luma_strength=float(skybox_settings.get("detail_luma_strength", 0.85)),
        detail_chroma_strength=float(skybox_settings.get("detail_chroma_strength", 0.12)),
        detail_horizon_margin_px=int(skybox_settings.get("detail_horizon_margin_px", 24)),
        detail_mask_erosion_px=int(skybox_settings.get("detail_mask_erosion_px", 3)),
        min_projected_elevation=float(skybox_settings.get("min_projected_elevation", 0.0)),
        observed_blur_radius_px=int(skybox_settings.get("observed_blur_radius_px", 20)),
        detail_blur_radius_px=int(skybox_settings.get("detail_blur_radius_px", 10)),
    )


def create_repaired_artifact_tarball(output_dir: Path, tarball_path: Path) -> Path:
    artifact_names = [
        "splat.ply",
        "background_skybox.webp",
        "background_skybox_observed.webp",
        "background_skybox_fill.webp",
        "background_skybox_base.webp",
        "background_skybox_detail.webp",
        "background_skybox_detail_support.png",
        "background_skybox_coverage.png",
        "background_manifest.json",
        "export_manifest.json",
        "training_metadata.json",
        "semantic_sky_mask_summary.json",
        "floater_pruning_summary.json",
        "export_quality_pass_summary.json",
    ]
    with tarfile.open(tarball_path, "w:gz") as tar:
        for name in artifact_names:
            candidate = output_dir / name
            if candidate.exists():
                tar.add(candidate, arcname=name)
    return tarball_path


def repair_artifact_without_checkpoint(
    trainer: NerfStudioTrainer,
    extracted_model_dir: Path,
    output_dir: Path,
    summary: dict[str, Any],
) -> None:
    ply_path = find_first_path(extracted_model_dir, "splat.ply") or find_first_path(extracted_model_dir, "*.ply")
    if ply_path is None:
        raise FileNotFoundError(f"No splat.ply or other .ply file found in extracted model artifact {extracted_model_dir}")

    copied_ply_path = output_dir / "splat.ply"
    shutil.copy2(ply_path, copied_ply_path)
    logger.info("📄 Reused foreground PLY from timed-out artifact: %s", ply_path)

    original_semantic_summary = load_json_if_exists(find_first_path(extracted_model_dir, "semantic_sky_mask_summary.json"))
    if original_semantic_summary is not None:
        summary["original_semantic_sky_mask_summary"] = original_semantic_summary

    skybox_config = trainer.config.get("output", {}).get("background_skybox", {})
    projected_settings = build_projected_settings(trainer)
    trainer.resolve_background_selection()

    fill_rgb = np.zeros(
        (
            int(skybox_config.get("height", 1024)),
            int(skybox_config.get("width", 2048)),
            3,
        ),
        dtype=np.float32,
    )

    background_manifest = build_projected_photo_skybox(
        data_dir=trainer.input_dir,
        output_dir=output_dir,
        width=int(skybox_config.get("width", 2048)),
        height=int(skybox_config.get("height", 1024)),
        quality=int(skybox_config.get("quality", 95)),
        fill_rgb=fill_rgb,
        settings=projected_settings,
    )
    background_manifest["artifact_repair_mode"] = "projected_photo_from_saved_ply"
    background_manifest["background_model_enabled"] = False
    (output_dir / "background_manifest.json").write_text(json.dumps(background_manifest, indent=2), encoding="utf-8")

    export_manifest = {
        "ply": copied_ply_path.name,
        "skybox": "background_skybox.webp",
        "projected_photo_skybox": True,
        "skybox_composition_mode": projected_settings.composition_mode,
        "training_mask_mode": projected_settings.training_mask_mode,
        "artifact_repair_mode": "projected_photo_from_saved_ply",
        "source_model_artifact": str(summary["model_artifact"]),
    }
    (output_dir / "export_manifest.json").write_text(json.dumps(export_manifest, indent=2), encoding="utf-8")

    trainer.prune_exported_foreground()
    trainer.patch_export_manifests()
    metadata = trainer.generate_training_metadata()
    metadata["artifact_repair_mode"] = "projected_photo_from_saved_ply"
    metadata["original_model_artifact"] = str(summary["model_artifact"])
    metadata["background_model_enabled"] = False
    with open(output_dir / "training_metadata.json", "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2)

    repaired_tarball = create_repaired_artifact_tarball(
        output_dir=output_dir,
        tarball_path=output_dir / "repaired_model.tar.gz",
    )
    summary.update(
        {
            "repair_mode": "projected_photo_from_saved_ply",
            "copied_ply": str(copied_ply_path),
            "background_manifest": str(output_dir / "background_manifest.json"),
            "training_metadata": metadata,
            "repaired_model_tarball": str(repaired_tarball),
        }
    )


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

    trainer = NerfStudioTrainer(str(config_path))
    trainer.input_dir = colmap_input_dir
    trainer.source_input_dir = colmap_input_dir
    trainer.output_dir = output_dir
    trainer.temp_dir = temp_dir / "work"
    trainer.output_dir.mkdir(parents=True, exist_ok=True)
    trainer.temp_dir.mkdir(parents=True, exist_ok=True)

    if not trainer.validate_input_data():
        raise RuntimeError("COLMAP validation/conversion failed for export-only quality pass")

    summary = {
        "model_artifact": str(model_tarball),
    }
    if source_configs:
        source_config = source_configs[0]
        patched_config_path = patch_config_data_path(
            source_config=source_config,
            data_dir=trainer.input_dir,
            patched_config_path=temp_dir / "patched" / "config.yml",
        )
        logger.info(f"📄 Patched config for export: {patched_config_path}")

        if not trainer.export_trained_model(source_config=patched_config_path):
            raise RuntimeError("Model export failed during no-retrain quality pass")

        metadata = trainer.generate_training_metadata()
        summary.update(
            {
                "repair_mode": "checkpoint_export",
                "patched_config": str(patched_config_path),
                "training_metadata": metadata,
            }
        )
    else:
        logger.warning(
            "⚠️ No config.yml found in extracted model artifact %s. "
            "Falling back to projected-photo repair from saved splat.ply only.",
            model_tarball,
        )
        repair_artifact_without_checkpoint(
            trainer=trainer,
            extracted_model_dir=extracted_model_dir,
            output_dir=output_dir,
            summary=summary,
        )

    summary_path = output_dir / "export_quality_pass_summary.json"
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    trainer.cleanup_temp_files()
    logger.info(f"✅ No-retrain export quality pass complete: {summary_path}")


if __name__ == "__main__":
    main()
