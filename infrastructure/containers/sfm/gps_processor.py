#!/usr/bin/env python3
"""
GPS Processor for Drone Flight Path Data
Parses CSV flight data and maps photos to GPS coordinates for OpenSfM
"""

import os
import csv
import json
import math
import numpy as np
import pandas as pd
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from datetime import datetime, timedelta
import utm
import pyproj
from geopy.distance import geodesic
from geopy import Point
import exifread
from PIL import Image
from PIL.ExifTags import TAGS
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class DroneFlightPathProcessor:
    """Process drone flight path CSV and map to photos"""
    
    def __init__(self, csv_path: Path, images_dir: Path):
        """
        Initialize GPS processor
        
        Args:
            csv_path: Path to drone flight path CSV
            images_dir: Directory containing drone photos
        """
        self.csv_path = Path(csv_path)
        self.images_dir = Path(images_dir)
        self.flight_data = None
        self.photo_gps_mapping = {}
        self.local_origin = None
        self.utm_zone = None
        self.utm_zone_letter = None
        
        logger.info(f"🛰️ Initializing GPS processor with CSV: {csv_path}")
        logger.info(f"📷 Images directory: {images_dir}")
    
    def parse_flight_csv(self) -> pd.DataFrame:
        """Parse the drone flight path CSV file"""
        try:
            # Read CSV with flexible column detection
            df = pd.read_csv(self.csv_path)
            
            # Standardize column names (handle variations)
            column_mapping = {
                'latitude': ['latitude', 'lat', 'Latitude', 'LAT'],
                'longitude': ['longitude', 'lon', 'lng', 'Longitude', 'LON', 'LNG'],
                'altitude': ['altitude(ft)', 'altitude', 'alt', 'Altitude', 'ALT'],
                'heading': ['heading(deg)', 'heading', 'yaw', 'Heading', 'YAW'],
                'gimbal_pitch': ['gimbalpitchangle', 'gimbal_pitch', 'pitch', 'Pitch'],
                'photo_time_interval': ['photo_timeinterval', 'time_interval', 'interval'],
                'photo_dist_interval': ['photo_distinterval', 'dist_interval', 'distance']
            }
            
            # Rename columns to standard names
            for standard_name, variations in column_mapping.items():
                for col in df.columns:
                    if col in variations:
                        df = df.rename(columns={col: standard_name})
                        break
            
            # Validate required columns
            required_cols = ['latitude', 'longitude', 'altitude']
            missing_cols = [col for col in required_cols if col not in df.columns]
            if missing_cols:
                raise ValueError(f"Missing required columns: {missing_cols}")
            
            # Convert altitude from feet to meters if needed
            if 'altitude' in df.columns:
                # Check if values suggest feet (typically > 100 for drone flights)
                if df['altitude'].mean() > 50:  # Likely in feet
                    df['altitude'] = df['altitude'] * 0.3048  # Convert to meters
                    logger.info("✅ Converted altitude from feet to meters")
            
            # Fill missing optional columns with defaults
            if 'heading' not in df.columns:
                df['heading'] = 0.0
                logger.warning("⚠️ No heading data found, using default 0°")
            
            if 'gimbal_pitch' not in df.columns:
                df['gimbal_pitch'] = -90.0  # Typical downward-facing drone camera
                logger.warning("⚠️ No gimbal pitch data found, using default -90°")
            
            self.flight_data = df
            logger.info(f"✅ Parsed flight data: {len(df)} waypoints")
            logger.info(f"📊 Lat range: {df['latitude'].min():.6f} to {df['latitude'].max():.6f}")
            logger.info(f"📊 Lon range: {df['longitude'].min():.6f} to {df['longitude'].max():.6f}")
            logger.info(f"📊 Alt range: {df['altitude'].min():.1f}m to {df['altitude'].max():.1f}m")
            
            return df
            
        except Exception as e:
            logger.error(f"❌ Failed to parse flight CSV: {e}")
            raise
    
    def get_photo_list(self) -> List[Path]:
        """Get sorted list of drone photos"""
        photo_extensions = {'.jpg', '.jpeg', '.png', '.JPG', '.JPEG', '.PNG'}
        photos = []
        
        for file_path in self.images_dir.rglob('*'):
            if file_path.suffix in photo_extensions:
                photos.append(file_path)
        
        # Sort by filename (assumes sequential naming)
        photos.sort(key=lambda p: p.name)
        
        logger.info(f"📸 Found {len(photos)} photos")
        if photos:
            logger.info(f"📸 Photo range: {photos[0].name} to {photos[-1].name}")
        
        return photos
    
    def extract_photo_timestamp(self, photo_path: Path) -> Optional[datetime]:
        """Extract timestamp from photo EXIF data"""
        try:
            with open(photo_path, 'rb') as f:
                tags = exifread.process_file(f, stop_tag='EXIF DateTimeOriginal')
                if 'EXIF DateTimeOriginal' in tags:
                    timestamp_str = str(tags['EXIF DateTimeOriginal'])
                    return datetime.strptime(timestamp_str, '%Y:%m:%d %H:%M:%S')
        except Exception as e:
            logger.debug(f"Could not extract timestamp from {photo_path.name}: {e}")
        
        return None
    
    def map_photos_to_gps_sequential(self, photos: List[Path]) -> Dict[str, Dict]:
        """Map photos to GPS coordinates using sequential order assumption"""
        if not self.flight_data is not None:
            raise ValueError("Flight data not loaded. Call parse_flight_csv() first.")
        
        mapping = {}
        num_photos = len(photos)
        num_waypoints = len(self.flight_data)
        
        logger.info(f"🗺️ Mapping {num_photos} photos to {num_waypoints} GPS waypoints (sequential)")
        
        if num_photos == 0:
            return mapping
        
        # Strategy 1: Direct mapping if counts are similar
        if abs(num_photos - num_waypoints) <= max(2, num_photos * 0.1):
            logger.info("📍 Using direct 1:1 mapping (similar counts)")
            for i, photo in enumerate(photos):
                if i < num_waypoints:
                    row = self.flight_data.iloc[i]
                    mapping[photo.name] = self._create_gps_entry(row, i)
                else:
                    # Use last waypoint for extra photos
                    row = self.flight_data.iloc[-1]
                    mapping[photo.name] = self._create_gps_entry(row, num_waypoints - 1)
        
        # Strategy 2: Interpolation mapping
        else:
            logger.info("🔄 Using interpolation mapping (different counts)")
            for i, photo in enumerate(photos):
                # Calculate position along flight path (0.0 to 1.0)
                progress = i / max(1, num_photos - 1) if num_photos > 1 else 0.0
                waypoint_index = progress * (num_waypoints - 1)
                
                # Get surrounding waypoints for interpolation
                idx_low = int(waypoint_index)
                idx_high = min(idx_low + 1, num_waypoints - 1)
                
                if idx_low == idx_high:
                    # Use exact waypoint
                    row = self.flight_data.iloc[idx_low]
                    mapping[photo.name] = self._create_gps_entry(row, idx_low)
                else:
                    # Interpolate between waypoints
                    alpha = waypoint_index - idx_low
                    row_low = self.flight_data.iloc[idx_low]
                    row_high = self.flight_data.iloc[idx_high]
                    
                    interpolated = self._interpolate_waypoints(row_low, row_high, alpha)
                    mapping[photo.name] = interpolated
        
        self.photo_gps_mapping = mapping
        logger.info(f"✅ Successfully mapped {len(mapping)} photos to GPS coordinates")
        
        return mapping
    
    def _create_gps_entry(self, row: pd.Series, index: int) -> Dict:
        """Create GPS entry dictionary from flight data row"""
        return {
            'latitude': float(row['latitude']),
            'longitude': float(row['longitude']),
            'altitude': float(row['altitude']),
            'heading': float(row.get('heading', 0.0)),
            'gimbal_pitch': float(row.get('gimbal_pitch', -90.0)),
            'waypoint_index': index,
            'gps_accuracy': 5.0  # Assumed GPS accuracy in meters
        }
    
    def _interpolate_waypoints(self, row1: pd.Series, row2: pd.Series, alpha: float) -> Dict:
        """Interpolate between two GPS waypoints"""
        # Use spherical interpolation for GPS coordinates
        point1 = Point(latitude=row1['latitude'], longitude=row1['longitude'])
        point2 = Point(latitude=row2['latitude'], longitude=row2['longitude'])
        
        # Calculate intermediate point using great circle interpolation
        bearing = point1.bearing(point2)
        distance = geodesic(point1, point2).meters * alpha
        interpolated_point = geodesic(meters=distance).destination(point1, bearing)
        
        return {
            'latitude': float(interpolated_point.latitude),
            'longitude': float(interpolated_point.longitude),
            'altitude': float(row1['altitude'] + alpha * (row2['altitude'] - row1['altitude'])),
            'heading': self._interpolate_angle(float(row1.get('heading', 0.0)), 
                                             float(row2.get('heading', 0.0)), alpha),
            'gimbal_pitch': float(row1.get('gimbal_pitch', -90.0) + 
                                alpha * (row2.get('gimbal_pitch', -90.0) - row1.get('gimbal_pitch', -90.0))),
            'waypoint_index': -1,  # Interpolated
            'gps_accuracy': 5.0
        }
    
    def _interpolate_angle(self, angle1: float, angle2: float, alpha: float) -> float:
        """Interpolate between two angles (handles 360° wraparound)"""
        # Convert to unit vectors and interpolate
        rad1, rad2 = math.radians(angle1), math.radians(angle2)
        x1, y1 = math.cos(rad1), math.sin(rad1)
        x2, y2 = math.cos(rad2), math.sin(rad2)
        
        x = x1 + alpha * (x2 - x1)
        y = y1 + alpha * (y2 - y1)
        
        return math.degrees(math.atan2(y, x)) % 360.0
    
    def setup_local_coordinate_system(self) -> Tuple[float, float, int, str]:
        """Set up local coordinate system for OpenSfM reconstruction"""
        if self.flight_data is None:
            raise ValueError("Flight data not loaded")
        
        # Use center of flight path as local origin
        center_lat = self.flight_data['latitude'].mean()
        center_lon = self.flight_data['longitude'].mean()
        
        # Convert to UTM for local coordinates
        utm_easting, utm_northing, utm_zone, utm_letter = utm.from_latlon(center_lat, center_lon)
        
        self.local_origin = (center_lat, center_lon)
        self.utm_zone = utm_zone
        self.utm_zone_letter = utm_letter
        
        logger.info(f"🌍 Local coordinate system setup:")
        logger.info(f"   Origin: {center_lat:.6f}, {center_lon:.6f}")
        logger.info(f"   UTM Zone: {utm_zone}{utm_letter}")
        
        return center_lat, center_lon, utm_zone, utm_letter
    
    def convert_gps_to_local(self, lat: float, lon: float, alt: float) -> Tuple[float, float, float]:
        """Convert GPS coordinates to local coordinate system"""
        if self.local_origin is None:
            self.setup_local_coordinate_system()
        
        # Convert to UTM
        utm_easting, utm_northing, _, _ = utm.from_latlon(lat, lon)
        
        # Convert origin to UTM
        origin_easting, origin_northing, _, _ = utm.from_latlon(
            self.local_origin[0], self.local_origin[1]
        )
        
        # Calculate local coordinates (meters from origin)
        local_x = utm_easting - origin_easting
        local_y = utm_northing - origin_northing
        local_z = alt  # Keep altitude as-is
        
        return local_x, local_y, local_z
    
    def generate_opensfm_gps_file(self, output_path: Path) -> None:
        """Generate GPS positions file for OpenSfM"""
        if not self.photo_gps_mapping:
            raise ValueError("Photo GPS mapping not created. Call map_photos_to_gps_sequential() first.")
        
        gps_data = {}
        
        for photo_name, gps_info in self.photo_gps_mapping.items():
            # Convert to local coordinates
            local_x, local_y, local_z = self.convert_gps_to_local(
                gps_info['latitude'], 
                gps_info['longitude'], 
                gps_info['altitude']
            )
            
            gps_data[photo_name] = {
                'latitude': gps_info['latitude'],
                'longitude': gps_info['longitude'],
                'altitude': gps_info['altitude'],
                'local_x': local_x,
                'local_y': local_y,
                'local_z': local_z,
                'heading': gps_info['heading'],
                'gimbal_pitch': gps_info['gimbal_pitch'],
                'gps_accuracy': gps_info['gps_accuracy']
            }
        
        # Save GPS data
        with open(output_path, 'w') as f:
            json.dump(gps_data, f, indent=2)
        
        logger.info(f"✅ Generated OpenSfM GPS file: {output_path}")
        logger.info(f"📊 GPS data for {len(gps_data)} photos")
    
    def create_reference_lla_file(self, output_path: Path) -> None:
        """Create reference.lla file for OpenSfM"""
        if self.local_origin is None:
            self.setup_local_coordinate_system()
        
        # OpenSfM reference.lla format: lat lon alt
        with open(output_path, 'w') as f:
            f.write(f"{self.local_origin[0]:.10f} {self.local_origin[1]:.10f} 0.0\n")
        
        logger.info(f"✅ Created reference.lla file: {output_path}")
    
    def get_processing_stats(self) -> Dict:
        """Get statistics about GPS processing"""
        if not self.photo_gps_mapping:
            return {}
        
        stats = {
            'total_photos': len(self.photo_gps_mapping),
            'total_waypoints': len(self.flight_data) if self.flight_data is not None else 0,
            'gps_coverage': '100%',  # All photos have GPS
            'coordinate_system': f"UTM {self.utm_zone}{self.utm_zone_letter}" if self.utm_zone else "Unknown",
            'local_origin': self.local_origin
        }
        
        if self.flight_data is not None:
            # Calculate flight path statistics
            coords = [(row['latitude'], row['longitude']) for _, row in self.flight_data.iterrows()]
            
            total_distance = 0
            for i in range(1, len(coords)):
                total_distance += geodesic(coords[i-1], coords[i]).meters
            
            stats.update({
                'flight_distance_meters': round(total_distance, 1),
                'altitude_range_meters': [
                    round(self.flight_data['altitude'].min(), 1),
                    round(self.flight_data['altitude'].max(), 1)
                ],
                'area_coverage_km2': self._calculate_coverage_area()
            })
        
        return stats
    
    def _calculate_coverage_area(self) -> float:
        """Calculate approximate area covered by flight path"""
        if self.flight_data is None or len(self.flight_data) < 3:
            return 0.0
        
        # Simple bounding box area calculation
        lat_min = self.flight_data['latitude'].min()
        lat_max = self.flight_data['latitude'].max()
        lon_min = self.flight_data['longitude'].min()
        lon_max = self.flight_data['longitude'].max()
        
        # Calculate distances
        lat_distance = geodesic((lat_min, lon_min), (lat_max, lon_min)).meters
        lon_distance = geodesic((lat_min, lon_min), (lat_min, lon_max)).meters
        
        # Area in km²
        area_km2 = (lat_distance * lon_distance) / 1_000_000
        return round(area_km2, 3)


def main():
    """Test GPS processor functionality"""
    import sys
    
    if len(sys.argv) != 3:
        print("Usage: python gps_processor.py <csv_file> <images_dir>")
        sys.exit(1)
    
    csv_path = Path(sys.argv[1])
    images_dir = Path(sys.argv[2])
    
    # Initialize processor
    processor = DroneFlightPathProcessor(csv_path, images_dir)
    
    # Parse flight data
    flight_data = processor.parse_flight_csv()
    print(f"Loaded {len(flight_data)} waypoints")
    
    # Get photos
    photos = processor.get_photo_list()
    print(f"Found {len(photos)} photos")
    
    # Map photos to GPS
    mapping = processor.map_photos_to_gps_sequential(photos)
    print(f"Mapped {len(mapping)} photos to GPS")
    
    # Setup coordinate system
    processor.setup_local_coordinate_system()
    
    # Generate outputs
    output_dir = Path("test_output")
    output_dir.mkdir(exist_ok=True)
    
    processor.generate_opensfm_gps_file(output_dir / "gps_data.json")
    processor.create_reference_lla_file(output_dir / "reference.lla")
    
    # Print stats
    stats = processor.get_processing_stats()
    print(json.dumps(stats, indent=2))


if __name__ == "__main__":
    main() 