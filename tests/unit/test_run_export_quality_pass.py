import importlib.util
import sys
import tarfile
import tempfile
import types
import unittest
from pathlib import Path


def load_export_quality_pass_module():
    fake_trainer_module = types.ModuleType("train_nerfstudio_production")
    fake_trainer_module.NerfStudioTrainer = object
    sys.modules.setdefault("train_nerfstudio_production", fake_trainer_module)
    fake_yaml_module = types.ModuleType("yaml")
    fake_yaml_module.safe_load = lambda handle: {}
    fake_yaml_module.safe_dump = lambda payload, handle, sort_keys=False: handle.write("{}\n")
    sys.modules.setdefault("yaml", fake_yaml_module)

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


if __name__ == "__main__":
    unittest.main()
