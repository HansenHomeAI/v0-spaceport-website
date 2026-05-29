import importlib.util
import json
import os
import sys
import tarfile
import tempfile
import types
import unittest
from unittest import mock
from pathlib import Path


def load_export_quality_pass_module(trainer_cls=None):
    fake_trainer_module = types.ModuleType("train_nerfstudio_production")
    fake_trainer_module.NerfStudioTrainer = trainer_cls or object
    sys.modules["train_nerfstudio_production"] = fake_trainer_module
    fake_yaml_module = types.ModuleType("yaml")
    fake_yaml_module.safe_load = lambda handle: {}
    fake_yaml_module.safe_dump = lambda payload, handle, sort_keys=False: handle.write("{}\n")
    sys.modules["yaml"] = fake_yaml_module

    module_path = (
        Path(__file__).resolve().parents[2]
        / "infrastructure"
        / "containers"
        / "3dgs"
        / "run_export_quality_pass.py"
    )
    spec = importlib.util.spec_from_file_location("run_export_quality_pass", module_path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class RunExportQualityPassTest(unittest.TestCase):
    def test_build_model_tarball_skips_the_tarball_it_creates(self):
        module = load_export_quality_pass_module()
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp)
            (output_dir / "splat.ply").write_text("ply\n", encoding="utf-8")
            (output_dir / "nested").mkdir()
            (output_dir / "nested" / "training_metadata.json").write_text("{}", encoding="utf-8")
            (output_dir / "model.tar.gz").write_bytes(b"old")

            tarball = module.build_model_tarball(output_dir, output_dir / "model.tar.gz")

            self.assertEqual(tarball, output_dir / "model.tar.gz")
            with tarfile.open(tarball, "r:gz") as archive:
                names = sorted(archive.getnames())
            self.assertEqual(names, ["nested/training_metadata.json", "splat.ply"])

    def test_main_direct_ply_prune_packages_exported_artifact_without_config(self):
        class FakeTrainer:
            def __init__(self, config_path):
                self.config_path = config_path
                self.input_dir = None
                self.output_dir = None
                self.temp_dir = None

            def validate_input_data(self):
                self.input_dir = self.temp_dir / "converted_data"
                self.input_dir.mkdir(parents=True, exist_ok=True)
                return True

            def prune_exported_foreground(self):
                (self.output_dir / "floater_pruning_summary.json").write_text(
                    json.dumps({"enabled": True, "removed_gaussians": 3}),
                    encoding="utf-8",
                )

            def cap_exported_foreground_density(self):
                return None

            def patch_export_manifests(self):
                (self.output_dir / "export_manifest.json").write_text(
                    json.dumps({"floater_pruning": {"removed_gaussians": 3}}),
                    encoding="utf-8",
                )

            def generate_training_metadata(self):
                return {"training_completed": True}

            def cleanup_temp_files(self):
                return None

        module = load_export_quality_pass_module(FakeTrainer)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            model_input_dir = root / "model"
            colmap_input_dir = root / "colmap"
            output_dir = root / "output"
            artifact_root = root / "artifact"
            model_input_dir.mkdir()
            colmap_input_dir.mkdir()
            artifact_root.mkdir()
            (artifact_root / "splat.ply").write_text("ply\n", encoding="utf-8")
            (artifact_root / "training_metadata.json").write_text("{}", encoding="utf-8")
            with tarfile.open(model_input_dir / "model.tar.gz", "w:gz") as archive:
                archive.add(artifact_root / "splat.ply", arcname="splat.ply")
                archive.add(artifact_root / "training_metadata.json", arcname="training_metadata.json")

            with mock.patch.dict(
                os.environ,
                {
                    "MODEL_INPUT_DIR": str(model_input_dir),
                    "COLMAP_INPUT_DIR": str(colmap_input_dir),
                    "OUTPUT_DIR": str(output_dir),
                },
            ):
                module.main()

            summary = json.loads((output_dir / "export_quality_pass_summary.json").read_text(encoding="utf-8"))
            self.assertEqual(summary["mode"], "direct_ply_prune")
            self.assertIsNone(summary["patched_config"])
            with tarfile.open(output_dir / "model.tar.gz", "r:gz") as archive:
                names = sorted(archive.getnames())
            self.assertIn("splat.ply", names)
            self.assertIn("floater_pruning_summary.json", names)
            self.assertNotIn("model.tar.gz", names)


if __name__ == "__main__":
    unittest.main()
