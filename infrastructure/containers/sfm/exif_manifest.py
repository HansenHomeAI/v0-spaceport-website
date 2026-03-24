"""EXIF manifest extraction and ENU coordinate conversion for DJI imagery."""

from __future__ import annotations

import json
import logging
import math
import subprocess
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Tuple


logger = logging.getLogger(__name__)


SUPPORTED_IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png"}
DEFAULT_GPS_ACCURACY_M = 5.0


@dataclass(frozen=True)
class ImageRecord:
    """Normalized EXIF metadata for one source image."""

    name: str
    path: str
    capture_time: Optional[str]
    capture_sort_key: str
    latitude: float
    longitude: float
    absolute_altitude_m: Optional[float]
    relative_altitude_m: Optional[float]
    chosen_altitude_m: float
    flight_yaw_deg: Optional[float]
    gimbal_pitch_deg: Optional[float]
    focal_length_mm: Optional[float]
    model: str
    width: int
    height: int
    camera_group: str
    gps_accuracy_m: float
    enu_x_m: float
    enu_y_m: float
    enu_z_m: float

    def to_dict(self) -> Dict[str, object]:
        return asdict(self)


def parse_capture_time(raw_value: Optional[str]) -> Optional[datetime]:
    """Parse EXIF timestamps returned by exiftool."""
    if raw_value is None:
        return None

    value = str(raw_value).strip()
    if not value:
        return None

    formats = (
        "%Y:%m:%d %H:%M:%S.%f",
        "%Y:%m:%d %H:%M:%S",
        "%Y-%m-%d %H:%M:%S.%f",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%dT%H:%M:%S.%f",
        "%Y-%m-%dT%H:%M:%S",
    )
    for fmt in formats:
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            continue
    return None


class ExifManifestBuilder:
    """Build a stable EXIF manifest for COLMAP SfM processing."""

    def __init__(self, images_dir: Path):
        self.images_dir = Path(images_dir)

    def list_images(self) -> List[Path]:
        return sorted(
            [
                path
                for path in self.images_dir.iterdir()
                if path.is_file() and path.suffix.lower() in SUPPORTED_IMAGE_SUFFIXES
            ],
            key=lambda path: path.name,
        )

    def extract_manifest(self) -> Tuple[List[ImageRecord], Dict[str, object]]:
        """Return valid EXIF records plus diagnostics for skipped frames."""
        images = self.list_images()
        if not images:
            return [], {"input_images": 0, "valid_images": 0, "skipped_images": []}

        metadata_rows = self._run_exiftool(images)
        parsed_rows = []
        skipped_images = []
        for image_path, row in zip(images, metadata_rows):
            parsed = self._parse_metadata_row(image_path, row)
            if parsed is None:
                skipped_images.append(
                    {
                        "name": image_path.name,
                        "reason": "missing_gps_exif",
                    }
                )
                continue
            parsed_rows.append(parsed)

        if not parsed_rows:
            return [], {
                "input_images": len(images),
                "valid_images": 0,
                "skipped_images": skipped_images,
                "median_relative_altitude_m": None,
            }

        records = self._with_enu_coordinates(parsed_rows)
        relative_altitudes = [
            record.relative_altitude_m
            for record in records
            if record.relative_altitude_m is not None
        ]
        return records, {
            "input_images": len(images),
            "valid_images": len(records),
            "skipped_images": skipped_images,
            "median_relative_altitude_m": _median(relative_altitudes),
        }

    def _run_exiftool(self, images: Sequence[Path]) -> List[Dict[str, object]]:
        command = [
            "exiftool",
            "-json",
            "-n",
            "-FileName",
            "-Model",
            "-ImageWidth",
            "-ImageHeight",
            "-GPSLatitude",
            "-GPSLongitude",
            "-GPSAltitude",
            "-AbsoluteAltitude",
            "-RelativeAltitude",
            "-FlightYawDegree",
            "-GimbalPitchDegree",
            "-FocalLength",
            "-SubSecDateTimeOriginal",
            "-DateTimeOriginal",
            "-CreateDate",
        ] + [str(path) for path in images]
        result = subprocess.run(
            command,
            check=True,
            capture_output=True,
            text=True,
        )
        rows = json.loads(result.stdout or "[]")
        if len(rows) != len(images):
            logger.warning(
                "exiftool returned %s rows for %s images; continuing with aligned prefix",
                len(rows),
                len(images),
            )
        return rows

    def _parse_metadata_row(
        self,
        image_path: Path,
        row: Dict[str, object],
    ) -> Optional[Dict[str, object]]:
        latitude = _optional_float(row.get("GPSLatitude"))
        longitude = _optional_float(row.get("GPSLongitude"))
        if latitude is None or longitude is None:
            logger.warning("Skipping %s because GPS EXIF is missing", image_path.name)
            return None

        absolute_altitude = _first_float(
            row.get("AbsoluteAltitude"),
            row.get("GPSAltitude"),
        )
        relative_altitude = _optional_float(row.get("RelativeAltitude"))
        chosen_altitude = _first_float(absolute_altitude, relative_altitude, 0.0)
        capture_time = parse_capture_time(
            str(row.get("SubSecDateTimeOriginal") or row.get("DateTimeOriginal") or row.get("CreateDate") or "")
        )
        model = str(row.get("Model") or "UNKNOWN_DJI").strip() or "UNKNOWN_DJI"
        width = int(_first_float(row.get("ImageWidth"), 0.0))
        height = int(_first_float(row.get("ImageHeight"), 0.0))
        camera_group = f"{model.replace(' ', '_')}_{width}x{height}"
        return {
            "name": image_path.name,
            "path": str(image_path),
            "capture_time": capture_time,
            "capture_sort_key": capture_time.isoformat() if capture_time else image_path.name,
            "latitude": latitude,
            "longitude": longitude,
            "absolute_altitude_m": absolute_altitude,
            "relative_altitude_m": relative_altitude,
            "chosen_altitude_m": float(chosen_altitude),
            "flight_yaw_deg": _optional_float(row.get("FlightYawDegree")),
            "gimbal_pitch_deg": _optional_float(row.get("GimbalPitchDegree")),
            "focal_length_mm": _optional_float(row.get("FocalLength")),
            "model": model,
            "width": width,
            "height": height,
            "camera_group": camera_group,
            "gps_accuracy_m": DEFAULT_GPS_ACCURACY_M,
        }

    def _with_enu_coordinates(self, rows: Sequence[Dict[str, object]]) -> List[ImageRecord]:
        sorted_rows = sorted(rows, key=lambda row: row["capture_sort_key"])
        reference = self._reference_point(sorted_rows)
        ref_lon, ref_lat, ref_alt = reference
        ref_x, ref_y, ref_z = _wgs84_to_ecef(ref_lat, ref_lon, ref_alt)

        sin_lat = math.sin(math.radians(ref_lat))
        cos_lat = math.cos(math.radians(ref_lat))
        sin_lon = math.sin(math.radians(ref_lon))
        cos_lon = math.cos(math.radians(ref_lon))

        rotation = (
            (-sin_lon, cos_lon, 0.0),
            (-sin_lat * cos_lon, -sin_lat * sin_lon, cos_lat),
            (cos_lat * cos_lon, cos_lat * sin_lon, sin_lat),
        )

        records = []
        for row in sorted_rows:
            x, y, z = _wgs84_to_ecef(
                row["latitude"],
                row["longitude"],
                row["chosen_altitude_m"],
            )
            dx = x - ref_x
            dy = y - ref_y
            dz = z - ref_z
            enu_x = rotation[0][0] * dx + rotation[0][1] * dy + rotation[0][2] * dz
            enu_y = rotation[1][0] * dx + rotation[1][1] * dy + rotation[1][2] * dz
            enu_z = rotation[2][0] * dx + rotation[2][1] * dy + rotation[2][2] * dz
            records.append(
                ImageRecord(
                    name=row["name"],
                    path=row["path"],
                    capture_time=row["capture_time"].isoformat() if row["capture_time"] else None,
                    capture_sort_key=row["capture_sort_key"],
                    latitude=row["latitude"],
                    longitude=row["longitude"],
                    absolute_altitude_m=row["absolute_altitude_m"],
                    relative_altitude_m=row["relative_altitude_m"],
                    chosen_altitude_m=row["chosen_altitude_m"],
                    flight_yaw_deg=row["flight_yaw_deg"],
                    gimbal_pitch_deg=row["gimbal_pitch_deg"],
                    focal_length_mm=row["focal_length_mm"],
                    model=row["model"],
                    width=row["width"],
                    height=row["height"],
                    camera_group=row["camera_group"],
                    gps_accuracy_m=row["gps_accuracy_m"],
                    enu_x_m=enu_x,
                    enu_y_m=enu_y,
                    enu_z_m=enu_z,
                )
            )
        return records

    @staticmethod
    def _reference_point(rows: Sequence[Dict[str, object]]) -> Tuple[float, float, float]:
        longitudes = [float(row["longitude"]) for row in rows]
        latitudes = [float(row["latitude"]) for row in rows]
        altitudes = [float(row["chosen_altitude_m"]) for row in rows]
        return (
            _median(longitudes),
            _median(latitudes),
            _median(altitudes),
        )


def records_to_manifest(records: Iterable[ImageRecord]) -> List[Dict[str, object]]:
    return [record.to_dict() for record in records]


def _optional_float(value: object) -> Optional[float]:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _first_float(*values: object) -> float:
    for value in values:
        coerced = _optional_float(value)
        if coerced is not None:
            return coerced
    return 0.0


def _median(values: Sequence[float]) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    midpoint = len(ordered) // 2
    if len(ordered) % 2:
        return float(ordered[midpoint])
    return float((ordered[midpoint - 1] + ordered[midpoint]) / 2.0)


def _wgs84_to_ecef(latitude: float, longitude: float, altitude_m: float) -> Tuple[float, float, float]:
    """Convert WGS84 latitude/longitude/altitude to ECEF meters."""
    a = 6378137.0
    e2 = 6.69437999014e-3

    lat_rad = math.radians(latitude)
    lon_rad = math.radians(longitude)
    sin_lat = math.sin(lat_rad)
    cos_lat = math.cos(lat_rad)
    sin_lon = math.sin(lon_rad)
    cos_lon = math.cos(lon_rad)

    prime_vertical_radius = a / math.sqrt(1.0 - e2 * sin_lat * sin_lat)
    x = (prime_vertical_radius + altitude_m) * cos_lat * cos_lon
    y = (prime_vertical_radius + altitude_m) * cos_lat * sin_lon
    z = ((1.0 - e2) * prime_vertical_radius + altitude_m) * sin_lat
    return x, y, z
