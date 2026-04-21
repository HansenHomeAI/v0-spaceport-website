import importlib.util
import sys
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = REPO_ROOT / "scripts" / "sfm" / "select_connected_chunk_subgraphs.py"
SPEC = importlib.util.spec_from_file_location("select_connected_chunk_subgraphs_test_module", MODULE_PATH)
chunk_selector = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
sys.modules[SPEC.name] = chunk_selector
SPEC.loader.exec_module(chunk_selector)


class ConnectedChunkSubgraphTests(unittest.TestCase):
    def test_rank_connected_candidates_prefers_stronger_shared_image_seam(self) -> None:
        manifest = {
            "chunks": [
                {"index": 0, "image_names": ["IMG_001.jpg", "IMG_002.jpg", "IMG_003.jpg"]},
                {"index": 1, "image_names": ["IMG_002.jpg", "IMG_003.jpg", "IMG_004.jpg"]},
                {"index": 2, "image_names": ["IMG_004.jpg", "IMG_005.jpg", "IMG_006.jpg"]},
                {"index": 3, "image_names": ["IMG_007.jpg", "IMG_008.jpg", "IMG_009.jpg"]},
            ]
        }

        ranked = chunk_selector.rank_connected_candidates(
            manifest,
            min_size=2,
            max_size=2,
            target_images=6,
        )

        self.assertGreaterEqual(len(ranked), 2)
        self.assertEqual(ranked[0]["chunk_indexes"], [0, 1])
        self.assertEqual(ranked[0]["total_shared_images"], 2)
        self.assertEqual(ranked[1]["chunk_indexes"], [1, 2])
        self.assertEqual(ranked[1]["total_shared_images"], 1)

    def test_rank_connected_candidates_supports_footprint_graph_manifest_fallback(self) -> None:
        manifest = {
            "footprint_graph_manifest": {
                "chunks": [
                    {"index": 4, "image_names": ["IMG_010.jpg", "IMG_011.jpg", "IMG_012.jpg"]},
                    {"index": 5, "image_names": ["IMG_012.jpg", "IMG_013.jpg", "IMG_014.jpg"]},
                    {"index": 6, "image_names": ["IMG_014.jpg", "IMG_015.jpg", "IMG_016.jpg"]},
                ]
            }
        }

        ranked = chunk_selector.rank_connected_candidates(
            manifest,
            min_size=3,
            max_size=3,
            target_images=7,
        )

        self.assertEqual(len(ranked), 1)
        self.assertEqual(ranked[0]["chunk_indexes"], [4, 5, 6])
        self.assertEqual(ranked[0]["edge_count"], 2)
        self.assertEqual(ranked[0]["unique_image_count"], 7)


if __name__ == "__main__":
    unittest.main()
