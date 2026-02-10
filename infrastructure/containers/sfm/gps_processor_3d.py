#!/usr/bin/env python3
"""
3D Path-Based GPS Processor for Drone Flight Path Data
Maps photos to 3D positions along flight path using speed and timing constraints
"""

import os
import csv
import json
import math
import re
import numpy as np
import pandas as pd
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Union
from datetime import datetime, timedelta
from dataclasses import dataclass
import utm
import pyproj
from geopy.distance import geodesic
from geopy import Point
import exifread
from PIL import Image
from PIL.ExifTags import TAGS
import logging
from scipy.interpolate import interp1d, CubicSpline
from scipy.spatial.distance import cdist

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def calculate_bearing_deg(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Compute initial bearing from (lat1, lon1) to (lat2, lon2) in degrees [0, 360)."""
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    d_lambda = math.radians(lon2 - lon1)

    y = math.sin(d_lambda) * math.cos(phi2)
    x = math.cos(phi1) * math.sin(phi2) - math.sin(phi1) * math.cos(phi2) * math.cos(d_lambda)
    bearing = math.degrees(math.atan2(y, x))
    return (bearing + 360.0) % 360.0


@dataclass
class FlightSegment:
    """Represents a segment between two waypoints with curvature support"""
    start_point: np.ndarray  # [x, y, z] in local coordinates
    end_point: np.ndarray
    control_points: List[np.ndarray]  # For curved paths
    start_waypoint_idx: int
    end_waypoint_idx: int
    distance: float  # meters (along curve)
    heading: float  # degrees
    altitude_change: float  # meters
    curvature_radius: Optional[float] = None  # meters, if specified
    
    def interpolate_point(self, t: float) -> np.ndarray:
        """Get point along segment (t=0 is start, t=1 is end)"""
        if self.control_points:
            # Use spline interpolation for curved path
            all_points = [self.start_point] + self.control_points + [self.end_point]
            t_values = np.linspace(0, 1, len(all_points))
            
            # Create spline for each dimension
            x_spline = CubicSpline(t_values, [p[0] for p in all_points])
            y_spline = CubicSpline(t_values, [p[1] for p in all_points])
            z_spline = CubicSpline(t_values, [p[2] for p in all_points])
            
            return np.array([x_spline(t), y_spline(t), z_spline(t)])
        else:
            # Linear interpolation for straight segments
            return self.start_point + t * (self.end_point - self.start_point)


class Advanced3DPathProcessor:
    """Advanced processor that maps photos to 3D positions along flight path"""
    
    # Fallback defaults (only used if CSV doesn't contain the data)
    FALLBACK_FLIGHT_SPEED_MPH = 17.9
    FALLBACK_PHOTO_INTERVAL_SEC = 3.0
    DEFAULT_GPS_ACCURACY_M = 5.0
    EXIF_TRAJECTORY_DOP = 2.0
    
    def __init__(self, csv_path: Path, images_dir: Path):
        """Initialize the 3D path processor"""
        self.csv_path = Path(csv_path)
        self.images_dir = Path(images_dir)
        self.flight_data = None
        self.photo_positions = {}
        self.local_origin = None
        self.utm_zone = None
        self.utm_zone_letter = None
        self.flight_segments = []
        self.path_distances = []
        self.total_path_length = 0
        
        # Flight parameters (extracted from CSV)
        self.flight_speed_mps = None
        self.photo_interval_sec = None
        self.distance_interval_m = None
        self.use_time_based = True  # Prefer time-based over distance-based
        
        logger.info(f"🚁 Initializing Advanced 3D Path Processor")
        logger.info(f"📂 CSV: {csv_path}")
        logger.info(f"📷 Images: {images_dir}")
    
    def parse_flight_csv(self) -> pd.DataFrame:
        """Parse the drone flight path CSV file with comprehensive parameter extraction"""
        try:
            # Read CSV
            df = pd.read_csv(self.csv_path)
            
            # Comprehensive column mapping
            column_mapping = {
                'latitude': ['latitude', 'lat', 'Latitude', 'LAT', 'gps_lat', 'GPS_Latitude'],
                'longitude': ['longitude', 'lon', 'lng', 'Longitude', 'LON', 'LNG', 'gps_lon', 'GPS_Longitude'],
                'altitude': ['altitude(ft)', 'altitude', 'alt', 'Altitude', 'ALT', 'height', 'elevation'],
                'heading': ['heading(deg)', 'heading', 'yaw', 'Heading', 'YAW', 'direction'],
                'gimbal_pitch': ['gimbalpitchangle', 'gimbal_pitch', 'pitch', 'Pitch', 'camera_pitch'],
                'speed': ['speed(mph)', 'speed', 'velocity', 'ground_speed', 'Speed', 'SPEED', 'groundspeed'],
                'time': ['time(s)', 'time', 'timestamp', 'Time', 'TIMESTAMP', 'datetime'],
                'photo_interval': ['photo_timeinterval(s)', 'photo_timeinterval', 'time_interval', 'interval', 'photo_interval'],
                'distance_interval': ['photo_distinterval(ft)', 'photo_distinterval', 'dist_interval', 'distance', 'photo_distance'],
                'curvature_radius': ['curvature_radius', 'curve_radius', 'turn_radius', 'radius'],
                'waypoint_type': ['waypoint_type', 'action', 'command', 'type'],
                'flight_time': ['flight_time', 'duration', 'elapsed_time']
            }
            
            # Rename columns to standard names
            for standard_name, variations in column_mapping.items():
                for col in df.columns:
                    if col in variations:
                        df = df.rename(columns={col: standard_name})
                        logger.info(f"✅ Mapped column '{col}' → '{standard_name}'")
                        break
            
            # Validate required columns
            required_cols = ['latitude', 'longitude', 'altitude']
            missing_cols = [col for col in required_cols if col not in df.columns]
            if missing_cols:
                raise ValueError(f"Missing required columns: {missing_cols}")
            
            # Process altitude (convert feet to meters if needed)
            if df['altitude'].mean() > 50:  # Likely in feet
                df['altitude'] = df['altitude'] * 0.3048
                logger.info("📏 Converted altitude from feet to meters")
            
            # Extract flight parameters from CSV data
            self._extract_flight_parameters(df)
            
            # Process distance intervals (convert feet to meters if needed)
            if 'distance_interval' in df.columns and df['distance_interval'].notna().any():
                dist_val = df['distance_interval'].iloc[0]
                if dist_val > 10:  # Likely in feet
                    self.distance_interval_m = dist_val * 0.3048
                else:
                    self.distance_interval_m = dist_val
                logger.info(f"📏 Using CSV distance interval: {self.distance_interval_m:.1f}m")
            
            # Fill missing columns with intelligent defaults
            if 'heading' not in df.columns:
                df['heading'] = self._calculate_headings_from_path(df)
                logger.info("🧭 Calculated headings from flight path")
            
            if 'gimbal_pitch' not in df.columns:
                df['gimbal_pitch'] = -90.0  # Typical nadir view
            
            # Add curvature information if not present
            if 'curvature_radius' not in df.columns:
                df['curvature_radius'] = None  # Will use default curved interpolation
            
            self.flight_data = df
            logger.info(f"✅ Loaded {len(df)} waypoints")
            logger.info(f"📊 Coverage: {df['latitude'].min():.6f} to {df['latitude'].max():.6f} lat")
            logger.info(f"📊 Altitude: {df['altitude'].min():.1f}m to {df['altitude'].max():.1f}m")
            
            return df
            
        except Exception as e:
            logger.error(f"❌ Failed to parse CSV: {e}")
            raise
    
    def _extract_flight_parameters(self, df: pd.DataFrame):
        """Extract flight parameters dynamically from CSV data"""
        
        # Extract speed
        if 'speed' in df.columns and df['speed'].notna().any():
            # Get non-zero speeds
            speeds = df['speed'][df['speed'] > 0]
            if len(speeds) > 0:
                avg_speed = speeds.mean()
                # Detect units (mph vs m/s vs km/h)
                if avg_speed > 50:  # Likely km/h
                    self.flight_speed_mps = avg_speed / 3.6
                    logger.info(f"🚁 Using CSV speed: {avg_speed:.1f} km/h ({self.flight_speed_mps:.1f} m/s)")
                elif avg_speed > 5:  # Likely mph
                    self.flight_speed_mps = avg_speed * 0.44704
                    logger.info(f"🚁 Using CSV speed: {avg_speed:.1f} mph ({self.flight_speed_mps:.1f} m/s)")
                else:  # Likely m/s
                    self.flight_speed_mps = avg_speed
                    logger.info(f"🚁 Using CSV speed: {avg_speed:.1f} m/s")
        
        # Extract photo time interval
        if 'photo_interval' in df.columns and df['photo_interval'].notna().any():
            interval = df['photo_interval'].iloc[0]
            if 0.5 <= interval <= 30:  # Reasonable range
                self.photo_interval_sec = interval
                logger.info(f"📸 Using CSV photo interval: {self.photo_interval_sec} seconds")
        
        # Calculate speed from time and distance if available
        if 'time' in df.columns and df['time'].notna().any() and self.flight_speed_mps is None:
            times = df['time'].values
            if len(times) > 1:
                # Calculate distance between waypoints
                total_distance = 0
                for i in range(len(df) - 1):
                    p1 = Point(df.iloc[i]['latitude'], df.iloc[i]['longitude'])
                    p2 = Point(df.iloc[i + 1]['latitude'], df.iloc[i + 1]['longitude'])
                    total_distance += geodesic(p1, p2).meters
                
                total_time = times[-1] - times[0]
                if total_time > 0:
                    calculated_speed = total_distance / total_time
                    self.flight_speed_mps = calculated_speed
                    logger.info(f"🚁 Calculated speed from waypoints: {calculated_speed:.1f} m/s")
        
        # Use fallbacks if nothing found in CSV
        if self.flight_speed_mps is None:
            self.flight_speed_mps = self.FALLBACK_FLIGHT_SPEED_MPH * 0.44704
            logger.warning(f"⚠️ Using fallback speed: {self.FALLBACK_FLIGHT_SPEED_MPH} mph ({self.flight_speed_mps:.1f} m/s)")
        
        if self.photo_interval_sec is None:
            self.photo_interval_sec = self.FALLBACK_PHOTO_INTERVAL_SEC
            logger.warning(f"⚠️ Using fallback photo interval: {self.photo_interval_sec} seconds")
        
        # Determine if we should use time-based or distance-based photo distribution
        if self.distance_interval_m is not None:
            self.use_time_based = False
            logger.info(f"📐 Using distance-based photo distribution: {self.distance_interval_m:.1f}m intervals")
        else:
            self.use_time_based = True
            calculated_distance = self.flight_speed_mps * self.photo_interval_sec
            logger.info(f"⏱️ Using time-based photo distribution: {calculated_distance:.1f}m intervals")
    
    def _calculate_headings_from_path(self, df: pd.DataFrame) -> List[float]:
        """Calculate heading angles from sequential waypoints"""
        headings = []
        
        for i in range(len(df)):
            if i < len(df) - 1:
                headings.append(
                    calculate_bearing_deg(
                        float(df.iloc[i]['latitude']),
                        float(df.iloc[i]['longitude']),
                        float(df.iloc[i + 1]['latitude']),
                        float(df.iloc[i + 1]['longitude']),
                    )
                )
            else:
                # Last point uses previous heading
                headings.append(headings[-1] if headings else 0.0)
        
        return headings
    
    # =============================
    # EXIF GPS EXTRACTION (DJI)
    # =============================
    def _ratio_to_float(self, value) -> float:
        """Convert exifread Ratio or tuple to float."""
        try:
            # exifread Ratio has .num and .den
            return float(value.num) / float(value.den)
        except AttributeError:
            # Sometimes it's a tuple (num, den)
            if isinstance(value, (list, tuple)) and len(value) == 2:
                return float(value[0]) / float(value[1])
            # Already numeric
            return float(value)
    
    def _dms_to_decimal(self, dms, ref: str) -> float:
        """Convert EXIF DMS components and ref to signed decimal degrees."""
        degrees = self._ratio_to_float(dms[0])
        minutes = self._ratio_to_float(dms[1])
        seconds = self._ratio_to_float(dms[2])
        decimal = degrees + minutes / 60.0 + seconds / 3600.0
        if ref in ['S', 'W']:
            decimal = -decimal
        return decimal
    
    def extract_dji_gps_from_exif(self, photo_path: Path) -> Optional[Dict]:
        """Extract GPS lat/lon from DJI EXIF and timestamp if available.
        Returns: {'latitude': float, 'longitude': float, 'altitude': Optional[float], 'timestamp': Optional[datetime]}
        """
        try:
            with open(photo_path, 'rb') as f:
                tags = exifread.process_file(f, details=False)
            # GPS tags can appear with or without dots; exifread typical names:
            lat_tag = None
            lat_ref_tag = None
            lon_tag = None
            lon_ref_tag = None
            alt_tag = None
            alt_ref_tag = None
            for key in [
                'GPS GPSLatitude', 'GPSLatitude',
            ]:
                if key in tags:
                    lat_tag = tags[key]
                    break
            for key in [
                'GPS GPSLatitudeRef', 'GPSLatitudeRef',
            ]:
                if key in tags:
                    lat_ref_tag = str(tags[key])
                    break
            for key in [
                'GPS GPSLongitude', 'GPSLongitude',
            ]:
                if key in tags:
                    lon_tag = tags[key]
                    break
            for key in [
                'GPS GPSLongitudeRef', 'GPSLongitudeRef',
            ]:
                if key in tags:
                    lon_ref_tag = str(tags[key])
                    break
            for key in [
                'GPS GPSAltitude', 'GPSAltitude',
            ]:
                if key in tags:
                    alt_tag = tags[key]
                    break
            for key in [
                'GPS GPSAltitudeRef', 'GPSAltitudeRef',
            ]:
                if key in tags:
                    alt_ref_tag = tags[key]
                    break

            if lat_tag and lat_ref_tag and lon_tag and lon_ref_tag:
                # exifread returns list of 3 Ratio values for D/M/S
                lat_vals = lat_tag.values if hasattr(lat_tag, 'values') else lat_tag
                lon_vals = lon_tag.values if hasattr(lon_tag, 'values') else lon_tag
                lat = self._dms_to_decimal(lat_vals, lat_ref_tag)
                lon = self._dms_to_decimal(lon_vals, lon_ref_tag)

                altitude = None
                if alt_tag is not None:
                    try:
                        alt_val = alt_tag.values[0] if hasattr(alt_tag, 'values') else alt_tag
                        altitude = float(self._ratio_to_float(alt_val))
                        # AltitudeRef: 0=above sea level, 1=below sea level
                        try:
                            alt_ref = int(str(alt_ref_tag)) if alt_ref_tag is not None else 0
                        except Exception:
                            alt_ref = 0
                        if alt_ref == 1:
                            altitude = -abs(altitude)
                    except Exception:
                        altitude = None

                # Timestamp (optional)
                timestamp = self._extract_photo_timestamp(photo_path)
                return {
                    'latitude': float(lat),
                    'longitude': float(lon),
                    'altitude': altitude,
                    'timestamp': timestamp
                }
        except Exception as e:
            logger.debug(f"Could not extract GPS EXIF from {photo_path.name}: {e}")
        return None
    
    def setup_local_coordinate_system(self):
        """Set up local 3D coordinate system centered on flight path"""
        if self.flight_data is None:
            raise ValueError("Flight data not loaded")
        
        # Use centroid of flight path as origin
        center_lat = self.flight_data['latitude'].mean()
        center_lon = self.flight_data['longitude'].mean()
        center_alt = self.flight_data['altitude'].mean()
        
        # Get UTM zone for local coordinates
        utm_easting, utm_northing, utm_zone, utm_letter = utm.from_latlon(center_lat, center_lon)
        
        self.local_origin = (center_lat, center_lon, center_alt)
        self.utm_zone = utm_zone
        self.utm_zone_letter = utm_letter
        
        logger.info(f"🌍 Local coordinate system:")
        logger.info(f"   Origin: {center_lat:.6f}°, {center_lon:.6f}°, {center_alt:.1f}m")
        logger.info(f"   UTM Zone: {utm_zone}{utm_letter}")
    
    def convert_to_local_3d(self, lat: float, lon: float, alt: float) -> np.ndarray:
        """Convert GPS coordinates to local 3D coordinates"""
        if self.local_origin is None:
            self.setup_local_coordinate_system()
        
        # Convert to UTM
        utm_e, utm_n, _, _ = utm.from_latlon(lat, lon)
        origin_e, origin_n, _, _ = utm.from_latlon(self.local_origin[0], self.local_origin[1])
        
        # Local coordinates relative to origin
        x = utm_e - origin_e
        y = utm_n - origin_n
        z = alt - self.local_origin[2]
        
        return np.array([x, y, z])
    
    def build_3d_flight_path(self):
        """Build 3D flight path with curved segments and cumulative distances"""
        if self.flight_data is None:
            raise ValueError("Flight data not loaded")
        
        self.flight_segments = []
        self.path_distances = [0.0]  # Cumulative distances
        
        # Convert all waypoints to 3D
        waypoints_3d = []
        for _, row in self.flight_data.iterrows():
            point_3d = self.convert_to_local_3d(
                row['latitude'], row['longitude'], row['altitude']
            )
            waypoints_3d.append(point_3d)
        
        # Build segments with curvature support
        for i in range(len(waypoints_3d) - 1):
            start = waypoints_3d[i]
            end = waypoints_3d[i + 1]
            
            # Get curvature information if available
            curvature_radius = None
            if 'curvature_radius' in self.flight_data.columns:
                curvature_radius = self.flight_data.iloc[i]['curvature_radius']
                if pd.isna(curvature_radius):
                    curvature_radius = None
            
            # Generate control points for curved path
            control_points = self._generate_curve_control_points(
                start, end, i, waypoints_3d, curvature_radius
            )
            
            # Calculate segment properties
            if control_points:
                # Calculate curved distance using spline
                distance = self._calculate_curved_distance(start, end, control_points)
            else:
                # Linear distance
                distance = np.linalg.norm(end - start)
            
            segment_vec = end - start
            heading = math.degrees(math.atan2(segment_vec[1], segment_vec[0]))
            altitude_change = segment_vec[2]
            
            segment = FlightSegment(
                start_point=start,
                end_point=end,
                control_points=control_points,
                start_waypoint_idx=i,
                end_waypoint_idx=i + 1,
                distance=distance,
                heading=heading,
                altitude_change=altitude_change,
                curvature_radius=curvature_radius
            )
            
            self.flight_segments.append(segment)
            self.path_distances.append(self.path_distances[-1] + distance)
        
        self.total_path_length = self.path_distances[-1]
        
        logger.info(f"🛤️ Built 3D flight path:")
        logger.info(f"   Segments: {len(self.flight_segments)}")
        logger.info(f"   Total length: {self.total_path_length:.1f}m")
        logger.info(f"   Curved segments: {sum(1 for s in self.flight_segments if s.control_points)}")
        logger.info(f"   Estimated flight time: {self.total_path_length / self.flight_speed_mps:.1f}s")
    
    # ==========================================
    # TRAJECTORY PROJECTION (EXIF → 3D PATH)
    # ==========================================
    def find_closest_trajectory_point(self, exif_xy: np.ndarray) -> Dict:
        """Find closest point on existing 3D trajectory to given XY in local frame.
        Returns dict with altitude (local z), confidence [0-1], segment_index, parameter_t,
        distance_m, and local_position (np.ndarray 3, local coords).
        """
        closest_distance = float('inf')
        closest = None
        # For linear segments we can compute the closest point analytically in XY.
        # For curved segments, sample along the spline.
        for seg_idx, segment in enumerate(self.flight_segments):
            if not segment.control_points:
                a = segment.start_point[:2]
                b = segment.end_point[:2]
                v = b - a
                denom = float(np.dot(v, v))
                if denom > 0:
                    t = float(np.dot(exif_xy - a, v) / denom)
                else:
                    t = 0.0
                t = float(max(0.0, min(1.0, t)))
                pt = segment.interpolate_point(t)
                distance = float(np.linalg.norm(exif_xy - pt[:2]))
                if distance < closest_distance:
                    closest_distance = distance
                    closest = {
                        'altitude_local': float(pt[2]),
                        'confidence': float(max(0.0, 1.0 - min(distance / 50.0, 1.0))),
                        'segment_index': int(seg_idx),
                        'parameter_t': float(t),
                        'distance_m': float(distance),
                        'local_position': pt
                    }
                continue

            for t in np.linspace(0.0, 1.0, 200):
                pt = segment.interpolate_point(float(t))
                distance = float(np.linalg.norm(exif_xy - pt[:2]))
                if distance < closest_distance:
                    closest_distance = distance
                    closest = {
                        'altitude_local': float(pt[2]),
                        'confidence': float(max(0.0, 1.0 - min(distance / 50.0, 1.0))),
                        'segment_index': int(seg_idx),
                        'parameter_t': float(t),
                        'distance_m': float(distance),
                        'local_position': pt
                    }
        return closest if closest is not None else {
            'altitude_local': 0.0,
            'confidence': 0.0,
            'segment_index': -1,
            'parameter_t': 0.0,
            'distance_m': float('inf'),
            'local_position': np.zeros(3, dtype=float)
        }
    
    def project_exif_gps_to_trajectory(self, photo_exif_gps: Dict) -> Dict:
        """Project EXIF GPS lat/lon to 3D trajectory to get precise altitude.
        Keeps original EXIF lat/lon, replaces altitude with trajectory altitude.
        Returns dict suitable for updating photo_positions entry.
        """
        # Convert EXIF GPS to local XY (alt zero to ignore EXIF altitude)
        exif_local = self.convert_to_local_3d(
            photo_exif_gps['latitude'],
            photo_exif_gps['longitude'],
            0.0
        )
        # Find closest trajectory point using XY only
        closest = self.find_closest_trajectory_point(exif_local[:2])
        # Build updated info
        # Convert EXIF lat/lon + trajectory altitude (local z) back to absolute altitude
        altitude_absolute = closest['altitude_local'] + self.local_origin[2]
        # Local 3D position uses EXIF XY and trajectory local Z
        updated_local_pos = np.array([exif_local[0], exif_local[1], closest['altitude_local']], dtype=float)
        # Heading from the segment
        heading = self.flight_segments[closest['segment_index']].heading if 0 <= closest['segment_index'] < len(self.flight_segments) else 0.0
        # Path distance for continuity checks
        if 0 <= closest['segment_index'] < len(self.flight_segments):
            seg_start_dist = self.path_distances[closest['segment_index']]
            seg_len = self.flight_segments[closest['segment_index']].distance
            path_distance = seg_start_dist + closest['parameter_t'] * seg_len
        else:
            path_distance = 0.0
        return {
            'latitude': float(photo_exif_gps['latitude']),
            'longitude': float(photo_exif_gps['longitude']),
            'altitude': float(altitude_absolute),
            'position_3d': updated_local_pos.tolist(),
            'heading': float(heading),
            'confidence': float(closest['confidence']),
            'gps_accuracy': float(self.EXIF_TRAJECTORY_DOP),
            'mapping_method': 'exif_trajectory_projection',
            'segment_index': int(closest['segment_index']),
            'segment_t': float(closest['parameter_t']),
            'path_distance': float(path_distance),
            'trajectory_metadata': {
                'exif_source': 'exif_gps',
                'source': 'exif_gps_trajectory_projection',
                'trajectory_confidence': float(closest['confidence']),
                'projection_distance_m': float(closest['distance_m']),
                'distance_from_path_m': float(closest['distance_m']),
                'flight_segment_id': int(closest['segment_index'])
            }
        }
    
    def _resolve_crossover_with_neighbors(self, i: int, projected: Dict, ordered_keys: List[str], temp_positions: Dict[str, Dict]) -> Dict:
        """Simple sequential continuity resolver for ambiguous projections.
        If confidence is low, bias toward continuity with previous/next path_distance.
        """
        current = projected
        prev_pd = None
        next_pd = None
        if i - 1 >= 0:
            prev_key = ordered_keys[i - 1]
            prev_pd = temp_positions.get(prev_key, {}).get('path_distance')
        if i + 1 < len(ordered_keys):
            # In absence of next projection yet, we can't use next_pd here realistically
            next_pd = None
        # If we have previous path distance, ensure monotonic increase
        if prev_pd is not None and current.get('path_distance') is not None:
            if current['path_distance'] < prev_pd:
                # Nudge forward along same segment if possible
                seg_idx = current.get('segment_index', -1)
                if 0 <= seg_idx < len(self.flight_segments):
                    seg_len = self.flight_segments[seg_idx].distance
                    seg_start = self.path_distances[seg_idx]
                    # Set path_distance minimally ahead of prev
                    desired = prev_pd + max(0.1, seg_len * 0.01)
                    # Clamp inside path
                    desired = min(max(desired, seg_start), seg_start + seg_len)
                    t = (desired - seg_start) / max(seg_len, 1e-6)
                    pt = self.flight_segments[seg_idx].interpolate_point(t)
                    # Keep EXIF XY, update only Z and segment_t/path_distance
                    current['segment_t'] = float(t)
                    current['path_distance'] = float(desired)
                    current['heading'] = self.flight_segments[seg_idx].heading
                    current['position_3d'][2] = float(pt[2])
                    current['altitude'] = float(pt[2] + self.local_origin[2])
                    current['trajectory_metadata']['trajectory_confidence'] = min(1.0, current['trajectory_metadata']['trajectory_confidence'] + 0.05)
        return current
    
    def apply_exif_trajectory_projection(self, photos: List[Tuple[Path, int, Optional[datetime]]]):
        """Refine mapped positions by projecting EXIF GPS onto trajectory to get altitude.
        Keeps EXIF lat/lon, replaces altitude using 3D path. Falls back gracefully.
        """
        if not self.flight_segments:
            self.build_3d_flight_path()
        # Preserve ordering keys
        ordered_keys = [p[0].name for p in photos]
        temp_positions: Dict[str, Dict] = {}
        for i, (photo_path, order_idx, timestamp) in enumerate(photos):
            exif = self.extract_dji_gps_from_exif(photo_path)
            if not exif:
                continue  # No EXIF GPS → keep previous mapping
            projected = self.project_exif_gps_to_trajectory(exif)
            # Attach order and timestamp
            projected['order_index'] = order_idx
            projected['timestamp'] = timestamp.isoformat() if timestamp else None
            # Resolve low-confidence by sequential continuity
            if projected.get('trajectory_metadata', {}).get('trajectory_confidence', 1.0) < 0.7:
                projected = self._resolve_crossover_with_neighbors(i, projected, ordered_keys, temp_positions)
            temp_positions[photo_path.name] = projected
        # Apply updates to self.photo_positions where available
        for name, proj in temp_positions.items():
            base = self.photo_positions.get(name, {})
            # Update core fields
            base.update({
                'latitude': proj['latitude'],
                'longitude': proj['longitude'],
                'altitude': proj['altitude'],
                'position_3d': proj['position_3d'],
                'heading': proj.get('heading', base.get('heading', 0.0)),
                'gps_accuracy': proj.get('gps_accuracy', self.DEFAULT_GPS_ACCURACY_M),
                'mapping_method': proj.get('mapping_method', 'exif_trajectory_projection'),
                'order_index': proj.get('order_index', base.get('order_index')),
                'segment_index': proj.get('segment_index', base.get('segment_index')),
                'segment_t': proj.get('segment_t', base.get('segment_t')),
                'path_distance': proj.get('path_distance', base.get('path_distance')),
                'confidence': max(proj.get('confidence', 0.0), base.get('confidence', 0.0))
            })
            # Attach trajectory metadata for debugging
            base['trajectory_metadata'] = proj.get('trajectory_metadata', {})
            self.photo_positions[name] = base
    
    def _generate_curve_control_points(self, start: np.ndarray, end: np.ndarray, 
                                     waypoint_idx: int, all_waypoints: List[np.ndarray],
                                     curvature_radius: Optional[float]) -> List[np.ndarray]:
        """Generate control points for smooth curved path between waypoints"""
        
        # For now, use simple curve generation
        # In a real implementation, this could use the curvature_radius parameter
        # and consider the drone's flight dynamics
        
        # Simple approach: add control points that create a smooth curve
        # considering the previous and next waypoints for continuity
        
        control_points = []
        
        # Get direction vectors for smooth transitions
        prev_point = all_waypoints[waypoint_idx - 1] if waypoint_idx > 0 else None
        next_point = all_waypoints[waypoint_idx + 2] if waypoint_idx + 2 < len(all_waypoints) else None
        
        # Calculate curve tension based on waypoint spacing
        segment_length = np.linalg.norm(end - start)
        curve_factor = 0.3  # 30% of segment length for curve control
        
        if prev_point is not None or next_point is not None:
            # Create smooth curve using Catmull-Rom spline approach
            
            # Direction from previous point (or start direction)
            if prev_point is not None:
                in_direction = (start - prev_point) / np.linalg.norm(start - prev_point)
            else:
                in_direction = (end - start) / np.linalg.norm(end - start)
            
            # Direction to next point (or end direction)  
            if next_point is not None:
                out_direction = (next_point - end) / np.linalg.norm(next_point - end)
            else:
                out_direction = (end - start) / np.linalg.norm(end - start)
            
            # Create control points for smooth curve
            control_1 = start + in_direction * segment_length * curve_factor
            control_2 = end - out_direction * segment_length * curve_factor
            
            control_points = [control_1, control_2]
            
            logger.debug(f"Generated curved path for segment {waypoint_idx} → {waypoint_idx + 1}")
        
        return control_points
    
    def _calculate_curved_distance(self, start: np.ndarray, end: np.ndarray, 
                                 control_points: List[np.ndarray]) -> float:
        """Calculate distance along curved path using numerical integration"""
        
        # Create spline path
        all_points = [start] + control_points + [end]
        t_values = np.linspace(0, 1, len(all_points))
        
        # Create splines
        x_spline = CubicSpline(t_values, [p[0] for p in all_points])
        y_spline = CubicSpline(t_values, [p[1] for p in all_points])
        z_spline = CubicSpline(t_values, [p[2] for p in all_points])
        
        # Numerical integration to get arc length
        def path_derivative(t):
            return np.array([x_spline(t, 1), y_spline(t, 1), z_spline(t, 1)])
        
        # Sample points along curve for integration
        t_samples = np.linspace(0, 1, 100)
        distances = []
        
        for i in range(len(t_samples) - 1):
            t1, t2 = t_samples[i], t_samples[i + 1]
            dt = t2 - t1
            
            # Average derivative over interval
            deriv1 = path_derivative(t1)
            deriv2 = path_derivative(t2)
            avg_deriv = (deriv1 + deriv2) / 2
            
            # Arc length element
            ds = np.linalg.norm(avg_deriv) * dt
            distances.append(ds)
        
        return sum(distances)
    
    def get_photo_list_with_validation(self) -> List[Tuple[Path, int, Optional[datetime]]]:
        """
        Get sorted photo list with intelligent ordering validation
        Returns: List of (photo_path, order_index, timestamp)
        """
        photo_extensions = {'.jpg', '.jpeg', '.png', '.JPG', '.JPEG', '.PNG'}
        photos = []
        
        # Collect all photos with metadata
        for file_path in self.images_dir.rglob('*'):
            if file_path.suffix in photo_extensions:
                timestamp = self._extract_photo_timestamp(file_path)
                photos.append((file_path, timestamp))
        
        if not photos:
            logger.warning("⚠️ No photos found!")
            return []
        
        # Check if timestamps are reliable
        timestamps = [ts for _, ts in photos if ts is not None]
        timestamps_valid = False
        
        if len(timestamps) >= len(photos) * 0.8:  # 80% have timestamps
            # Check if timestamps are different (not batch edited)
            unique_timestamps = len(set(timestamps))
            if unique_timestamps >= len(timestamps) * 0.9:  # 90% unique
                timestamps_valid = True
                logger.info("✅ Using EXIF timestamps for photo ordering")
            else:
                logger.warning("⚠️ Timestamps appear batch-edited, using filename ordering")
        else:
            logger.warning("⚠️ Insufficient EXIF data, using filename ordering")
        
        # Sort photos
        if timestamps_valid:
            # Sort by timestamp, with filename as tiebreaker
            photos.sort(key=lambda x: (x[1] or datetime.max, x[0].name))
        else:
            # Sort by filename (handles various naming schemes)
            photos.sort(key=lambda x: self._extract_photo_number(x[0]))
        
        # Create final list with order indices
        result = [(photo[0], i, photo[1]) for i, photo in enumerate(photos)]
        
        logger.info(f"📸 Ordered {len(result)} photos")
        if result:
            logger.info(f"   First: {result[0][0].name}")
            logger.info(f"   Last: {result[-1][0].name}")
        
        return result
    
    def _extract_photo_timestamp(self, photo_path: Path) -> Optional[datetime]:
        """Extract reliable timestamp from photo EXIF"""
        try:
            with open(photo_path, 'rb') as f:
                tags = exifread.process_file(f, stop_tag='EXIF DateTimeOriginal')
                
                # Try multiple timestamp tags
                timestamp_tags = [
                    'EXIF DateTimeOriginal',
                    'EXIF DateTimeDigitized',
                    'Image DateTime'
                ]
                
                for tag in timestamp_tags:
                    if tag in tags:
                        timestamp_str = str(tags[tag])
                        try:
                            return datetime.strptime(timestamp_str, '%Y:%m:%d %H:%M:%S')
                        except:
                            continue
        except Exception as e:
            logger.debug(f"Could not extract timestamp from {photo_path.name}: {e}")
        
        return None
    
    def _extract_photo_number(self, photo_path: Path) -> Tuple[str, int]:
        """Extract number from filename for sorting"""
        import re
        
        name = photo_path.stem
        
        # Try to find number patterns
        patterns = [
            r'IMG_?(\d+)',      # IMG_0001, IMG0001
            r'DSC_?(\d+)',      # DSC_0001, DSC0001
            r'DJI_?(\d+)',      # DJI_0001, DJI0001
            r'P(\d+)',          # P0001
            r'(\d+)',           # Just numbers
        ]
        
        for pattern in patterns:
            match = re.search(pattern, name, re.IGNORECASE)
            if match:
                return (pattern, int(match.group(1)))
        
        # Fallback to full name
        return (name, 0)
    
    def map_photos_to_3d_positions(self, photos: List[Tuple[Path, int, Optional[datetime]]]):
        """
        Map photos to 3D positions along flight path using CSV-derived parameters
        """
        if not self.flight_segments:
            self.build_3d_flight_path()
        
        num_photos = len(photos)
        if num_photos == 0:
            return
        
        # Use parameters extracted from CSV
        if self.use_time_based:
            # Time-based distribution using CSV speed and interval
            photo_distance = self.flight_speed_mps * self.photo_interval_sec
            expected_total_distance = photo_distance * (num_photos - 1)
            
            logger.info(f"📐 Time-based photo mapping parameters:")
            logger.info(f"   Photos: {num_photos}")
            logger.info(f"   Speed: {self.flight_speed_mps:.1f} m/s (from CSV)")
            logger.info(f"   Interval: {self.photo_interval_sec} s (from CSV)")
            logger.info(f"   Calculated spacing: {photo_distance:.1f} m")
            
            # Determine mapping strategy
            if abs(expected_total_distance - self.total_path_length) < self.total_path_length * 0.2:
                logger.info("✅ Using time-based distribution (CSV parameters)")
                self._map_photos_speed_based(photos, photo_distance)
            else:
                logger.info("📊 Using proportional distribution (path length mismatch)")
                logger.info(f"   Expected: {expected_total_distance:.1f}m, Actual: {self.total_path_length:.1f}m")
                self._map_photos_proportional(photos)
        else:
            # Distance-based distribution using CSV distance interval
            photo_distance = self.distance_interval_m
            expected_total_distance = photo_distance * (num_photos - 1)
            
            logger.info(f"📐 Distance-based photo mapping parameters:")
            logger.info(f"   Photos: {num_photos}")
            logger.info(f"   Distance interval: {photo_distance:.1f} m (from CSV)")
            logger.info(f"   Expected total: {expected_total_distance:.1f} m")
            
            if abs(expected_total_distance - self.total_path_length) < self.total_path_length * 0.2:
                logger.info("✅ Using distance-based distribution (CSV parameters)")
                self._map_photos_distance_based(photos, photo_distance)
            else:
                logger.info("📊 Using proportional distribution (path length mismatch)")
                logger.info(f"   Expected: {expected_total_distance:.1f}m, Actual: {self.total_path_length:.1f}m")
                self._map_photos_proportional(photos)
        
        # Add additional metadata
        self._enhance_photo_positions()
        
        logger.info(f"✅ Mapped {len(self.photo_positions)} photos to 3D positions")
    
    def _map_photos_speed_based(self, photos: List[Tuple[Path, int, Optional[datetime]]], 
                                photo_distance: float):
        """Map photos based on constant speed assumption (time-based)"""
        current_distance = 0.0
        
        for photo_path, order_idx, timestamp in photos:
            # Find position along path
            position_3d = self._get_position_at_distance(current_distance)
            
            # Get additional context
            segment_idx, segment_t = self._get_segment_at_distance(current_distance)
            segment = self.flight_segments[segment_idx] if segment_idx < len(self.flight_segments) else None
            
            self.photo_positions[photo_path.name] = {
                'position_3d': position_3d.tolist(),
                'path_distance': current_distance,
                'mapping_method': 'time_based',
                'photo_interval_sec': self.photo_interval_sec,
                'flight_speed_mps': self.flight_speed_mps,
                'order_index': order_idx,
                'segment_index': segment_idx,
                'segment_t': segment_t,
                'heading': segment.heading if segment else 0.0,
                'confidence': 0.9 if current_distance <= self.total_path_length else 0.5,
                'timestamp': timestamp.isoformat() if timestamp else None
            }
            
            current_distance += photo_distance
    
    def _map_photos_distance_based(self, photos: List[Tuple[Path, int, Optional[datetime]]], 
                                  photo_distance: float):
        """Map photos based on fixed distance intervals (distance-based)"""
        current_distance = 0.0
        
        for photo_path, order_idx, timestamp in photos:
            # Find position along path
            position_3d = self._get_position_at_distance(current_distance)
            
            # Get additional context
            segment_idx, segment_t = self._get_segment_at_distance(current_distance)
            segment = self.flight_segments[segment_idx] if segment_idx < len(self.flight_segments) else None
            
            self.photo_positions[photo_path.name] = {
                'position_3d': position_3d.tolist(),
                'path_distance': current_distance,
                'mapping_method': 'distance_based',
                'distance_interval_m': self.distance_interval_m,
                'path_progress': current_distance / max(1, self.total_path_length),
                'order_index': order_idx,
                'timestamp': timestamp.isoformat() if timestamp else None,
                'segment_index': segment_idx,
                'segment_t': segment_t,
                'heading': segment.heading if segment else 0.0,
                'confidence': 0.9 if current_distance <= self.total_path_length else 0.5  # High confidence for distance-based
            }
            
            current_distance += photo_distance
    
    def _map_photos_proportional(self, photos: List[Tuple[Path, int, Optional[datetime]]]):
        """Map photos proportionally along path"""
        num_photos = len(photos)
        
        for i, (photo_path, order_idx, timestamp) in enumerate(photos):
            # Calculate proportional position
            if num_photos > 1:
                progress = i / (num_photos - 1)
            else:
                progress = 0.0
            
            distance = progress * self.total_path_length
            position_3d = self._get_position_at_distance(distance)
            
            # Get segment info
            segment_idx, segment_t = self._get_segment_at_distance(distance)
            segment = self.flight_segments[segment_idx] if segment_idx < len(self.flight_segments) else None
            
            self.photo_positions[photo_path.name] = {
                'position_3d': position_3d.tolist(),
                'path_distance': distance,
                'path_progress': progress,
                'order_index': order_idx,
                'timestamp': timestamp.isoformat() if timestamp else None,
                'segment_index': segment_idx,
                'segment_t': segment_t,
                'heading': segment.heading if segment else 0.0,
                'confidence': 0.6  # Lower confidence for proportional
            }
    
    def _get_position_at_distance(self, distance: float) -> np.ndarray:
        """Get 3D position at given distance along path"""
        if distance <= 0:
            return self.flight_segments[0].start_point if self.flight_segments else np.zeros(3)
        
        if distance >= self.total_path_length:
            return self.flight_segments[-1].end_point if self.flight_segments else np.zeros(3)
        
        # Find segment containing this distance
        segment_idx, segment_t = self._get_segment_at_distance(distance)
        
        if segment_idx < len(self.flight_segments):
            segment = self.flight_segments[segment_idx]
            return segment.interpolate_point(segment_t)
        
        return self.flight_segments[-1].end_point
    
    def _get_segment_at_distance(self, distance: float) -> Tuple[int, float]:
        """Find which segment contains the given distance and position within it"""
        for i in range(len(self.path_distances) - 1):
            if self.path_distances[i] <= distance <= self.path_distances[i + 1]:
                segment_start = self.path_distances[i]
                segment_length = self.path_distances[i + 1] - segment_start
                
                if segment_length > 0:
                    t = (distance - segment_start) / segment_length
                else:
                    t = 0.0
                
                return i, t
        
        # Beyond path end
        return len(self.flight_segments) - 1, 1.0
    
    def _enhance_photo_positions(self):
        """Add GPS coordinates and additional metadata to photo positions"""
        for photo_name, data in self.photo_positions.items():
            # Convert back to GPS
            x, y, z = data['position_3d']
            
            # Convert local to UTM
            origin_e, origin_n, _, _ = utm.from_latlon(self.local_origin[0], self.local_origin[1])
            utm_e = origin_e + x
            utm_n = origin_n + y
            
            # Convert UTM to lat/lon
            lat, lon = utm.to_latlon(utm_e, utm_n, self.utm_zone, self.utm_zone_letter)
            alt = z + self.local_origin[2]
            
            # Add GPS data
            data.update({
                'latitude': lat,
                'longitude': lon,
                'altitude': alt,
                'gps_accuracy': self.DEFAULT_GPS_ACCURACY_M,
                'coordinate_system': f'UTM_{self.utm_zone}{self.utm_zone_letter}'
            })
    
    def generate_opensfm_files(self, output_dir: Path):
        """Generate all required OpenSfM files"""
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # 1. Generate exif_overrides.json
        exif_overrides = {}
        for photo_name, data in self.photo_positions.items():
            exif_overrides[photo_name] = {
                'gps': {
                    'latitude': data['latitude'],
                    'longitude': data['longitude'],
                    'altitude': data['altitude'],
                    'dop': data.get('gps_accuracy', self.DEFAULT_GPS_ACCURACY_M)
                },
                'orientation': 1,  # Standard EXIF orientation (1=normal, OpenSfM expects int 1-8)
                'heading_deg': data['heading'] if 'heading' in data else 0  # Preserve heading as custom field
            }
            # Include trajectory metadata for debugging/validation if present
            if 'trajectory_metadata' in data:
                exif_overrides[photo_name]['_trajectory_metadata'] = data['trajectory_metadata']
        
        with open(output_dir / 'exif_overrides.json', 'w') as f:
            json.dump(exif_overrides, f, indent=2)
        
        # 2. Generate reference_lla.json (origin GPS coordinates for OpenSfM)
        reference_lla = {
            'latitude': self.local_origin[0],
            'longitude': self.local_origin[1],
            'altitude': self.local_origin[2]
        }

        with open(output_dir / 'reference_lla.json', 'w') as f:
            json.dump(reference_lla, f, indent=2)
        
        # 3. Generate reference.txt (coordinate system origin)
        with open(output_dir / 'reference.txt', 'w') as f:
            f.write(f"WGS84 {self.local_origin[0]:.10f} {self.local_origin[1]:.10f} {self.local_origin[2]:.2f}\n")
        
        # 4. Generate gps_priors.json (for bundle adjustment)
        gps_priors = {
            'points': {},
            'cameras': {}
        }
        
        for photo_name, data in self.photo_positions.items():
            gps_priors['cameras'][photo_name] = {
                'position': data['position_3d'],
                'position_std': [data['gps_accuracy']] * 3,
                'orientation': [0, 0, data['heading'] if 'heading' in data else 0],
                'orientation_std': [180, 180, 10]  # Allow pitch/roll freedom, constrain yaw
            }
        
        with open(output_dir / 'gps_priors.json', 'w') as f:
            json.dump(gps_priors, f, indent=2)
        
        logger.info(f"✅ Generated OpenSfM files in {output_dir}")
        logger.info(f"   - exif_overrides.json")
        logger.info(f"   - reference_lla.json")
        logger.info(f"   - reference.txt")
        logger.info(f"   - gps_priors.json")
    
    def get_processing_summary(self) -> Dict:
        """Get comprehensive processing summary"""
        if not self.photo_positions:
            return {'status': 'No photos processed'}
        
        positions = np.array([data['position_3d'] for data in self.photo_positions.values()])
        
        summary = {
            'photos_processed': len(self.photo_positions),
            'waypoints_used': len(self.flight_data) if self.flight_data is not None else 0,
            'path_length_m': round(self.total_path_length, 1),
            'photo_spacing_m': round(self.flight_speed_mps * self.photo_interval_sec, 1),
            'coordinate_system': f'UTM {self.utm_zone}{self.utm_zone_letter}',
            'origin': {
                'latitude': self.local_origin[0],
                'longitude': self.local_origin[1],
                'altitude': self.local_origin[2]
            },
            'bounds_local_m': {
                'x': [float(positions[:, 0].min()), float(positions[:, 0].max())],
                'y': [float(positions[:, 1].min()), float(positions[:, 1].max())],
                'z': [float(positions[:, 2].min()), float(positions[:, 2].max())]
            },
            'confidence_stats': {
                'mean': float(np.mean([d['confidence'] for d in self.photo_positions.values()])),
                'min': min([d['confidence'] for d in self.photo_positions.values()]),
                'max': max([d['confidence'] for d in self.photo_positions.values()])
            }
        }
        
        return summary


def main():
    """Test the 3D path processor"""
    import sys
    
    if len(sys.argv) != 3:
        print("Usage: python gps_processor_3d.py <csv_file> <images_dir>")
        sys.exit(1)
    
    csv_path = Path(sys.argv[1])
    images_dir = Path(sys.argv[2])
    
    # Initialize processor
    processor = Advanced3DPathProcessor(csv_path, images_dir)
    
    # Process flight data
    processor.parse_flight_csv()
    processor.setup_local_coordinate_system()
    processor.build_3d_flight_path()
    
    # Process photos
    photos = processor.get_photo_list_with_validation()
    processor.map_photos_to_3d_positions(photos)
    
    # Generate outputs
    output_dir = Path("test_3d_output")
    processor.generate_opensfm_files(output_dir)
    
    # Print summary
    summary = processor.get_processing_summary()
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()


class ExifOnlyPriorBuilder:
    """Build OpenSfM GPS priors directly from image EXIF (no CSV flight path required)."""

    DEFAULT_GPS_ACCURACY_M = 8.0

    def __init__(self, images_dir: Path, min_images_with_gps: int = 5):
        self.images_dir = Path(images_dir)
        self.min_images_with_gps = int(min_images_with_gps)

        self.photo_positions: Dict[str, Dict] = {}
        self.local_origin: Optional[Tuple[float, float, float]] = None
        self.utm_zone: Optional[int] = None
        self.utm_zone_letter: Optional[str] = None

        # Reuse the existing EXIF parsing helpers from Advanced3DPathProcessor.
        # csv_path is unused for EXIF-only mode.
        self._exif_proc = Advanced3DPathProcessor(csv_path=Path("/tmp/unused.csv"), images_dir=self.images_dir)

    def _list_images(self) -> List[Path]:
        imgs: List[Path] = []
        for p in sorted(self.images_dir.iterdir()):
            if p.suffix.lower() in {".jpg", ".jpeg", ".png"} and p.is_file():
                imgs.append(p)
        return imgs

    def _extract_dji_gimbal_from_xmp(self, photo_path: Path) -> Dict[str, float]:
        """Best-effort DJI gimbal extraction from embedded XMP.

        DJI typically stores these in XMP under the `drone-dji:*` namespace.
        We keep this intentionally forgiving: if tags aren't present, return {}.
        """
        try:
            raw = photo_path.read_bytes()
        except Exception:
            return {}

        # Decode with latin1 to avoid hard failures on arbitrary binary bytes.
        text = raw.decode("latin1", errors="ignore")

        def _find(attr: str) -> Optional[float]:
            m = re.search(rf'{re.escape(attr)}="(-?\\d+(?:\\.\\d+)?)"', text)
            if not m:
                return None
            try:
                return float(m.group(1))
            except Exception:
                return None

        gimbal_pitch = _find("drone-dji:GimbalPitchDegree")
        gimbal_roll = _find("drone-dji:GimbalRollDegree")
        gimbal_yaw = _find("drone-dji:GimbalYawDegree")
        flight_yaw = _find("drone-dji:FlightYawDegree")
        flight_pitch = _find("drone-dji:FlightPitchDegree")
        flight_roll = _find("drone-dji:FlightRollDegree")

        out: Dict[str, float] = {}
        if gimbal_pitch is not None:
            out["gimbal_pitch_deg"] = gimbal_pitch
        if gimbal_roll is not None:
            out["gimbal_roll_deg"] = gimbal_roll
        if gimbal_yaw is not None:
            out["gimbal_yaw_deg"] = gimbal_yaw
        if flight_yaw is not None:
            out["flight_yaw_deg"] = flight_yaw
        if flight_pitch is not None:
            out["flight_pitch_deg"] = flight_pitch
        if flight_roll is not None:
            out["flight_roll_deg"] = flight_roll
        return out

    def _setup_local_coordinate_system(self, points: List[Dict]) -> None:
        lats = [p["latitude"] for p in points]
        lons = [p["longitude"] for p in points]
        alts = [p["altitude"] for p in points if p.get("altitude") is not None]

        center_lat = float(np.mean(lats))
        center_lon = float(np.mean(lons))
        center_alt = float(np.mean(alts)) if alts else 0.0

        _, _, utm_zone, utm_letter = utm.from_latlon(center_lat, center_lon)
        self.local_origin = (center_lat, center_lon, center_alt)
        self.utm_zone = utm_zone
        self.utm_zone_letter = utm_letter

        logger.info("🌍 EXIF-only local coordinate system:")
        logger.info(f"   Origin: {center_lat:.6f}°, {center_lon:.6f}°, {center_alt:.1f}m")
        logger.info(f"   UTM Zone: {utm_zone}{utm_letter}")

    def _convert_to_local_3d(self, lat: float, lon: float, alt: Optional[float]) -> np.ndarray:
        if self.local_origin is None:
            raise ValueError("local_origin not initialized")
        origin_lat, origin_lon, origin_alt = self.local_origin
        utm_e, utm_n, _, _ = utm.from_latlon(lat, lon)
        origin_e, origin_n, _, _ = utm.from_latlon(origin_lat, origin_lon)

        x = utm_e - origin_e
        y = utm_n - origin_n
        z = (float(alt) if alt is not None else origin_alt) - origin_alt
        return np.array([x, y, z], dtype=float)

    def _compute_headings(self, ordered_points: List[Dict]) -> List[float]:
        """Compute flight headings (bearing) from sequential EXIF GPS points."""
        headings: List[float] = []
        for i in range(len(ordered_points)):
            if i < len(ordered_points) - 1:
                headings.append(
                    calculate_bearing_deg(
                        float(ordered_points[i]["latitude"]),
                        float(ordered_points[i]["longitude"]),
                        float(ordered_points[i + 1]["latitude"]),
                        float(ordered_points[i + 1]["longitude"]),
                    )
                )
            else:
                headings.append(headings[-1] if headings else 0.0)
        return headings

    def build_photo_positions(self) -> Dict:
        """Collect EXIF GPS and build per-photo priors in local coordinates."""
        images = self._list_images()
        exif_points: List[Dict] = []

        for p in images:
            exif = self._exif_proc.extract_dji_gps_from_exif(p)
            if not exif:
                continue
            exif_points.append(
                {
                    "name": p.name,
                    "path": p,
                    "latitude": exif["latitude"],
                    "longitude": exif["longitude"],
                    "altitude": exif.get("altitude"),
                    "timestamp": exif.get("timestamp"),
                }
            )

        summary = {
            "photos_total": len(images),
            "photos_with_exif_gps": len(exif_points),
            "used_exif_timestamps": False,
        }

        if len(exif_points) < self.min_images_with_gps:
            logger.warning(
                f"⚠️ EXIF-only priors unavailable: found GPS in {len(exif_points)}/{len(images)} images "
                f"(need >= {self.min_images_with_gps})"
            )
            return {**summary, "ok": False}

        # Order points by EXIF time when available, otherwise filename ordering.
        have_ts = [p for p in exif_points if p.get("timestamp") is not None]
        if len(have_ts) >= max(3, int(0.5 * len(exif_points))):
            exif_points.sort(key=lambda d: d.get("timestamp") or datetime.min)
            summary["used_exif_timestamps"] = True
            logger.info("✅ EXIF-only priors: using EXIF timestamps for ordering")
        else:
            exif_points.sort(key=lambda d: d["name"])
            logger.info("⚠️ EXIF-only priors: insufficient timestamps, using filename ordering")

        self._setup_local_coordinate_system(exif_points)
        headings = self._compute_headings(exif_points)

        for idx, (pt, heading) in enumerate(zip(exif_points, headings)):
            gimbal = self._extract_dji_gimbal_from_xmp(pt["path"])
            pos_3d = self._convert_to_local_3d(pt["latitude"], pt["longitude"], pt.get("altitude"))
            self.photo_positions[pt["name"]] = {
                "position_3d": pos_3d.tolist(),
                "latitude": pt["latitude"],
                "longitude": pt["longitude"],
                "altitude": float(pt["altitude"]) if pt.get("altitude") is not None else (self.local_origin[2] if self.local_origin else 0.0),
                "gps_accuracy": float(self.DEFAULT_GPS_ACCURACY_M),
                "heading": float(heading),
                "timestamp": pt["timestamp"].isoformat() if pt.get("timestamp") else None,
                "order_index": idx,
                **gimbal,
            }

        return {**summary, "ok": True}

    def generate_opensfm_files(self, output_dir: Path) -> None:
        if self.local_origin is None or self.utm_zone is None or self.utm_zone_letter is None:
            raise ValueError("Exif-only priors not initialized (missing local origin)")

        output_dir.mkdir(parents=True, exist_ok=True)

        # 1) exif_overrides.json
        exif_overrides: Dict[str, Dict] = {}
        for photo_name, data in self.photo_positions.items():
            exif_overrides[photo_name] = {
                "gps": {
                    "latitude": data["latitude"],
                    "longitude": data["longitude"],
                    "altitude": data["altitude"],
                    "dop": data.get("gps_accuracy", self.DEFAULT_GPS_ACCURACY_M),
                },
                "orientation": 1,
                "heading_deg": data.get("heading", 0.0),
            }
            # Keep gimbal fields around for debugging (OpenSfM will ignore unknown keys).
            for k in ("gimbal_pitch_deg", "gimbal_roll_deg", "gimbal_yaw_deg", "flight_yaw_deg", "flight_pitch_deg", "flight_roll_deg"):
                if k in data:
                    exif_overrides[photo_name][k] = data[k]

        with open(output_dir / "exif_overrides.json", "w") as f:
            json.dump(exif_overrides, f, indent=2)

        # 2) reference_lla.json
        reference_lla = {
            "latitude": self.local_origin[0],
            "longitude": self.local_origin[1],
            "altitude": self.local_origin[2],
        }
        with open(output_dir / "reference_lla.json", "w") as f:
            json.dump(reference_lla, f, indent=2)

        # 3) reference.txt
        with open(output_dir / "reference.txt", "w") as f:
            f.write(f"WGS84 {self.local_origin[0]:.10f} {self.local_origin[1]:.10f} {self.local_origin[2]:.2f}\n")

        # 4) gps_priors.json
        gps_priors = {"points": {}, "cameras": {}}
        for photo_name, data in self.photo_positions.items():
            # If gimbal pitch/roll are present, include them; keep loose std to avoid hard failures.
            pitch = float(data.get("gimbal_pitch_deg", 0.0))
            roll = float(data.get("gimbal_roll_deg", 0.0))
            yaw = float(data.get("heading", 0.0))

            gps_priors["cameras"][photo_name] = {
                "position": data["position_3d"],
                "position_std": [data.get("gps_accuracy", self.DEFAULT_GPS_ACCURACY_M)] * 3,
                "orientation": [pitch, roll, yaw],
                "orientation_std": [180, 180, 10],
            }

        with open(output_dir / "gps_priors.json", "w") as f:
            json.dump(gps_priors, f, indent=2)

        logger.info(f"✅ Generated EXIF-only OpenSfM priors in {output_dir}")
