import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


MODULE_ROOT = Path(__file__).resolve().parents[2] / "infrastructure" / "containers" / "sfm"
if str(MODULE_ROOT) not in sys.path:
    sys.path.insert(0, str(MODULE_ROOT))

from colmap_runner import ColmapRunner
from model_analyzer import SparseModelMetrics


class ColmapRunnerFallbackTests(unittest.TestCase):
    def test_mapper_chain_falls_back_when_global_mapper_registers_too_few_images(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            runner = ColmapRunner(
                work_dir=root,
                source_images_dir=root,
                runtime_plan={
                    "worker_threads": 2,
                    "global_mapper_min_registered_ratio": 0.85,
                },
            )

            commands = []

            def fake_run_command(command, *, segment_id, stage):
                commands.append(command[1])

            def fake_resolve_model_dir(output_dir):
                return Path(output_dir)

            metrics = [
                SparseModelMetrics(1, 4, 100, 10.0, 2.0, 0.5, ["a", "b", "c", "d"]),
                SparseModelMetrics(1, 10, 200, 12.0, 2.5, 0.4, [f"img_{i}" for i in range(10)]),
            ]

            with mock.patch.object(runner, "_run_command", side_effect=fake_run_command), \
                mock.patch.object(runner, "_resolve_model_dir", side_effect=fake_resolve_model_dir), \
                mock.patch.object(runner, "command_available", side_effect=lambda name: name != "pose_prior_mapper"), \
                mock.patch("colmap_runner.analyze_sparse_text_model", side_effect=metrics):
                engine, model_dir = runner._run_mapper_chain(
                    root / "database.db",
                    root / "images",
                    root / "sparse",
                    10,
                    "segment-000",
                )

            self.assertEqual(engine, "mapper")
            self.assertEqual(model_dir, root / "sparse" / "mapper")
            self.assertIn("global_mapper", commands)
            self.assertIn("mapper", commands)


if __name__ == "__main__":
    unittest.main()
