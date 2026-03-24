import json
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest import mock


MODULE_ROOT = Path(__file__).resolve().parents[2] / "infrastructure" / "containers" / "sfm"
if str(MODULE_ROOT) not in sys.path:
    sys.path.insert(0, str(MODULE_ROOT))

from exif_manifest import ExifManifestBuilder


class ExifManifestTests(unittest.TestCase):
    def test_extract_manifest_skips_missing_gps_and_sorts_by_timestamp(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            images_dir = Path(temp_dir)
            for name in ("DJI_0003.JPG", "DJI_0001.JPG", "DJI_0002.JPG"):
                (images_dir / name).write_bytes(b"fake")

            rows = [
                {
                    "FileName": "DJI_0001.JPG",
                    "Model": "FC7303",
                    "ImageWidth": 4000,
                    "ImageHeight": 3000,
                    "GPSLatitude": 41.0,
                    "GPSLongitude": -111.0,
                    "AbsoluteAltitude": 1424.0,
                    "RelativeAltitude": 40.0,
                    "FlightYawDegree": -179.6,
                    "GimbalPitchDegree": 0.0,
                    "FocalLength": 4.5,
                    "SubSecDateTimeOriginal": "2026:03:08 09:00:01.000",
                },
                {
                    "FileName": "DJI_0002.JPG",
                    "Model": "FC7303",
                    "ImageWidth": 4000,
                    "ImageHeight": 3000,
                    "GPSLatitude": 41.0001,
                    "GPSLongitude": -111.0001,
                    "AbsoluteAltitude": 1425.0,
                    "RelativeAltitude": 41.0,
                    "FlightYawDegree": -179.5,
                    "GimbalPitchDegree": 0.0,
                    "FocalLength": 4.5,
                    "SubSecDateTimeOriginal": "2026:03:08 09:00:02.000",
                },
                {
                    "FileName": "DJI_0003.JPG",
                    "Model": "FC7303",
                    "ImageWidth": 4000,
                    "ImageHeight": 3000,
                    "SubSecDateTimeOriginal": "2026:03:08 09:00:03.000",
                },
            ]

            with mock.patch("exif_manifest.subprocess.run") as run_mock:
                run_mock.return_value = types.SimpleNamespace(stdout=json.dumps(rows))
                builder = ExifManifestBuilder(images_dir)
                records, diagnostics = builder.extract_manifest()

            self.assertEqual(len(records), 2)
            self.assertEqual(records[0].name, "DJI_0001.JPG")
            self.assertEqual(records[1].name, "DJI_0002.JPG")
            self.assertEqual(records[0].camera_group, "FC7303_4000x3000")
            self.assertEqual(diagnostics["input_images"], 3)
            self.assertEqual(diagnostics["valid_images"], 2)
            self.assertEqual(len(diagnostics["skipped_images"]), 1)
            self.assertAlmostEqual(records[0].relative_altitude_m, 40.0)
            self.assertNotEqual(records[0].enu_x_m, records[1].enu_x_m)


if __name__ == "__main__":
    unittest.main()
