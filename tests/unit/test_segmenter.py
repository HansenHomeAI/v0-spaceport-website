import sys
import unittest
from datetime import datetime, timedelta
from pathlib import Path


MODULE_ROOT = Path(__file__).resolve().parents[2] / "infrastructure" / "containers" / "sfm"
if str(MODULE_ROOT) not in sys.path:
    sys.path.insert(0, str(MODULE_ROOT))

from exif_manifest import ImageRecord
from segmenter import build_segments


def make_record(index: int, *, gap: float = 1.0) -> ImageRecord:
    capture_time = (datetime(2026, 3, 8, 9, 0, 0) + timedelta(seconds=index)).isoformat()
    return ImageRecord(
        name=f"DJI_{index:04d}.JPG",
        path=f"/tmp/DJI_{index:04d}.JPG",
        capture_time=capture_time,
        capture_sort_key=f"{index:05d}",
        latitude=41.0,
        longitude=-111.0,
        absolute_altitude_m=1424.0,
        relative_altitude_m=40.0,
        chosen_altitude_m=1424.0,
        flight_yaw_deg=-179.0,
        gimbal_pitch_deg=0.0,
        focal_length_mm=4.5,
        model="FC7303",
        width=4000,
        height=3000,
        camera_group="FC7303_4000x3000",
        gps_accuracy_m=5.0,
        enu_x_m=index * gap,
        enu_y_m=0.0,
        enu_z_m=0.0,
    )


class SegmenterTests(unittest.TestCase):
    def test_large_group_uses_overlap_windows(self):
        records = [make_record(index) for index in range(700)]
        segments = build_segments(
            records,
            target_size=450,
            overlap=90,
            max_size=600,
            min_size=250,
        )

        self.assertEqual(len(segments), 2)
        self.assertEqual(segments[0].image_count, 450)
        self.assertEqual(segments[1].image_count, 340)
        self.assertEqual(segments[1].image_names[0], records[360].name)

    def test_large_gap_creates_hard_break(self):
        records = [make_record(index) for index in range(250)]
        records.extend(make_record(index, gap=1000.0) for index in range(250, 500))
        segments = build_segments(
            records,
            target_size=450,
            overlap=90,
            max_size=600,
            min_size=250,
        )

        self.assertEqual(len(segments), 2)
        self.assertEqual(segments[0].image_count, 250)
        self.assertEqual(segments[1].image_count, 250)


if __name__ == "__main__":
    unittest.main()
