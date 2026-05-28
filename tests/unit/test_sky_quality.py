import importlib.util
import sys
import types
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = REPO_ROOT / "infrastructure" / "containers" / "3dgs" / "sky_quality.py"


def load_module_with_stubs():
    pil_stub = types.ModuleType("PIL")
    pil_stub.Image = types.SimpleNamespace()
    original_pil = sys.modules.get("PIL")
    sys.modules["PIL"] = pil_stub
    spec = importlib.util.spec_from_file_location("sky_quality_test_module", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    try:
        sys.modules[spec.name] = module
        spec.loader.exec_module(module)
    finally:
        if original_pil is None:
            sys.modules.pop("PIL", None)
        else:
            sys.modules["PIL"] = original_pil
    return module


class SkyQualityFrameSelectionTests(unittest.TestCase):
    def test_priority_frame_selection_matches_original_names_from_image_map(self):
        module = load_module_with_stubs()
        frames = [
            {"file_path": "images/frame_00157.JPG", "colmap_im_id": 157},
            {"file_path": "images/frame_00165.JPG", "colmap_im_id": 165},
            {"file_path": "images/frame_00166.JPG", "colmap_im_id": 166},
        ]
        image_name_map = {
            "by_converted_name": {
                "frame_00157.JPG": {
                    "original_image_name": "DJI_00801.JPG",
                    "converted_file_path": "images/frame_00157.JPG",
                }
            },
            "by_colmap_im_id": {
                "165": {
                    "original_image_name": "DJI_00809.JPG",
                    "converted_file_path": "images/frame_00165.JPG",
                }
            },
        }

        indices, match_count = module._select_pruning_frame_indices(
            frames,
            sampled_views=1,
            priority_frame_names=["DJI_00801.JPG", "DJI_00809.JPG"],
            image_name_map=image_name_map,
        )

        self.assertEqual(match_count, 2)
        self.assertEqual(indices.tolist(), [0, 1])


if __name__ == "__main__":
    unittest.main()
