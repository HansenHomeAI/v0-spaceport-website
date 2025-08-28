#!/usr/bin/env python3
"""
Simple validation script for EXIF GPS + 3D Trajectory Enhancement
Demonstrates key functionality without requiring external dependencies
"""

import sys
import tempfile
import csv
from pathlib import Path
from datetime import datetime

# Import the enhanced GPS processor
try:
    from gps_processor_3d import Advanced3DPathProcessor
    print("✅ Successfully imported Advanced3DPathProcessor with enhancements")
except ImportError as e:
    print(f"❌ Import failed: {e}")
    sys.exit(1)


def create_test_csv(csv_path):
    """Create test CSV with flight path data"""
    csv_data = [
        ['latitude', 'longitude', 'altitude(ft)', 'heading(deg)', 'speed(m/s)', 'photo_timeinterval'],
        [41.73272, -111.83423, 130.0, 249, 8.85, 3.0],
        [41.73256, -111.83481, 141.91, 189, 8.85, 3.0],
        [41.73201, -111.83493, 156.09, 351, 8.85, 3.0],
        [41.73268, -111.83508, 173.61, 51, 8.85, 3.0],
        [41.7332, -111.83423, 194.46, 250, 8.85, 3.0],
    ]
    
    with open(csv_path, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerows(csv_data)
    
    print(f"✅ Created test CSV with {len(csv_data)-1} waypoints")


def test_dms_conversion():
    """Test DMS to decimal conversion"""
    print("\n🧪 Testing DMS to decimal conversion...")
    
    test_dir = Path(tempfile.mkdtemp())
    csv_path = test_dir / "test.csv"
    images_dir = test_dir / "images"
    images_dir.mkdir()
    
    create_test_csv(csv_path)
    processor = Advanced3DPathProcessor(csv_path, images_dir)
    
    test_cases = [
        ("47° 51' 0.198\"", "N", 47.8500550),
        ("114° 15' 44.142\"", "W", -114.2622617),
        ("[47, 51, 198/1000]", "N", 47.8500550),
        ("47:51:0.198", "N", 47.8500550),
    ]
    
    success_count = 0
    for dms_str, direction, expected in test_cases:
        try:
            result = processor._dms_to_decimal(dms_str, direction)
            if result is not None and abs(result - expected) < 0.0001:
                print(f"  ✅ {dms_str} → {result:.6f}")
                success_count += 1
            else:
                print(f"  ❌ {dms_str} → {result} (expected {expected})")
        except Exception as e:
            print(f"  ❌ {dms_str} → Error: {e}")
    
    print(f"✅ DMS conversion: {success_count}/{len(test_cases)} tests passed")
    return success_count == len(test_cases)


def test_trajectory_setup():
    """Test 3D trajectory setup"""
    print("\n🧪 Testing 3D trajectory setup...")
    
    test_dir = Path(tempfile.mkdtemp())
    csv_path = test_dir / "test.csv"
    images_dir = test_dir / "images"
    images_dir.mkdir()
    
    create_test_csv(csv_path)
    processor = Advanced3DPathProcessor(csv_path, images_dir)
    
    try:
        # Test CSV parsing
        processor.parse_flight_csv()
        print(f"  ✅ Parsed CSV: {len(processor.flight_data)} waypoints")
        
        # Test coordinate system setup
        processor.setup_local_coordinate_system()
        print(f"  ✅ Local coordinate system: Origin at {processor.local_origin[0]:.6f}, {processor.local_origin[1]:.6f}")
        
        # Test 3D trajectory building
        processor.build_3d_flight_path()
        print(f"  ✅ Built 3D trajectory: {len(processor.flight_segments)} segments, {processor.total_path_length:.1f}m total")
        
        return True
        
    except Exception as e:
        print(f"  ❌ Trajectory setup failed: {e}")
        return False


def test_gps_projection():
    """Test GPS projection onto trajectory"""
    print("\n🧪 Testing GPS projection onto trajectory...")
    
    test_dir = Path(tempfile.mkdtemp())
    csv_path = test_dir / "test.csv"
    images_dir = test_dir / "images"
    images_dir.mkdir()
    
    create_test_csv(csv_path)
    processor = Advanced3DPathProcessor(csv_path, images_dir)
    
    try:
        # Setup trajectory
        processor.parse_flight_csv()
        processor.setup_local_coordinate_system()
        processor.build_3d_flight_path()
        
        # Test GPS projection
        test_exif_gps = {
            'latitude': 41.73272,  # Near first waypoint
            'longitude': -111.83423,
            'timestamp': datetime.now()
        }
        
        result = processor.project_exif_gps_to_trajectory(test_exif_gps)
        
        print(f"  ✅ GPS projection successful:")
        print(f"    Input: {test_exif_gps['latitude']:.6f}, {test_exif_gps['longitude']:.6f}")
        print(f"    Output: {result['latitude']:.6f}, {result['longitude']:.6f}, {result['altitude']:.2f}m")
        print(f"    Confidence: {result['trajectory_confidence']:.2f}")
        print(f"    Source: {result['source']}")
        
        return result['trajectory_confidence'] > 0.0
        
    except Exception as e:
        print(f"  ❌ GPS projection failed: {e}")
        return False


def test_method_availability():
    """Test that all new methods are available"""
    print("\n🧪 Testing method availability...")
    
    test_dir = Path(tempfile.mkdtemp())
    csv_path = test_dir / "test.csv"
    images_dir = test_dir / "images"
    images_dir.mkdir()
    
    create_test_csv(csv_path)
    processor = Advanced3DPathProcessor(csv_path, images_dir)
    
    required_methods = [
        'extract_dji_gps_from_exif',
        'project_exif_gps_to_trajectory',
        'find_closest_trajectory_point',
        'process_photos_with_exif_gps_enhancement',
        '_dms_to_decimal',
        '_convert_gps_coordinate'
    ]
    
    success_count = 0
    for method_name in required_methods:
        if hasattr(processor, method_name):
            print(f"  ✅ {method_name}")
            success_count += 1
        else:
            print(f"  ❌ {method_name} - NOT FOUND")
    
    print(f"✅ Method availability: {success_count}/{len(required_methods)} methods found")
    return success_count == len(required_methods)


def main():
    """Run all validation tests"""
    print("🚀 EXIF GPS + 3D Trajectory Enhancement Validation")
    print("=" * 60)
    
    tests = [
        ("Method Availability", test_method_availability),
        ("DMS Conversion", test_dms_conversion),
        ("3D Trajectory Setup", test_trajectory_setup),
        ("GPS Projection", test_gps_projection),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        try:
            if test_func():
                passed += 1
                print(f"✅ {test_name}: PASSED\n")
            else:
                print(f"❌ {test_name}: FAILED\n")
        except Exception as e:
            print(f"❌ {test_name}: ERROR - {e}\n")
    
    print("=" * 60)
    print(f"🎯 VALIDATION SUMMARY: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 ALL TESTS PASSED - Enhancement ready for deployment!")
        return 0
    else:
        print("⚠️  Some tests failed - review implementation")
        return 1


if __name__ == "__main__":
    sys.exit(main())