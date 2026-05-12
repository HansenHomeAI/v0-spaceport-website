import importlib.util
import tarfile
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = REPO_ROOT / "scripts" / "3dgs" / "extract_md1_visual_qa_bundle.py"


def load_module():
    spec = importlib.util.spec_from_file_location("extract_md1_visual_qa_bundle_test_module", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


class ExtractMd1VisualQaBundleTests(unittest.TestCase):
    def test_extracts_visual_assets_and_skips_model_weights(self):
        module = load_module()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            archive_path = root / "review.tar.gz"
            panel = root / "panel.png"
            panel.write_bytes(b"panel")
            manifest = root / "visual_qa_manifest.json"
            manifest.write_text("{}", encoding="utf-8")
            ply = root / "merged_splat.ply"
            ply.write_text("ply", encoding="utf-8")

            with tarfile.open(archive_path, "w:gz") as archive:
                archive.add(panel, arcname="quality_review/visual_panels/boundary/DJI_0068.png")
                archive.add(manifest, arcname="visual_qa_manifest.json")
                archive.add(ply, arcname="merged/merged_splat.ply")

            output_dir = root / "bundle"
            summary = module.extract_visual_qa_bundle(artifact=str(archive_path), output_dir=output_dir)

            self.assertEqual(summary["extracted_count"], 2)
            self.assertTrue((output_dir / "quality_review/visual_panels/boundary/DJI_0068.png").exists())
            self.assertTrue((output_dir / "visual_qa_manifest.json").exists())
            self.assertFalse((output_dir / "merged/merged_splat.ply").exists())
            self.assertIn("merged/merged_splat.ply", summary["skipped_files_sample"])

    def test_rejects_unsafe_tar_members(self):
        module = load_module()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            archive_path = root / "unsafe.tar.gz"
            payload = root / "payload.png"
            payload.write_bytes(b"x")
            with tarfile.open(archive_path, "w:gz") as archive:
                archive.add(payload, arcname="../quality_review/visual_panels/x.png")

            with self.assertRaisesRegex(RuntimeError, "Refusing unsafe tar member"):
                module.extract_visual_qa_bundle(artifact=str(archive_path), output_dir=root / "bundle")


if __name__ == "__main__":
    unittest.main()
