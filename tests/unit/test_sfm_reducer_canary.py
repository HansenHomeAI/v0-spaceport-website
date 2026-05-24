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
        camera_positions: dict[str, tuple[float, float, float]] | None = None,
        point_positions: list[tuple[float, float, float]] | None = None,
    ) -> None:
        path.mkdir(parents=True, exist_ok=True)
        (path / "cameras.txt").write_text("# Camera list\n1 PINHOLE 100 100 1 2 3 4\n", encoding="utf-8")
        image_name_to_id = {name: index + 1 for index, name in enumerate(image_names)}
        image_lines: list[str] = ["# Image list\n"]
        for index, name in enumerate(image_names, start=1):
            position = (camera_positions or {}).get(name, (float(index), 0.0, 0.0))
            image_lines.append(
                f"{index} 1 0 0 0 {-position[0]} {-position[1]} {-position[2]} 1 {name}\n"
            )
            image_lines.append("0 0 -1\n")
        (path / "images.txt").write_text("".join(image_lines), encoding="utf-8")
        point_lines: list[str] = ["# Point list\n"]
        for point_id, (first_name, second_name) in enumerate(point_tracks, start=1):
            point_position = (point_positions or [(float(point_id), 0.0, 0.0)] * len(point_tracks))[point_id - 1]
            point_lines.append(
                f"{point_id} {point_position[0]} {point_position[1]} {point_position[2]} 255 0 0 0.5 "
                f"{image_name_to_id[first_name]} 0 {image_name_to_id[second_name]} 0\n"
            )
        (path / "points3D.txt").write_text("".join(point_lines), encoding="utf-8")

    def grid_positions(self, names: list[str], scale: float = 1.0) -> dict[str, tuple[float, float, float]]:
        return {
            name: (scale * float(index % 5), scale * float(index // 5), scale * float((index % 3) * 0.25))
            for index, name in enumerate(names)
        }

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

        self.assertEqual(report["strategy"], "seam_graph_sim3_v1")
        self.assertEqual(len(report["accepted_merge_tree"]), 2)
        self.assertIn("H.JPG", images)
        self.assertIn("I.JPG", images)

    def test_clean_sim3_seam_passes_strict_report(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            names = [f"IMG_{index:04d}.JPG" for index in range(22)]
            positions = self.grid_positions(names)
            self.write_model(root / "leaf0", names, [(names[0], names[1])], camera_positions=positions)
            self.write_model(root / "leaf1", names, [(names[2], names[3])], camera_positions=positions)

            report = reducer_canary.build_seam_merge_graph(
                normalized_dirs=[root / "leaf0", root / "leaf1"],
                thresholds=reducer_canary.SeamThresholds(
                    min_shared_images=20,
                    max_scale_delta=0.15,
                    max_sim3_p95_residual_m=0.25,
                    max_baseline_normalized_residual=0.01,
                    strict_production_gates=True,
                ),
            )

        self.assertEqual(report["decision"], "pass")
        self.assertEqual(report["accepted_merge_tree"][0]["blockers"], [])

    def test_manifest_pose_priors_emit_gps_exif_residual(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            names = [f"IMG_{index:04d}.JPG" for index in range(22)]
            positions = self.grid_positions(names)
            self.write_model(root / "leaf0", names, [(names[0], names[1])], camera_positions=positions)
            self.write_model(root / "leaf1", names, [(names[2], names[3])], camera_positions=positions)

            report = reducer_canary.build_seam_merge_graph(
                normalized_dirs=[root / "leaf0", root / "leaf1"],
                thresholds=reducer_canary.SeamThresholds(
                    min_shared_images=20,
                    max_scale_delta=0.15,
                    max_sim3_p95_residual_m=0.25,
                    max_baseline_normalized_residual=0.01,
                    strict_production_gates=True,
                ),
                planner_manifest={
                    "image_pose_priors_local": {
                        name: {
                            "local_x_m": xyz[0],
                            "local_y_m": xyz[1],
                            "local_z_m": xyz[2],
                        }
                        for name, xyz in positions.items()
                    }
                },
            )

        gps = report["candidate_edges"][0]["gps_exif_residual"]
        self.assertEqual(gps["status"], "evaluated")
        self.assertEqual(gps["shared_reference_count"], 22)
        self.assertEqual(gps["max_p95_m"], 0.0)

    def test_overlap_only_camera_outlier_tail_is_reported_and_quarantined(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            core_names = [f"CORE_{index:04d}.JPG" for index in range(22)]
            overlap_names = [f"OVERLAP_{index:04d}.JPG" for index in range(6)]
            all_names = core_names + overlap_names
            base_positions = self.grid_positions(all_names)
            shifted_overlap_positions = {
                **{name: base_positions[name] for name in core_names},
                **{
                    name: (base_positions[name][0] + 12.0, base_positions[name][1], base_positions[name][2])
                    for name in overlap_names
                },
            }
            self.write_model(root / "leaf0", all_names, [(core_names[0], core_names[1])], camera_positions=base_positions)
            self.write_model(
                root / "leaf1",
                all_names,
                [(core_names[2], core_names[3])],
                camera_positions=shifted_overlap_positions,
            )

            report = reducer_canary.build_seam_merge_graph(
                normalized_dirs=[root / "leaf0", root / "leaf1"],
                thresholds=reducer_canary.SeamThresholds(
                    min_shared_images=20,
                    max_scale_delta=0.15,
                    max_sim3_p95_residual_m=0.25,
                    max_baseline_normalized_residual=0.01,
                    strict_production_gates=True,
                ),
                planner_manifest={
                    "chunks": [
                        {"index": 2, "image_names": all_names, "core_names": core_names, "overlap_names": overlap_names},
                        {"index": 6, "image_names": all_names, "core_names": core_names, "overlap_names": overlap_names},
                    ]
                },
            )

        edge = report["candidate_edges"][0]
        role_report = edge["shared_camera_residual_roles"]
        self.assertEqual(report["decision"], "pass")
        self.assertEqual(edge["decision"], "accept")
        self.assertIn("overlap_only_camera_residual_tail_quarantined", edge["warnings"])
        self.assertGreater(edge["sim3_residual_m"]["p95"], 0.25)
        self.assertLess(role_report["trusted_core_involved_residual_m"]["p95"], 0.25)
        self.assertEqual(role_report["trusted_core_involved_count"], 22)
        self.assertEqual(role_report["top_outlier_images"][0]["role_pair"], "overlap|overlap")
        self.assertEqual(report["planner_leaf_mapping"]["leaf_to_chunk_index"], {"0": 2, "1": 6})

    def test_scaled_duplicate_wall_fails_strict_seam_gate(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            names = [f"IMG_{index:04d}.JPG" for index in range(22)]
            self.write_model(root / "leaf0", names, [(names[0], names[1])], camera_positions=self.grid_positions(names))
            self.write_model(
                root / "leaf1",
                names,
                [(names[2], names[3])],
                camera_positions=self.grid_positions(names, scale=1.30),
            )

            edge, _ = reducer_canary.evaluate_seam_edge(
                leaf_a=0,
                leaf_b=1,
                leaf_a_by_name={parts[9]: (parts, line) for parts, line in reducer_canary.image_record_pairs(root / "leaf0" / "images.txt")},
                leaf_b_by_name={parts[9]: (parts, line) for parts, line in reducer_canary.image_record_pairs(root / "leaf1" / "images.txt")},
                thresholds=reducer_canary.SeamThresholds(20, 0.15, 0.25, 0.01, True),
            )

        self.assertEqual(edge["decision"], "reject")
        self.assertIn("scale_delta_exceeds_gate", edge["blockers"])

    def test_collinear_shared_camera_degeneracy_fails_strict_gate(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            names = [f"IMG_{index:04d}.JPG" for index in range(22)]
            self.write_model(root / "leaf0", names, [(names[0], names[1])])
            self.write_model(root / "leaf1", names, [(names[2], names[3])])

            edge, _ = reducer_canary.evaluate_seam_edge(
                leaf_a=0,
                leaf_b=1,
                leaf_a_by_name={parts[9]: (parts, line) for parts, line in reducer_canary.image_record_pairs(root / "leaf0" / "images.txt")},
                leaf_b_by_name={parts[9]: (parts, line) for parts, line in reducer_canary.image_record_pairs(root / "leaf1" / "images.txt")},
                thresholds=reducer_canary.SeamThresholds(20, 0.15, 0.25, 0.01, True),
            )

        self.assertEqual(edge["decision"], "reject")
        self.assertIn("degenerate_shared_camera_layout", edge["blockers"])

    def test_weak_seam_below_20_shared_images_fails_production_mode(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            names = [f"IMG_{index:04d}.JPG" for index in range(19)]
            positions = self.grid_positions(names)
            self.write_model(root / "leaf0", names, [(names[0], names[1])], camera_positions=positions)
            self.write_model(root / "leaf1", names, [(names[2], names[3])], camera_positions=positions)

            edge, _ = reducer_canary.evaluate_seam_edge(
                leaf_a=0,
                leaf_b=1,
                leaf_a_by_name={parts[9]: (parts, line) for parts, line in reducer_canary.image_record_pairs(root / "leaf0" / "images.txt")},
                leaf_b_by_name={parts[9]: (parts, line) for parts, line in reducer_canary.image_record_pairs(root / "leaf1" / "images.txt")},
                thresholds=reducer_canary.SeamThresholds(20, 0.15, 0.25, 0.01, True),
            )

        self.assertEqual(edge["decision"], "reject")
        self.assertIn("weak_shared_camera_count", edge["blockers"])

    def test_graph_merge_rejects_bad_middle_seam_and_uses_safe_tree(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            names_01 = [f"A_{index}.JPG" for index in range(5)]
            names_02 = [f"B_{index}.JPG" for index in range(5)]
            names_12 = [f"C_{index}.JPG" for index in range(5)]
            leaf0_names = names_01 + names_02
            leaf1_names = names_01 + names_12
            leaf2_names = names_02 + names_12
            pos0 = {**self.grid_positions(names_01), **self.grid_positions(names_02)}
            pos1 = {**self.grid_positions(names_01, scale=1.3), **self.grid_positions(names_12)}
            pos2 = {**self.grid_positions(names_02), **self.grid_positions(names_12)}
            self.write_model(root / "leaf0", leaf0_names, [(leaf0_names[0], leaf0_names[1])], camera_positions=pos0)
            self.write_model(root / "leaf1", leaf1_names, [(leaf1_names[0], leaf1_names[1])], camera_positions=pos1)
            self.write_model(root / "leaf2", leaf2_names, [(leaf2_names[0], leaf2_names[1])], camera_positions=pos2)

            report = reducer_canary.build_seam_merge_graph(
                normalized_dirs=[root / "leaf0", root / "leaf1", root / "leaf2"],
                thresholds=reducer_canary.SeamThresholds(5, 0.15, 0.25, 0.01, True),
            )

        tree_pairs = {tuple(sorted((edge["leaf_a"], edge["leaf_b"]))) for edge in report["accepted_merge_tree"]}
        self.assertNotIn((0, 1), tree_pairs)
        self.assertEqual(tree_pairs, {(0, 2), (1, 2)})

    def test_duplicate_core_ownership_contract_culls_points_and_audits(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            shared = [f"IMG_{index:04d}.JPG" for index in range(20)]
            leaf0_names = shared + ["LEAF0_ONLY_A.JPG", "LEAF0_ONLY_B.JPG"]
            leaf1_names = shared + ["LEAF1_ONLY_A.JPG", "LEAF1_ONLY_B.JPG"]
            positions0 = {**self.grid_positions(shared), "LEAF0_ONLY_A.JPG": (8.0, 0.0, 0.0), "LEAF0_ONLY_B.JPG": (9.0, 0.0, 0.0)}
            positions1 = {**self.grid_positions(shared), "LEAF1_ONLY_A.JPG": (7.0, 7.0, 0.0), "LEAF1_ONLY_B.JPG": (8.0, 7.0, 0.0)}
            self.write_model(root / "leaf0", leaf0_names, [(shared[0], shared[1])], camera_positions=positions0)
            self.write_model(
                root / "leaf1",
                leaf1_names,
                [("LEAF1_ONLY_A.JPG", "LEAF1_ONLY_B.JPG")],
                camera_positions=positions1,
            )

            report = reducer_canary.write_pose_aligned_merge(
                normalized_dirs=[root / "leaf0", root / "leaf1"],
                output_dir=root / "merged",
                min_shared_images=20,
                planner_manifest={"chunks": [{"index": 1, "core_names": ["SOME_OTHER_CORE.JPG"]}]},
            )

        culling = report["post_merge_jurisdiction_culling"]
        self.assertEqual(culling["by_reason"]["no_core_owned_track"], 1)
        self.assertEqual(culling["removed_point_count"], 1)

    def test_shifted_duplicate_surface_fails_if_most_incoming_points_are_culled(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            shared = [f"IMG_{index:04d}.JPG" for index in range(22)]
            leaf0_names = shared + ["LEAF0_ONLY_A.JPG", "LEAF0_ONLY_B.JPG"]
            leaf1_names = shared + ["LEAF1_ONLY_A.JPG", "LEAF1_ONLY_B.JPG"]
            positions = self.grid_positions(shared)
            leaf0_points = [(float(index % 4) * 0.2, float(index // 4) * 0.2, 0.0) for index in range(12)]
            leaf1_points = [(x, y, z + 8.0) for x, y, z in leaf0_points]
            self.write_model(
                root / "leaf0",
                leaf0_names,
                [(shared[0], shared[1]) for _ in leaf0_points],
                camera_positions={
                    **positions,
                    "LEAF0_ONLY_A.JPG": (8.0, 0.0, 0.0),
                    "LEAF0_ONLY_B.JPG": (9.0, 0.0, 0.0),
                },
                point_positions=leaf0_points,
            )
            self.write_model(
                root / "leaf1",
                leaf1_names,
                [("LEAF1_ONLY_A.JPG", "LEAF1_ONLY_B.JPG") for _ in leaf1_points],
                camera_positions={
                    **positions,
                    "LEAF1_ONLY_A.JPG": (8.0, 1.0, 0.0),
                    "LEAF1_ONLY_B.JPG": (9.0, 1.0, 0.0),
                },
                point_positions=leaf1_points,
            )

            report = reducer_canary.write_pose_aligned_merge(
                normalized_dirs=[root / "leaf0", root / "leaf1"],
                output_dir=root / "merged",
                min_shared_images=20,
                strict_production_gates=True,
            )

        culling = report["post_merge_jurisdiction_culling"]
        self.assertEqual(culling["status"], "fail_excessive_duplicate_surface_culling")
        self.assertIn("excessive_duplicate_surface_culling", report["promotion_blockers"])
        self.assertGreaterEqual(culling["removed_point_count"], 12)

    def test_low_support_global_double_surface_points_are_culled_not_hidden(self):
        low_support_lines = []
        for index in range(20):
            z = 0.0 if index < 10 else 8.0
            low_support_lines.append(
                f"{index + 1} {(index % 5) * 0.05:.3f} {(index // 5) * 0.05:.3f} {z:.3f} "
                "255 0 0 0.5 1 0 2 0 3 0"
            )

        filtered, removed_ids, audit = reducer_canary.cull_low_support_global_double_surface_points(
            low_support_lines,
            max_points_per_cell=32,
        )

        self.assertEqual(filtered, [])
        self.assertEqual(len(removed_ids), 20)
        self.assertEqual(audit["status"], "pass_culled_low_support_cells")
        self.assertEqual(audit["removed_cell_count"], 1)

        high_support_lines = []
        for index in range(40):
            z = 0.0 if index < 20 else 8.0
            high_support_lines.append(
                f"{index + 1} {(index % 8) * 0.05:.3f} {(index // 8) * 0.05:.3f} {z:.3f} "
                "255 0 0 0.5 1 0 2 0 3 0"
            )

        filtered, removed_ids, audit = reducer_canary.cull_low_support_global_double_surface_points(
            high_support_lines,
            max_points_per_cell=32,
        )

        self.assertEqual(filtered, high_support_lines)
        self.assertEqual(removed_ids, set())
        self.assertEqual(audit["flagged_but_retained_cell_count"], 1)

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
