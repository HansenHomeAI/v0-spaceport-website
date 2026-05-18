import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = REPO_ROOT / "scripts" / "sfm" / "run_sfm_reducer_canary.py"
SPEC = importlib.util.spec_from_file_location("run_sfm_reducer_canary_test_module", MODULE_PATH)
reducer_canary = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = reducer_canary
SPEC.loader.exec_module(reducer_canary)


class SfmReducerCanaryTest(unittest.TestCase):
    def write_model(
        self,
        path: Path,
        image_names: list[str],
        point_tracks: list[tuple[str, str]],
    ) -> None:
        path.mkdir(parents=True, exist_ok=True)
        (path / "cameras.txt").write_text("# Camera list\n1 PINHOLE 100 100 1 2 3 4\n", encoding="utf-8")
        image_name_to_id = {name: index + 1 for index, name in enumerate(image_names)}
        image_lines: list[str] = ["# Image list\n"]
        for index, name in enumerate(image_names, start=1):
            image_lines.append(f"{index} 1 0 0 0 {-float(index)} 0 0 1 {name}\n")
            image_lines.append("0 0 -1\n")
        (path / "images.txt").write_text("".join(image_lines), encoding="utf-8")
        point_lines: list[str] = ["# Point list\n"]
        for point_id, (first_name, second_name) in enumerate(point_tracks, start=1):
            point_lines.append(
                f"{point_id} {float(point_id)} 0 0 255 0 0 0.5 "
                f"{image_name_to_id[first_name]} 0 {image_name_to_id[second_name]} 0\n"
            )
        (path / "points3D.txt").write_text("".join(point_lines), encoding="utf-8")

    def test_pose_aligned_merge_chains_through_intermediate_leaf(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            leaf0 = root / "leaf0"
            leaf1 = root / "leaf1"
            leaf2 = root / "leaf2"
            output = root / "merged"
            self.write_model(leaf0, ["A.JPG", "B.JPG", "C.JPG", "D.JPG"], [("A.JPG", "B.JPG")])
            self.write_model(leaf1, ["B.JPG", "C.JPG", "D.JPG", "E.JPG", "F.JPG", "G.JPG"], [("E.JPG", "F.JPG")])
            self.write_model(leaf2, ["E.JPG", "F.JPG", "G.JPG", "H.JPG", "I.JPG"], [("H.JPG", "I.JPG")])

            report = reducer_canary.write_pose_aligned_merge(
                normalized_dirs=[leaf0, leaf1, leaf2],
                output_dir=output,
                min_shared_images=3,
            )

            images = (output / "images.txt").read_text(encoding="utf-8")

        self.assertEqual([item["leaf_index"] for item in report["transforms"]], [1, 2])
        self.assertIn("H.JPG", images)
        self.assertIn("I.JPG", images)

    def test_rewrite_model_text_normalizes_image_camera_and_track_ids(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "source"
            target = root / "target"
            source.mkdir()
            (source / "cameras.txt").write_text(
                "# Camera list\n7 PINHOLE 100 100 1 2 3 4\n",
                encoding="utf-8",
            )
            (source / "images.txt").write_text(
                "# Image list\n"
                "34 1 0 0 0 0 0 0 7 A.JPG\n"
                "0 0 1\n"
                "88 1 0 0 0 1 0 0 7 B.JPG\n"
                "0 0 2\n",
                encoding="utf-8",
            )
            (source / "points3D.txt").write_text(
                "# Point list\n"
                "9 0 0 0 255 0 0 0.7 34 0 88 1\n"
                "10 0 0 1 255 0 0 0.9 34 0\n",
                encoding="utf-8",
            )
            (source / "frames.txt").write_text(
                "# Frame list\n1 1 1 0 0 0 0 0 0 1 1 7 34\n",
                encoding="utf-8",
            )
            reducer_canary.rewrite_model_text(
                input_dir=source,
                output_dir=target,
                image_ids_by_name={"A.JPG": 1, "B.JPG": 2},
                camera_ids_by_old_id={7: 3},
                global_camera_records={3: ["PINHOLE", "100", "100", "1", "2", "3", "4"]},
            )

            images = (target / "images.txt").read_text(encoding="utf-8")
            points = (target / "points3D.txt").read_text(encoding="utf-8")
            frames = (target / "frames.txt").read_text(encoding="utf-8")

        self.assertIn("1 1 0 0 0 0 0 0 3 A.JPG", images)
        self.assertIn("2 1 0 0 0 1 0 0 3 B.JPG", images)
        self.assertIn("9 0 0 0 255 0 0 0.7 1 0 2 1", points)
        self.assertNotIn("10 0 0 1", points)
        self.assertIn("1 1 1 0 0 0 0 0 0 1 1 7 1", frames)

    def test_cross_leaf_surface_overlap_passes_aligned_cells(self):
        existing = [(float(index % 3) * 0.2, float(index // 3) * 0.2, 10.0 + index * 0.01) for index in range(9)]
        incoming = [(float(index % 3) * 0.2, float(index // 3) * 0.2, 10.15 + index * 0.01) for index in range(9)]

        stats = reducer_canary.cross_leaf_surface_overlap_stats(existing, incoming)

        self.assertEqual(stats["overlap_cell_count"], 1)
        self.assertEqual(stats["flagged_overlap_cell_count"], 0)
        self.assertEqual(stats["flagged_overlap_cell_ratio"], 0.0)

    def test_cross_leaf_surface_overlap_flags_layered_cells(self):
        existing = [(float(index % 3) * 0.2, float(index // 3) * 0.2, 10.0 + index * 0.01) for index in range(9)]
        incoming = [(float(index % 3) * 0.2, float(index // 3) * 0.2, 17.0 + index * 0.01) for index in range(9)]

        stats = reducer_canary.cross_leaf_surface_overlap_stats(existing, incoming)

        self.assertEqual(stats["overlap_cell_count"], 1)
        self.assertEqual(stats["flagged_overlap_cell_count"], 1)
        self.assertGreater(stats["flagged_overlap_cell_ratio"], 0.0)


if __name__ == "__main__":
    unittest.main()
