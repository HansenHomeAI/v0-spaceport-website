#!/usr/bin/env python3
"""Unit tests for DJI EXIF DMS parsing and trajectory projection helpers."""

import math
import numpy as np
from pathlib import Path

from infrastructure.containers.sfm.gps_processor_3d import Advanced3DPathProcessor, FlightSegment, ExifOnlyPriorBuilder


def test_dms_to_decimal_north_east_west_south():
    proc = Advanced3DPathProcessor(csv_path=Path('/tmp/none.csv'), images_dir=Path('/tmp/none'))

    # 47° 51' 0.198" N -> 47 + 51/60 + 0.198/3600
    lat_dms = [(47, 1), (51, 1), (198, 1000)]
    lat = proc._dms_to_decimal(lat_dms, 'N')
    assert abs(lat - (47 + 51/60 + 0.198/3600)) < 1e-8

    # 114° 15' 44.142" W -> negative
    lon_dms = [(114, 1), (15, 1), (44142, 1000)]
    lon = proc._dms_to_decimal(lon_dms, 'W')
    assert abs(lon - (-(114 + 15/60 + 44.142/3600))) < 1e-8


def test_find_closest_trajectory_point_straight_segment():
    proc = Advanced3DPathProcessor(csv_path=Path('/tmp/none.csv'), images_dir=Path('/tmp/none'))
    # Create a simple straight segment from (0,0,10) to (100,0,20)
    seg = FlightSegment(
        start_point=np.array([0.0, 0.0, 10.0]),
        end_point=np.array([100.0, 0.0, 20.0]),
        control_points=[],
        start_waypoint_idx=0,
        end_waypoint_idx=1,
        distance=100.0,
        heading=0.0,
        altitude_change=10.0,
        curvature_radius=None,
    )
    proc.flight_segments = [seg]
    proc.path_distances = [0.0, 100.0]

    # EXIF XY close to the midpoint in XY (x=50, y=2)
    exif_xy = np.array([50.0, 2.0])
    closest = proc.find_closest_trajectory_point(exif_xy)
    assert closest['segment_index'] == 0
    # Altitude should be ~15 at t ~0.5
    assert math.isclose(closest['altitude_local'], 15.0, rel_tol=0, abs_tol=0.2)
    # Distance should be ~2 meters (y offset)
    assert math.isclose(closest['distance_m'], 2.0, rel_tol=0, abs_tol=0.2)


def test_project_exif_gps_to_trajectory_uses_trajectory_altitude():
    proc = Advanced3DPathProcessor(csv_path=Path('/tmp/none.csv'), images_dir=Path('/tmp/none'))
    # Mock local origin altitude and simple segment
    proc.local_origin = (0.0, 0.0, 100.0)  # altitude origin = 100
    proc.path_distances = [0.0, 100.0]
    seg = FlightSegment(
        start_point=np.array([0.0, 0.0, 10.0]),
        end_point=np.array([100.0, 0.0, 20.0]),
        control_points=[],
        start_waypoint_idx=0,
        end_waypoint_idx=1,
        distance=100.0,
        heading=0.0,
        altitude_change=10.0,
        curvature_radius=None,
    )
    proc.flight_segments = [seg]

    # Monkeypatch local conversion to treat lat->x and lon->y directly in meters for this unit test
    proc.convert_to_local_3d = lambda lat, lon, alt: np.array([lat, lon, alt], dtype=float)

    # EXIF location maps to x=50, y=0 (on the path mid point)
    exif = {'latitude': 50.0, 'longitude': 0.0}
    projected = proc.project_exif_gps_to_trajectory(exif)

    # At t=0.5, local z = 15 -> absolute altitude = 115
    assert math.isclose(projected['altitude'], 115.0, rel_tol=0, abs_tol=0.2)
    assert projected['mapping_method'] == 'exif_trajectory_projection'
    assert projected['segment_index'] == 0
    assert 0.45 <= projected['segment_t'] <= 0.55


def test_exif_only_prior_builder_writes_opensfm_files(tmp_path):
    images_dir = tmp_path / "images"
    images_dir.mkdir()
    (images_dir / "IMG_0001.JPG").write_bytes(b"not-a-real-jpeg")
    (images_dir / "IMG_0002.JPG").write_bytes(b"not-a-real-jpeg")

    builder = ExifOnlyPriorBuilder(images_dir=images_dir, min_images_with_gps=2)

    # Monkeypatch EXIF extraction to avoid needing real JPEG EXIF blocks.
    def _fake_extract(p: Path):
        if p.name == "IMG_0001.JPG":
            return {"latitude": 41.0, "longitude": -111.0, "altitude": 150.0, "timestamp": None}
        if p.name == "IMG_0002.JPG":
            return {"latitude": 41.0001, "longitude": -111.0001, "altitude": 151.0, "timestamp": None}
        return None

    builder._exif_proc.extract_dji_gps_from_exif = _fake_extract  # type: ignore[attr-defined]

    summary = builder.build_photo_positions()
    assert summary["ok"] is True
    assert summary["photos_total"] == 2
    assert summary["photos_with_exif_gps"] == 2
    assert len(builder.photo_positions) == 2

    out_dir = tmp_path / "opensfm"
    builder.generate_opensfm_files(out_dir)

    assert (out_dir / "exif_overrides.json").exists()
    assert (out_dir / "gps_priors.json").exists()
    assert (out_dir / "reference_lla.json").exists()
    assert (out_dir / "reference.txt").exists()
