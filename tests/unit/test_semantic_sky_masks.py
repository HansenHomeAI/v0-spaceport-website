import json
import sys
import tempfile
import unittest
from io import BytesIO
from pathlib import Path

import numpy as np
from PIL import Image


REPO_ROOT = Path(__file__).resolve().parents[2]
CONTAINER_DIR = REPO_ROOT / "infrastructure" / "containers" / "3dgs"
if str(CONTAINER_DIR) not in sys.path:
    sys.path.insert(0, str(CONTAINER_DIR))

from semantic_sky_masks import (  # noqa: E402
    SemanticSkyMaskSettings,
    attach_masks_to_transforms,
    load_rgb_image_for_semantic_mask,
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
            source_confidence_a = temp_path / "source-mask-a__confidence.png"
            source_confidence_b = temp_path / "source-mask-b__confidence.png"
            Image.fromarray(
                np.array([[255, 255], [0, 0]], dtype=np.uint8),
                mode="L",
            ).save(source_mask_a)
            Image.fromarray(
                np.array([[0, 0], [255, 255]], dtype=np.uint8),
                mode="L",
            ).save(source_mask_b)
            Image.new("L", (2, 2), color=192).save(source_confidence_a)
            Image.new("L", (2, 2), color=224).save(source_confidence_b)

            source_summary = {
                "records_by_id": {
                    11: {
                        "image_id": 11,
                        "image_name": "IMG_001.png",
                        "mask_path": str(source_mask_a),
                        "confidence_path": str(source_confidence_a),
                        "mask_ratio": 0.21,
                        "top_border_ratio": 0.70,
                    },
                    22: {
                        "image_id": 22,
                        "image_name": "IMG_002.png",
                        "mask_path": str(source_mask_b),
                        "confidence_path": str(source_confidence_b),
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
            self.assertEqual(
                saved["frames"][0]["semantic_sky_confidence_path"],
                "semantic_sky_confidence/frame_00001.png",
            )
            with Image.open(converted_dir / "masks" / "frame_00001.png") as training_mask_a:
                self.assertEqual(np.asarray(training_mask_a).tolist(), [[0, 0], [255, 255]])
            with Image.open(converted_dir / "masks" / "frame_00002.png") as training_mask_b:
                self.assertEqual(np.asarray(training_mask_b).tolist(), [[255, 255], [0, 0]])
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
            self.assertNotIn("semantic_sky_confidence_path", saved["frames"][0])
            self.assertFalse(summary["enabled"])
            self.assertEqual(summary["frames_with_masks"], 0)

    def test_attach_masks_to_transforms_writes_downscaled_mask_variants(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            converted_dir = temp_path / "converted_data"
            images_dir = converted_dir / "images"
            images_4_dir = converted_dir / "images_4"
            images_dir.mkdir(parents=True)
            images_4_dir.mkdir(parents=True)

            transforms_path = converted_dir / "transforms.json"
            transforms_path.write_text(
                json.dumps(
                    {
                        "frames": [
                            {"file_path": "images/frame_00001.png", "colmap_im_id": 11},
                        ]
                    }
                ),
                encoding="utf-8",
            )

            Image.new("RGB", (8, 8), color=(20, 30, 40)).save(images_dir / "frame_00001.png")
            Image.new("RGB", (2, 2), color=(20, 30, 40)).save(images_4_dir / "frame_00001.png")

            source_mask = temp_path / "source-mask.png"
            Image.new("L", (8, 8), color=255).save(source_mask)

            source_summary = {
                "records_by_id": {
                    11: {
                        "image_id": 11,
                        "image_name": "IMG_001.png",
                        "mask_path": str(source_mask),
                        "mask_ratio": 1.0,
                        "top_border_ratio": 1.0,
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

            self.assertEqual(summary["downscale_mask_directories"], ["masks_4"])
            self.assertTrue((converted_dir / "masks" / "frame_00001.png").exists())
            self.assertTrue((converted_dir / "masks_4" / "frame_00001.png").exists())
            with Image.open(converted_dir / "masks_4" / "frame_00001.png") as resized_mask:
                self.assertEqual(resized_mask.size, (2, 2))
                self.assertEqual(np.asarray(resized_mask).tolist(), [[0, 0], [0, 0]])

    def test_load_rgb_image_for_semantic_mask_recovers_truncated_jpeg(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            image_path = Path(temp_dir) / "truncated.jpg"
            image = Image.new("RGB", (32, 24), color=(80, 140, 220))
            encoded = BytesIO()
            image.save(encoded, format="JPEG", quality=90)
            truncated_bytes = encoded.getvalue()[:-8]
            image_path.write_bytes(truncated_bytes)

            loaded = load_rgb_image_for_semantic_mask(image_path)

            self.assertEqual(loaded.mode, "RGB")
            self.assertEqual(loaded.size, (32, 24))
            self.assertGreater(np.asarray(loaded).mean(), 0.0)


if __name__ == "__main__":
    unittest.main()
