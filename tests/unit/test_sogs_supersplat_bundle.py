import json
import importlib.util
import sys
import tempfile
import types
import unittest
from unittest import mock
from pathlib import Path


MODULE_PATH = (
    Path(__file__).resolve().parents[2]
    / "infrastructure"
    / "containers"
    / "compressor"
    / "compress.py"
)


if "boto3" not in sys.modules:
    fake_boto3 = types.SimpleNamespace(client=lambda *_args, **_kwargs: None)
    sys.modules["boto3"] = fake_boto3

SPEC = importlib.util.spec_from_file_location("compress_module", MODULE_PATH)
compress_module = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(compress_module)


class SogsSupersplatBundleTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.root = Path(self.temp_dir.name)
        self.output_dir = self.root / "output"
        self.output_dir.mkdir()
        self.compressed_dir = self.root / "compressed_example"
        self.compressed_dir.mkdir()

        (self.compressed_dir / "meta.json").write_text('{"asset": "ok"}', encoding="utf-8")
        (self.compressed_dir / "lod-meta.json").write_text(
            '{"lodLevels": 2, "filenames": ["0_0/meta.json"], "tree": {"lods": {"0": {"file": 0, "offset": 0, "count": 1}}}}',
            encoding="utf-8",
        )
        (self.compressed_dir / "chunk-0.webp").write_bytes(b"webp")
        (self.compressed_dir / "0_0").mkdir()
        (self.compressed_dir / "0_0" / "meta.json").write_text('{"asset": "lod"}', encoding="utf-8")
        (self.compressed_dir / "0_0" / "means_l.webp").write_bytes(b"lod-webp")

        self.skybox_source = self.root / "source-skybox.png"
        self.skybox_source.write_bytes(b"png")

        self.compressor = compress_module.PlayCanvasSOGSCompressor.__new__(
            compress_module.PlayCanvasSOGSCompressor
        )
        self.compressor.output_dir = str(self.output_dir)

    def test_create_supersplat_bundle_copies_bundle_and_writes_optimized_skybox_manifest(self):
        results = {
            "compressed_outputs": [
                {
                    "output_dir": str(self.compressed_dir),
                }
            ]
        }

        original_source = compress_module.CONTAINER_SKYBOX_SOURCE
        compress_module.CONTAINER_SKYBOX_SOURCE = self.skybox_source
        try:
            def fake_convert(_source, destination):
                destination.write_bytes(b"webp")
                return True

            with mock.patch.object(
                compress_module,
                "_convert_skybox_to_webp",
                side_effect=fake_convert,
            ):
                self.compressor._create_supersplat_bundle(results)
        finally:
            compress_module.CONTAINER_SKYBOX_SOURCE = original_source

        bundle_dir = self.output_dir / "supersplat_bundle"
        self.assertTrue((bundle_dir / "meta.json").exists())
        self.assertTrue((bundle_dir / "lod-meta.json").exists())
        self.assertTrue((bundle_dir / "chunk-0.webp").exists())
        self.assertTrue((bundle_dir / "0_0" / "meta.json").exists())
        self.assertTrue((bundle_dir / "0_0" / "means_l.webp").exists())
        self.assertTrue((bundle_dir / "settings.json").exists())

        bundled_skybox = bundle_dir / "skybox" / compress_module.SKYBOX_GENERATED_ASSET_NAME
        self.assertTrue(bundled_skybox.exists())
        self.assertEqual(bundled_skybox.read_bytes(), b"webp")

        manifest = json.loads((bundle_dir / "spaceport_bundle.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest["version"], 1)
        self.assertEqual(manifest["skybox"]["type"], "equirect")
        self.assertEqual(manifest["skybox"]["path"], compress_module.SKYBOX_BUNDLE_RELATIVE_PATH)
        self.assertEqual(manifest["entrypoints"]["default"], "lod-meta.json")
        self.assertEqual(manifest["streaming"]["lodLevels"], 2)

    def test_create_supersplat_bundle_prefers_generated_background_skybox(self):
        results = {
            "compressed_outputs": [
                {
                    "output_dir": str(self.compressed_dir),
                }
            ]
        }
        generated_skybox = self.root / "background_skybox.webp"
        generated_skybox.write_bytes(b"generated-webp")

        self.compressor._create_supersplat_bundle(results, [generated_skybox])

        bundle_dir = self.output_dir / "supersplat_bundle"
        self.assertTrue((bundle_dir / "background_skybox.webp").exists())
        bundled_skybox = bundle_dir / "skybox" / "background_skybox.webp"
        self.assertTrue(bundled_skybox.exists())
        self.assertEqual(bundled_skybox.read_bytes(), b"generated-webp")

        manifest = json.loads((bundle_dir / "spaceport_bundle.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest["skybox"]["path"], "skybox/background_skybox.webp")

    def test_create_supersplat_bundle_falls_back_to_source_skybox_when_conversion_fails(self):
        results = {
            "compressed_outputs": [
                {
                    "output_dir": str(self.compressed_dir),
                }
            ]
        }

        original_source = compress_module.CONTAINER_SKYBOX_SOURCE
        compress_module.CONTAINER_SKYBOX_SOURCE = self.skybox_source
        try:
            with mock.patch.object(compress_module, "_convert_skybox_to_webp", return_value=False):
                self.compressor._create_supersplat_bundle(results)
        finally:
            compress_module.CONTAINER_SKYBOX_SOURCE = original_source

        bundle_dir = self.output_dir / "supersplat_bundle"
        bundled_skybox = bundle_dir / "skybox" / compress_module.SKYBOX_SOURCE_ASSET_NAME
        self.assertTrue(bundled_skybox.exists())
        self.assertEqual(bundled_skybox.read_bytes(), b"png")

        manifest = json.loads((bundle_dir / "spaceport_bundle.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest["skybox"]["path"], compress_module.SKYBOX_SOURCE_BUNDLE_RELATIVE_PATH)

    def test_create_supersplat_bundle_sets_null_skybox_when_asset_missing(self):
        results = {
            "compressed_outputs": [
                {
                    "output_dir": str(self.compressed_dir),
                }
            ]
        }

        original_source = compress_module.CONTAINER_SKYBOX_SOURCE
        compress_module.CONTAINER_SKYBOX_SOURCE = self.root / "missing.png"
        try:
            self.compressor._create_supersplat_bundle(results)
        finally:
            compress_module.CONTAINER_SKYBOX_SOURCE = original_source

        manifest = json.loads(
            (self.output_dir / "supersplat_bundle" / "spaceport_bundle.json").read_text(encoding="utf-8")
        )
        self.assertIsNone(manifest["skybox"])


if __name__ == "__main__":
    unittest.main()
