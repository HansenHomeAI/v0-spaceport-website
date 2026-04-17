import importlib.util
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest import mock


REPO_ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = REPO_ROOT / "scripts" / "sfm" / "build_manifest_subset_zip.py"
SPEC = importlib.util.spec_from_file_location("build_manifest_subset_zip_test_module", MODULE_PATH)
subset_zip = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
sys.modules[SPEC.name] = subset_zip
SPEC.loader.exec_module(subset_zip)


class ManifestSubsetZipTests(unittest.TestCase):
    def write_zip(self, zip_path: Path, members: dict[str, bytes]) -> None:
        with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            for name, content in members.items():
                archive.writestr(name, content)

    def test_resolve_subset_basenames_supports_dotted_paths(self):
        manifest = {
            "probe_subsets": {
                "geometry_mix": [
                    "captures/IMG_001.jpg",
                    "s3://bucket/datasets/IMG_002.jpg",
                    "https://example.com/files/IMG_003.jpg?token=abc123",
                ]
            }
        }

        basenames = subset_zip.resolve_subset_basenames(manifest, "probe_subsets.geometry_mix")

        self.assertEqual(basenames, ["IMG_001.jpg", "IMG_002.jpg", "IMG_003.jpg"])

    def test_resolve_subset_basenames_supports_dict_payloads(self):
        manifest = {
            "probe_subsets": {
                "geometry_mix": {
                    "image_names": [
                        {"path": "nested/IMG_004.jpg"},
                        {"uri": "s3://bucket/probes/IMG_005.jpg"},
                    ]
                }
            }
        }

        basenames = subset_zip.resolve_subset_basenames(manifest, "probe_subsets.geometry_mix")

        self.assertEqual(basenames, ["IMG_004.jpg", "IMG_005.jpg"])

    def test_create_subset_zip_writes_requested_images_in_order(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            input_zip = root / "input.zip"
            output_zip = root / "subset.zip"
            self.write_zip(
                input_zip,
                {
                    "captures/IMG_001.jpg": b"first",
                    "captures/IMG_002.jpg": b"second",
                    "notes/readme.txt": b"ignore me",
                },
            )

            written = subset_zip.create_subset_zip(
                input_zip,
                ["IMG_002.jpg", "IMG_001.jpg"],
                output_zip,
            )

            self.assertEqual(written, ["IMG_002.jpg", "IMG_001.jpg"])
            with zipfile.ZipFile(output_zip, "r") as archive:
                self.assertEqual(archive.namelist(), ["IMG_002.jpg", "IMG_001.jpg"])
                self.assertEqual(archive.read("IMG_002.jpg"), b"second")
                self.assertEqual(archive.read("IMG_001.jpg"), b"first")

    def test_create_subset_zip_rejects_missing_and_duplicate_basenames(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            duplicate_zip = root / "duplicate.zip"
            self.write_zip(
                duplicate_zip,
                {
                    "captures/a/IMG_001.jpg": b"first",
                    "captures/b/IMG_001.jpg": b"second",
                },
            )

            with self.assertRaisesRegex(ValueError, "duplicate image basename"):
                subset_zip.create_subset_zip(duplicate_zip, ["IMG_001.jpg"], root / "unused.zip")

            input_zip = root / "input.zip"
            self.write_zip(input_zip, {"captures/IMG_010.jpg": b"present"})

            with self.assertRaisesRegex(ValueError, "missing from archive"):
                subset_zip.create_subset_zip(input_zip, ["IMG_011.jpg"], root / "missing.zip")

    def test_parse_args_accepts_input_zip_flag(self):
        with mock.patch.object(
            sys,
            "argv",
            [
                "build_manifest_subset_zip.py",
                "--input-zip",
                "s3://bucket/input.zip",
                "--manifest-uri",
                "s3://bucket/manifest.json",
                "--subset-key",
                "probe_subsets.geometry_mix",
                "--output",
                "/tmp/subset.zip",
            ],
        ):
            args = subset_zip.parse_args()

        self.assertEqual(args.input_zip, "s3://bucket/input.zip")
        self.assertEqual(args.manifest_uri, "s3://bucket/manifest.json")
        self.assertEqual(args.subset_key, "probe_subsets.geometry_mix")


if __name__ == "__main__":
    unittest.main()
