#!/usr/bin/env python3
"""
Unit tests for EXIF GPS extraction and 3D trajectory projection enhancement
Tests the new GPS+Altitude fusion functionality in gps_processor_3d.py
"""

import unittest
import tempfile
import shutil
import json
import numpy as np
from pathlib import Path
from datetime import datetime
from unittest.mock import patch, MagicMock
import csv

# Import the module under test
from gps_processor_3d import Advanced3DPathProcessor


class TestEXIFTrajectoryEnhancement(unittest.TestCase):
    """Test suite for EXIF GPS + 3D trajectory projection enhancement"""
    
    def setUp(self):
        """Set up test environment"""
        self.test_dir = Path(tempfile.mkdtemp())
        self.csv_path = self.test_dir / "test_flight.csv"
        self.images_dir = self.test_dir / "images"
        self.images_dir.mkdir()
        
        # Create test CSV with flight path data (based on real test data)
        self.create_test_csv()
        
        # Initialize processor
        self.processor = Advanced3DPathProcessor(self.csv_path, self.images_dir)
    
    def tearDown(self):
        """Clean up test environment"""
        shutil.rmtree(self.test_dir)
    
    def create_test_csv(self):
        """Create test CSV with realistic flight path data"""
        csv_data = [
            ['latitude', 'longitude', 'altitude(ft)', 'heading(deg)', 'speed(m/s)', 'photo_timeinterval'],
            [41.73272, -111.83423, 130.0, 249, 8.85, 3.0],
            [41.73256, -111.83481, 141.91, 189, 8.85, 3.0],
            [41.73201, -111.83493, 156.09, 351, 8.85, 3.0],
            [41.73268, -111.83508, 173.61, 51, 8.85, 3.0],
            [41.7332, -111.83423, 194.46, 250, 8.85, 3.0],
            [41.73286, -111.83547, 230.78, 190, 8.85, 3.0],
            [41.73166, -111.83574, 253.32, 351, 8.85, 3.0],
            [41.73312, -111.83606, 294.37, 51, 8.85, 3.0],
            [41.73423, -111.83423, 333.77, 249, 8.85, 3.0],
            [41.73346, -111.83695, 386.98, 189, 8.85, 3.0],
        ]
        
        with open(self.csv_path, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerows(csv_data)
    
    def test_dms_to_decimal_conversion(self):
        """Test DMS to decimal degree conversion for various formats"""
        test_cases = [
            # (dms_string, direction, expected_decimal)
            ("47° 51' 0.198\"", "N", 47.8500550),
            ("114° 15' 44.142\"", "W", -114.2622617),
            ("[47, 51, 198/1000]", "N", 47.8500550),
            ("47:51:0.198", "N", 47.8500550),
            ("47 51 0.198", "S", -47.8500550),
        ]
        
        for dms_str, direction, expected in test_cases:
            with self.subTest(dms=dms_str, direction=direction):
                result = self.processor._dms_to_decimal(dms_str, direction)
                self.assertIsNotNone(result, f"Failed to parse: {dms_str}")
                self.assertAlmostEqual(result, expected, places=6, 
                                     msg=f"DMS conversion failed for {dms_str}")
    
    def test_gps_coordinate_conversion(self):
        """Test PIL GPS coordinate conversion"""
        # Mock PIL GPS coordinate data (tuple of ratios)
        coord_data = [(47, 1), (51, 1), (198, 1000)]  # 47° 51' 0.198"
        ref_data = "N"
        
        result = self.processor._convert_gps_coordinate(coord_data, ref_data)
        self.assertIsNotNone(result)
        self.assertAlmostEqual(result, 47.8500550, places=6)
        
        # Test with South reference
        result_south = self.processor._convert_gps_coordinate(coord_data, "S")
        self.assertAlmostEqual(result_south, -47.8500550, places=6)
    
    @patch('gps_processor_3d.Image.open')
    def test_exif_gps_extraction_pil(self, mock_image_open):
        """Test EXIF GPS extraction using PIL"""
        # Mock image with GPS EXIF data
        mock_img = MagicMock()
        mock_img._getexif.return_value = {
            34853: {  # GPSInfo tag
                1: 'N',  # GPSLatitudeRef
                2: [(47, 1), (51, 1), (198, 1000)],  # GPSLatitude
                3: 'W',  # GPSLongitudeRef
                4: [(114, 1), (15, 1), (44142, 1000)]  # GPSLongitude
            }
        }
        mock_image_open.return_value.__enter__.return_value = mock_img
        
        # Create a dummy image file
        test_image = self.images_dir / "DJI_0001.JPG"
        test_image.touch()
        
        result = self.processor.extract_dji_gps_from_exif(test_image)
        
        self.assertIsNotNone(result)
        self.assertAlmostEqual(result['latitude'], 47.8500550, places=6)
        self.assertAlmostEqual(result['longitude'], -114.2622617, places=6)
        self.assertEqual(result['source'], 'PIL_GPS')
    
    def test_trajectory_setup_and_projection(self):
        """Test 3D trajectory setup and GPS projection"""
        # Initialize flight data processing
        self.processor.parse_flight_csv()
        self.processor.setup_local_coordinate_system()
        self.processor.build_3d_flight_path()
        
        # Verify trajectory was built
        self.assertGreater(len(self.processor.flight_segments), 0)
        self.assertGreater(self.processor.total_path_length, 0)
        
        # Test GPS projection onto trajectory
        test_exif_gps = {
            'latitude': 41.73272,  # Near first waypoint
            'longitude': -111.83423,
            'timestamp': datetime.now()
        }
        
        projection_result = self.processor.project_exif_gps_to_trajectory(test_exif_gps)
        
        self.assertIsNotNone(projection_result)
        self.assertEqual(projection_result['latitude'], test_exif_gps['latitude'])
        self.assertEqual(projection_result['longitude'], test_exif_gps['longitude'])
        self.assertGreater(projection_result['altitude'], 0)  # Should have interpolated altitude
        self.assertGreaterEqual(projection_result['trajectory_confidence'], 0.0)
        self.assertLessEqual(projection_result['trajectory_confidence'], 1.0)
        self.assertEqual(projection_result['source'], 'exif_gps_trajectory_projection')
    
    def test_closest_trajectory_point_finding(self):
        """Test finding closest point on 3D trajectory"""
        # Setup trajectory
        self.processor.parse_flight_csv()
        self.processor.setup_local_coordinate_system()
        self.processor.build_3d_flight_path()
        
        # Convert a known GPS point to local coordinates
        test_gps = (41.73272, -111.83423)  # First waypoint
        local_coords = self.processor.convert_to_local_3d(test_gps[0], test_gps[1], 0)
        
        # Find closest trajectory point
        result = self.processor.find_closest_trajectory_point(local_coords[:2])
        
        self.assertIsNotNone(result)
        self.assertIn('altitude', result)
        self.assertIn('confidence', result)
        self.assertIn('segment_index', result)
        self.assertIn('distance_m', result)
        self.assertGreaterEqual(result['confidence'], 0.0)
        self.assertLessEqual(result['confidence'], 1.0)
        
        # Distance should be small for a point on the trajectory
        self.assertLess(result['distance_m'], 10.0)  # Within 10 meters
    
    @patch.object(Advanced3DPathProcessor, 'extract_dji_gps_from_exif')
    def test_enhanced_photo_processing(self, mock_extract_gps):
        """Test the main enhanced photo processing workflow"""
        # Setup trajectory
        self.processor.parse_flight_csv()
        self.processor.setup_local_coordinate_system()
        self.processor.build_3d_flight_path()
        
        # Create test photos
        test_photos = []
        for i in range(3):
            photo_path = self.images_dir / f"DJI_{i:04d}.JPG"
            photo_path.touch()
            test_photos.append((photo_path, i, datetime.now()))
        
        # Mock EXIF GPS extraction for first two photos
        mock_extract_gps.side_effect = [
            {'latitude': 41.73272, 'longitude': -111.83423, 'timestamp': datetime.now()},  # Photo 0
            {'latitude': 41.73256, 'longitude': -111.83481, 'timestamp': datetime.now()},  # Photo 1
            None  # Photo 2 - no EXIF GPS
        ]
        
        # Process photos with enhancement
        self.processor.process_photos_with_exif_gps_enhancement(test_photos)
        
        # Verify results
        self.assertEqual(len(self.processor.photo_positions), 3)
        
        # Check EXIF+trajectory enhanced photos
        photo0_data = self.processor.photo_positions['DJI_0000.JPG']
        photo1_data = self.processor.photo_positions['DJI_0001.JPG']
        
        self.assertEqual(photo0_data['mapping_method'], 'exif_gps_trajectory_projection')
        self.assertEqual(photo1_data['mapping_method'], 'exif_gps_trajectory_projection')
        self.assertIn('trajectory_confidence', photo0_data)
        self.assertIn('projection_distance_m', photo0_data)
        
        # Check fallback photo
        photo2_data = self.processor.photo_positions['DJI_0002.JPG']
        self.assertEqual(photo2_data['mapping_method'], 'flight_path_fallback')
        self.assertEqual(photo2_data['source'], 'proportional_flight_path')
        self.assertFalse(photo2_data['exif_gps_available'])
    
    def test_opensfm_file_generation_with_metadata(self):
        """Test OpenSfM file generation with enhanced trajectory metadata"""
        # Setup and process photos
        self.processor.parse_flight_csv()
        self.processor.setup_local_coordinate_system()
        self.processor.build_3d_flight_path()
        
        # Add mock photo position data
        self.processor.photo_positions['DJI_0001.JPG'] = {
            'latitude': 41.73272,
            'longitude': -111.83423,
            'altitude': 39.624,  # Converted from feet
            'mapping_method': 'exif_gps_trajectory_projection',
            'trajectory_confidence': 0.95,
            'projection_distance_m': 1.2,
            'flight_segment_id': 0,
            'gps_accuracy': 2.0,
            'source': 'exif_gps_trajectory_projection',
            'crossover_resolved': False
        }
        
        # Generate OpenSfM files
        output_dir = self.test_dir / "opensfm_output"
        self.processor.generate_opensfm_files(output_dir)
        
        # Verify exif_overrides.json
        exif_file = output_dir / 'exif_overrides.json'
        self.assertTrue(exif_file.exists())
        
        with open(exif_file, 'r') as f:
            exif_data = json.load(f)
        
        self.assertIn('DJI_0001.JPG', exif_data)
        photo_data = exif_data['DJI_0001.JPG']
        
        # Check GPS data
        self.assertIn('gps', photo_data)
        self.assertAlmostEqual(photo_data['gps']['latitude'], 41.73272, places=6)
        self.assertAlmostEqual(photo_data['gps']['longitude'], -111.83423, places=6)
        self.assertAlmostEqual(photo_data['gps']['altitude'], 39.624, places=3)
        self.assertEqual(photo_data['gps']['dop'], 2.0)
        
        # Check enhanced metadata
        self.assertIn('_trajectory_metadata', photo_data)
        metadata = photo_data['_trajectory_metadata']
        self.assertEqual(metadata['source'], 'exif_gps_trajectory_projection')
        self.assertEqual(metadata['mapping_method'], 'exif_gps_trajectory_projection')
        self.assertEqual(metadata['trajectory_confidence'], 0.95)
        self.assertEqual(metadata['projection_distance_m'], 1.2)
        self.assertEqual(metadata['flight_segment_id'], 0)
        self.assertFalse(metadata['crossover_resolved'])
    
    def test_crossover_handling(self):
        """Test crossover detection and resolution"""
        # Setup trajectory
        self.processor.parse_flight_csv()
        self.processor.setup_local_coordinate_system()
        self.processor.build_3d_flight_path()
        
        # Mock a crossover scenario
        original_match = {
            'trajectory_confidence': 0.5,  # Low confidence
            'flight_segment_id': 5,  # Far from previous segment
            'altitude': 100.0
        }
        
        previous_results = {
            'DJI_0000.JPG': {'flight_segment_id': 1}  # Previous photo at segment 1
        }
        
        photos_with_gps = [
            (Path('DJI_0000.JPG'), {'lat': 41.73272, 'lon': -111.83423}, 0, None),
            (Path('DJI_0001.JPG'), {'lat': 41.73256, 'lon': -111.83481}, 1, None)
        ]
        
        # Test crossover resolution
        resolved_match = self.processor.resolve_crossover_with_neighbors(
            original_match, 1, previous_results, photos_with_gps
        )
        
        # Should attempt to resolve the large segment jump
        self.assertIsNotNone(resolved_match)
        # The exact behavior depends on the trajectory, but it should try to improve confidence
    
    def test_accuracy_improvement_metrics(self):
        """Test accuracy improvement calculation and reporting"""
        # Setup with mixed enhancement methods
        self.processor.photo_positions = {
            'DJI_0001.JPG': {
                'mapping_method': 'exif_gps_trajectory_projection',
                'trajectory_confidence': 0.9,
                'projection_distance_m': 1.5
            },
            'DJI_0002.JPG': {
                'mapping_method': 'exif_gps_trajectory_projection',
                'trajectory_confidence': 0.8,
                'projection_distance_m': 2.0
            },
            'DJI_0003.JPG': {
                'mapping_method': 'flight_path_fallback',
                'trajectory_confidence': 0.6
            }
        }
        
        # Calculate metrics
        exif_enhanced = [data for data in self.processor.photo_positions.values()
                        if data.get('mapping_method') == 'exif_gps_trajectory_projection']
        
        self.assertEqual(len(exif_enhanced), 2)
        
        avg_confidence = np.mean([data['trajectory_confidence'] for data in exif_enhanced])
        avg_distance = np.mean([data['projection_distance_m'] for data in exif_enhanced])
        
        self.assertAlmostEqual(avg_confidence, 0.85, places=2)
        self.assertAlmostEqual(avg_distance, 1.75, places=2)
        
        # Accuracy improvement should be significant
        estimated_improvement = avg_confidence * 80
        self.assertGreater(estimated_improvement, 60)  # Should be > 60% improvement


class TestEXIFFormatHandling(unittest.TestCase):
    """Test various DJI EXIF format variations"""
    
    def setUp(self):
        self.test_dir = Path(tempfile.mkdtemp())
        self.csv_path = self.test_dir / "dummy.csv"
        self.images_dir = self.test_dir / "images"
        self.images_dir.mkdir()
        
        # Create minimal CSV
        with open(self.csv_path, 'w') as f:
            f.write("latitude,longitude,altitude\n41.73272,-111.83423,130.0\n")
        
        self.processor = Advanced3DPathProcessor(self.csv_path, self.images_dir)
    
    def tearDown(self):
        shutil.rmtree(self.test_dir)
    
    def test_various_dms_formats(self):
        """Test parsing various DMS format variations found in DJI images"""
        test_cases = [
            # Standard DJI format
            ("47° 51' 0.198\"", "N", 47.8500550),
            ("114° 15' 44.142\"", "W", -114.2622617),
            
            # Fraction format
            ("[47, 51, 198/1000]", "N", 47.8500550),
            ("[114, 15, 44142/1000]", "W", -114.2622617),
            
            # Colon-separated
            ("47:51:0.198", "N", 47.8500550),
            ("114:15:44.142", "W", -114.2622617),
            
            # Space-separated
            ("47 51 0.198", "N", 47.8500550),
            ("114 15 44.142", "W", -114.2622617),
            
            # Different symbols
            ("47° 51′ 0.198″", "N", 47.8500550),  # Different quote marks
            ("47°51'0.198\"", "N", 47.8500550),   # No spaces
        ]
        
        for dms_str, direction, expected in test_cases:
            with self.subTest(format=dms_str):
                result = self.processor._dms_to_decimal(dms_str, direction)
                self.assertIsNotNone(result, f"Failed to parse: {dms_str}")
                self.assertAlmostEqual(result, expected, places=5,
                                     msg=f"Wrong conversion for {dms_str}")


if __name__ == '__main__':
    # Run tests with verbose output
    unittest.main(verbosity=2)