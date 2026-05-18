import io
import json
import tempfile
import unittest
import zipfile
from pathlib import Path

from scripts.montana_time_capsule import cv_hr_time_capsule as mtc


class FakeS3:
    def __init__(self, data: bytes):
        self.data = data

    def get_object(self, *, Bucket, Key, Range):  # noqa: N803 - boto3 shape
        start, end = [int(part) for part in Range.removeprefix("bytes=").split("-")]
        return {"Body": io.BytesIO(self.data[start : end + 1])}


def make_zip(names):
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_STORED) as archive:
        for name in names:
            archive.writestr(name, b"data")
    return output.getvalue()


class MontanaTimeCapsuleTests(unittest.TestCase):
    def test_parse_zip_image_count_from_central_directory(self):
        data = make_zip(["a/DJI_0001.JPG", "a/DJI_0002.dng", "notes/readme.txt"])

        summary = mtc.parse_zip_image_count(FakeS3(data), bucket="bucket", key="cv.zip", size=len(data))

        self.assertEqual(summary["zip_entries"], 3)
        self.assertEqual(summary["central_directory_entries"], 3)
        self.assertEqual(summary["image_count"], 2)
        self.assertEqual(summary["first_images"], ["a/DJI_0001.JPG", "a/DJI_0002.dng"])

    def test_profiles_use_digest_pinned_exact_montana_images(self):
        brass = mtc.PROFILES["brass-chunked"]
        horsetail = mtc.PROFILES["horsetail-gps"]

        self.assertIn(
            "@sha256:8fe38e3413e09954dcad77b8436c2a04defd20a39bdae1b3df573c504ef98811",
            brass.sfm_image,
        )
        self.assertIn(
            "@sha256:a7e2553455ad8ca7988256f4b0d38395e1770b2522532c41c6f535fc8a49f157",
            horsetail.sfm_image,
        )
        self.assertTrue(
            mtc.MONTANA_3DGS_IMAGE.endswith(
                "@sha256:482c1789b2d885beccf351b68d50e4b8135c43d5921c2379b0ba5fb152ed15db"
            )
        )
        self.assertTrue(
            mtc.MONTANA_COMPRESSOR_IMAGE.endswith(
                "@sha256:a0784727da1870ce9caa4774dc831a32fb96cd1574df389cf9093fbf18f4f4ab"
            )
        )

    def test_save_state_records_update_timestamp(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "state.json"
            mtc.save_state(path, {"status": "waiting"})
            saved = json.loads(path.read_text())

        self.assertEqual(saved["status"], "waiting")
        self.assertTrue(saved["updated_at"].endswith("Z"))

    def test_validate_run_id_accepts_isolated_parallel_name(self):
        self.assertEqual(
            mtc.validate_run_id("cvhr-secondary-20260518t2115z"),
            "cvhr-secondary-20260518t2115z",
        )

    def test_validate_run_id_rejects_unsafe_name(self):
        with self.assertRaises(ValueError):
            mtc.validate_run_id("cvhr_secondary_20260518T2115Z")
