import importlib.util
import json
import sys
import tempfile
import types
import unittest
from pathlib import Path

import numpy as np

try:
    from plyfile import PlyData, PlyElement
except ModuleNotFoundError:
    class PlyElement:
        def __init__(self, data, name: str):
            self.data = data
            self.name = name

        @classmethod
        def describe(cls, data, name: str):
            return cls(data, name)

    class PlyData:
        def __init__(self, elements, text: bool = False):
            self._elements = {element.name: element for element in elements}

        def __getitem__(self, key: str):
            return self._elements[key]

        def write(self, path: str) -> None:
            with open(path, "wb") as handle:
                np.save(handle, self._elements["vertex"].data, allow_pickle=False)

        @classmethod
        def read(cls, path: str):
            with open(path, "rb") as handle:
                vertex_data = np.load(handle, allow_pickle=False)
            return cls([PlyElement(vertex_data, "vertex")])

    sys.modules["plyfile"] = types.SimpleNamespace(PlyData=PlyData, PlyElement=PlyElement)


REPO_ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = REPO_ROOT / "infrastructure" / "containers" / "3dgs" / "tile_pipeline.py"
SPEC = importlib.util.spec_from_file_location("tile_pipeline_test_module", MODULE_PATH)
tile_pipeline = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
sys.modules[SPEC.name] = tile_pipeline
SPEC.loader.exec_module(tile_pipeline)


def write_test_ply(path: Path, vertices: list[tuple[float, float, float, float]]) -> None:
    vertex_array = np.array(
        vertices,
        dtype=[
            ("x", "f4"),
            ("y", "f4"),
            ("z", "f4"),
            ("opacity", "f4"),
        ],
    )
    PlyData([PlyElement.describe(vertex_array, "vertex")], text=False).write(str(path))


def write_gaussian_test_ply(path: Path, vertices: list[tuple[float, float, float, float, float, float, float]]) -> None:
    vertex_array = np.array(
        vertices,
        dtype=[
            ("x", "f4"),
            ("y", "f4"),
            ("z", "f4"),
            ("opacity", "f4"),
            ("f_dc_0", "f4"),
            ("f_dc_1", "f4"),
            ("f_dc_2", "f4"),
        ],
    )
    PlyData([PlyElement.describe(vertex_array, "vertex")], text=False).write(str(path))


class GaussianTilePipelineTests(unittest.TestCase):
    def test_synthesize_tiled_inputs_from_chunk_planner_builds_compatibility_manifest(self):
        manifest, view_buckets, resolution = tile_pipeline.synthesize_tiled_inputs_from_chunk_planner(
            {
                "planner": "footprint_graph_v1",
                "chunk_matcher_strategy": "pair_list",
                "probe_subsets": {
                    "geometry_mix": ["a.jpg", "b.jpg"],
                    "cross_pass": ["c.jpg"],
                    "horizon_context": ["d.jpg"],
                },
                "chunks": [
                    {
                        "index": 0,
                        "core_names": ["a.jpg", "b.jpg"],
                        "overlap_names": ["c.jpg"],
                        "image_names": ["a.jpg", "b.jpg", "c.jpg"],
                    },
                    {
                        "index": 1,
                        "core_names": ["d.jpg", "e.jpg"],
                        "overlap_names": ["c.jpg"],
                        "image_names": ["c.jpg", "d.jpg", "e.jpg"],
                    },
                ],
            },
            sfm_metadata={"hierarchy_mode": "balanced_tree_v1"},
            global_scaffold_max_images=5,
            global_scaffold_stride=1,
            tile_context_images=2,
        )

        self.assertEqual(manifest["manifest_resolution"]["source_mode"], "chunk_planner_synthesized_v1")
        self.assertEqual(len(manifest["tiles"]), 2)
        self.assertEqual(view_buckets["near_detail_camera_ids"], ["a.jpg", "b.jpg"])
        self.assertEqual(view_buckets["boundary_camera_ids"], ["c.jpg"])
        self.assertEqual(view_buckets["horizon_camera_ids"], ["d.jpg"])
        self.assertFalse(manifest["tiles"][0]["ownership_bounds_available"])
        self.assertIn("support_statistics", manifest)
        self.assertIn("selected_cameras_by_role", manifest["tiles"][0])
        self.assertIn("overlap_stats_by_neighbor", manifest["tiles"][0])
        self.assertEqual(resolution["tile_count"], 2)

    def test_synthesize_tiled_inputs_uses_sfm_seam_graph_authority(self):
        manifest, _view_buckets, resolution = tile_pipeline.synthesize_tiled_inputs_from_chunk_planner(
            {
                "planner": "visibility_cell_v1",
                "chunks": [
                    {
                        "index": 0,
                        "core_names": ["a.jpg", "b.jpg"],
                        "overlap_names": ["c.jpg"],
                        "image_names": ["a.jpg", "b.jpg", "c.jpg"],
                    },
                    {
                        "index": 1,
                        "core_names": ["d.jpg", "e.jpg"],
                        "overlap_names": ["c.jpg"],
                        "image_names": ["c.jpg", "d.jpg", "e.jpg"],
                    },
                ],
            },
            reducer_metadata={
                "decision": "pass",
                "merge_strategy": "seam_graph_sim3_v1",
                "leaf_count": 2,
                "accepted_merge_tree": [
                    {
                        "leaf_a": 0,
                        "leaf_b": 1,
                        "confidence": 42.0,
                        "shared_registered_images": 5,
                        "strict_decision": "accept",
                        "blockers": [],
                    }
                ],
                "cycle_consistency": {"status": "pass", "failures": []},
                "promotion_blockers": [],
            },
            require_sfm_authority=True,
        )

        self.assertTrue(resolution["sfm_authority_available"])
        self.assertEqual(manifest["version"], "3dgs_tile_manifest_v1")
        self.assertEqual(manifest["sfm_authority_validation"]["status"], "pass")
        self.assertEqual(manifest["tiles"][0]["neighbor_tile_ids"], ["tile_01"])
        self.assertEqual(manifest["candidate_pairs"][0]["sfm_seam_confidence"], 42.0)
        self.assertEqual(manifest["candidate_pairs"][0]["sfm_shared_registered_images"], 5)
        self.assertIn("reducer_metadata_sha256", manifest["parent_hashes"])

    def test_required_sfm_authority_rejects_isolated_tiles(self):
        with self.assertRaises(ValueError):
            tile_pipeline.synthesize_tiled_inputs_from_chunk_planner(
                {
                    "planner": "visibility_cell_v1",
                    "chunks": [
                        {"index": 0, "core_names": ["a.jpg"], "overlap_names": [], "image_names": ["a.jpg"]},
                        {"index": 1, "core_names": ["b.jpg"], "overlap_names": [], "image_names": ["b.jpg"]},
                    ],
                },
                reducer_metadata={
                    "decision": "pass",
                    "merge_strategy": "seam_graph_sim3_v1",
                    "leaf_count": 2,
                    "accepted_merge_tree": [],
                    "cycle_consistency": {"status": "pass", "failures": []},
                    "promotion_blockers": [],
                },
                require_sfm_authority=True,
            )

    def test_synthesize_tiled_inputs_from_chunk_planner_uses_sparse_model_for_bounds(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            sparse_dir = Path(temp_dir) / "sparse" / "0"
            sparse_dir.mkdir(parents=True, exist_ok=True)
            (sparse_dir / "images.txt").write_text(
                "\n".join(
                    [
                        "1 1 0 0 0 0 0 0 1 a.jpg",
                        "",
                        "2 1 0 0 0 10 0 0 1 b.jpg",
                        "",
                        "3 1 0 0 0 20 0 0 1 c.jpg",
                        "",
                    ]
                ),
                encoding="utf-8",
            )
            (sparse_dir / "points3D.txt").write_text(
                "\n".join(
                    [
                        "1 0 0 -2 255 255 255 0.1 1 0 2 0",
                        "2 20 0 -5 255 255 255 0.1 2 0 3 0",
                    ]
                ),
                encoding="utf-8",
            )

            manifest, _, resolution = tile_pipeline.synthesize_tiled_inputs_from_chunk_planner(
                {
                    "planner": "footprint_graph_v1",
                    "chunks": [
                        {
                            "index": 0,
                            "core_names": ["a.jpg", "b.jpg"],
                            "overlap_names": [],
                            "image_names": ["a.jpg", "b.jpg"],
                        },
                        {
                            "index": 1,
                            "core_names": ["c.jpg"],
                            "overlap_names": ["b.jpg"],
                            "image_names": ["b.jpg", "c.jpg"],
                        },
                    ],
                },
                colmap_sparse_dir=sparse_dir,
            )

        self.assertTrue(resolution["ownership_bounds_available"])
        tile_zero = manifest["tiles"][0]
        self.assertTrue(tile_zero["ownership_bounds_available"])
        self.assertEqual(tile_zero["bounds_strategy"]["core"], "observed_points")
        self.assertLess(tile_zero["core_bounds"]["min_x"], 0.0)
        self.assertGreater(tile_zero["core_bounds"]["max_x"], 19.0)
        self.assertLess(tile_zero["core_bounds"]["min_z"], -5.0)

    def test_synthesize_tiled_inputs_prefers_transformed_camera_centers_before_point_bounds(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            sparse_dir = Path(temp_dir) / "sparse" / "0"
            sparse_dir.mkdir(parents=True, exist_ok=True)
            (sparse_dir / "images.txt").write_text(
                "\n".join(
                    [
                        "1 1 0 0 0 0 0 0 1 a.jpg",
                        "",
                        "2 1 0 0 0 10 0 0 1 b.jpg",
                        "",
                        "3 1 0 0 0 20 0 0 1 c.jpg",
                        "",
                    ]
                ),
                encoding="utf-8",
            )
            (sparse_dir / "points3D.txt").write_text(
                "\n".join(
                    [
                        "1 0 -2 20 255 255 255 0.1 1 0 2 0",
                        "2 20 5 30 255 255 255 0.1 2 0 3 0",
                    ]
                ),
                encoding="utf-8",
            )

            manifest, _, resolution = tile_pipeline.synthesize_tiled_inputs_from_chunk_planner(
                {
                    "planner": "footprint_graph_v1",
                    "chunks": [
                        {
                            "index": 0,
                            "core_names": ["a.jpg", "b.jpg"],
                            "overlap_names": [],
                            "image_names": ["a.jpg", "b.jpg"],
                        },
                        {
                            "index": 1,
                            "core_names": ["c.jpg"],
                            "overlap_names": ["b.jpg"],
                            "image_names": ["b.jpg", "c.jpg"],
                        },
                    ],
                },
                colmap_sparse_dir=sparse_dir,
                transforms_payload={
                    "applied_transform": [
                        [1.0, 0.0, 0.0, 0.0],
                        [0.0, 0.0, 1.0, 0.0],
                        [0.0, -1.0, 0.0, 0.0],
                    ],
                    "frames": [
                        {
                            "file_path": "images/frame_0001.jpg",
                            "transform_matrix": [
                                [1.0, 0.0, 0.0, 1.0],
                                [0.0, 1.0, 0.0, 2.0],
                                [0.0, 0.0, 1.0, 3.0],
                                [0.0, 0.0, 0.0, 1.0],
                            ],
                        },
                        {
                            "file_path": "images/frame_0002.jpg",
                            "transform_matrix": [
                                [1.0, 0.0, 0.0, 4.0],
                                [0.0, 1.0, 0.0, 5.0],
                                [0.0, 0.0, 1.0, 6.0],
                                [0.0, 0.0, 0.0, 1.0],
                            ],
                        },
                        {
                            "file_path": "images/frame_0003.jpg",
                            "transform_matrix": [
                                [1.0, 0.0, 0.0, 10.0],
                                [0.0, 1.0, 0.0, 0.0],
                                [0.0, 0.0, 1.0, -2.0],
                                [0.0, 0.0, 0.0, 1.0],
                            ],
                        },
                    ],
                },
                image_name_map_payload={
                    "by_converted_name": {
                        "frame_0001.jpg": {"original_image_name": "a.jpg"},
                        "frame_0002.jpg": {"original_image_name": "b.jpg"},
                        "frame_0003.jpg": {"original_image_name": "c.jpg"},
                    },
                    "by_original_image_name": {
                        "a.jpg": {"converted_file_path": "images/frame_0001.jpg"},
                        "b.jpg": {"converted_file_path": "images/frame_0002.jpg"},
                        "c.jpg": {"converted_file_path": "images/frame_0003.jpg"},
                    },
                },
            )

        self.assertTrue(resolution["ownership_bounds_available"])
        tile_zero = manifest["tiles"][0]
        self.assertEqual(tile_zero["bounds_strategy"]["core"], "transformed_camera_centers")
        self.assertAlmostEqual(tile_zero["core_bounds"]["min_x"], -11.0)
        self.assertAlmostEqual(tile_zero["core_bounds"]["max_x"], 16.0)
        self.assertAlmostEqual(tile_zero["core_bounds"]["min_y"], -10.0)
        self.assertAlmostEqual(tile_zero["core_bounds"]["max_y"], 17.0)
        self.assertAlmostEqual(tile_zero["core_bounds"]["min_z"], -9.0)
        self.assertAlmostEqual(tile_zero["core_bounds"]["max_z"], 18.0)

    def test_select_review_image_names_by_bucket_caps_per_bucket(self):
        review_images = tile_pipeline.select_review_image_names_by_bucket(
            ["a.jpg", "b.jpg", "c.jpg", "d.jpg", "e.jpg"],
            {
                "near_detail_camera_ids": ["a.jpg", "b.jpg", "z.jpg"],
                "boundary_camera_ids": ["c.jpg", "d.jpg"],
                "horizon_camera_ids": ["e.jpg"],
            },
            max_images_per_bucket=1,
        )

        self.assertEqual(review_images["near_detail_camera_ids"], ["a.jpg"])
        self.assertEqual(review_images["boundary_camera_ids"], ["c.jpg"])
        self.assertEqual(review_images["horizon_camera_ids"], ["e.jpg"])

    def test_select_pipeline_review_image_names_by_bucket_uses_selected_tiles(self):
        manifest = {
            "tiles": [
                {
                    "tile_id": "tile_00",
                    "base_camera_ids": ["a.jpg"],
                    "border_camera_ids": ["b.jpg"],
                    "context_camera_ids": ["c.jpg"],
                    "image_names": ["a.jpg", "b.jpg"],
                },
                {
                    "tile_id": "tile_01",
                    "base_camera_ids": ["d.jpg"],
                    "border_camera_ids": ["e.jpg"],
                    "context_camera_ids": ["f.jpg"],
                    "image_names": ["d.jpg", "e.jpg"],
                },
            ]
        }

        review_images = tile_pipeline.select_pipeline_review_image_names_by_bucket(
            manifest,
            {
                "near_detail_camera_ids": ["a.jpg", "d.jpg"],
                "boundary_camera_ids": ["b.jpg", "e.jpg"],
                "horizon_camera_ids": ["c.jpg", "f.jpg"],
            },
            selected_tile_ids=["tile_01"],
            max_images_per_bucket=2,
        )

        self.assertEqual(review_images["near_detail_camera_ids"], ["d.jpg"])
        self.assertEqual(review_images["boundary_camera_ids"], ["e.jpg"])
        self.assertEqual(review_images["horizon_camera_ids"], ["f.jpg"])

    def test_select_manifest_tile_ids_supports_subset_and_caps(self):
        manifest = {
            "tiles": [
                {"tile_id": "tile_00"},
                {"tile_id": "tile_01"},
                {"tile_id": "tile_02"},
            ]
        }

        self.assertEqual(
            tile_pipeline.select_manifest_tile_ids(manifest, max_tiles=2),
            ["tile_00", "tile_01"],
        )
        self.assertEqual(
            tile_pipeline.select_manifest_tile_ids(
                manifest,
                explicit_tile_ids=["tile_02", "tile_00"],
            ),
            ["tile_02", "tile_00"],
        )

    def test_subset_tile_manifest_keeps_only_selected_tiles(self):
        manifest = {
            "all_image_names": ["a.jpg", "b.jpg"],
            "tiles": [
                {"tile_id": "tile_00", "base_camera_ids": ["a.jpg"]},
                {"tile_id": "tile_01", "base_camera_ids": ["b.jpg"]},
            ],
        }

        subset = tile_pipeline.subset_tile_manifest(
            manifest,
            selected_tile_ids=["tile_01"],
        )

        self.assertEqual([tile["tile_id"] for tile in subset["tiles"]], ["tile_01"])
        self.assertEqual(subset["all_image_names"], ["a.jpg", "b.jpg"])

    def test_select_training_image_names_scaffold_and_leaf_tile(self):
        manifest = {
            "all_image_names": ["a.jpg", "b.jpg", "c.jpg", "d.jpg"],
            "global_scaffold_camera_ids": ["a.jpg", "b.jpg", "c.jpg", "d.jpg"],
            "tiles": [
                {
                    "tile_id": "tile_00",
                    "base_camera_ids": ["a.jpg"],
                    "border_camera_ids": ["b.jpg"],
                    "context_camera_ids": ["c.jpg"],
                }
            ],
        }

        scaffold = tile_pipeline.select_training_image_names(
            training_mode="global_scaffold",
            tile_manifest=manifest,
            max_images=2,
            stride=2,
        )
        leaf = tile_pipeline.select_training_image_names(
            training_mode="leaf_tile",
            tile_manifest=manifest,
            tile_id="tile_00",
        )

        self.assertEqual(scaffold, ["a.jpg", "c.jpg"])
        self.assertEqual(leaf, ["a.jpg", "b.jpg", "c.jpg"])

    def test_filter_transforms_frames_filters_split_filename_lists(self):
        transforms = {
            "frames": [
                {"file_path": "./images/a.jpg"},
                {"file_path": "images/b.jpg"},
                {"file_path": "images/c.jpg"},
            ],
            "train_filenames": ["./images/a.jpg", "images/b.jpg"],
            "val_filenames": ["images/c.jpg"],
            "test_filenames": ["images/b.jpg", "images/c.jpg"],
        }

        filtered = tile_pipeline.filter_transforms_frames(transforms, ["b.jpg", "c.jpg"])

        self.assertEqual(
            [Path(frame["file_path"]).name for frame in filtered["frames"]],
            ["b.jpg", "c.jpg"],
        )
        self.assertEqual(filtered["train_filenames"], ["images/b.jpg"])
        self.assertEqual(filtered["val_filenames"], ["images/c.jpg"])
        self.assertEqual(filtered["test_filenames"], ["images/b.jpg", "images/c.jpg"])

    def test_filter_transforms_frames_uses_colmap_name_map_for_renamed_frames(self):
        transforms = {
            "frames": [
                {"file_path": "images/frame_00001.JPG", "colmap_im_id": 101},
                {"file_path": "images/frame_00002.JPG", "colmap_im_id": 102},
            ],
            "train_filenames": ["images/frame_00001.JPG", "images/frame_00002.JPG"],
        }
        image_name_map = {
            "by_colmap_im_id": {
                "101": {
                    "original_image_name": "DJI_0001.JPG",
                    "converted_file_path": "images/frame_00001.JPG",
                    "converted_image_name": "frame_00001.JPG",
                },
                "102": {
                    "original_image_name": "DJI_0002.JPG",
                    "converted_file_path": "images/frame_00002.JPG",
                    "converted_image_name": "frame_00002.JPG",
                },
            },
            "by_converted_name": {
                "frame_00001.JPG": {"original_image_name": "DJI_0001.JPG"},
                "frame_00002.JPG": {"original_image_name": "DJI_0002.JPG"},
            },
        }

        filtered = tile_pipeline.filter_transforms_frames(
            transforms,
            ["DJI_0002.JPG"],
            image_name_map=image_name_map,
        )

        self.assertEqual(
            [Path(frame["file_path"]).name for frame in filtered["frames"]],
            ["frame_00002.JPG"],
        )
        self.assertEqual(filtered["train_filenames"], ["images/frame_00002.JPG"])

    def test_merge_tile_outputs_uses_overlap_fallback_when_core_retains_none(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            tile_dir = root / "tiles" / "tile_00"
            tile_dir.mkdir(parents=True)
            write_test_ply(
                tile_dir / "splat.ply",
                [
                    (1.0, 0.0, 0.0, 0.8),
                    (1.5, 0.0, 0.0, 0.6),
                ],
            )

            report = tile_pipeline.merge_tile_outputs(
                tile_manifest={
                    "tiles": [
                        {
                            "tile_id": "tile_00",
                            "core_bounds": {
                                "min_x": 0.0,
                                "max_x": 0.5,
                                "min_y": -1.0,
                                "max_y": 1.0,
                                "min_z": -1.0,
                                "max_z": 1.0,
                            },
                            "overlap_bounds": {
                                "min_x": 0.0,
                                "max_x": 2.0,
                                "min_y": -1.0,
                                "max_y": 1.0,
                                "min_z": -1.0,
                                "max_z": 1.0,
                            },
                        }
                    ]
                },
                tile_output_dirs={"tile_00": tile_dir},
                output_dir=root / "merged",
            )

            self.assertEqual(report["retained_gaussians"], 2)
            self.assertEqual(report["tiles"][0]["retention_strategy"], "overlap_bounds_fallback")
            self.assertEqual(report["fallback_tile_count"], 1)
            self.assertTrue((root / "merged" / "merged_splat.ply").exists())

    def test_merge_tile_outputs_retains_all_when_bounds_are_degenerate(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            tile_dir = root / "tiles" / "tile_00"
            tile_dir.mkdir(parents=True)
            write_test_ply(tile_dir / "splat.ply", [(10.0, 0.0, 0.0, 0.9)])

            report = tile_pipeline.merge_tile_outputs(
                tile_manifest={
                    "tiles": [
                        {
                            "tile_id": "tile_00",
                            "core_bounds": {
                                "min_x": 0.0,
                                "max_x": 0.0,
                                "min_y": 0.0,
                                "max_y": 0.0,
                                "min_z": 0.0,
                                "max_z": 0.0,
                            },
                            "overlap_bounds": {
                                "min_x": 0.0,
                                "max_x": 0.0,
                                "min_y": 0.0,
                                "max_y": 0.0,
                                "min_z": 0.0,
                                "max_z": 0.0,
                            },
                        }
                    ]
                },
                tile_output_dirs={"tile_00": tile_dir},
                output_dir=root / "merged",
            )

            self.assertEqual(report["retained_gaussians"], 1)
            self.assertEqual(report["tiles"][0]["retention_strategy"], "retain_all")
            self.assertEqual(report["retain_all_tile_count"], 1)

    def test_merge_tile_outputs_retains_all_when_non_degenerate_bounds_still_match_nothing(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            tile_dir = root / "tiles" / "tile_00"
            tile_dir.mkdir(parents=True)
            write_test_ply(tile_dir / "splat.ply", [(10.0, 0.0, 0.0, 0.9)])

            report = tile_pipeline.merge_tile_outputs(
                tile_manifest={
                    "tiles": [
                        {
                            "tile_id": "tile_00",
                            "core_bounds": {
                                "min_x": -5.0,
                                "max_x": -1.0,
                                "min_y": -1.0,
                                "max_y": 1.0,
                                "min_z": -1.0,
                                "max_z": 1.0,
                            },
                            "overlap_bounds": {
                                "min_x": -5.0,
                                "max_x": -1.0,
                                "min_y": -1.0,
                                "max_y": 1.0,
                                "min_z": -1.0,
                                "max_z": 1.0,
                            },
                        }
                    ]
                },
                tile_output_dirs={"tile_00": tile_dir},
                output_dir=root / "merged",
            )

            self.assertEqual(report["retained_gaussians"], 1)
            self.assertEqual(report["tiles"][0]["retention_strategy"], "retain_all")
            self.assertEqual(report["retain_all_tile_count"], 1)
            self.assertEqual(report["fallback_tile_count"], 1)

    def test_merge_tile_outputs_uses_centroid_voronoi_fallback_before_retain_all(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            tile_zero_dir = root / "tiles" / "tile_00"
            tile_one_dir = root / "tiles" / "tile_01"
            tile_zero_dir.mkdir(parents=True)
            tile_one_dir.mkdir(parents=True)
            write_test_ply(
                tile_zero_dir / "splat.ply",
                [
                    (0.0, 0.0, 0.0, 0.9),
                    (1.0, 0.0, 0.0, 0.8),
                ],
            )
            write_test_ply(
                tile_one_dir / "splat.ply",
                [
                    (10.0, 0.0, 0.0, 0.9),
                    (11.0, 0.0, 0.0, 0.8),
                ],
            )

            report = tile_pipeline.merge_tile_outputs(
                tile_manifest={
                    "tiles": [
                        {
                            "tile_id": "tile_00",
                            "neighbor_tile_ids": ["tile_01"],
                            "core_bounds": {
                                "min_x": -5.0,
                                "max_x": -1.0,
                                "min_y": -1.0,
                                "max_y": 1.0,
                                "min_z": -1.0,
                                "max_z": 1.0,
                            },
                            "overlap_bounds": {
                                "min_x": -5.0,
                                "max_x": -1.0,
                                "min_y": -1.0,
                                "max_y": 1.0,
                                "min_z": -1.0,
                                "max_z": 1.0,
                            },
                        },
                        {
                            "tile_id": "tile_01",
                            "neighbor_tile_ids": ["tile_00"],
                            "core_bounds": {
                                "min_x": 20.0,
                                "max_x": 25.0,
                                "min_y": -1.0,
                                "max_y": 1.0,
                                "min_z": -1.0,
                                "max_z": 1.0,
                            },
                            "overlap_bounds": {
                                "min_x": 20.0,
                                "max_x": 25.0,
                                "min_y": -1.0,
                                "max_y": 1.0,
                                "min_z": -1.0,
                                "max_z": 1.0,
                            },
                        },
                    ]
                },
                tile_output_dirs={"tile_00": tile_zero_dir, "tile_01": tile_one_dir},
                output_dir=root / "merged",
            )

            self.assertEqual(report["retained_gaussians"], 4)
            self.assertEqual(report["tiles"][0]["retention_strategy"], "centroid_voronoi_fallback")
            self.assertEqual(report["tiles"][1]["retention_strategy"], "centroid_voronoi_fallback")
            self.assertEqual(report["retain_all_tile_count"], 0)
            self.assertEqual(report["fallback_tile_count"], 2)

    def test_merge_tile_outputs_promotes_best_background_skybox(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            tile_zero_dir = root / "tiles" / "tile_00"
            tile_one_dir = root / "tiles" / "tile_01"
            tile_zero_dir.mkdir(parents=True)
            tile_one_dir.mkdir(parents=True)
            write_test_ply(tile_zero_dir / "splat.ply", [(0.0, 0.0, 0.0, 0.9)])
            write_test_ply(tile_one_dir / "splat.ply", [(10.0, 0.0, 0.0, 0.9)])
            (tile_zero_dir / "background_skybox.webp").write_bytes(b"tile-zero")
            (tile_one_dir / "background_skybox.webp").write_bytes(b"tile-one")
            (tile_zero_dir / "background_manifest.json").write_text(
                json.dumps({"selection": {"score": 0.25}}),
                encoding="utf-8",
            )
            (tile_one_dir / "background_manifest.json").write_text(
                json.dumps({"selection": {"score": 0.9}}),
                encoding="utf-8",
            )

            report = tile_pipeline.merge_tile_outputs(
                tile_manifest={
                    "tiles": [
                        {
                            "tile_id": "tile_00",
                            "core_bounds": {
                                "min_x": -1.0,
                                "max_x": 1.0,
                                "min_y": -1.0,
                                "max_y": 1.0,
                                "min_z": -1.0,
                                "max_z": 1.0,
                            },
                            "overlap_bounds": {
                                "min_x": -1.0,
                                "max_x": 1.0,
                                "min_y": -1.0,
                                "max_y": 1.0,
                                "min_z": -1.0,
                                "max_z": 1.0,
                            },
                        },
                        {
                            "tile_id": "tile_01",
                            "core_bounds": {
                                "min_x": 9.0,
                                "max_x": 11.0,
                                "min_y": -1.0,
                                "max_y": 1.0,
                                "min_z": -1.0,
                                "max_z": 1.0,
                            },
                            "overlap_bounds": {
                                "min_x": 9.0,
                                "max_x": 11.0,
                                "min_y": -1.0,
                                "max_y": 1.0,
                                "min_z": -1.0,
                                "max_z": 1.0,
                            },
                        },
                    ]
                },
                tile_output_dirs={"tile_00": tile_zero_dir, "tile_01": tile_one_dir},
                output_dir=root / "merged",
            )

            self.assertEqual(report["background_asset"]["source_tile_id"], "tile_01")
            self.assertTrue((root / "merged" / "background_skybox.webp").exists())
            manifest = json.loads((root / "merged" / "background_manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(manifest["source_tile_id"], "tile_01")
            self.assertEqual(manifest["selection_mode"], "best_score")

    def test_merge_tile_outputs_can_force_background_skybox_source(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            tile_zero_dir = root / "tiles" / "tile_00"
            tile_one_dir = root / "tiles" / "tile_01"
            tile_zero_dir.mkdir(parents=True)
            tile_one_dir.mkdir(parents=True)
            write_test_ply(tile_zero_dir / "splat.ply", [(0.0, 0.0, 0.0, 0.9)])
            write_test_ply(tile_one_dir / "splat.ply", [(10.0, 0.0, 0.0, 0.9)])
            (tile_zero_dir / "background_skybox.webp").write_bytes(b"tile-zero")
            (tile_one_dir / "background_skybox.webp").write_bytes(b"tile-one")
            (tile_zero_dir / "background_manifest.json").write_text(
                json.dumps({"selection": {"score": 0.25}}),
                encoding="utf-8",
            )
            (tile_one_dir / "background_manifest.json").write_text(
                json.dumps({"selection": {"score": 0.9}}),
                encoding="utf-8",
            )

            report = tile_pipeline.merge_tile_outputs(
                tile_manifest={
                    "tiles": [
                        {
                            "tile_id": "tile_00",
                            "core_bounds": {
                                "min_x": -1.0,
                                "max_x": 1.0,
                                "min_y": -1.0,
                                "max_y": 1.0,
                                "min_z": -1.0,
                                "max_z": 1.0,
                            },
                            "overlap_bounds": {
                                "min_x": -1.0,
                                "max_x": 1.0,
                                "min_y": -1.0,
                                "max_y": 1.0,
                                "min_z": -1.0,
                                "max_z": 1.0,
                            },
                        },
                        {
                            "tile_id": "tile_01",
                            "core_bounds": {
                                "min_x": 9.0,
                                "max_x": 11.0,
                                "min_y": -1.0,
                                "max_y": 1.0,
                                "min_z": -1.0,
                                "max_z": 1.0,
                            },
                            "overlap_bounds": {
                                "min_x": 9.0,
                                "max_x": 11.0,
                                "min_y": -1.0,
                                "max_y": 1.0,
                                "min_z": -1.0,
                                "max_z": 1.0,
                            },
                        },
                    ]
                },
                tile_output_dirs={"tile_00": tile_zero_dir, "tile_01": tile_one_dir},
                output_dir=root / "merged",
                background_source_tile_id="tile_00",
            )

            self.assertEqual(report["background_asset"]["source_tile_id"], "tile_00")
            self.assertEqual(report["background_asset"]["selection_mode"], "forced_tile")
            self.assertEqual(report["background_asset"]["requested_source_tile_id"], "tile_00")
            self.assertEqual((root / "merged" / "background_skybox.webp").read_bytes(), b"tile-zero")
            manifest = json.loads((root / "merged" / "background_manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(manifest["source_tile_id"], "tile_00")
            self.assertEqual(manifest["selection_mode"], "forced_tile")

    def test_rank_candidate_tile_pairs_uses_shared_images_boundary_support_and_fallback(self):
        manifest = {
            "tiles": [
                {
                    "tile_id": "tile_02",
                    "neighbor_tile_ids": ["tile_05"],
                    "base_camera_ids": [f"shared_{index}.jpg" for index in range(6)],
                    "border_camera_ids": ["boundary_0.jpg", "boundary_1.jpg"],
                    "context_camera_ids": [],
                    "image_names": [f"shared_{index}.jpg" for index in range(6)] + ["boundary_0.jpg"],
                    "core_bounds": {"min_x": 0, "max_x": 1, "min_y": 0, "max_y": 1, "min_z": 0, "max_z": 1},
                    "overlap_bounds": {"min_x": 0, "max_x": 2, "min_y": 0, "max_y": 1, "min_z": 0, "max_z": 1},
                },
                {
                    "tile_id": "tile_05",
                    "neighbor_tile_ids": ["tile_02"],
                    "base_camera_ids": [f"shared_{index}.jpg" for index in range(6)],
                    "border_camera_ids": ["boundary_0.jpg"],
                    "context_camera_ids": [],
                    "image_names": [f"shared_{index}.jpg" for index in range(6)] + ["boundary_0.jpg"],
                    "core_bounds": {"min_x": 1, "max_x": 2, "min_y": 0, "max_y": 1, "min_z": 0, "max_z": 1},
                    "overlap_bounds": {"min_x": 0, "max_x": 2, "min_y": 0, "max_y": 1, "min_z": 0, "max_z": 1},
                },
            ]
        }

        ranked = tile_pipeline.rank_candidate_tile_pairs(
            manifest,
            {"boundary_camera_ids": [f"shared_{index}.jpg" for index in range(4)]},
            merge_report={"tiles": [{"tile_id": "tile_05", "retention_strategy": "overlap_bounds_fallback"}]},
            min_shared_assigned_images=4,
        )

        self.assertEqual(ranked[0]["tile_ids"], ["tile_02", "tile_05"])
        self.assertTrue(ranked[0]["eligible"])
        self.assertEqual(ranked[0]["boundary_support_count"], 4)
        self.assertEqual(ranked[0]["boundary_support_source"], "view_bucket_intersection")
        self.assertEqual(ranked[0]["boundary_support_quality"], "explicit_boundary_bucket")
        self.assertTrue(ranked[0]["fallback_involved"])

    def test_rank_candidate_tile_pairs_can_use_shared_images_as_boundary_fallback(self):
        shared_names = [f"shared_{index}.jpg" for index in range(6)]
        bounds = {"min_x": 0, "max_x": 1, "min_y": 0, "max_y": 1, "min_z": 0, "max_z": 1}
        manifest = {
            "tiles": [
                {
                    "tile_id": "tile_04",
                    "neighbor_tile_ids": ["tile_06"],
                    "base_camera_ids": shared_names,
                    "border_camera_ids": [],
                    "context_camera_ids": [],
                    "image_names": shared_names,
                    "core_bounds": bounds,
                    "overlap_bounds": bounds,
                },
                {
                    "tile_id": "tile_06",
                    "neighbor_tile_ids": ["tile_04"],
                    "base_camera_ids": shared_names,
                    "border_camera_ids": [],
                    "context_camera_ids": [],
                    "image_names": shared_names,
                    "core_bounds": bounds,
                    "overlap_bounds": bounds,
                },
            ]
        }

        ranked = tile_pipeline.rank_candidate_tile_pairs(
            manifest,
            {"boundary_camera_ids": ["unrelated_boundary.jpg"]},
            min_shared_assigned_images=4,
        )

        self.assertTrue(ranked[0]["eligible"])
        self.assertEqual(ranked[0]["boundary_support_count"], 6)
        self.assertEqual(ranked[0]["boundary_support_source"], "shared_assigned_images_fallback")
        self.assertEqual(ranked[0]["boundary_support_quality"], "shared_images_no_bucket_intersection")
        self.assertTrue(ranked[0]["uses_shared_assigned_fallback"])

    def test_rank_candidate_tile_pairs_blocks_poor_boundary_support(self):
        shared_names = [f"shared_{index}.jpg" for index in range(3)]
        bounds = {"min_x": 0, "max_x": 1, "min_y": 0, "max_y": 1, "min_z": 0, "max_z": 1}
        manifest = {
            "tiles": [
                {
                    "tile_id": "tile_00",
                    "neighbor_tile_ids": ["tile_01"],
                    "base_camera_ids": shared_names,
                    "image_names": shared_names,
                    "core_bounds": bounds,
                    "overlap_bounds": bounds,
                },
                {
                    "tile_id": "tile_01",
                    "neighbor_tile_ids": ["tile_00"],
                    "base_camera_ids": shared_names,
                    "image_names": shared_names,
                    "core_bounds": bounds,
                    "overlap_bounds": bounds,
                },
            ]
        }

        ranked = tile_pipeline.rank_candidate_tile_pairs(
            manifest,
            {"boundary_camera_ids": []},
            min_shared_assigned_images=1,
            min_boundary_support_images=4,
        )

        self.assertFalse(ranked[0]["eligible"])
        self.assertIn("boundary_support_below_minimum", ranked[0]["ineligible_reasons"])
        self.assertTrue(ranked[0]["poor_boundary_support"])

    def test_rank_candidate_tile_triples_anchors_on_uncompleted_supported_pair(self):
        bounds = {"min_x": 0, "max_x": 1, "min_y": 0, "max_y": 1, "min_z": 0, "max_z": 1}

        def tile(tile_id, neighbors, names):
            return {
                "tile_id": tile_id,
                "neighbor_tile_ids": neighbors,
                "base_camera_ids": names,
                "border_camera_ids": names[:4],
                "image_names": names,
                "core_bounds": bounds,
                "overlap_bounds": bounds,
            }

        shared_0205 = [f"shared_0205_{index}.jpg" for index in range(6)]
        shared_0506 = [f"shared_0506_{index}.jpg" for index in range(6)]
        tile02_context = [f"tile02_context_{index}.jpg" for index in range(6)]
        tile06_context = [f"tile06_context_{index}.jpg" for index in range(6)]
        manifest = {
            "tiles": [
                tile("tile_02", ["tile_05"], shared_0205 + tile02_context),
                tile("tile_05", ["tile_02", "tile_06"], shared_0205 + shared_0506),
                tile("tile_06", ["tile_05"], shared_0506 + tile06_context),
            ]
        }

        ranked = tile_pipeline.rank_candidate_tile_triples(
            manifest,
            {"boundary_camera_ids": shared_0205[:4] + shared_0506[:4]},
            completed_pair_tile_ids=[["tile_02", "tile_05"]],
            min_shared_assigned_images=4,
        )

        self.assertEqual(ranked[0]["tile_ids"], ["tile_02", "tile_05", "tile_06"])
        self.assertTrue(ranked[0]["eligible"])
        self.assertEqual(ranked[0]["anchor_pair_tile_ids"], ["tile_05", "tile_06"])
        self.assertEqual(ranked[0]["eligible_pair_count"], 2)
        self.assertEqual(ranked[0]["completed_pair_tile_ids"], [["tile_02", "tile_05"]])

    def test_merge_tile_outputs_support_weighted_overlap_arbitrates_boundary_candidates(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            tile_zero_dir = root / "tiles" / "tile_00"
            tile_one_dir = root / "tiles" / "tile_01"
            tile_zero_dir.mkdir(parents=True)
            tile_one_dir.mkdir(parents=True)
            write_test_ply(tile_zero_dir / "splat.ply", [(1.0, 0.0, 0.0, 0.9), (5.5, 0.0, 0.0, 0.9)])
            write_test_ply(tile_one_dir / "splat.ply", [(5.5, 0.0, 0.0, 0.9), (7.0, 0.0, 0.0, 0.9)])

            report = tile_pipeline.merge_tile_outputs(
                tile_manifest={
                    "tiles": [
                        {
                            "tile_id": "tile_00",
                            "neighbor_tile_ids": ["tile_01"],
                            "base_camera_ids": ["a.jpg", "shared.jpg"],
                            "border_camera_ids": ["boundary.jpg"],
                            "image_names": ["a.jpg", "shared.jpg", "boundary.jpg"],
                            "core_bounds": {
                                "min_x": 0.0,
                                "max_x": 3.0,
                                "min_y": -1.0,
                                "max_y": 1.0,
                                "min_z": -1.0,
                                "max_z": 1.0,
                            },
                            "overlap_bounds": {
                                "min_x": 0.0,
                                "max_x": 6.0,
                                "min_y": -1.0,
                                "max_y": 1.0,
                                "min_z": -1.0,
                                "max_z": 1.0,
                            },
                        },
                        {
                            "tile_id": "tile_01",
                            "neighbor_tile_ids": ["tile_00"],
                            "base_camera_ids": ["b.jpg", "shared.jpg"],
                            "border_camera_ids": ["boundary.jpg"],
                            "image_names": ["b.jpg", "shared.jpg", "boundary.jpg"],
                            "core_bounds": {
                                "min_x": 5.0,
                                "max_x": 8.0,
                                "min_y": -1.0,
                                "max_y": 1.0,
                                "min_z": -1.0,
                                "max_z": 1.0,
                            },
                            "overlap_bounds": {
                                "min_x": 2.0,
                                "max_x": 8.0,
                                "min_y": -1.0,
                                "max_y": 1.0,
                                "min_z": -1.0,
                                "max_z": 1.0,
                            },
                        },
                    ]
                },
                tile_output_dirs={"tile_00": tile_zero_dir, "tile_01": tile_one_dir},
                output_dir=root / "support_weighted",
                merge_mode="support_weighted_overlap",
            )

            self.assertEqual(report["merge_mode"], "support_weighted_overlap")
            self.assertEqual(report["retain_all_tile_count"], 0)
            self.assertEqual(report["fallback_tile_count"], 0)
            self.assertEqual(report["retained_gaussians"], 3)
            self.assertEqual(report["tiles"][0]["support_weighted_overlap"]["overlap_candidate_count"], 1)

    def test_merge_tile_outputs_support_weighted_overlap_can_protect_boundary_candidates(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            tile_zero_dir = root / "tiles" / "tile_00"
            tile_one_dir = root / "tiles" / "tile_01"
            tile_zero_dir.mkdir(parents=True)
            tile_one_dir.mkdir(parents=True)
            write_test_ply(tile_zero_dir / "splat.ply", [(1.0, 0.0, 0.0, 0.9), (5.5, 0.0, 0.0, 0.9)])
            write_test_ply(tile_one_dir / "splat.ply", [(5.5, 0.0, 0.0, 0.9), (7.0, 0.0, 0.0, 0.9)])

            manifest = {
                "tiles": [
                    {
                        "tile_id": "tile_00",
                        "neighbor_tile_ids": ["tile_01"],
                        "image_names": ["a.jpg", "shared.jpg", "boundary.jpg"],
                        "core_bounds": {
                            "min_x": 0.0,
                            "max_x": 3.0,
                            "min_y": -1.0,
                            "max_y": 1.0,
                            "min_z": -1.0,
                            "max_z": 1.0,
                        },
                        "overlap_bounds": {
                            "min_x": 0.0,
                            "max_x": 6.0,
                            "min_y": -1.0,
                            "max_y": 1.0,
                            "min_z": -1.0,
                            "max_z": 1.0,
                        },
                    },
                    {
                        "tile_id": "tile_01",
                        "neighbor_tile_ids": ["tile_00"],
                        "image_names": ["b.jpg", "shared.jpg", "boundary.jpg"],
                        "core_bounds": {
                            "min_x": 5.0,
                            "max_x": 8.0,
                            "min_y": -1.0,
                            "max_y": 1.0,
                            "min_z": -1.0,
                            "max_z": 1.0,
                        },
                        "overlap_bounds": {
                            "min_x": 2.0,
                            "max_x": 8.0,
                            "min_y": -1.0,
                            "max_y": 1.0,
                            "min_z": -1.0,
                            "max_z": 1.0,
                        },
                    },
                ]
            }

            report = tile_pipeline.merge_tile_outputs(
                tile_manifest=manifest,
                tile_output_dirs={"tile_00": tile_zero_dir, "tile_01": tile_one_dir},
                output_dir=root / "support_weighted_protected",
                merge_mode="support_weighted_overlap",
                protected_overlap_tile_ids=["tile_00"],
                protected_overlap_mode="retain_all",
            )

            self.assertEqual(report["retained_gaussians"], 4)
            self.assertEqual(report["protected_overlap_mode"], "retain_all")
            self.assertEqual(report["protected_overlap_tile_ids"], ["tile_00"])
            stats = report["tiles"][0]["support_weighted_overlap"]
            self.assertTrue(stats["protected_overlap_enabled"])
            self.assertEqual(stats["protected_overlap_retained_count"], 1)
            self.assertEqual(stats["protected_overlap_added_count"], 1)

    def test_merge_tile_outputs_support_weighted_overlap_preserves_marked_context(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            tile_dir = root / "tiles" / "tile_00"
            tile_dir.mkdir(parents=True)
            write_test_ply(tile_dir / "splat.ply", [(0.5, 0.0, 0.0, 0.9), (8.0, 0.0, 0.0, 0.2)])

            report = tile_pipeline.merge_tile_outputs(
                tile_manifest={
                    "tiles": [
                        {
                            "tile_id": "tile_00",
                            "neighbor_tile_ids": [],
                            "base_camera_ids": ["a.jpg"],
                            "border_camera_ids": [],
                            "image_names": ["a.jpg"],
                            "core_bounds": {
                                "min_x": 0.0,
                                "max_x": 1.0,
                                "min_y": -1.0,
                                "max_y": 1.0,
                                "min_z": -1.0,
                                "max_z": 1.0,
                            },
                            "overlap_bounds": {
                                "min_x": 0.0,
                                "max_x": 1.0,
                                "min_y": -1.0,
                                "max_y": 1.0,
                                "min_z": -1.0,
                                "max_z": 1.0,
                            },
                            "context_bounds": {
                                "min_x": 0.0,
                                "max_x": 10.0,
                                "min_y": -1.0,
                                "max_y": 1.0,
                                "min_z": -1.0,
                                "max_z": 1.0,
                            },
                            "preserve_context_gaussians": True,
                        }
                    ]
                },
                tile_output_dirs={"tile_00": tile_dir},
                output_dir=root / "support_weighted_context",
                merge_mode="support_weighted_overlap",
            )

            self.assertEqual(report["fallback_tile_count"], 0)
            self.assertEqual(report["retain_all_tile_count"], 0)
            self.assertEqual(report["retained_gaussians"], 2)
            stats = report["tiles"][0]["support_weighted_overlap"]
            self.assertTrue(stats["context_preserve_enabled"])
            self.assertEqual(stats["context_candidate_count"], 1)
            self.assertEqual(stats["retained_context_count"], 1)

    def test_write_point_cloud_ply_from_gaussians_filters_scaffold_to_padded_bounds(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "scaffold.ply"
            target = root / "tile" / "scaffold_init.ply"
            write_gaussian_test_ply(
                source,
                [
                    (0.0, 0.0, 0.0, 0.8, 0.1, 0.1, 0.1),
                    (5.0, 0.0, 0.0, 0.8, 0.1, 0.1, 0.1),
                ],
            )

            metadata = tile_pipeline.write_point_cloud_ply_from_gaussians(
                source,
                target,
                bounds={"min_x": -1, "max_x": 1, "min_y": -1, "max_y": 1, "min_z": -1, "max_z": 1},
                padding_ratio=0.1,
            )

            filtered = PlyData.read(str(target))["vertex"].data
            self.assertEqual(len(filtered), 1)
            self.assertEqual(metadata["inherited_gaussian_count"], 1)
            self.assertEqual(metadata["source_rejected_gaussian_count"], 1)
            self.assertAlmostEqual(metadata["source_filter_retention_ratio"], 0.5)
            self.assertTrue(metadata["scaffold_filter_selective"])
            self.assertEqual(metadata["scaffold_inheritance_mode"], "global_scaffold_ply_filtered_point_cloud")

    def test_write_point_cloud_ply_from_gaussians_reports_nonselective_bounds(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "scaffold.ply"
            target = root / "tile" / "scaffold_init.ply"
            write_gaussian_test_ply(
                source,
                [
                    (0.0, 0.0, 0.0, 0.8, 0.1, 0.1, 0.1),
                    (0.5, 0.0, 0.0, 0.8, 0.1, 0.1, 0.1),
                ],
            )

            metadata = tile_pipeline.write_point_cloud_ply_from_gaussians(
                source,
                target,
                bounds={"min_x": -1, "max_x": 1, "min_y": -1, "max_y": 1, "min_z": -1, "max_z": 1},
                padding_ratio=0.1,
            )

            self.assertEqual(metadata["source_filtered_gaussian_count"], 2)
            self.assertEqual(metadata["source_rejected_gaussian_count"], 0)
            self.assertAlmostEqual(metadata["source_filter_retention_ratio"], 1.0)
            self.assertFalse(metadata["scaffold_filter_selective"])
            self.assertFalse(metadata["fallback_used"])

    def test_write_point_cloud_ply_from_gaussians_caps_scaffold_init_points(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "scaffold.ply"
            target = root / "tile" / "scaffold_init.ply"
            write_gaussian_test_ply(
                source,
                [
                    (float(index), float(index % 3), 0.0, 0.8, 0.1, 0.1, 0.1)
                    for index in range(10)
                ],
            )

            metadata = tile_pipeline.write_point_cloud_ply_from_gaussians(
                source,
                target,
                max_points=4,
            )

            filtered = PlyData.read(str(target))["vertex"].data
            self.assertEqual(len(filtered), 4)
            self.assertEqual(metadata["source_filtered_gaussian_count"], 10)
            self.assertEqual(metadata["inherited_gaussian_count"], 4)
            self.assertEqual(metadata["inherited_gaussian_cap"], 4)
            self.assertEqual(metadata["scaffold_init_downsample_strategy"], "spatial_key_even_sample")


if __name__ == "__main__":
    unittest.main()
