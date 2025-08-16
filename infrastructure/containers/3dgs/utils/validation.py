#!/usr/bin/env python3
"""
Data Validation Utilities for NerfStudio Training
Ensures COLMAP data compatibility with NerfStudio requirements
"""

import logging
from pathlib import Path
from typing import Dict, List, Tuple, Optional

logger = logging.getLogger(__name__)

def validate_colmap_structure(data_dir: Path) -> Dict[str, any]:
    """
    Validate COLMAP data structure for NerfStudio compatibility
    
    Args:
        data_dir: Path to COLMAP dataset directory
        
    Returns:
        Dictionary with validation results
    """
    validation_results = {
        'valid': False,
        'errors': [],
        'warnings': [],
        'statistics': {}
    }
    
    try:
        # Check required structure
        required_paths = [
            data_dir / "sparse" / "0" / "cameras.txt",
            data_dir / "sparse" / "0" / "images.txt",
            data_dir / "sparse" / "0" / "points3D.txt",
            data_dir / "images"
        ]
        
        for path in required_paths:
            if not path.exists():
                validation_results['errors'].append(f"Missing required path: {path}")
        
        if validation_results['errors']:
            return validation_results
        
        # Validate file contents
        cameras_file = data_dir / "sparse" / "0" / "cameras.txt"
        images_file = data_dir / "sparse" / "0" / "images.txt"
        points_file = data_dir / "sparse" / "0" / "points3D.txt"
        images_dir = data_dir / "images"
        
        # Count cameras
        camera_count = 0
        with open(cameras_file, 'r') as f:
            for line in f:
                if line.strip() and not line.startswith('#'):
                    camera_count += 1
        
        # Count images
        image_count = 0
        with open(images_file, 'r') as f:
            lines = [line for line in f if line.strip() and not line.startswith('#')]
            image_count = len(lines) // 2  # COLMAP format: 2 lines per image
        
        # Count 3D points
        point_count = 0
        with open(points_file, 'r') as f:
            for line in f:
                if line.strip() and not line.startswith('#'):
                    point_count += 1
        
        # Count image files
        image_extensions = ['*.jpg', '*.jpeg', '*.png', '*.JPG', '*.JPEG', '*.PNG']
        image_files = []
        for ext in image_extensions:
            image_files.extend(list(images_dir.glob(ext)))
        image_file_count = len(image_files)
        
        # Store statistics
        validation_results['statistics'] = {
            'camera_count': camera_count,
            'image_count': image_count,
            'point_count': point_count,
            'image_file_count': image_file_count
        }
        
        # Quality checks
        if camera_count == 0:
            validation_results['errors'].append("No cameras found")
        
        if image_count == 0:
            validation_results['errors'].append("No images found")
        
        if point_count < 1000:
            validation_results['errors'].append(f"Insufficient 3D points: {point_count} < 1000")
        
        if image_file_count < image_count * 0.8:
            validation_results['warnings'].append(
                f"Missing image files: {image_file_count} < {image_count * 0.8}"
            )
        
        # Set validation status
        validation_results['valid'] = len(validation_results['errors']) == 0
        
        logger.info(f"COLMAP validation: {'✅ PASSED' if validation_results['valid'] else '❌ FAILED'}")
        logger.info(f"Statistics: {validation_results['statistics']}")
        
        return validation_results
        
    except Exception as e:
        validation_results['errors'].append(f"Validation failed: {e}")
        return validation_results


def check_nerfstudio_compatibility(data_dir: Path) -> bool:
    """
    Quick check for NerfStudio data compatibility
    
    Args:
        data_dir: Path to dataset directory
        
    Returns:
        True if compatible, False otherwise
    """
    validation = validate_colmap_structure(data_dir)
    return validation['valid']


def get_dataset_statistics(data_dir: Path) -> Dict[str, int]:
    """
    Get basic dataset statistics
    
    Args:
        data_dir: Path to dataset directory
        
    Returns:
        Dictionary with dataset statistics
    """
    validation = validate_colmap_structure(data_dir)
    return validation.get('statistics', {})
