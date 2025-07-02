#!/usr/bin/env python3
"""
3D Path-Based GPS Processor for Drone Flight Path Data
Maps photos to 3D positions along flight path using speed and timing constraints
"""

import os
import csv
import json
import math
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
from scipy.interpolate import interp1d
from scipy.spatial.distance import cdist

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


@dataclass
class FlightSegment:
    """Represents a segment between two waypoints"""
    start_point: np.ndarray  # [x, y, z] in local coordinates
    end_point: np.ndarray
    start_waypoint_idx: int
    end_waypoint_idx: int
    distance: float  # meters
    heading: float  # degrees
    altitude_change: float  # meters
    
    def interpolate_point(self, t: float) -> np.ndarray:
        """Get point along segment (t=0 is start, t=1 is end)"""
        return self.start_point + t * (self.end_point - self.start_point)


class Advanced3DPathProcessor:
    """Advanced processor that maps photos to 3D positions along flight path"""
    
    # Default flight parameters
    DEFAULT_FLIGHT_SPEED_MPH = 17.9
    DEFAULT_PHOTO_INTERVAL_SEC = 3.0
    DEFAULT_GPS_ACCURACY_M = 5.0
    
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
        
        # Flight parameters (can be overridden)
        self.flight_speed_mps = self.DEFAULT_FLIGHT_SPEED_MPH * 0.44704  # Convert to m/s
        self.photo_interval_sec = self.DEFAULT_PHOTO_INTERVAL_SEC
        
        logger.info(f"🚁 Initializing 3D Path Processor")
        logger.info(f"📂 CSV: {csv_path}")
        logger.info(f"📷 Images: {images_dir}")
    
    def parse_flight_csv(self) -> pd.DataFrame:
        """Parse the drone flight path CSV file with intelligent column detection"""
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
                'speed': ['speed', 'velocity', 'ground_speed', 'Speed', 'SPEED'],
                'time': ['time', 'timestamp', 'Time', 'TIMESTAMP', 'datetime'],
                'photo_interval': ['photo_timeinterval', 'time_interval', 'interval', 'photo_interval'],
                'distance_interval': ['photo_distinterval', 'dist_interval', 'distance', 'photo_distance']
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
            
            # Extract flight parameters if available
            if 'speed' in df.columns and df['speed'].notna().any():
                avg_speed = df['speed'].mean()
                if avg_speed > 0:
                    self.flight_speed_mps = avg_speed * 0.44704 if avg_speed < 50 else avg_speed
                    logger.info(f"🚁 Using CSV speed: {self.flight_speed_mps:.1f} m/s")
            
            if 'photo_interval' in df.columns and df['photo_interval'].notna().any():
                interval = df['photo_interval'].iloc[0]
                if 0.5 <= interval <= 10:  # Reasonable range
                    self.photo_interval_sec = interval
                    logger.info(f"📸 Using CSV photo interval: {self.photo_interval_sec} seconds")
            
            # Fill missing columns with intelligent defaults
            if 'heading' not in df.columns:
                df['heading'] = self._calculate_headings_from_path(df)
                logger.info("🧭 Calculated headings from flight path")
            
            if 'gimbal_pitch' not in df.columns:
                df['gimbal_pitch'] = -90.0  # Typical nadir view
            
            self.flight_data = df
            logger.info(f"✅ Loaded {len(df)} waypoints")
            logger.info(f"📊 Coverage: {df['latitude'].min():.6f} to {df['latitude'].max():.6f} lat")
            logger.info(f"📊 Altitude: {df['altitude'].min():.1f}m to {df['altitude'].max():.1f}m")
            
            return df
            
        except Exception as e:
            logger.error(f"❌ Failed to parse CSV: {e}")
            raise
    
    def _calculate_headings_from_path(self, df: pd.DataFrame) -> List[float]:
        """Calculate heading angles from sequential waypoints"""
        headings = []
        
        for i in range(len(df)):
            if i < len(df) - 1:
                # Calculate bearing to next point
                p1 = Point(df.iloc[i]['latitude'], df.iloc[i]['longitude'])
                p2 = Point(df.iloc[i + 1]['latitude'], df.iloc[i + 1]['longitude'])
                bearing = p1.bearing(p2)
                headings.append(bearing)
            else:
                # Last point uses previous heading
                headings.append(headings[-1] if headings else 0.0)
        
        return headings
    
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
        """Build 3D flight path with segments and cumulative distances"""
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
        
        # Build segments
        for i in range(len(waypoints_3d) - 1):
            start = waypoints_3d[i]
            end = waypoints_3d[i + 1]
            
            # Calculate segment properties
            segment_vec = end - start
            distance = np.linalg.norm(segment_vec)
            heading = math.degrees(math.atan2(segment_vec[1], segment_vec[0]))
            altitude_change = segment_vec[2]
            
            segment = FlightSegment(
                start_point=start,
                end_point=end,
                start_waypoint_idx=i,
                end_waypoint_idx=i + 1,
                distance=distance,
                heading=heading,
                altitude_change=altitude_change
            )
            
            self.flight_segments.append(segment)
            self.path_distances.append(self.path_distances[-1] + distance)
        
        self.total_path_length = self.path_distances[-1]
        
        logger.info(f"🛤️ Built 3D flight path:")
        logger.info(f"   Segments: {len(self.flight_segments)}")
        logger.info(f"   Total length: {self.total_path_length:.1f}m")
        logger.info(f"   Estimated flight time: {self.total_path_length / self.flight_speed_mps:.1f}s")
    
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
        Map photos to 3D positions along flight path using speed and timing
        """
        if not self.flight_segments:
            self.build_3d_flight_path()
        
        num_photos = len(photos)
        if num_photos == 0:
            return
        
        # Calculate expected photo spacing
        photo_distance = self.flight_speed_mps * self.photo_interval_sec
        expected_total_distance = photo_distance * (num_photos - 1)
        
        logger.info(f"📐 Photo mapping parameters:")
        logger.info(f"   Photos: {num_photos}")
        logger.info(f"   Speed: {self.flight_speed_mps:.1f} m/s")
        logger.info(f"   Interval: {self.photo_interval_sec} s")
        logger.info(f"   Spacing: {photo_distance:.1f} m")
        
        # Determine mapping strategy
        if abs(expected_total_distance - self.total_path_length) < self.total_path_length * 0.2:
            # Path length matches expected distance well
            logger.info("✅ Using speed-based distribution")
            self._map_photos_speed_based(photos, photo_distance)
        else:
            # Significant mismatch - use proportional distribution
            logger.info("📊 Using proportional distribution (path length mismatch)")
            self._map_photos_proportional(photos)
        
        # Add additional metadata
        self._enhance_photo_positions()
        
        logger.info(f"✅ Mapped {len(self.photo_positions)} photos to 3D positions")
    
    def _map_photos_speed_based(self, photos: List[Tuple[Path, int, Optional[datetime]]], 
                                photo_distance: float):
        """Map photos based on constant speed assumption"""
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
                'path_progress': current_distance / max(1, self.total_path_length),
                'order_index': order_idx,
                'timestamp': timestamp.isoformat() if timestamp else None,
                'segment_index': segment_idx,
                'segment_t': segment_t,
                'heading': segment.heading if segment else 0.0,
                'confidence': 0.8  # High confidence for speed-based
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
                    'dop': data['gps_accuracy']
                },
                'orientation': data['heading'] if 'heading' in data else 0
            }
        
        with open(output_dir / 'exif_overrides.json', 'w') as f:
            json.dump(exif_overrides, f, indent=2)
        
        # 2. Generate reference_lla.json (local coordinates)
        reference_lla = {}
        for photo_name, data in self.photo_positions.items():
            reference_lla[photo_name] = data['position_3d']  # [x, y, z] in meters
        
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
                'orientation': [0, 0, data['heading']],
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
                'mean': np.mean([d['confidence'] for d in self.photo_positions.values()]),
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