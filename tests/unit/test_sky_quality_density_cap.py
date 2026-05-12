import importlib.util
import sys
import unittest
from pathlib import Path
import tempfile

import numpy as np
try:
    from plyfile import PlyData, PlyElement
except ModuleNotFoundError:  # pragma: no cover - local host may not have container deps
    PlyData = None
    PlyElement = None


REPO_ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = REPO_ROOT / "infrastructure" / "containers" / "3dgs" / "sky_quality.py"
sky_quality = None
if PlyData is not None and PlyElement is not None:
    SPEC = importlib.util.spec_from_file_location("sky_quality_density_cap_test_module", MODULE_PATH)
    sky_quality = importlib.util.module_from_spec(SPEC)
    assert SPEC and SPEC.loader
    sys.modules[SPEC.name] = sky_quality
    SPEC.loader.exec_module(sky_quality)


def write_opacity_ply(path: Path) -> None:
    vertex_array = np.array(
        [
            (1.0, 0.0, 0.0, -4.0),
            (2.0, 0.0, 0.0, -2.0),
            (3.0, 0.0, 0.0, 0.0),
            (4.0, 0.0, 0.0, 2.0),
            (5.0, 0.0, 0.0, 4.0),
        ],
        dtype=[
            ("x", "f4"),
            ("y", "f4"),
            ("z", "f4"),
            ("opacity", "f4"),
        ],
    )
    PlyData([PlyElement.describe(vertex_array, "vertex")], text=False).write(str(path))


class SkyQualityDensityCapTests(unittest.TestCase):
    @unittest.skipUnless(sky_quality is not None, "plyfile is not installed in this local test environment")
    def test_cap_gaussian_count_by_importance_keeps_highest_opacity(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "splat.ply"
            write_opacity_ply(path)

            result = sky_quality.cap_gaussian_count_by_importance(path, max_gaussians=3)

            vertex = PlyData.read(str(path))["vertex"].data
            self.assertEqual(result.original_gaussians, 5)
            self.assertEqual(result.kept_gaussians, 3)
            self.assertEqual(result.removed_gaussians, 2)
            self.assertEqual([float(x) for x in vertex["x"]], [3.0, 4.0, 5.0])
            self.assertGreaterEqual(result.min_kept_opacity, result.max_removed_opacity)

    @unittest.skipUnless(sky_quality is not None, "plyfile is not installed in this local test environment")
    def test_cap_gaussian_count_noops_when_already_under_limit(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "splat.ply"
            write_opacity_ply(path)

            result = sky_quality.cap_gaussian_count_by_importance(path, max_gaussians=10)

            vertex = PlyData.read(str(path))["vertex"].data
            self.assertEqual(result.original_gaussians, 5)
            self.assertEqual(result.kept_gaussians, 5)
            self.assertEqual(result.removed_gaussians, 0)
            self.assertEqual(len(vertex), 5)


if __name__ == "__main__":
    unittest.main()
