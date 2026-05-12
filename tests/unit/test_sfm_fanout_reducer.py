import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SFM_SCRIPT_DIR = REPO_ROOT / "scripts" / "sfm"
if str(SFM_SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SFM_SCRIPT_DIR))
MODULE_PATH = SFM_SCRIPT_DIR / "run_sfm_fanout_reducer.py"
SPEC = importlib.util.spec_from_file_location("run_sfm_fanout_reducer_test_module", MODULE_PATH)
fanout_reducer = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
sys.modules[SPEC.name] = fanout_reducer
SPEC.loader.exec_module(fanout_reducer)


class SfmFanoutReducerTest(unittest.TestCase):
    def test_materialize_leaf_sparse_prefers_sparse_raw(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            leaf = root / "leaf"
            sparse_raw = leaf / "sparse_raw" / "0"
            sparse = leaf / "sparse" / "0"
            sparse_raw.mkdir(parents=True)
            sparse.mkdir(parents=True)
            for directory, marker in ((sparse_raw, "raw"), (sparse, "filtered")):
                (directory / "cameras.txt").write_text(f"# {marker}\n", encoding="utf-8")
                (directory / "images.txt").write_text(f"# {marker}\n", encoding="utf-8")
                (directory / "points3D.txt").write_text(f"# {marker}\n", encoding="utf-8")

            materialized, report = fanout_reducer.materialize_leaf_sparse(str(leaf), root / "downloaded")

            self.assertEqual((materialized / "cameras.txt").read_text(encoding="utf-8"), "# raw\n")
            self.assertEqual(report["source"], str(sparse_raw))

    def test_write_standard_output_package_writes_sparse_and_metadata(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            merged = root / "merged"
            merged.mkdir()
            for file_name in ("cameras.txt", "images.txt", "points3D.txt"):
                (merged / file_name).write_text(file_name, encoding="utf-8")
            output = root / "output"

            fanout_reducer.write_standard_output_package(
                merged_text_dir=merged,
                output_dir=output,
                reducer_metadata={"decision": "pass"},
            )

            self.assertTrue((output / "sparse" / "0" / "images.txt").exists())
            self.assertTrue((output / "sparse_raw" / "0" / "points3D.txt").exists())
            self.assertIn("\"decision\": \"pass\"", (output / "reducer_metadata.json").read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
