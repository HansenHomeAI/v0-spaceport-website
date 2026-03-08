import json
import sys
import tempfile
import time
import types
import unittest
from pathlib import Path


MODULE_ROOT = Path(__file__).resolve().parents[2] / "infrastructure" / "containers" / "sfm"
if str(MODULE_ROOT) not in sys.path:
    sys.path.insert(0, str(MODULE_ROOT))

sys.modules.setdefault("yaml", types.ModuleType("yaml"))
gps_processor_stub = types.ModuleType("gps_processor")
gps_processor_stub.DroneFlightPathProcessor = object
sys.modules.setdefault("gps_processor", gps_processor_stub)
gps_processor_3d_stub = types.ModuleType("gps_processor_3d")
gps_processor_3d_stub.Advanced3DPathProcessor = object
sys.modules.setdefault("gps_processor_3d", gps_processor_3d_stub)
colmap_converter_stub = types.ModuleType("colmap_converter")
colmap_converter_stub.OpenSfMToCOLMAPConverter = object
sys.modules.setdefault("colmap_converter", colmap_converter_stub)

from run_opensfm_gps import OpenSfMGPSPipeline


class SfmMetadataTests(unittest.TestCase):
    def test_metadata_includes_runtime_diagnostics(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            input_dir = root / "input"
            output_dir = root / "output"
            opensfm_dir = root / "opensfm"
            input_dir.mkdir()
            output_dir.mkdir()
            opensfm_dir.mkdir()

            reconstruction = [
                {
                    "shots": {f"image-{index}.jpg": {"camera": "cam"} for index in range(6)},
                    "points": {str(index): {"coordinates": [0, 0, 0]} for index in range(1500)},
                }
            ]
            (opensfm_dir / "reconstruction.json").write_text(json.dumps(reconstruction), encoding="utf-8")

            pipeline = OpenSfMGPSPipeline(input_dir, output_dir)
            pipeline.opensfm_dir = opensfm_dir
            pipeline.image_count = 12
            pipeline.sfm_only = True
            pipeline.sfm_instance_type = "ml.c6i.4xlarge"
            pipeline.feature_stats = {
                "selected_profile": "large_dataset",
                "selected_neighbors": 10,
                "estimated_pairs": 120,
                "stage_timeouts": {"match_features": 7200, "reconstruct": 7200},
            }
            pipeline.stage_metrics = {
                "match_features": {"duration_seconds": 123.4, "peak_memory_mb": 2048.5},
            }
            pipeline.peak_memory_mb = 3072.25
            pipeline._start_time = time.time() - 10

            pipeline.generate_metadata_json()

            metadata = json.loads((output_dir / "sfm_metadata.json").read_text(encoding="utf-8"))
            self.assertEqual(metadata["selected_profile"], "large_dataset")
            self.assertEqual(metadata["selected_neighbors"], 10)
            self.assertEqual(metadata["estimated_pairs"], 120)
            self.assertEqual(metadata["instance_type"], "ml.c6i.4xlarge")
            self.assertTrue(metadata["sfm_only"])
            self.assertIn("match_features", metadata["stage_metrics"])
            self.assertEqual(metadata["peak_memory_mb"], 3072.25)


if __name__ == "__main__":
    unittest.main()
