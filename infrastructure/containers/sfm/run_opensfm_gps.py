#!/usr/bin/env python3
"""
OpenSfM GPS-Enhanced SfM Processing Pipeline
Runs Structure-from-Motion with GPS priors from drone flight path data
"""

import os
import sys
import json
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Dict, List, Tuple
import logging
import zipfile
import yaml
import time

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Add current directory to Python path for imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import our GPS processors
from gps_processor import DroneFlightPathProcessor
from gps_processor_3d import Advanced3DPathProcessor
from colmap_converter import OpenSfMToCOLMAPConverter


def log_memory_usage(stage: str) -> None:
    """Log current process and system memory usage in MB."""
    rss_mb = None
    mem_total_mb = None
    mem_avail_mb = None

    try:
        import resource

        usage = resource.getrusage(resource.RUSAGE_SELF)
        # ru_maxrss is kilobytes on Linux
        rss_mb = usage.ru_maxrss / 1024.0
    except Exception:
        pass

    try:
        meminfo = {}
        with open("/proc/meminfo", "r") as f:
            for line in f:
                parts = line.split()
                if len(parts) >= 2:
                    meminfo[parts[0].rstrip(":")] = float(parts[1])
        if "MemTotal" in meminfo:
            mem_total_mb = meminfo["MemTotal"] / 1024.0
        if "MemAvailable" in meminfo:
            mem_avail_mb = meminfo["MemAvailable"] / 1024.0
    except Exception:
        pass

    pieces = []
    if rss_mb is not None:
        pieces.append(f"rss={rss_mb:.1f}MB")
    if mem_total_mb is not None:
        pieces.append(f"total={mem_total_mb:.0f}MB")
    if mem_avail_mb is not None:
        pieces.append(f"avail={mem_avail_mb:.0f}MB")

    if pieces:
        msg = " | ".join(pieces)
        print(f"MEMORY_PROBE [{stage}]: {msg}", flush=True)
        logger.info(f"🧠 Memory ({stage}): {msg}")


class OpenSfMGPSPipeline:
    """Main pipeline for GPS-enhanced OpenSfM processing"""
    
    def __init__(self, input_dir: Path, output_dir: Path, gps_csv_path: Path = None):
        """
        Initialize OpenSfM GPS pipeline
        
        Args:
            input_dir: Directory containing input ZIP or images
            output_dir: Directory for output files
            gps_csv_path: Optional path to GPS CSV file
        """
        self.input_dir = Path(input_dir)
        self.output_dir = Path(output_dir)
        self.gps_csv_path = Path(gps_csv_path) if gps_csv_path else None
        self.work_dir = None
        self.images_dir = None
        self.opensfm_dir = None
        self.has_gps_priors = False
        self.image_count = 0
        self.feature_stats = {}

        # Ensure output directory exists
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def setup_workspace(self) -> Path:
        """Set up temporary workspace for processing"""
        self.work_dir = Path(tempfile.mkdtemp(prefix="opensfm_"))
        self.images_dir = self.work_dir / "images"
        self.opensfm_dir = self.work_dir / "opensfm"
        
        # Create directories
        self.images_dir.mkdir(parents=True, exist_ok=True)
        self.opensfm_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"🏗️ Created workspace: {self.work_dir}")
        return self.work_dir
    
    def extract_images(self) -> int:
        """Extract images from input directory or ZIP file"""
        image_count = 0
        
        # Check if input is a ZIP file
        zip_files = list(self.input_dir.glob("*.zip"))
        if zip_files:
            # Extract first ZIP file found
            zip_path = zip_files[0]
            logger.info(f"📦 Extracting ZIP: {zip_path}")
            
            with zipfile.ZipFile(zip_path, 'r') as zf:
                for member in zf.namelist():
                    if member.lower().endswith(('.jpg', '.jpeg', '.png')):
                        # Extract to images directory
                        target_path = self.images_dir / Path(member).name
                        with zf.open(member) as source, open(target_path, 'wb') as target:
                            target.write(source.read())
                        image_count += 1
        else:
            # Copy images from input directory
            for img_path in self.input_dir.rglob('*'):
                if img_path.suffix.lower() in ['.jpg', '.jpeg', '.png']:
                    shutil.copy2(img_path, self.images_dir / img_path.name)
                    image_count += 1
        
        logger.info(f"📷 Extracted {image_count} images")
        return image_count
    
    def process_gps_data(self) -> bool:
        """Process GPS data if available"""
        if not self.gps_csv_path or not self.gps_csv_path.exists():
            # Check for GPS CSV in input directory
            csv_files = list(self.input_dir.glob("gps/*.csv"))
            if not csv_files:
                logger.warning("⚠️ No GPS CSV file found, proceeding without GPS priors")
                return False
            self.gps_csv_path = csv_files[0]
        
        logger.info(f"🛰️ Processing GPS data from: {self.gps_csv_path}")
        
        try:
            # Use the new Advanced 3D Path Processor
            processor = Advanced3DPathProcessor(self.gps_csv_path, self.images_dir)
            
            # Process flight data
            processor.parse_flight_csv()
            processor.setup_local_coordinate_system()
            processor.build_3d_flight_path()
            
            # Process photos with intelligent ordering
            photos = processor.get_photo_list_with_validation()
            if not photos:
                logger.error("❌ No photos found to process")
                return False
            
            # Map photos to 3D positions
            processor.map_photos_to_3d_positions(photos)
            # Refine using EXIF+trajectory projection for sub-meter altitude
            try:
                processor.apply_exif_trajectory_projection(photos)
                logger.info("✅ Applied EXIF+trajectory projection refinement")
            except Exception as refine_err:
                logger.warning(f"⚠️ EXIF+trajectory projection skipped due to error: {refine_err}")
            
            # Generate OpenSfM files
            processor.generate_opensfm_files(self.opensfm_dir)
            
            # Get processing summary
            summary = processor.get_processing_summary()
            logger.info(f"📊 GPS Processing Summary:")
            logger.info(f"   Photos: {summary['photos_processed']}")
            logger.info(f"   Path length: {summary['path_length_m']}m")
            logger.info(f"   Photo spacing: {summary['photo_spacing_m']}m")
            logger.info(f"   Confidence: {summary['confidence_stats']['mean']:.2f}")
            
            self.has_gps_priors = True
            return True
            
        except Exception as e:
            logger.error(f"❌ GPS processing failed: {e}")
            logger.warning("⚠️ Continuing without GPS priors")
            return False
    
    def create_opensfm_config(self) -> None:
        """Create OpenSfM configuration file"""
        base_config = {
            # Feature extraction
            'feature_type': 'SIFT',
            'feature_process_size': 2048,
            'feature_max_num_features': 20000,
            'feature_min_frames': 4000,
            'sift_peak_threshold': 0.006,
            
            # Matching
            'matching_gps_neighbors': 30,
            'matching_gps_distance': 300,
            'matching_graph_rounds': 80,
            'robust_matching_min_match': 8,
            
            # Reconstruction
            'min_ray_angle_degrees': 1.0,
            'reconstruction_min_ratio': 0.6,
            'triangulation_min_ray_angle_degrees': 1.0,
            
            # GPS integration
            'use_altitude_tag': True,
            'gps_accuracy': 5.0,
            
            # Bundle adjustment
            'bundle_use_gps': True,
            'bundle_use_gcp': False,
            
            # Optimization
            'optimize_camera_parameters': True,
            'bundle_max_iterations': 100,
            
            # Output
            'processes': 4,
            
            # Train/test split for 3DGS
            'reconstruction_split_ratio': 0.8,
            'reconstruction_split_method': 'sequential',
            'save_partial_reconstructions': True,
        }

        conservative_overrides = {
            'feature_process_size': 1200,
            'feature_max_num_features': 6000,
            'feature_min_frames': 1200,
            'sift_peak_threshold': 0.01,  # reduce feature count
            'matching_gps_neighbors': 10,
            'matching_gps_distance': 120,
            'matching_graph_rounds': 16,
            'robust_matching_min_match': 12,
            'processes': 1,
        }

        config = base_config.copy()
        if not self.has_gps_priors:
            config.update(conservative_overrides)
            logger.info("🧭 Using conservative no-CSV profile for matching/features (lower memory).")
        
        config_path = self.opensfm_dir / "config.yaml"
        with open(config_path, 'w') as f:
            yaml.dump(config, f)
        
        logger.info(f"✅ Created OpenSfM config: {config_path}")

        try:
            image_count = self.image_count or len(list(self.images_dir.iterdir()))
            neighbors = config.get('matching_gps_neighbors', 0)
            estimated_pairs = image_count * neighbors
            logger.info(f"📈 Matching plan: images={image_count}, neighbors≈{neighbors}, est. pairs≈{estimated_pairs}")
            print(f"CONFIG_PROFILE has_gps={self.has_gps_priors} processes={config.get('processes')} neighbors={neighbors} est_pairs={estimated_pairs} feature_process_size={config.get('feature_process_size')} max_features={config.get('feature_max_num_features')} min_frames={config.get('feature_min_frames')}", flush=True)
        except Exception:
            pass
    
    def copy_images_to_opensfm(self) -> None:
        """Copy images to OpenSfM directory structure"""
        opensfm_images = self.opensfm_dir / "images"
        if opensfm_images.exists():
            shutil.rmtree(opensfm_images)
        shutil.copytree(self.images_dir, opensfm_images)
        logger.info(f"✅ Copied {len(list(opensfm_images.iterdir()))} images to OpenSfM")
    
    def run_opensfm_commands(self) -> bool:
        """Run OpenSfM reconstruction pipeline"""
        commands = [
            ("extract_metadata", "Extract image metadata"),
            ("detect_features", "Detect features"),
            ("match_features", "Match features"),
            ("create_tracks", "Create tracks"),
            ("reconstruct", "Reconstruct 3D structure"),
            ("export_colmap", "Export tracks to COLMAP format"),
        ]
        
        for cmd, description in commands:
            logger.info(f"🔧 {description}...")
            log_memory_usage(f"before_{cmd}")
            
            try:
                if cmd in {"match_features", "reconstruct"}:
                    # Stream output and enforce a max duration for reconstruct to detect hangs
                    max_seconds = 7200 if cmd == "reconstruct" else 2400  # reconstruct up to 120m, match up to 40m
                    proc = subprocess.Popen(
                        ["opensfm", cmd, str(self.opensfm_dir)],
                        stdout=subprocess.PIPE,
                        stderr=subprocess.STDOUT,
                        text=True,
                    )
                    start = time.time()
                    last_log = start
                    while True:
                        line = proc.stdout.readline()
                        if line:
                            line = line.rstrip()
                            tag = "RECONSTRUCT" if cmd == "reconstruct" else "MATCH"
                            print(f"OPENSFM_{tag}: {line}", flush=True)
                        now = time.time()
                        if now - last_log > 300:  # heartbeat every 5 minutes
                            log_memory_usage(f"{cmd}_heartbeat_{int(now-start)}s")
                            last_log = now
                        if now - start > max_seconds:
                            proc.kill()
                            logger.error(f"❌ OpenSfM {cmd} timed out")
                            return False
                        if line == '' and proc.poll() is not None:
                            break
                    ret = proc.wait()
                    if ret != 0:
                        logger.error(f"❌ OpenSfM {cmd} failed with code {ret}")
                        return False
                else:
                    subprocess.run(
                        ["opensfm", cmd, str(self.opensfm_dir)],
                        check=True,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        text=True,
                    )

                logger.info(f"✅ {description} completed")
                log_memory_usage(f"after_{cmd}")
                
            except subprocess.CalledProcessError as e:
                logger.error(f"❌ OpenSfM {cmd} failed:")
                logger.error(f"   stdout: {e.stdout}")
                logger.error(f"   stderr: {e.stderr}")
                return False
        
        return True
    
    def validate_reconstruction(self) -> bool:
        """Validate OpenSfM reconstruction quality"""
        reconstruction_file = self.opensfm_dir / "reconstruction.json"
        
        if not reconstruction_file.exists():
            logger.error("❌ No reconstruction file found")
            return False
        
        with open(reconstruction_file, 'r') as f:
            reconstructions = json.load(f)
        
        if not reconstructions:
            logger.error("❌ Empty reconstruction")
            return False
        
        # Get the largest reconstruction
        recon = max(reconstructions, key=lambda r: len(r.get('points', {})))
        
        shots_dict = recon.get('shots', {})
        num_cameras = len(shots_dict)
        num_points = len(recon.get('points', {}))
        
        logger.info(f"📊 Reconstruction statistics:")
        logger.info(f"   Cameras: {num_cameras}")
        logger.info(f"   3D points: {num_points}")
        
        # Log which images were registered (first 20 for brevity)
        registered_images = list(shots_dict.keys())
        logger.info(f"   Registered images (showing up to 20): {registered_images[:20]}")
        
        # Determine unregistered images for debugging
        all_images = [p.name for p in (self.images_dir).iterdir() if p.suffix.lower() in {'.jpg', '.jpeg', '.png'}]
        unregistered = sorted(set(all_images) - set(registered_images))
        if unregistered:
            logger.warning(f"⚠️ Unregistered images (showing up to 20): {unregistered[:20]}")
        
        # Validate minimum quality
        if num_cameras < 5:
            logger.error("❌ Too few cameras reconstructed")
            return False
        
        if num_points < 1000:
            logger.error("❌ Too few 3D points reconstructed")
            return False

        logger.info("✅ Reconstruction validated")
        return True
    
    def validate_exported_colmap(self) -> Dict:
        """Validate OpenSfM exported COLMAP files for track quality"""
        sparse_dir = self.output_dir / "sparse" / "0"
        
        # Initialize results
        results = {
            'camera_count': 0,
            'image_count': 0,
            'point_count': 0,
            'has_tracks': False,
            'mean_observations': 0.0,
            'mean_track_length': 0.0,
            'quality_check_passed': False
        }
        
        try:
            # Validate cameras.txt
            cameras_file = sparse_dir / "cameras.txt"
            if cameras_file.exists():
                with open(cameras_file, 'r') as f:
                    camera_lines = [line for line in f if line.strip() and not line.startswith('#')]
                    results['camera_count'] = len(camera_lines)
            
            # Validate images.txt and check for observations
            images_file = sparse_dir / "images.txt"
            if images_file.exists():
                with open(images_file, 'r') as f:
                    lines = f.readlines()
                    
                # Check header for mean observations
                for line in lines:
                    if line.startswith('# Number of images:') and 'mean observations per image:' in line:
                        parts = line.split('mean observations per image:')
                        if len(parts) > 1:
                            try:
                                results['mean_observations'] = float(parts[1].strip())
                                if results['mean_observations'] > 0:
                                    results['has_tracks'] = True
                            except ValueError:
                                pass
                        break
                
                # Count images
                image_lines = [line for line in lines if line.strip() and not line.startswith('#')]
                results['image_count'] = len(image_lines) // 2  # COLMAP format: 2 lines per image
            
            # Validate points3D.txt and check for track length
            points_file = sparse_dir / "points3D.txt"
            if points_file.exists():
                with open(points_file, 'r') as f:
                    lines = f.readlines()
                    
                # Check for tracks by analyzing COLMAP points3D.txt structure
                # OpenSfM native export doesn't include mean track length header,
                # so we validate tracks by checking if points have observations
                non_comment_lines = [line for line in lines if line.strip() and not line.startswith('#')]
                if non_comment_lines:
                    # Sample first few points to check for track data
                    sample_size = min(10, len(non_comment_lines))
                    total_observations = 0
                    
                    for line in non_comment_lines[:sample_size]:
                        parts = line.strip().split()
                        # COLMAP points3D.txt format: POINT3D_ID X Y Z R G B ERROR TRACK[...]
                        if len(parts) >= 8:  # At least point data + error
                            # Track data starts after ERROR (index 7)
                            track_data = parts[8:]  # Everything after ERROR
                            # Track format: IMAGE_ID POINT2D_IDX IMAGE_ID POINT2D_IDX ...
                            observations = len(track_data) // 2  # Each observation is 2 values
                            total_observations += observations
                    
                    if total_observations > 0:
                        results['mean_track_length'] = total_observations / sample_size
                        results['has_tracks'] = True
                        logger.info(f"   Track validation: {total_observations} total observations in {sample_size} sample points")
                    else:
                        logger.warning("   Track validation: No observations found in sampled points")
                
                # Count points
                point_lines = [line for line in lines if line.strip() and not line.startswith('#')]
                results['point_count'] = len(point_lines)
            
            # Quality check
            results['quality_check_passed'] = (
                results['camera_count'] > 0 and
                results['image_count'] > 0 and
                results['point_count'] > 0 and
                results['has_tracks']  # NEW: Must have tracks for quality
            )
            
        except Exception as e:
            logger.error(f"❌ Validation error: {e}")
        
        return results
    
    def convert_to_colmap(self) -> bool:
        """Convert OpenSfM output to COLMAP format"""
        try:
            # Check if OpenSfM exported COLMAP files directly
            exported_colmap_dir = self.opensfm_dir / "colmap_export"
            logger.info(f"🔍 Checking for OpenSfM export in: {exported_colmap_dir}")
            
            if exported_colmap_dir.exists():
                logger.info("✅ Found OpenSfM exported COLMAP directory!")
                
                # List what's in the directory
                colmap_files = ["cameras.txt", "images.txt", "points3D.txt"]
                found_files = []
                for file_name in colmap_files:
                    src_file = exported_colmap_dir / file_name
                    if src_file.exists():
                        found_files.append(file_name)
                        logger.info(f"   ✅ Found: {file_name}")
                    else:
                        logger.warning(f"   ⚠️ Missing: {file_name}")
                
                if len(found_files) == 3:
                    logger.info("🔄 Using OpenSfM exported COLMAP files (with tracks)")
                    
                    # Copy exported COLMAP files to output
                    sparse_output = self.output_dir / "sparse" / "0"
                    sparse_output.mkdir(parents=True, exist_ok=True)
                    
                    # Copy COLMAP files
                    for file_name in found_files:
                        src_file = exported_colmap_dir / file_name
                        dst_file = sparse_output / file_name
                        shutil.copy2(src_file, dst_file)
                        logger.info(f"✅ Copied {file_name} with track data")
                    
                    # Validate the exported files
                    validation_results = self.validate_exported_colmap()
                    logger.info(f"📊 Exported COLMAP Validation:")
                    logger.info(f"   Cameras: {validation_results.get('camera_count', 0)}")
                    logger.info(f"   Images: {validation_results.get('image_count', 0)}")
                    logger.info(f"   Points: {validation_results.get('point_count', 0)}")
                    logger.info(f"   Track Quality: {'✅ WITH TRACKS' if validation_results.get('has_tracks', False) else '❌ NO TRACKS'}")
                    
                    return validation_results.get('quality_check_passed', False)
                else:
                    logger.warning(f"⚠️ OpenSfM export incomplete - found {len(found_files)}/3 files")
                    logger.warning("   Falling back to custom converter")
            else:
                logger.warning(f"⚠️ OpenSfM export directory not found: {exported_colmap_dir}")
                logger.warning("   Falling back to custom converter")
            
            # Fallback to custom converter
            logger.info("🔄 Using custom OpenSfM to COLMAP converter")
            converter = OpenSfMToCOLMAPConverter(self.opensfm_dir, self.output_dir)
            validation_results = converter.convert()
            
            # Log conversion results
            logger.info(f"📊 COLMAP Conversion Results:")
            logger.info(f"   Cameras: {validation_results.get('camera_count', 0)}")
            logger.info(f"   Images: {validation_results.get('image_count', 0)}")
            logger.info(f"   Points: {validation_results.get('point_count', 0)}")
            logger.info(f"   Quality Check: {'✅ PASSED' if validation_results.get('quality_check_passed', False) else '❌ FAILED'}")
            
            return validation_results.get('quality_check_passed', False)
                
        except Exception as e:
            logger.error(f"❌ COLMAP conversion failed: {e}")
            return False
    
    def copy_images_for_3dgs(self) -> None:
        """Copy images to output directory for 3DGS training"""
        output_images_dir = self.output_dir / "images"
        
        if output_images_dir.exists():
            shutil.rmtree(output_images_dir)
        
        # Copy images from extracted directory
        shutil.copytree(self.images_dir, output_images_dir)
        
        image_count = len(list(output_images_dir.iterdir()))
        logger.info(f"✅ Copied {image_count} images to output directory for 3DGS training")
    
    def generate_metadata_json(self) -> None:
        """Generate metadata JSON file with processing statistics"""
        # Get reconstruction statistics
        reconstruction_file = self.opensfm_dir / "reconstruction.json"
        
        if not reconstruction_file.exists():
            logger.warning("⚠️ No reconstruction file found for metadata generation")
            return
        
        with open(reconstruction_file, 'r') as f:
            reconstructions = json.load(f)
        
        if not reconstructions:
            logger.warning("⚠️ Empty reconstruction for metadata generation")
            return
        
        # Get the largest reconstruction
        recon = max(reconstructions, key=lambda r: len(r.get('points', {})))
        
        shots_dict = recon.get('shots', {})
        num_cameras = len(shots_dict)
        num_points = len(recon.get('points', {}))
        
        # Calculate processing time (approximate)
        processing_time = time.time() - getattr(self, '_start_time', time.time())
        
        # Generate metadata
        metadata = {
            'pipeline': 'OpenSfM GPS-Enhanced Structure-from-Motion',
            'processing_time_seconds': round(processing_time, 2),
            'cameras_registered': num_cameras,
            'images_registered': num_cameras,  # Assuming 1:1 mapping
            'points_3d': num_points,
            'gps_enhanced': hasattr(self, 'gps_csv_path') and self.gps_csv_path is not None,
            'quality_check_passed': num_points >= 1000,
            'colmap_format': True,
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime())
        }
        
        metadata_file = self.output_dir / "sfm_metadata.json"
        with open(metadata_file, 'w') as f:
            json.dump(metadata, f, indent=2)
        
        logger.info(f"✅ Generated metadata JSON: {metadata_file}")
    
    def create_stub_database(self) -> None:
        """Create a stub COLMAP database.db file for compatibility"""
        import sqlite3
        
        database_file = self.output_dir / "database.db"
        
        # Create minimal COLMAP database schema
        conn = sqlite3.connect(str(database_file))
        cursor = conn.cursor()
        
        # Create basic COLMAP database tables (minimal schema)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS cameras (
                camera_id INTEGER PRIMARY KEY,
                model INTEGER NOT NULL,
                width INTEGER NOT NULL,
                height INTEGER NOT NULL,
                params BLOB,
                prior_focal_length INTEGER NOT NULL
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS images (
                image_id INTEGER PRIMARY KEY,
                name TEXT NOT NULL UNIQUE,
                camera_id INTEGER NOT NULL,
                prior_qw REAL,
                prior_qx REAL,
                prior_qy REAL,
                prior_qz REAL,
                prior_tx REAL,
                prior_ty REAL,
                prior_tz REAL,
                CONSTRAINT fk_images_camera_id FOREIGN KEY(camera_id) REFERENCES cameras(camera_id)
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS keypoints (
                image_id INTEGER NOT NULL,
                rows INTEGER NOT NULL,
                cols INTEGER NOT NULL,
                data BLOB,
                CONSTRAINT fk_keypoints_image_id FOREIGN KEY(image_id) REFERENCES images(image_id)
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS matches (
                pair_id INTEGER PRIMARY KEY,
                rows INTEGER NOT NULL,
                cols INTEGER NOT NULL,
                data BLOB
            )
        ''')
        
        # Insert minimal data based on COLMAP conversion
        sparse_dir = self.output_dir / "sparse" / "0"
        cameras_file = sparse_dir / "cameras.txt"
        images_file = sparse_dir / "images.txt"
        
        if cameras_file.exists():
            with open(cameras_file, 'r') as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith('#'):
                        continue
                    parts = line.split()
                    if len(parts) >= 5:
                        try:
                            camera_id = int(parts[0])
                            model = 1  # PINHOLE model
                            width = int(parts[2])
                            height = int(parts[3])
                            cursor.execute(
                                'INSERT OR REPLACE INTO cameras (camera_id, model, width, height, params, prior_focal_length) VALUES (?, ?, ?, ?, ?, ?)',
                                (camera_id, model, width, height, b'', 0)
                            )
                        except (ValueError, IndexError) as e:
                            logger.warning(f"Skipping malformed camera line: {line} - {e}")
                            continue
        
        if images_file.exists():
            with open(images_file, 'r') as f:
                lines = f.readlines()
                i = 0
                image_id = 1
                while i < len(lines):
                    line = lines[i].strip()
                    if not line or line.startswith('#'):
                        i += 1
                        continue
                    parts = line.split()
                    if len(parts) >= 10:
                        try:
                            camera_id = int(parts[8])
                            name = parts[9]
                            cursor.execute(
                                'INSERT OR REPLACE INTO images (image_id, name, camera_id) VALUES (?, ?, ?)',
                                (image_id, name, camera_id)
                            )
                            image_id += 1
                        except (ValueError, IndexError) as e:
                            logger.warning(f"Skipping malformed image line: {line} - {e}")
                    i += 2  # Skip points2D line
        
        conn.commit()
        conn.close()
        
        logger.info(f"✅ Created stub COLMAP database: {database_file}")
    
    def cleanup(self) -> None:
        """Clean up temporary files"""
        if self.work_dir and self.work_dir.exists():
            shutil.rmtree(self.work_dir)
            logger.info("🧹 Cleanup completed")
    
    def run(self) -> int:
        """Run the complete pipeline"""
        try:
            # Record start time for metadata
            self._start_time = time.time()
            
            # Set up workspace
            self.setup_workspace()
            log_memory_usage("setup_workspace")
            
            # Extract images
            image_count = self.extract_images()
            self.image_count = image_count
            log_memory_usage("after_extract_images")
            if image_count == 0:
                logger.error("❌ No images found to process")
                return 1
            
            # Process GPS data (if available)
            has_gps = self.process_gps_data()
            self.has_gps_priors = has_gps
            log_memory_usage("after_gps_processing")
            
            # Create OpenSfM config
            self.create_opensfm_config()
            log_memory_usage("after_config_creation")
            
            # Copy images
            self.copy_images_to_opensfm()
            log_memory_usage("after_copy_images")
            
            # Run OpenSfM
            logger.info("🔄 Running OpenSfM reconstruction...")
            if not self.run_opensfm_commands():
                logger.error("❌ OpenSfM reconstruction failed")
                return 1
            log_memory_usage("after_opensfm_commands")
            
            # Validate reconstruction
            if not self.validate_reconstruction():
                return 1
            log_memory_usage("after_reconstruction_validation")
            
            # Convert to COLMAP format
            logger.info("🔄 Converting to COLMAP format...")
            if not self.convert_to_colmap():
                return 1
            log_memory_usage("after_colmap_conversion")
            
            # Generate additional artifacts for 3DGS compatibility
            logger.info("🔄 Generating additional artifacts for 3DGS compatibility...")
            self.copy_images_for_3dgs()
            self.generate_metadata_json()
            self.create_stub_database()
            log_memory_usage("after_artifact_generation")
            
            logger.info("✅ OpenSfM GPS pipeline completed successfully")
            return 0
            
        except Exception as e:
            logger.error(f"❌ Pipeline failed with error: {e}")
            import traceback
            traceback.print_exc()
            return 1
        
        finally:
            # Always cleanup
            self.cleanup()


def main():
    """Main entry point"""
    if len(sys.argv) < 3:
        print("Usage: python run_opensfm_gps.py <input_dir> <output_dir> [gps_csv]")
        sys.exit(1)
    
    input_dir = Path(sys.argv[1])
    output_dir = Path(sys.argv[2])
    gps_csv = Path(sys.argv[3]) if len(sys.argv) > 3 else None
    
    # Run pipeline
    pipeline = OpenSfMGPSPipeline(input_dir, output_dir, gps_csv)
    exit_code = pipeline.run()
    
    logger.info(f"🏁 Pipeline finished with exit code: {exit_code}")
    sys.exit(exit_code)


if __name__ == "__main__":
    main() # Trigger rebuild
