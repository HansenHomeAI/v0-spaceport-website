import importlib.util
import json
import os
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest import mock


REPO_ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = REPO_ROOT / "infrastructure" / "containers" / "3dgs" / "train_nerfstudio_production.py"
CONFIG_PATH = REPO_ROOT / "infrastructure" / "containers" / "3dgs" / "nerfstudio_config.yaml"


def load_training_module():
    original_torch = sys.modules.get("torch")
    original_yaml = sys.modules.get("yaml")
    sys.modules["torch"] = types.SimpleNamespace(
        _dynamo=types.SimpleNamespace(config=types.SimpleNamespace(suppress_errors=False))
    )
    sys.modules["yaml"] = types.SimpleNamespace(safe_load=lambda _handle: {})
    try:
        spec = importlib.util.spec_from_file_location("nerfstudio_training_quality_test_module", MODULE_PATH)
        module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = module
        spec.loader.exec_module(module)
        return module
    finally:
        if original_torch is None:
            sys.modules.pop("torch", None)
        else:
            sys.modules["torch"] = original_torch
        if original_yaml is None:
            sys.modules.pop("yaml", None)
        else:
            sys.modules["yaml"] = original_yaml


class NerfstudioTrainingQualityGateTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.training = load_training_module()

    def test_ns_eval_report_passes_only_with_all_metrics_and_panels(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            render_dir = root / "renders"
            render_dir.mkdir()
            (render_dir / "heldout-000.png").write_bytes(b"fake")
            raw = root / "ns_eval.json"
            raw.write_text(
                json.dumps(
                    {
                        "num_eval_images": 1,
                        "results": {
                            "eval/psnr": 28.0,
                            "eval/ssim": 0.86,
                            "eval/lpips": 0.16,
                        },
                    }
                ),
                encoding="utf-8",
            )

            report = self.training.build_splat_heldout_render_report(raw, render_dir, root / "config.yml")

        self.assertEqual(report["decision"], "pass")
        self.assertEqual(report["holdout_count"], 1)
        self.assertEqual(report["successful_render_count"], 1)
        self.assertEqual(report["metrics"]["lpips"]["median"], 0.16)
        self.assertEqual(report["proof_panels"]["count"], 1)

    def test_ns_eval_report_fails_without_lpips_or_render_panels(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            raw = root / "ns_eval.json"
            raw.write_text(json.dumps({"num_eval_images": 2, "results": {"psnr": 25.0, "ssim": 0.8}}), encoding="utf-8")

            report = self.training.build_splat_heldout_render_report(raw, root / "missing-renders", root / "config.yml")

        self.assertEqual(report["decision"], "fail")
        self.assertIn("missing_lpips", report["blockers"])
        self.assertIn("missing_render_proof_panels", report["blockers"])

    def test_container_config_enables_required_heldout_eval(self):
        config_text = CONFIG_PATH.read_text(encoding="utf-8")
        self.assertIn("quality:", config_text)
        self.assertIn("heldout_eval:", config_text)
        self.assertIn("enabled: true", config_text)
        self.assertIn("fail_on_missing_metrics: true", config_text)

    def test_ns_eval_preserves_config_snapshot_inside_model_artifact(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            config = root / "container_config.yaml"
            config.write_text("quality:\n  heldout_eval:\n    enabled: true\n", encoding="utf-8")
            with mock.patch.dict(
                os.environ,
                {
                    "SM_MODEL_DIR": str(root / "model"),
                    "SM_CHANNEL_TRAINING": str(root / "input"),
                },
            ):
                trainer = self.training.NerfStudioTrainer(str(config))
            trainer.output_dir = root / "model"
            trainer.temp_dir = root / "training"
            run_dir = trainer.temp_dir / "run"
            run_dir.mkdir(parents=True)
            latest_config = run_dir / "config.yml"
            latest_config.write_text("method_name: splatfacto\n", encoding="utf-8")

            def fake_run_logged_command(cmd, *, timeout_seconds, log_prefix, tail_limit=120):
                raw_path = Path(cmd[cmd.index("--output-path") + 1])
                render_dir = Path(cmd[cmd.index("--render-output-path") + 1])
                render_dir.mkdir(parents=True, exist_ok=True)
                (render_dir / "heldout-000.png").write_bytes(b"fake")
                raw_path.write_text(
                    json.dumps(
                        {
                            "num_eval_images": 1,
                            "results": {
                                "eval/psnr": 28.0,
                                "eval/ssim": 0.86,
                                "eval/lpips": 0.16,
                            },
                        }
                    ),
                    encoding="utf-8",
                )
                return 0, [f"{log_prefix}complete"], False

            with mock.patch.object(self.training, "run_logged_command", side_effect=fake_run_logged_command):
                self.assertTrue(trainer.run_nerfstudio_evaluation())

            eval_dir = trainer.output_dir / "quality_eval"
            snapshot = eval_dir / "nerfstudio_config.yml"
            report = json.loads((eval_dir / "splat_heldout_render_metrics.json").read_text(encoding="utf-8"))
            stdout_log = (eval_dir / "ns_eval_stdout.log").read_text(encoding="utf-8")

            self.assertTrue(snapshot.exists())
            self.assertEqual(snapshot.read_text(encoding="utf-8"), "method_name: splatfacto\n")
            self.assertEqual(report["load_config"], str(snapshot))
            self.assertIn("NS_EVAL: complete", stdout_log)

    def test_training_uses_supported_cpu_image_cache_by_default(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            config = root / "container_config.yaml"
            config.write_text("training:\n  max_iterations: 10\n", encoding="utf-8")
            with mock.patch.dict(
                os.environ,
                {
                    "SM_MODEL_DIR": str(root / "model"),
                    "SM_CHANNEL_TRAINING": str(root / "input"),
                },
                clear=False,
            ):
                trainer = self.training.NerfStudioTrainer(str(config))
            trainer.config = {
                "model": {"variant": "splatfacto", "sh_degree": 3, "bilateral_processing": False},
                "training": {"max_iterations": 10, "log_interval": 5},
            }

            captured = {}

            def fake_run_logged_command(cmd, *, timeout_seconds, log_prefix, tail_limit=120):
                captured["cmd"] = cmd
                return 0, ["done"], False

            with mock.patch.dict(os.environ, {"NS_CACHE_IMAGES": "disk"}, clear=False):
                with mock.patch.object(self.training, "run_logged_command", side_effect=fake_run_logged_command):
                    self.assertTrue(trainer.run_nerfstudio_training())

            cmd = captured["cmd"]
            cache_index = cmd.index("--pipeline.datamanager.cache-images") + 1
            self.assertEqual(cmd[cache_index], "cpu")

    def test_training_forces_heldout_split_for_tiny_canary_samples(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            config = root / "container_config.yaml"
            config.write_text("training:\n  max_iterations: 10\n", encoding="utf-8")
            input_dir = root / "input"
            input_dir.mkdir()
            (input_dir / "transforms.json").write_text(
                json.dumps({"frames": [{"file_path": f"images/{index}.jpg"} for index in range(8)]}),
                encoding="utf-8",
            )
            with mock.patch.dict(
                os.environ,
                {
                    "SM_MODEL_DIR": str(root / "model"),
                    "SM_CHANNEL_TRAINING": str(input_dir),
                },
                clear=False,
            ):
                trainer = self.training.NerfStudioTrainer(str(config))
            trainer.config = {
                "model": {"variant": "splatfacto", "sh_degree": 3, "bilateral_processing": False},
                "training": {"max_iterations": 10, "log_interval": 5},
            }
            trainer.input_dir = input_dir

            captured = {}

            def fake_run_logged_command(cmd, *, timeout_seconds, log_prefix, tail_limit=120):
                captured["cmd"] = cmd
                return 0, ["done"], False

            with mock.patch.object(self.training, "run_logged_command", side_effect=fake_run_logged_command):
                self.assertTrue(trainer.run_nerfstudio_training())

            cmd = captured["cmd"]
            split_index = cmd.index("--pipeline.datamanager.dataparser.train-split-fraction") + 1
            eval_mode_index = cmd.index("--pipeline.datamanager.dataparser.eval-mode") + 1
            self.assertEqual(cmd[split_index], "0.75")
            self.assertEqual(cmd[eval_mode_index], "fraction")

    def test_training_split_fraction_env_override_is_clamped(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            config = root / "container_config.yaml"
            config.write_text("training:\n  max_iterations: 10\n", encoding="utf-8")
            with mock.patch.dict(
                os.environ,
                {
                    "SM_MODEL_DIR": str(root / "model"),
                    "SM_CHANNEL_TRAINING": str(root / "input"),
                    "NS_TRAIN_SPLIT_FRACTION": "0.99",
                },
                clear=False,
            ):
                trainer = self.training.NerfStudioTrainer(str(config))
                self.assertEqual(trainer.resolve_train_split_fraction({}), 0.95)


if __name__ == "__main__":
    unittest.main()
