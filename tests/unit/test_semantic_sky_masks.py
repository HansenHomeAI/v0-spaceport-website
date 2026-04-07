import json
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np


REPO_ROOT = Path(__file__).resolve().parents[2]
CONTAINER_DIR = REPO_ROOT / "infrastructure" / "containers" / "3dgs"
if str(CONTAINER_DIR) not in sys.path:
    sys.path.insert(0, str(CONTAINER_DIR))

from semantic_sky_masks import (  # noqa: E402
    SemanticSkyMaskSettings,
    attach_masks_to_transforms,
    post_process_semantic_sky_mask,
)


class SemanticSkyMaskTests(unittest.TestCase):
    def test_post_process_keeps_top_connected_sky_and_fills_small_holes(self):
        mask = np.zeros((10, 10), dtype=bool)
        mask[:3, :] = True
        mask[1, 4] = False  # small interior hole that should be filled
        mask[5:7, 2:6] = True  # disconnected horizon swallow that should be removed
        mask[8, 8] = True  # isolated island that should be removed

        processed = post_process_semantic_sky_mask(
            mask=mask,
            min_component_area_ratio=0.02,
            fill_hole_area_ratio=0.02,
            keep_top_connected_only=True,
        )

        self.assertTrue(processed[1, 4], "small hole inside the kept sky region should be filled")
        self.assertFalse(processed[8, 8], "small isolated islands should be removed")
        self.assertFalse(processed[5, 3], "sky regions not connected to the top border should be removed")
        self.assertTrue(processed[0, 0], "top-connected sky should remain")
        self.assertTrue(processed[2, 9], "top-connected sky should remain across the horizon width")

    def test_attach_masks_to_transforms_adds_mask_paths_when_enabled(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            converted_dir = temp_path / "converted_data"
            converted_dir.mkdir()
            transforms_path = converted_dir / "transforms.json"

            transforms = {
                "frames": [
                    {"file_path": "images/frame_00001.png", "colmap_im_id": 11},
                    {"file_path": "images/frame_00002.png", "colmap_im_id": 22},
                ]
            }
            transforms_path.write_text(json.dumps(transforms), encoding="utf-8")

            source_mask_a = temp_path / "source-mask-a.png"
            source_mask_b = temp_path / "source-mask-b.png"
            source_mask_a.write_bytes(b"mask-a")
            source_mask_b.write_bytes(b"mask-b")

            source_summary = {
                "records_by_id": {
                    11: {
                        "image_id": 11,
                        "image_name": "IMG_001.png",
                        "mask_path": str(source_mask_a),
                        "mask_ratio": 0.21,
                        "top_border_ratio": 0.70,
                    },
                    22: {
                        "image_id": 22,
                        "image_name": "IMG_002.png",
                        "mask_path": str(source_mask_b),
                        "mask_ratio": 0.32,
                        "top_border_ratio": 0.81,
                    },
                },
                "records_by_name": {},
                "mask_records": [],
            }

            summary = attach_masks_to_transforms(
                transforms_path=transforms_path,
                converted_data_dir=converted_dir,
                source_summary=source_summary,
                settings=SemanticSkyMaskSettings(enabled=True),
            )

            saved = json.loads(transforms_path.read_text(encoding="utf-8"))
            self.assertEqual(saved["frames"][0]["mask_path"], "masks/frame_00001.png")
            self.assertEqual(saved["frames"][1]["mask_path"], "masks/frame_00002.png")
            self.assertEqual((converted_dir / "masks" / "frame_00001.png").read_bytes(), b"mask-a")
            self.assertEqual((converted_dir / "masks" / "frame_00002.png").read_bytes(), b"mask-b")
            self.assertEqual(summary["frames_with_masks"], 2)
            self.assertEqual(summary["mapping_strategy_counts"], {"colmap_im_id": 2})

    def test_attach_masks_to_transforms_strips_masks_when_disabled(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            converted_dir = temp_path / "converted_data"
            converted_dir.mkdir()
            transforms_path = converted_dir / "transforms.json"
            transforms_path.write_text(
                json.dumps(
                    {
                        "frames": [
                            {"file_path": "images/frame_00001.png", "mask_path": "masks/old.png"},
                            {"file_path": "images/frame_00002.png", "mask_path": "masks/old2.png"},
                        ]
                    }
                ),
                encoding="utf-8",
            )

            summary = attach_masks_to_transforms(
                transforms_path=transforms_path,
                converted_data_dir=converted_dir,
                source_summary={},
                settings=SemanticSkyMaskSettings(enabled=False),
            )

            saved = json.loads(transforms_path.read_text(encoding="utf-8"))
            self.assertNotIn("mask_path", saved["frames"][0])
            self.assertNotIn("mask_path", saved["frames"][1])
            self.assertFalse(summary["enabled"])
            self.assertEqual(summary["frames_with_masks"], 0)


if __name__ == "__main__":
    unittest.main()
