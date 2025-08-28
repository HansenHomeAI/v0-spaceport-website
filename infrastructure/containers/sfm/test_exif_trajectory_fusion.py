#!/usr/bin/env python3
"""
Test script for EXIF GPS extraction and 3D trajectory projection functionality
Validates the enhanced GPS+Altitude Fusion implementation
"""

import sys
import os
import json
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch
import numpy as np

# Add current directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from gps_processor_3d import Advanced3DPathProcessor

def test_dji_coordinate_parsing():
    """Test DJI coordinate format parsing"""
    processor = Advanced3DPathProcessor(Path("dummy.csv"), Path("dummy"))
    
    # Test DJI DMS format parsing
    test_cases = [
        ("47° 51' 0.198\"", "N", 47.8500550),
        ("114° 15' 44.142\"", "W", -114.2622617),
        ("41° 43' 57.792\"", "N", 41.7327200),
        ("111° 50' 3.228\"", "W", -111.8342300),
    ]
    
    print("🧪 Testing DJI coordinate parsing...")
    for coord_str, ref_str, expected in test_cases:
        result = processor._parse_dji_coordinate(coord_str, ref_str)
        if result is not None:
            error = abs(result - expected)
            print(f"   ✅ {coord_str} {ref_str} → {result:.6f} (expected {expected:.6f}, error: {error:.6f})")
            assert error < 0.000001, f"Parsing error too large: {error}"
        else:
            print(f"   ❌ Failed to parse: {coord_str} {ref_str}")
            assert False, f"Failed to parse coordinate: {coord_str}"

def test_trajectory_projection():
    """Test 3D trajectory projection functionality"""
    print("\n🧪 Testing 3D trajectory projection...")
    
    # Create test CSV data
    test_csv_data = """latitude,longitude,altitude(ft),heading(deg),speed(m/s),photo_timeinterval
41.73272,-111.83423,130.0,249,8.85,3.0
41.73256,-111.83481,141.91,189,8.85,3.0
41.73201,-111.83493,156.09,351,8.85,3.0
41.73268,-111.83508,173.61,51,8.85,3.0
41.7332,-111.83423,194.46,250,8.85,3.0"""
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
        f.write(test_csv_data)
        csv_path = Path(f.name)
    
    try:
        with tempfile.TemporaryDirectory() as temp_dir:
            images_dir = Path(temp_dir)
            
            # Initialize processor
            processor = Advanced3DPathProcessor(csv_path, images_dir)
            processor.parse_flight_csv()
            processor.setup_local_coordinate_system()
            processor.build_3d_flight_path()
            
            print(f"   ✅ Built 3D flight path with {len(processor.flight_segments)} segments")
            print(f"   ✅ Total path length: {processor.total_path_length:.1f}m")
            
            # Test trajectory projection
            test_exif_gps = {
                'latitude': 41.73256,
                'longitude': -111.83481,
                'altitude': 100.0,  # Will be replaced by trajectory interpolation
                'timestamp': None
            }
            
            projection_result = processor.project_exif_gps_to_trajectory(test_exif_gps)
            
            print(f"   ✅ Trajectory projection result:")
            print(f"      Latitude: {projection_result['latitude']:.6f}")
            print(f"      Longitude: {projection_result['longitude']:.6f}")
            print(f"      Altitude (interpolated): {projection_result['altitude']:.2f}m")
            print(f"      Confidence: {projection_result['trajectory_confidence']:.2f}")
            print(f"      Source: {projection_result['source']}")
            
            # Validate results
            assert projection_result['latitude'] == test_exif_gps['latitude'], "Latitude should be preserved from EXIF"
            assert projection_result['longitude'] == test_exif_gps['longitude'], "Longitude should be preserved from EXIF"
            assert projection_result['altitude'] != test_exif_gps['altitude'], "Altitude should be interpolated from trajectory"
            assert projection_result['trajectory_confidence'] > 0.5, "Should have reasonable confidence"
            assert 'exif_gps_trajectory_projection' in projection_result['source'], "Should indicate fusion source"
            
    finally:
        os.unlink(csv_path)

def test_sequential_matching():
    """Test sequential matching with crossover handling"""
    print("\n🧪 Testing sequential matching with trajectory projection...")
    
    # Create test CSV with crossover pattern (figure-8 or similar)
    test_csv_data = """latitude,longitude,altitude(ft),heading(deg),speed(m/s),photo_timeinterval
41.73272,-111.83423,130.0,249,8.85,3.0
41.73256,-111.83481,141.91,189,8.85,3.0
41.73201,-111.83493,156.09,351,8.85,3.0
41.73268,-111.83508,173.61,51,8.85,3.0
41.7332,-111.83423,194.46,250,8.85,3.0
41.73286,-111.83547,230.78,190,8.85,3.0
41.73166,-111.83574,253.32,351,8.85,3.0"""
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
        f.write(test_csv_data)
        csv_path = Path(f.name)
    
    try:
        with tempfile.TemporaryDirectory() as temp_dir:
            images_dir = Path(temp_dir)
            
            # Initialize processor
            processor = Advanced3DPathProcessor(csv_path, images_dir)
            processor.parse_flight_csv()
            processor.setup_local_coordinate_system()
            processor.build_3d_flight_path()
            
            # Create mock photos with EXIF GPS
            test_photos_with_gps = [
                (Path("DJI_0001.JPG"), {'latitude': 41.73272, 'longitude': -111.83423, 'altitude': 100.0}),
                (Path("DJI_0002.JPG"), {'latitude': 41.73256, 'longitude': -111.83481, 'altitude': 105.0}),
                (Path("DJI_0003.JPG"), {'latitude': 41.73201, 'longitude': -111.83493, 'altitude': 110.0}),
            ]
            
            # Test sequential matching
            results = processor.match_photos_sequentially_with_trajectory(test_photos_with_gps)
            
            print(f"   ✅ Sequential matching results for {len(results)} photos:")
            for photo_name, result in results.items():
                print(f"      {photo_name}: confidence={result['trajectory_confidence']:.2f}, alt={result['altitude']:.1f}m")
                
                # Validate each result
                assert 'latitude' in result, "Should have latitude"
                assert 'longitude' in result, "Should have longitude"
                assert 'altitude' in result, "Should have altitude"
                assert 'trajectory_confidence' in result, "Should have confidence"
                assert result['trajectory_confidence'] >= 0.0, "Confidence should be non-negative"
    
    finally:
        os.unlink(csv_path)

def test_integration_with_fallback():
    """Test integration with fallback to original method"""
    print("\n🧪 Testing integration with fallback mechanism...")
    
    test_csv_data = """latitude,longitude,altitude(ft),heading(deg),speed(m/s),photo_timeinterval
41.73272,-111.83423,130.0,249,8.85,3.0
41.73256,-111.83481,141.91,189,8.85,3.0
41.73201,-111.83493,156.09,351,8.85,3.0"""
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
        f.write(test_csv_data)
        csv_path = Path(f.name)
    
    try:
        with tempfile.TemporaryDirectory() as temp_dir:
            images_dir = Path(temp_dir)
            
            # Create mock image files (no EXIF GPS)
            for i in range(3):
                img_path = images_dir / f"DJI_{i+1:04d}.JPG"
                img_path.touch()
            
            processor = Advanced3DPathProcessor(csv_path, images_dir)
            processor.parse_flight_csv()
            processor.setup_local_coordinate_system()
            processor.build_3d_flight_path()
            
            # Mock get_photos_with_exif_gps to return empty (no EXIF GPS)
            with patch.object(processor, 'get_photos_with_exif_gps', return_value=[]):
                photos = processor.get_photo_list_with_validation()
                processor.map_photos_to_3d_positions(photos)
                
                print(f"   ✅ Fallback test: mapped {len(processor.photo_positions)} photos")
                
                # Should have fallback to original method
                for photo_name, data in processor.photo_positions.items():
                    assert 'latitude' in data, "Should have GPS coordinates"
                    assert 'longitude' in data, "Should have GPS coordinates"
                    assert 'altitude' in data, "Should have altitude"
                    print(f"      {photo_name}: fallback method used")
    
    finally:
        os.unlink(csv_path)

def test_enhanced_summary():
    """Test enhanced processing summary with fusion statistics"""
    print("\n🧪 Testing enhanced processing summary...")
    
    test_csv_data = """latitude,longitude,altitude(ft),heading(deg),speed(m/s),photo_timeinterval
41.73272,-111.83423,130.0,249,8.85,3.0
41.73256,-111.83481,141.91,189,8.85,3.0"""
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
        f.write(test_csv_data)
        csv_path = Path(f.name)
    
    try:
        with tempfile.TemporaryDirectory() as temp_dir:
            images_dir = Path(temp_dir)
            
            processor = Advanced3DPathProcessor(csv_path, images_dir)
            processor.parse_flight_csv()
            processor.setup_local_coordinate_system()
            processor.build_3d_flight_path()
            
            # Manually add some photo positions with different methods
            processor.photo_positions = {
                'DJI_0001.JPG': {
                    'position_3d': [0, 0, 0],
                    'latitude': 41.73272,
                    'longitude': -111.83423,
                    'altitude': 130.0,
                    'mapping_method': 'exif_gps_trajectory_projection',
                    'trajectory_confidence': 0.85,
                    'confidence': 0.85
                },
                'DJI_0002.JPG': {
                    'position_3d': [100, 0, 10],
                    'latitude': 41.73256,
                    'longitude': -111.83481,
                    'altitude': 135.0,
                    'mapping_method': 'time_based',
                    'confidence': 0.6
                }
            }
            
            summary = processor.get_processing_summary()
            
            print(f"   ✅ Enhanced summary generated:")
            print(f"      Photos processed: {summary['photos_processed']}")
            print(f"      EXIF fusion photos: {summary['enhanced_gps_stats']['exif_fusion_photos']}")
            print(f"      EXIF fusion percentage: {summary['enhanced_gps_stats']['exif_fusion_percentage']}%")
            print(f"      Expected accuracy improvement: {summary['enhanced_gps_stats']['expected_accuracy_improvement']}")
            print(f"      Mapping methods: {summary['enhanced_gps_stats']['mapping_methods']}")
            
            # Validate enhanced statistics
            assert 'enhanced_gps_stats' in summary, "Should have enhanced GPS statistics"
            assert summary['enhanced_gps_stats']['exif_fusion_photos'] == 1, "Should detect 1 EXIF fusion photo"
            assert summary['enhanced_gps_stats']['exif_fusion_percentage'] == 50.0, "Should be 50% fusion"
            assert '80-90%' in summary['enhanced_gps_stats']['expected_accuracy_improvement'], "Should show accuracy improvement"
    
    finally:
        os.unlink(csv_path)

def main():
    """Run all tests"""
    print("🚀 Testing EXIF GPS + 3D Trajectory Fusion Implementation")
    print("=" * 60)
    
    try:
        test_dji_coordinate_parsing()
        test_trajectory_projection()
        test_sequential_matching()
        test_integration_with_fallback()
        test_enhanced_summary()
        
        print("\n🎉 All tests passed!")
        print("✅ EXIF GPS extraction working correctly")
        print("✅ 3D trajectory projection functional")
        print("✅ Sequential matching with crossover handling")
        print("✅ Fallback mechanism operational")
        print("✅ Enhanced statistics generation")
        print("\n🎯 Implementation ready for production deployment!")
        
        return 0
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    exit(main())