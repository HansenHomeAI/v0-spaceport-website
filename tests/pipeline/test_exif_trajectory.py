#!/usr/bin/env python3
"""Unit tests for EXIF DMS conversion and trajectory projection."""

from pathlib import Path
import types
import numpy as np


def test_dms_to_decimal_and_projection_smoke():
    # Load module directly
    module_path = Path(__file__).parents[2] / 'infrastructure' / 'containers' / 'sfm' / 'gps_processor_3d.py'
    import importlib.util
    spec = importlib.util.spec_from_file_location("gps_processor_3d", str(module_path))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    # Test DMS conversion strings
    proc = types.SimpleNamespace()
    proc._dms_to_decimal = getattr(mod.Advanced3DPathProcessor, '_dms_to_decimal')
    # Bind to instance-like by calling through class expecting (self, ...)
    dummy = mod.Advanced3DPathProcessor.__new__(mod.Advanced3DPathProcessor)
    # North/East
    lat = mod.Advanced3DPathProcessor._dms_to_decimal(dummy, '47° 51\' 0.198" N', 'N')
    lon = mod.Advanced3DPathProcessor._dms_to_decimal(dummy, '114° 15\' 44.142" W', 'W')
    assert abs(lat - 47.850055) < 1e-6
    assert abs(lon - (-114.2622617)) < 1e-5

    # Prepare tiny synthetic flight path for projection
    # Create a minimal processor with two waypoints
    import pandas as pd
    csv_path = Path(__file__).parent / 'tmp_flight.csv'
    df = pd.DataFrame({
        'latitude': [47.85, 47.851],
        'longitude': [-114.2625, -114.2620],
        'altitude': [130.0, 131.0],
    })
    df.to_csv(csv_path, index=False)

    images_dir = Path(__file__).parent
    p = mod.Advanced3DPathProcessor(csv_path, images_dir)
    p.parse_flight_csv()
    p.setup_local_coordinate_system()
    p.build_3d_flight_path()

    # Project EXIF lat/lon near the path
    fused = p.project_exif_gps_to_trajectory({'latitude': float(lat), 'longitude': float(lon), 'timestamp': None})
    assert 'altitude' in fused and isinstance(fused['altitude'], float)
    assert 'trajectory_confidence' in fused and 0.0 <= fused['trajectory_confidence'] <= 1.0

    # Cleanup
    try:
        csv_path.unlink()
    except Exception:
        pass

