#!/usr/bin/env python3
"""Unit tests for the Litchi CSV -> DJI Fly KMZ converter."""
from __future__ import annotations

import csv
import zipfile
from pathlib import Path
from typing import List
import xml.etree.ElementTree as ET

import pytest

from mission_converter import ConversionOptions, convert_litchi_csv_to_dji_fly_kmz

NS = {
    "kml": "http://www.opengis.net/kml/2.2",
    "wpml": "http://www.dji.com/wpmz/1.0.2",
}

FIXTURE_DIR = Path(__file__).resolve().parents[1] / "fixtures"
EDGEWOOD_CSV = FIXTURE_DIR / "Edgewood-1.csv"


def _read_wpml(path: Path) -> ET.Element:
    with zipfile.ZipFile(path) as archive:
        data = archive.read("wpmz/waylines.wpml")
    return ET.fromstring(data)


def _placemarks(root: ET.Element) -> List[ET.Element]:
    return root.findall("kml:Document/kml:Folder/kml:Placemark", NS)


def _action_groups(placemark: ET.Element, trigger_type: str) -> List[ET.Element]:
    return [
        group
        for group in placemark.findall("wpml:actionGroup", NS)
        if group.find("wpml:actionTrigger/wpml:actionTriggerType", NS).text == trigger_type
    ]


def _count_csv_rows(csv_path: Path) -> int:
    with csv_path.open(newline="", encoding="utf-8-sig") as handle:
        return sum(1 for _ in csv.DictReader(handle))


def test_edgewood_waypoint_count_and_last_point(tmp_path: Path) -> None:
    output = tmp_path / "edgewood.kmz"
    options = ConversionOptions(
        emit_per_waypoint_photo=True,
        set_heading_from_csv=True,
        insert_yaw_actions=True,
    )
    convert_litchi_csv_to_dji_fly_kmz(EDGEWOOD_CSV, output, options)

    root = _read_wpml(output)
    placemarks = _placemarks(root)

    assert len(placemarks) == _count_csv_rows(EDGEWOOD_CSV)

    # Terminal waypoint must match the CSV coordinates.
    with EDGEWOOD_CSV.open(newline="", encoding="utf-8-sig") as handle:
        rows = list(csv.DictReader(handle))
    last_row = rows[-1]
    last_coords = tuple(map(float, (last_row["longitude"], last_row["latitude"])))

    last_pm = placemarks[-1]
    coords_text = last_pm.find("kml:Point/kml:coordinates", NS).text
    lon, lat = map(float, coords_text.split(","))
    assert (lon, lat) == pytest.approx(last_coords)


def test_action_group_indices_do_not_exceed_waypoints(tmp_path: Path) -> None:
    output = tmp_path / "edgewood.kmz"
    convert_litchi_csv_to_dji_fly_kmz(EDGEWOOD_CSV, output, ConversionOptions(emit_per_waypoint_photo=True))

    root = _read_wpml(output)
    placemarks = _placemarks(root)
    max_index = len(placemarks) - 1

    for placemark in placemarks:
        for action_group in placemark.findall("wpml:actionGroup", NS):
            end_index = int(action_group.find("wpml:actionGroupEndIndex", NS).text)
            assert end_index <= max_index


def test_gimbal_evenly_rotate_tracks_next_pitch(tmp_path: Path) -> None:
    output = tmp_path / "edgewood.kmz"
    convert_litchi_csv_to_dji_fly_kmz(EDGEWOOD_CSV, output, ConversionOptions())

    root = _read_wpml(output)
    placemarks = _placemarks(root)

    for idx, placemark in enumerate(placemarks[:-1]):
        actions = _action_groups(placemark, "betweenAdjacentPoints")
        assert actions, f"Expected gimbalEvenlyRotate action at waypoint {idx}"
        action = actions[0].find("wpml:action", NS)
        func = action.find("wpml:actionActuatorFunc", NS).text
        assert func == "gimbalEvenlyRotate"
        end_idx = int(actions[0].find("wpml:actionGroupEndIndex", NS).text)
        assert end_idx == idx + 1

    # Final waypoint should not contain betweenAdjacentPoints actions.
    assert not _action_groups(placemarks[-1], "betweenAdjacentPoints")


def test_photo_intervals_skip_terminal_segment(tmp_path: Path) -> None:
    output = tmp_path / "edgewood.kmz"
    convert_litchi_csv_to_dji_fly_kmz(EDGEWOOD_CSV, output, ConversionOptions(emit_per_waypoint_photo=True))

    root = _read_wpml(output)
    placemarks = _placemarks(root)

    # All legs except the final should have multipleTiming actions.
    for idx, placemark in enumerate(placemarks[:-1]):
        groups = _action_groups(placemark, "multipleTiming")
        assert groups, f"Expected multipleTiming action at waypoint {idx}"
        assert int(groups[0].find("wpml:actionGroupEndIndex", NS).text) == idx + 1
        func = groups[0].find("wpml:action/wpml:actionActuatorFunc", NS).text
        assert func == "takePhoto"

    assert not _action_groups(placemarks[-1], "multipleTiming")


def test_heading_angle_fields_follow_cli_flags(tmp_path: Path) -> None:
    output = tmp_path / "edgewood.kmz"
    convert_litchi_csv_to_dji_fly_kmz(
        EDGEWOOD_CSV,
        output,
        ConversionOptions(set_heading_from_csv=True, insert_yaw_actions=True),
    )

    root = _read_wpml(output)
    placemarks = _placemarks(root)

    for placemark in placemarks:
        enable = placemark.find("wpml:waypointHeadingParam/wpml:waypointHeadingAngleEnable", NS)
        assert enable is not None and enable.text == "1"
        yaw_actions = _action_groups(placemark, "reachPoint")
        # There will be gimbalRotate reachPoint at WP0; ensure a rotateYaw exists alongside.
        funcs = {
            action.find("wpml:actionActuatorFunc", NS).text
            for group in yaw_actions
            for action in group.findall("wpml:action", NS)
        }
        assert "rotateYaw" in funcs


def test_distance_interval_warning(tmp_path: Path) -> None:
    csv_path = tmp_path / "distance.csv"
    csv_path.write_text(
        "latitude,longitude,altitude(ft),heading(deg),curvesize(ft),rotationdir,gimbalmode,gimbalpitchangle,altitudemode,speed(m/s),poi_latitude,poi_longitude,poi_altitude(ft),poi_altitudemode,photo_timeinterval,photo_distinterval\n"
        "38.0,-78.0,100,0,0,0,0,0,0,5,0,0,0,0,0,5\n"
        "38.0001,-78.0001,100,0,0,0,0,0,0,5,0,0,0,0,0,0\n",
        encoding="utf-8",
    )

    output = tmp_path / "distance.kmz"
    with pytest.warns(RuntimeWarning):
        convert_litchi_csv_to_dji_fly_kmz(csv_path, output, ConversionOptions())


def test_agl_requires_acknowledgement(tmp_path: Path) -> None:
    csv_path = tmp_path / "agl.csv"
    csv_path.write_text(
        "latitude,longitude,altitude(ft),heading(deg),curvesize(ft),rotationdir,gimbalmode,gimbalpitchangle,altitudemode,speed(m/s),poi_latitude,poi_longitude,poi_altitude(ft),poi_altitudemode,photo_timeinterval,photo_distinterval\n"
        "38.0,-78.0,100,0,0,0,0,0,1,5,0,0,0,0,0,0\n",
        encoding="utf-8",
    )

    output = tmp_path / "agl.kmz"
    with pytest.raises(ValueError):
        convert_litchi_csv_to_dji_fly_kmz(csv_path, output, ConversionOptions())

    convert_litchi_csv_to_dji_fly_kmz(csv_path, output, ConversionOptions(assume_agl=True))
