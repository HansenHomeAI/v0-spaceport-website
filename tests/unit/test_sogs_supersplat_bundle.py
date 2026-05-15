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
        (self.compressed_dir / "chunk-0.webp").write_bytes(b"webp")

        self.skybox_source = self.root / "source-skybox.png"
        self.skybox_source.write_bytes(b"png")
        self.trained_skybox_source = self.root / "background_skybox.png"
        self.trained_skybox_source.write_bytes(b"trained-png")

        self.compressor = compress_module.PlayCanvasSOGSCompressor.__new__(
            compress_module.PlayCanvasSOGSCompressor
        )
        self.compressor.output_dir = str(self.output_dir)

    def test_create_supersplat_bundle_copies_trained_skybox_sidecar_and_writes_manifest(self):
        results = {
            "compressed_outputs": [
                {
                    "output_dir": str(self.compressed_dir),
                }
            ],
            "supporting_files": [str(self.trained_skybox_source)],
        }

        def fake_convert(source, destination):
            self.assertEqual(Path(source), self.trained_skybox_source)
            destination.write_bytes(b"webp")
            return True

        with mock.patch.object(
            compress_module,
            "_convert_skybox_to_webp",
            side_effect=fake_convert,
        ):
            self.compressor._create_supersplat_bundle(results)

        bundle_dir = self.output_dir / "supersplat_bundle"
        self.assertTrue((bundle_dir / "meta.json").exists())
        self.assertTrue((bundle_dir / "chunk-0.webp").exists())
        self.assertTrue((bundle_dir / "settings.json").exists())

        bundled_skybox = bundle_dir / "skybox" / "background_skybox.webp"
        self.assertTrue(bundled_skybox.exists())
        self.assertEqual(bundled_skybox.read_bytes(), b"webp")

        manifest = json.loads((bundle_dir / "spaceport_bundle.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest["version"], 1)
        self.assertEqual(manifest["skybox"]["type"], "equirect")
        self.assertEqual(manifest["skybox"]["path"], "skybox/background_skybox.webp")

    def test_create_supersplat_bundle_falls_back_to_trained_skybox_when_conversion_fails(self):
        results = {
            "compressed_outputs": [
                {
                    "output_dir": str(self.compressed_dir),
                }
            ],
            "supporting_files": [str(self.trained_skybox_source)],
        }

        with mock.patch.object(compress_module, "_convert_skybox_to_webp", return_value=False):
            self.compressor._create_supersplat_bundle(results)

        bundle_dir = self.output_dir / "supersplat_bundle"
        bundled_skybox = bundle_dir / "skybox" / "background_skybox.png"
        self.assertTrue(bundled_skybox.exists())
        self.assertEqual(bundled_skybox.read_bytes(), b"trained-png")

        manifest = json.loads((bundle_dir / "spaceport_bundle.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest["skybox"]["path"], "skybox/background_skybox.png")

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

    def test_create_supersplat_bundle_uses_default_skybox_only_when_opted_in(self):
        results = {
            "compressed_outputs": [
                {
                    "output_dir": str(self.compressed_dir),
                }
            ]
        }

        original_source = compress_module.CONTAINER_SKYBOX_SOURCE
        original_env = compress_module.os.environ.get("SOGS_BUNDLE_DEFAULT_SKYBOX")
        compress_module.CONTAINER_SKYBOX_SOURCE = self.skybox_source
        compress_module.os.environ["SOGS_BUNDLE_DEFAULT_SKYBOX"] = "1"
        try:
            def fake_convert(source, destination):
                self.assertEqual(Path(source), self.skybox_source)
                destination.write_bytes(b"default-webp")
                return True

            with mock.patch.object(
                compress_module,
                "_convert_skybox_to_webp",
                side_effect=fake_convert,
            ):
                self.compressor._create_supersplat_bundle(results)
        finally:
            compress_module.CONTAINER_SKYBOX_SOURCE = original_source
            if original_env is None:
                compress_module.os.environ.pop("SOGS_BUNDLE_DEFAULT_SKYBOX", None)
            else:
                compress_module.os.environ["SOGS_BUNDLE_DEFAULT_SKYBOX"] = original_env

        manifest = json.loads(
            (self.output_dir / "supersplat_bundle" / "spaceport_bundle.json").read_text(encoding="utf-8")
        )
        self.assertEqual(manifest["skybox"]["path"], "skybox/source-skybox.webp")


if __name__ == "__main__":
    unittest.main()
