import json
import sys
import tarfile
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import numpy as np
from PIL import Image


REPO_ROOT = Path(__file__).resolve().parents[2]
CONTAINER_DIR = REPO_ROOT / "infrastructure" / "containers" / "3dgs"
if str(CONTAINER_DIR) not in sys.path:
    sys.path.insert(0, str(CONTAINER_DIR))

from run_export_quality_pass import repair_artifact_without_checkpoint  # noqa: E402


class _DummyResult:
    def __init__(self, payload):
        self.payload = payload

    def to_dict(self):
        return dict(self.payload)


class _DummyTrainer:
    def __init__(self, input_dir: Path, output_dir: Path):
        self.input_dir = input_dir
        self.output_dir = output_dir
        self.config = {
            "output": {
                "background_skybox": {
                    "width": 64,
                    "height": 32,
                    "quality": 90,
                    "enable_projected_photo_skybox": True,
                    "composition_mode": "projected_photo_low_frequency",
                    "world_up_source": "colmap_pose_consensus",
                    "min_sky_mask_ratio": 0.01,
                    "min_observations_per_pixel": 1,
                    "blend_edge_feather_px": 24,
                    "low_frequency_fill": True,
                    "projection_max_long_side": 64,
                    "projection_mask_mode": "semantic_horizon_fill",
                    "projection_confidence_threshold": 0.25,
                    "projection_horizon_smoothing_px": 31,
                }
            }
        }
        self.background_selection_result = None
        self.floater_pruning_result = None
        self.semantic_mask_summary = {"enabled": True}

    def get_semantic_mask_settings(self):
        return SimpleNamespace(training_mask_mode="exclude_sky")

    def resolve_background_selection(self):
        self.background_selection_result = _DummyResult({"camera_idx": 3, "resolved_mode": "camera"})
        return self.background_selection_result

    def prune_exported_foreground(self):
        self.floater_pruning_result = _DummyResult({"removed_gaussians": 12})
        return self.floater_pruning_result

    def patch_export_manifests(self):
        background_manifest_path = self.output_dir / "background_manifest.json"
        export_manifest_path = self.output_dir / "export_manifest.json"
        if background_manifest_path.exists():
            payload = json.loads(background_manifest_path.read_text(encoding="utf-8"))
            payload["patched"] = True
            background_manifest_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        if export_manifest_path.exists():
            payload = json.loads(export_manifest_path.read_text(encoding="utf-8"))
            payload["patched"] = True
            export_manifest_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    def generate_training_metadata(self):
        return {"generated": True}


class RunExportQualityPassTests(unittest.TestCase):
    def test_repair_artifact_without_checkpoint_rebuilds_sidecars_and_tarball(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            extracted_model_dir = temp_path / "extracted"
            extracted_model_dir.mkdir()
            output_dir = temp_path / "output"
            output_dir.mkdir()

            (extracted_model_dir / "splat.ply").write_bytes(b"ply\nformat binary_little_endian 1.0\nend_header\n")
            (extracted_model_dir / "semantic_sky_mask_summary.json").write_text(
                json.dumps({"registered_image_count": 10}),
                encoding="utf-8",
            )

            trainer = _DummyTrainer(input_dir=temp_path / "converted_data", output_dir=output_dir)
            summary = {"model_artifact": "s3://example-bucket/model.tar.gz"}

            def fake_projected_skybox(**kwargs):
                image = Image.new("RGB", (64, 32), color=(120, 180, 255))
                image.save(output_dir / "background_skybox.webp", format="WEBP", quality=90)
                image.save(output_dir / "background_skybox_observed.webp", format="WEBP", quality=90)
                image.save(output_dir / "background_skybox_fill.webp", format="WEBP", quality=90)
                Image.fromarray(np.full((32, 64), 255, dtype=np.uint8), mode="L").save(
                    output_dir / "background_skybox_coverage.png"
                )
                payload = {
                    "asset": "background_skybox.webp",
                    "background_skybox_generation_method": kwargs["settings"].composition_mode,
                    "observed_coverage_ratio": 0.8,
                }
                (output_dir / "background_manifest.json").write_text(
                    json.dumps(payload, indent=2),
                    encoding="utf-8",
                )
                return payload

            with patch("run_export_quality_pass.build_projected_photo_skybox", side_effect=fake_projected_skybox):
                repair_artifact_without_checkpoint(
                    trainer=trainer,
                    extracted_model_dir=extracted_model_dir,
                    output_dir=output_dir,
                    summary=summary,
                )

            self.assertEqual(summary["repair_mode"], "projected_photo_from_saved_ply")
            self.assertTrue((output_dir / "splat.ply").exists())
            self.assertTrue((output_dir / "background_skybox.webp").exists())
            self.assertTrue((output_dir / "training_metadata.json").exists())
            self.assertTrue((output_dir / "export_manifest.json").exists())
            self.assertTrue((output_dir / "repaired_model.tar.gz").exists())

            background_manifest = json.loads((output_dir / "background_manifest.json").read_text(encoding="utf-8"))
            training_metadata = json.loads((output_dir / "training_metadata.json").read_text(encoding="utf-8"))
            self.assertEqual(background_manifest["artifact_repair_mode"], "projected_photo_from_saved_ply")
            self.assertTrue(background_manifest["patched"])
            self.assertFalse(training_metadata["background_model_enabled"])
            self.assertEqual(training_metadata["artifact_repair_mode"], "projected_photo_from_saved_ply")

            with tarfile.open(output_dir / "repaired_model.tar.gz", "r:gz") as tar:
                members = tar.getnames()
            self.assertIn("splat.ply", members)
            self.assertIn("background_skybox.webp", members)
            self.assertIn("training_metadata.json", members)


if __name__ == "__main__":
    unittest.main()
