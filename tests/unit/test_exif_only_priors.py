#!/usr/bin/env python3
"""Unit tests for EXIF-only GPS prior generation."""

from datetime import datetime, timedelta
from pathlib import Path
import json

from infrastructure.containers.sfm.gps_processor_3d import ExifOnlyPriorBuilder


def test_exif_only_priors_writes_opensfm_files(tmp_path: Path):
    images_dir = tmp_path / "images"
    output_dir = tmp_path / "output"
    images_dir.mkdir(parents=True)

    # Create fake image files
    for idx in range(6):
        (images_dir / f"DJI_{idx:04d}.JPG").write_bytes(b"fake")

    builder = ExifOnlyPriorBuilder(images_dir, output_dir)

    # Inject deterministic EXIF data
    def fake_exif(photo_path: Path):
        idx = int(photo_path.stem.split('_')[-1])
        return {
            'latitude': 40.0 + idx * 0.0001,
            'longitude': -111.0 - idx * 0.0001,
            'altitude': 100.0 + idx,
            'gps_accuracy': 5.0,
            'timestamp': datetime(2025, 1, 1, 12, 0, 0) + timedelta(seconds=idx),
            'flight_yaw': None,
            'flight_pitch': None,
            'flight_roll': None,
            'gimbal_yaw': None,
            'gimbal_pitch': None,
            'gimbal_roll': None,
        }

    builder.exif_reader.extract_dji_gps_from_exif = fake_exif  # type: ignore[attr-defined]

    ok, stats = builder.build_priors()
    assert ok
    builder.write_opensfm_files(stats['entries'])

    exif_overrides = output_dir / 'exif_overrides.json'
    gps_priors = output_dir / 'gps_priors.json'
    reference_lla = output_dir / 'reference_lla.json'

    assert exif_overrides.exists()
    assert gps_priors.exists()
    assert reference_lla.exists()

    with open(exif_overrides, 'r') as f:
        overrides = json.load(f)
    assert len(overrides) == 6

    with open(gps_priors, 'r') as f:
        priors = json.load(f)
    assert len(priors['cameras']) == 6
