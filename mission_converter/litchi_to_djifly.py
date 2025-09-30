"""Convert Litchi waypoint CSV missions into DJI Fly KMZ (WPML) missions."""
from __future__ import annotations

import csv
import io
import math
import time
import warnings
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Tuple
import xml.etree.ElementTree as ET

NS_KML = "http://www.opengis.net/kml/2.2"
NS_WP = "http://www.dji.com/wpmz/1.0.2"

ET.register_namespace("", NS_KML)
ET.register_namespace("wpml", NS_WP)


@dataclass(frozen=True)
class ConversionOptions:
    """User-configurable conversion behaviour."""

    finish_action: str = "goHome"
    global_transitional_speed: float = 3.0
    set_heading_from_csv: bool = False
    insert_yaw_actions: bool = False
    emit_per_waypoint_photo: bool = False
    assume_agl: bool = False
    drone_enum_value: str = "68"
    drone_sub_enum_value: str = "0"
    mission_author: str = "SpaceportConverter"

    def validate(self) -> None:
        if self.global_transitional_speed <= 0:
            raise ValueError("global_transitional_speed must be > 0")
        allowed = {"goHome", "land", "hover", "returnToStartPoint"}
        if self.finish_action not in allowed:
            raise ValueError(f"finish_action must be one of {sorted(allowed)}")


@dataclass
class LitchiWaypoint:
    """Normalised representation of a Litchi CSV waypoint row."""

    index: int
    latitude: float
    longitude: float
    altitude_ft: float
    heading_deg: Optional[float]
    curvesize_ft: float
    rotation_dir: Optional[int]
    gimbal_mode: Optional[int]
    gimbal_pitch_deg: Optional[float]
    altitude_mode: Optional[int]
    speed_mps: Optional[float]
    poi_latitude: Optional[float]
    poi_longitude: Optional[float]
    poi_altitude_ft: Optional[float]
    photo_timeinterval_s: Optional[float]
    photo_distinterval_m: Optional[float]

    @property
    def altitude_m(self) -> float:
        return feet_to_metres(self.altitude_ft)

    @property
    def poi_altitude_m(self) -> Optional[float]:
        return feet_to_metres(self.poi_altitude_ft) if self.poi_altitude_ft is not None else None


class ActionGroupCounter:
    """Simple counter to hand out unique actionGroupId values."""

    def __init__(self) -> None:
        self._next = 0

    def increment(self) -> str:
        current = self._next
        self._next += 1
        return str(current)


def feet_to_metres(value_ft: float) -> float:
    return value_ft * 0.3048


def maybe_float(value: Optional[str]) -> Optional[float]:
    if value is None:
        return None
    value = value.strip()
    if not value:
        return None
    try:
        return float(value)
    except ValueError:
        raise ValueError(f"Unable to parse float from '{value}'") from None


def maybe_int(value: Optional[str]) -> Optional[int]:
    if value is None:
        return None
    value = value.strip()
    if not value:
        return None
    try:
        return int(float(value))
    except ValueError:
        raise ValueError(f"Unable to parse int from '{value}'") from None


REQUIRED_COLUMNS = {"latitude", "longitude", "altitude(ft)"}


def parse_litchi_csv(csv_path: Path) -> List[LitchiWaypoint]:
    """Read and normalise the Litchi CSV rows."""

    with csv_path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            raise ValueError("CSV is missing header row")
        missing = REQUIRED_COLUMNS.difference(reader.fieldnames)
        if missing:
            raise ValueError(f"CSV is missing required columns: {sorted(missing)}")

        waypoints: List[LitchiWaypoint] = []
        for idx, row in enumerate(reader):
            lat = maybe_float(row.get("latitude"))
            lon = maybe_float(row.get("longitude"))
            alt_ft = maybe_float(row.get("altitude(ft)"))
            if lat is None or lon is None or alt_ft is None:
                raise ValueError(f"Row {idx} is missing latitude/longitude/altitude")

            waypoint = LitchiWaypoint(
                index=idx,
                latitude=lat,
                longitude=lon,
                altitude_ft=alt_ft,
                heading_deg=maybe_float(row.get("heading(deg)")),
                curvesize_ft=maybe_float(row.get("curvesize(ft)")) or 0.0,
                rotation_dir=maybe_int(row.get("rotationdir")),
                gimbal_mode=maybe_int(row.get("gimbalmode")),
                gimbal_pitch_deg=maybe_float(row.get("gimbalpitchangle")),
                altitude_mode=maybe_int(row.get("altitudemode")),
                speed_mps=maybe_float(row.get("speed(m/s)")),
                poi_latitude=maybe_float(row.get("poi_latitude")),
                poi_longitude=maybe_float(row.get("poi_longitude")),
                poi_altitude_ft=maybe_float(row.get("poi_altitude(ft)")),
                photo_timeinterval_s=maybe_float(row.get("photo_timeinterval")),
                photo_distinterval_m=maybe_float(row.get("photo_distinterval")),
            )
            waypoints.append(waypoint)

    if not waypoints:
        raise ValueError("CSV does not contain any waypoint rows")

    return waypoints


def _validate_altitude_modes(waypoints: Sequence[LitchiWaypoint], options: ConversionOptions) -> None:
    modes = {wp.altitude_mode for wp in waypoints if wp.altitude_mode is not None}
    if 1 in modes and not options.assume_agl:
        raise ValueError(
            "Mission includes altitudemode=1 (AGL). Pass --assume-agl to continue or convert heights with a DEM first."
        )


def _format_float(value: float, decimals: int = 6) -> str:
    return f"{value:.{decimals}f}"


def _add_text(parent: ET.Element, tag: str, text: str) -> ET.Element:
    elem = ET.SubElement(parent, ET.QName(NS_WP, tag))
    elem.text = text
    return elem


def _build_mission_config(parent: ET.Element, options: ConversionOptions) -> None:
    mission = ET.SubElement(parent, ET.QName(NS_WP, "missionConfig"))
    _add_text(mission, "flyToWaylineMode", "safely")
    _add_text(mission, "finishAction", options.finish_action)
    _add_text(mission, "exitOnRCLost", "executeLostAction")
    _add_text(mission, "executeRCLostAction", "goBack")
    _add_text(mission, "globalTransitionalSpeed", _format_float(options.global_transitional_speed, 2))

    drone = ET.SubElement(mission, ET.QName(NS_WP, "droneInfo"))
    _add_text(drone, "droneEnumValue", options.drone_enum_value)
    _add_text(drone, "droneSubEnumValue", options.drone_sub_enum_value)


def _build_folder(parent: ET.Element, options: ConversionOptions) -> ET.Element:
    folder = ET.SubElement(parent, "Folder")
    _add_text(folder, "templateId", "0")
    _add_text(folder, "executeHeightMode", "relativeToStartPoint")
    _add_text(folder, "waylineId", "0")
    _add_text(folder, "distance", "0")
    _add_text(folder, "duration", "0")
    _add_text(folder, "autoFlightSpeed", _format_float(options.global_transitional_speed, 2))
    return folder


def _populate_waypoint(
    folder: ET.Element,
    waypoint: LitchiWaypoint,
    options: ConversionOptions,
) -> ET.Element:
    placemark = ET.SubElement(folder, "Placemark")

    point = ET.SubElement(placemark, "Point")
    coords = ET.SubElement(point, "coordinates")
    coords.text = f"{waypoint.longitude:.6f},{waypoint.latitude:.6f}"

    _add_text(placemark, "index", str(waypoint.index))
    _add_text(placemark, "executeHeight", _format_float(waypoint.altitude_m, 9))
    speed = waypoint.speed_mps if waypoint.speed_mps is not None else options.global_transitional_speed
    _add_text(placemark, "waypointSpeed", _format_float(speed, 2))

    heading_param = ET.SubElement(placemark, ET.QName(NS_WP, "waypointHeadingParam"))
    _add_text(heading_param, "waypointHeadingMode", "manually")

    heading_value = 0.0
    heading_enable = "0"
    if options.set_heading_from_csv and waypoint.heading_deg is not None:
        heading_value = waypoint.heading_deg % 360.0
        heading_enable = "1"
    _add_text(heading_param, "waypointHeadingAngle", _format_float(heading_value, 2))

    if waypoint.poi_latitude is not None and waypoint.poi_longitude is not None and waypoint.poi_altitude_m is not None:
        poi = f"{waypoint.poi_latitude:.12f},{waypoint.poi_longitude:.12f},{waypoint.poi_altitude_m:.12f}"
        _add_text(heading_param, "waypointPoiPoint", poi)

    _add_text(heading_param, "waypointHeadingAngleEnable", heading_enable)
    _add_text(heading_param, "waypointHeadingPathMode", "followBadArc")

    turn_param = ET.SubElement(placemark, ET.QName(NS_WP, "waypointTurnParam"))
    curvesize_m = max(0.0, feet_to_metres(waypoint.curvesize_ft))
    if waypoint.index == 0:
        turn_mode = "toPointAndStopWithContinuityCurvature"
    elif curvesize_m > 0:
        turn_mode = "toPointAndPassWithContinuityCurvature"
    else:
        turn_mode = "toPointAndStopWithContinuityCurvature"
    _add_text(turn_param, "waypointTurnMode", turn_mode)
    _add_text(turn_param, "waypointTurnDampingDist", _format_float(curvesize_m, 3))

    # DJI exports keep useStraightLine at 0 regardless of turn behaviour; mirror that for compatibility.
    _add_text(placemark, "useStraightLine", "0")

    return placemark


def _create_action_group(
    parent: ET.Element,
    counter: ActionGroupCounter,
    trigger_type: str,
    start_index: int,
    end_index: int,
    mode: str,
    actions: Sequence[Tuple[str, Dict[str, str]]],
    trigger_param: Optional[str] = None,
) -> None:
    action_group = ET.SubElement(parent, ET.QName(NS_WP, "actionGroup"))
    _add_text(action_group, "actionGroupId", counter.increment())
    _add_text(action_group, "actionGroupStartIndex", str(start_index))
    _add_text(action_group, "actionGroupEndIndex", str(end_index))
    _add_text(action_group, "actionGroupMode", mode)

    trigger = ET.SubElement(action_group, ET.QName(NS_WP, "actionTrigger"))
    _add_text(trigger, "actionTriggerType", trigger_type)
    if trigger_param is not None:
        _add_text(trigger, "actionTriggerParam", trigger_param)

    for func_name, params in actions:
        action = ET.SubElement(action_group, ET.QName(NS_WP, "action"))
        _add_text(action, "actionId", "0")
        _add_text(action, "actionActuatorFunc", func_name)
        actuator_params = ET.SubElement(action, ET.QName(NS_WP, "actionActuatorFuncParam"))
        for key, value in params.items():
            _add_text(actuator_params, key, value)


def _emit_gimbal_actions(
    placemarks: List[ET.Element],
    waypoints: Sequence[LitchiWaypoint],
    counter: ActionGroupCounter,
) -> None:
    if not placemarks:
        return

    # Absolute pitch at first waypoint.
    first = waypoints[0]
    if first.gimbal_pitch_deg is not None and first.gimbal_mode == 2:
        _create_action_group(
            placemarks[0],
            counter,
            trigger_type="reachPoint",
            start_index=first.index,
            end_index=first.index,
            mode="parallel",
            actions=[(
                "gimbalRotate",
                {
                    "gimbalHeadingYawBase": "aircraft",
                    "gimbalRotateMode": "absoluteAngle",
                    "gimbalPitchRotateEnable": "1",
                    "gimbalPitchRotateAngle": _format_float(first.gimbal_pitch_deg, 2),
                    "gimbalYawRotateEnable": "0",
                    "gimbalYawRotateAngle": "0",
                    "gimbalRollRotateEnable": "0",
                    "gimbalRollRotateAngle": "0",
                    "gimbalRotateTimeEnable": "0",
                    "gimbalRotateTime": "0",
                    "payloadPositionIndex": "0",
                },
            )],
        )

    # Evenly rotate between legs when gimbal_mode == 2 (interpolate).
    for i in range(len(waypoints) - 1):
        current = waypoints[i]
        nxt = waypoints[i + 1]
        if nxt.gimbal_pitch_deg is None or current.gimbal_mode != 2:
            continue
        _create_action_group(
            placemarks[i],
            counter,
            trigger_type="betweenAdjacentPoints",
            start_index=current.index,
            end_index=nxt.index,
            mode="parallel",
            actions=[(
                "gimbalEvenlyRotate",
                {
                    "gimbalPitchRotateAngle": _format_float(nxt.gimbal_pitch_deg, 2),
                    "payloadPositionIndex": "0",
                },
            )],
        )


def _emit_photo_actions(
    placemarks: List[ET.Element],
    waypoints: Sequence[LitchiWaypoint],
    counter: ActionGroupCounter,
) -> None:
    for i, waypoint in enumerate(waypoints[:-1]):
        interval = waypoint.photo_timeinterval_s
        if interval is None or interval <= 0:
            continue
        trigger_param = _format_float(interval, 1)
        _create_action_group(
            placemarks[i],
            counter,
            trigger_type="multipleTiming",
            start_index=waypoint.index,
            end_index=waypoints[i + 1].index,
            mode="sequence",
            actions=[(
                "takePhoto",
                {
                    "payloadPositionIndex": "0",
                    "useGlobalPayloadLensIndex": "0",
                },
            )],
            trigger_param=trigger_param,
        )


def _emit_yaw_actions(
    placemarks: List[ET.Element],
    waypoints: Sequence[LitchiWaypoint],
    counter: ActionGroupCounter,
) -> None:
    for placemark, waypoint in zip(placemarks, waypoints):
        if waypoint.heading_deg is None:
            continue
        _create_action_group(
            placemark,
            counter,
            trigger_type="reachPoint",
            start_index=waypoint.index,
            end_index=waypoint.index,
            mode="parallel",
            actions=[(
                "rotateYaw",
                {
                    "relative": "false",
                    "yawAngle": _format_float(waypoint.heading_deg % 360.0, 2),
                },
            )],
        )


def _build_waylines_document(
    mission_name: str,
    waypoints: Sequence[LitchiWaypoint],
    options: ConversionOptions,
) -> ET.Element:
    root = ET.Element(ET.QName(NS_KML, "kml"))
    document = ET.SubElement(root, "Document")

    _build_mission_config(document, options)
    folder = _build_folder(document, options)

    placemarks: List[ET.Element] = []
    for waypoint in waypoints:
        placemark = _populate_waypoint(folder, waypoint, options)
        placemarks.append(placemark)

    counter = ActionGroupCounter()
    _emit_gimbal_actions(placemarks, waypoints, counter)
    if options.emit_per_waypoint_photo:
        _emit_photo_actions(placemarks, waypoints, counter)
    if options.insert_yaw_actions and options.set_heading_from_csv:
        _emit_yaw_actions(placemarks, waypoints, counter)

    return root


def _build_template_document(options: ConversionOptions) -> ET.Element:
    now = str(int(time.time()))
    root = ET.Element(ET.QName(NS_KML, "kml"))
    document = ET.SubElement(root, "Document")
    _add_text(document, "author", options.mission_author)
    _add_text(document, "createTime", now)
    _add_text(document, "updateTime", now)
    _build_mission_config(document, options)
    return root


def _write_kmz(waylines: ET.Element, template: ET.Element, output_path: Path) -> None:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, mode="w", compression=zipfile.ZIP_DEFLATED) as archive:
        waylines_bytes = ET.tostring(waylines, encoding="utf-8", xml_declaration=True)
        archive.writestr("wpmz/waylines.wpml", waylines_bytes)
        template_bytes = ET.tostring(template, encoding="utf-8", xml_declaration=True)
        archive.writestr("wpmz/template.kml", template_bytes)
    output_path.write_bytes(buffer.getvalue())


def convert_litchi_csv_to_dji_fly_kmz(
    csv_path: Path,
    output_path: Path,
    options: Optional[ConversionOptions] = None,
) -> None:
    """Convert the provided Litchi CSV into a DJI Fly-compatible KMZ file."""

    options = options or ConversionOptions()
    options.validate()

    waypoints = parse_litchi_csv(csv_path)
    _validate_altitude_modes(waypoints, options)

    # Warn about unsupported distance intervals so the user is aware.
    if any((wp.photo_distinterval_m or 0) > 0 for wp in waypoints):
        warnings.warn(
            "photo_distinterval is not supported by DJI Fly; distance-based intervals are skipped",
            RuntimeWarning,
            stacklevel=2,
        )

    mission_name = csv_path.stem
    waylines_doc = _build_waylines_document(mission_name, waypoints, options)
    template_doc = _build_template_document(options)
    _write_kmz(waylines_doc, template_doc, output_path)


__all__ = [
    "ConversionOptions",
    "LitchiWaypoint",
    "convert_litchi_csv_to_dji_fly_kmz",
    "parse_litchi_csv",
]
