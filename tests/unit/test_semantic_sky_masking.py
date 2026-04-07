import json
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np
from PIL import Image


MODULE_ROOT = Path(__file__).resolve().parents[2] / "infrastructure" / "containers" / "3dgs"
if str(MODULE_ROOT) not in sys.path:
    sys.path.insert(0, str(MODULE_ROOT))

from semantic_sky_masking import (
    SemanticSkyMaskConfig,
    _open_image_rgb,
    build_training_keep_mask,
    materialize_nerfstudio_training_masks,
    postprocess_sky_mask,
)


class SemanticSkyMaskingTests(unittest.TestCase):
    def test_postprocess_keeps_top_connected_sky_and_fills_small_holes(self):
        mask = np.zeros((20, 20), dtype=bool)
        mask[:8, :] = True
        mask[2:4, 2:4] = False
        mask[15:17, 15:17] = True
        mask[9:12, 3:6] = True

        config = SemanticSkyMaskConfig(
            enabled=True,
            min_component_area=0.01,
            fill_hole_area=0.02,
            keep_top_connected_only=True,
        )

        processed = postprocess_sky_mask(mask, config)

        self.assertTrue(processed[0, 0])
        self.assertTrue(processed[2, 2], "small holes inside the sky region should be filled")
        self.assertFalse(processed[15, 15], "isolated islands should be removed")
        self.assertFalse(processed[10, 4], "sky not connected to the top border should be removed")

    def test_build_training_keep_mask_blacks_out_sky(self):
        sky_mask = np.array([[True, False], [False, True]], dtype=bool)
        keep_mask = build_training_keep_mask(sky_mask)

        self.assertEqual(keep_mask.tolist(), [[0, 255], [255, 0]])

    def test_open_image_rgb_recovers_from_truncated_jpeg(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            image_path = Path(temp_dir) / "truncated.JPG"
            Image.new("RGB", (24, 16), color=(64, 128, 255)).save(image_path, format="JPEG")
            original_bytes = image_path.read_bytes()
            image_path.write_bytes(original_bytes[:-8])

            loaded = _open_image_rgb(image_path)

            self.assertEqual(loaded.mode, "RGB")
            self.assertEqual(loaded.size, (24, 16))

    def test_materialize_masks_adds_mask_paths_for_every_frame(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            converted_dir = temp_path / "converted_data"
            images_dir = converted_dir / "images"
            masks_dir = temp_path / "source_masks"
            images_dir.mkdir(parents=True)
            masks_dir.mkdir(parents=True)

            Image.new("RGB", (6, 4), color=(255, 255, 255)).save(images_dir / "frame_00001.JPG")
            Image.new("RGB", (6, 4), color=(255, 255, 255)).save(images_dir / "frame_00002.JPG")

            sky_mask = np.zeros((4, 6), dtype=np.uint8)
            sky_mask[:2, :] = 255
            Image.fromarray(sky_mask, mode="L").save(masks_dir / "source_a.png")
            Image.fromarray(sky_mask, mode="L").save(masks_dir / "source_b.png")

            transforms_path = converted_dir / "transforms.json"
            transforms_path.write_text(
                json.dumps(
                    {
                        "frames": [
                            {"file_path": "images/frame_00001.JPG", "colmap_im_id": 11, "transform_matrix": [[1, 0, 0, 0]] * 4},
                            {"file_path": "images/frame_00002.JPG", "colmap_im_id": 12, "transform_matrix": [[1, 0, 0, 0]] * 4},
                        ]
                    },
                    indent=2,
                ),
                encoding="utf-8",
            )

            colmap_images_path = temp_path / "images.txt"
            colmap_images_path.write_text(
                "\n".join(
                    [
                        "11 1 0 0 0 0 0 0 1 source_a.JPG",
                        "0 0 0",
                        "12 1 0 0 0 0 0 0 1 source_b.JPG",
                        "0 0 0",
                    ]
                ),
                encoding="utf-8",
            )

            summary = materialize_nerfstudio_training_masks(
                enabled=True,
                converted_dir=converted_dir,
                transforms_path=transforms_path,
                source_mask_dir=masks_dir,
                colmap_images_path=colmap_images_path,
                config=SemanticSkyMaskConfig(enabled=True),
            )

            self.assertEqual(summary.frame_count, 2)

            transforms = json.loads(transforms_path.read_text(encoding="utf-8"))
            self.assertEqual(transforms["frames"][0]["mask_path"], "masks/source_a.png")
            self.assertEqual(transforms["frames"][1]["mask_path"], "masks/source_b.png")

            keep_mask = np.asarray(Image.open(converted_dir / "masks" / "source_a.png").convert("L"))
            self.assertTrue(np.all(keep_mask[:2, :] == 0))
            self.assertTrue(np.all(keep_mask[2:, :] == 255))

    def test_materialize_masks_is_noop_when_disabled(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            converted_dir = temp_path / "converted_data"
            converted_dir.mkdir(parents=True)
            transforms_path = converted_dir / "transforms.json"
            transforms_path.write_text(
                json.dumps({"frames": [{"file_path": "images/frame_00001.JPG", "transform_matrix": [[1, 0, 0, 0]] * 4}]}, indent=2),
                encoding="utf-8",
            )

            summary = materialize_nerfstudio_training_masks(
                enabled=False,
                converted_dir=converted_dir,
                transforms_path=transforms_path,
                source_mask_dir=temp_path / "unused",
                colmap_images_path=temp_path / "unused_images.txt",
            )

            self.assertFalse(summary.enabled)
            transforms = json.loads(transforms_path.read_text(encoding="utf-8"))
            self.assertNotIn("mask_path", transforms["frames"][0])


if __name__ == "__main__":
    unittest.main()
