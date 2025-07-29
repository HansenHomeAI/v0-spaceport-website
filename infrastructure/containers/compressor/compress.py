#!/usr/bin/env python3
"""
Production PlayCanvas SOGS Compression Container
Real implementation using the official PlayCanvas SOGS package from:
https://github.com/playcanvas/sogs

This container uses the actual `sogs-compress` CLI tool to compress 3D Gaussian splats
into WebP textures and metadata for use with SuperSplat viewer.
"""

import os
import sys
import json
import logging
import tarfile
import tempfile
import zipfile
import subprocess
from pathlib import Path
from typing import Dict, List, Any
import boto3

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class PlayCanvasSOGSCompressor:
    """Real PlayCanvas SOGS Compression Implementation using official package"""
    
    def __init__(self):
        self.s3_client = boto3.client('s3')
        self.input_dir = "/opt/ml/processing/input"
        self.output_dir = "/opt/ml/processing/output"
        
        # Verify GPU availability
        try:
            import torch
        if not torch.cuda.is_available():
            logger.error("GPU not available - SOGS requires CUDA GPU!")
                sys.exit(1)
            logger.info("✅ GPU available for SOGS compression")
        except ImportError:
            logger.error("PyTorch not available")
            sys.exit(1)
        
        # Verify SOGS CLI is available
        try:
            result = subprocess.run(['sogs-compress', '--help'], 
                                  capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                logger.info("✅ SOGS CLI tool available")
            else:
                logger.error("❌ SOGS CLI tool not working properly")
                sys.exit(1)
        except (subprocess.TimeoutExpired, FileNotFoundError) as e:
            logger.error(f"❌ SOGS CLI tool not found: {e}")
            sys.exit(1)
    
    def compress_gaussian_splats(self, input_ply_files: List[str], output_dir: str) -> Dict[str, Any]:
        """
        Compress Gaussian splats using real PlayCanvas SOGS CLI tool
        
        Args:
            input_ply_files: List of PLY file paths to compress
            output_dir: Directory to save compressed output
            
        Returns:
            Dict containing compression results and metadata
        """
        logger.info(f"🚀 Starting PlayCanvas SOGS compression on {len(input_ply_files)} PLY files")
        
        results = {
            'method': 'playcanvas_sogs_official',
            'version': self._get_sogs_version(),
            'gpu_accelerated': True,
            'input_files': input_ply_files,
            'compressed_outputs': [],
            'compression_stats': {}
        }
        
        for i, ply_file in enumerate(input_ply_files):
            logger.info(f"Processing PLY file {i+1}/{len(input_ply_files)}: {ply_file}")
            
            try:
                # Create output directory for this PLY file
                file_base = Path(ply_file).stem
                compress_dir = os.path.join(output_dir, f"compressed_{file_base}")
                os.makedirs(compress_dir, exist_ok=True)
                
                # Run PlayCanvas SOGS compression
                compression_result = self._run_sogs_compression(ply_file, compress_dir)
                
                # Collect output files and calculate statistics
                output_files = list(Path(compress_dir).glob('*'))
                original_size = os.path.getsize(ply_file)
                compressed_size = sum(f.stat().st_size for f in output_files)
                compression_ratio = original_size / compressed_size if compressed_size > 0 else 0
                
                file_result = {
                    'input_file': ply_file,
                    'output_dir': compress_dir,
                    'output_files': [str(f) for f in output_files],
                    'original_size_mb': original_size / (1024 * 1024),
                    'compressed_size_mb': compressed_size / (1024 * 1024),
                    'compression_ratio': compression_ratio,
                    'webp_files': [str(f) for f in output_files if f.suffix == '.webp'],
                    'metadata_file': str(Path(compress_dir) / 'meta.json') if (Path(compress_dir) / 'meta.json').exists() else None
                }
                
                results['compressed_outputs'].append(file_result)
                results['compression_stats'][f'file_{i}'] = {
                    'original_size_mb': file_result['original_size_mb'],
                    'compressed_size_mb': file_result['compressed_size_mb'],
                    'compression_ratio': compression_ratio,
                    'webp_count': len(file_result['webp_files'])
                }
                
                logger.info(f"✅ File {i+1} compressed: {compression_ratio:.2f}x ratio, {len(file_result['webp_files'])} WebP files")
            
            except Exception as e:
                logger.error(f"Failed to compress {ply_file}: {e}")
                raise
        
        # Generate final summary
        total_original = sum(stats['original_size_mb'] for stats in results['compression_stats'].values())
        total_compressed = sum(stats['compressed_size_mb'] for stats in results['compression_stats'].values())
        overall_ratio = total_original / total_compressed if total_compressed > 0 else 0
        
        results['overall_compression_ratio'] = overall_ratio
        results['total_original_mb'] = total_original
        results['total_compressed_mb'] = total_compressed
        results['total_webp_files'] = sum(stats['webp_count'] for stats in results['compression_stats'].values())
        
        logger.info(f"🎯 PlayCanvas SOGS Compression Complete: {overall_ratio:.2f}x overall compression")
        logger.info(f"📁 Generated {results['total_webp_files']} WebP texture files")
        
        return results

    def _run_sogs_compression(self, ply_file: str, output_dir: str) -> Dict[str, Any]:
        """Run the official PlayCanvas SOGS compression CLI tool"""
        logger.info(f"🔧 Running SOGS compression: {ply_file} -> {output_dir}")
        
        # Run the official SOGS CLI command
        cmd = ['sogs-compress', '--ply', ply_file, '--output-dir', output_dir]
        
        logger.info(f"Executing: {' '.join(cmd)}")
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=1800,  # 30 minutes timeout
                cwd=output_dir
            )
            
            if result.returncode == 0:
                logger.info("✅ SOGS compression completed successfully")
                logger.info(f"STDOUT: {result.stdout}")
                if result.stderr:
                    logger.info(f"STDERR: {result.stderr}")
                
                # Check for expected output files
                output_files = list(Path(output_dir).glob('*'))
                webp_files = [f for f in output_files if f.suffix == '.webp']
                meta_file = Path(output_dir) / 'meta.json'
                
                logger.info(f"Generated {len(webp_files)} WebP files: {[f.name for f in webp_files]}")
                
                if meta_file.exists():
                    logger.info("✅ meta.json file generated")
                    with open(meta_file, 'r') as f:
                        metadata = json.load(f)
                        logger.info(f"Metadata keys: {list(metadata.keys())}")
                else:
                    logger.warning("⚠️ meta.json file not found")
                
                return {
                    'success': True,
                    'output_files': len(output_files),
                    'webp_files': len(webp_files),
                    'has_metadata': meta_file.exists()
                }
            else:
                logger.error(f"❌ SOGS compression failed with return code {result.returncode}")
                logger.error(f"STDOUT: {result.stdout}")
                logger.error(f"STDERR: {result.stderr}")
                raise RuntimeError(f"SOGS compression failed: {result.stderr}")
                
        except subprocess.TimeoutExpired:
            logger.error("❌ SOGS compression timed out after 30 minutes")
            raise RuntimeError("SOGS compression timed out")
        except Exception as e:
            logger.error(f"❌ SOGS compression failed: {e}")
            raise

    def _get_sogs_version(self) -> str:
        """Get the version of the SOGS package"""
        try:
            result = subprocess.run(['pip', 'show', 'sogs'], 
                                  capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                for line in result.stdout.split('\n'):
                    if line.startswith('Version:'):
                        return line.split(':', 1)[1].strip()
            return "unknown"
        except:
            return "unknown"

    def process_job(self):
        """Main processing function for SageMaker"""
        logger.info("🚀 Starting PlayCanvas SOGS compression job")
        
        try:
            # Find PLY files in input
            ply_files = []
            
            # Check for PLY files and archives recursively
            for root, dirs, files in os.walk(self.input_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    if file.endswith('.ply'):
                        ply_files.append(file_path)
                    elif file.endswith(('.tar.gz', '.zip')):
                        # Extract and find PLY files
                        extracted_plys = self._extract_and_find_plys(file_path)
                        ply_files.extend(extracted_plys)
            
            if not ply_files:
                logger.error("No PLY files found in input directory")
                sys.exit(1)
            
            logger.info(f"Found {len(ply_files)} PLY files to compress")
            
            # Verify PLY files are valid for SOGS
            for ply_file in ply_files:
                if not self._validate_ply_for_sogs(ply_file):
                    logger.error(f"PLY file not compatible with SOGS: {ply_file}")
                    sys.exit(1)
            
            # Compress using PlayCanvas SOGS
            results = self.compress_gaussian_splats(ply_files, self.output_dir)
            
            # Save compression summary
            summary_path = os.path.join(self.output_dir, "sogs_compression_summary.json")
            with open(summary_path, 'w') as f:
                json.dump(results, f, indent=2, cls=NumpyEncoder)
            
            # Create SuperSplat viewer compatible structure
            self._create_supersplat_bundle(results)
            
            logger.info(f"✅ PlayCanvas SOGS compression completed successfully")
            logger.info(f"📊 Overall compression ratio: {results['overall_compression_ratio']:.2f}x")
            logger.info(f"📁 WebP texture files: {results['total_webp_files']}")
            logger.info(f"💾 Output saved to: {self.output_dir}")
            
        except Exception as e:
            logger.error(f"Compression job failed: {e}")
            raise

    def _validate_ply_for_sogs(self, ply_file: str) -> bool:
        """Validate that PLY file has required fields for SOGS compression"""
        try:
            with open(ply_file, 'rb') as f:
                header = f.read(2048).decode('utf-8', errors='ignore')
                
            # Check for required fields
            required_fields = ['f_dc_0', 'f_dc_1', 'f_dc_2', 'opacity', 'scale_0', 'scale_1', 'scale_2']
            
            for field in required_fields:
                if field not in header:
                    logger.error(f"Missing required field '{field}' in PLY file: {ply_file}")
                    return False
            
            logger.info(f"✅ PLY file validated for SOGS: {ply_file}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to validate PLY file {ply_file}: {e}")
            return False

    def _create_supersplat_bundle(self, results: Dict[str, Any]):
        """Create a bundle compatible with SuperSplat viewer"""
        logger.info("📦 Creating SuperSplat viewer bundle")
        
        # Find the largest/best compression result
        if not results['compressed_outputs']:
            logger.warning("No compressed outputs to bundle")
            return
        
        # Use the first result (or could select based on size/quality)
        best_result = results['compressed_outputs'][0]
        source_dir = Path(best_result['output_dir'])
        bundle_dir = Path(self.output_dir) / "supersplat_bundle"
        bundle_dir.mkdir(exist_ok=True)
        
        # Copy all WebP files and metadata
        for file_path in Path(best_result['output_dir']).glob('*'):
            if file_path.is_file():
                dest_path = bundle_dir / file_path.name
                import shutil
                shutil.copy2(file_path, dest_path)
                logger.info(f"Copied {file_path.name} to SuperSplat bundle")
        
        # Create viewer settings file for SuperSplat
        settings = {
            "background": {"color": [0, 0, 0, 0]},
            "camera": {
                "fov": 1.0,
                "position": [0, 1, -1],
                "target": [0, 0, 0],
                "startAnim": "orbit"
            }
        }
        
        settings_path = bundle_dir / "settings.json"
        with open(settings_path, 'w') as f:
            json.dump(settings, f, indent=2)
        
        logger.info(f"✅ SuperSplat bundle created at: {bundle_dir}")

    def _extract_and_find_plys(self, archive_path: str) -> List[str]:
        """Extract archive and find PLY files"""
        logger.info(f"Extracting archive: {archive_path}")
        
        extract_dir = os.path.join(self.input_dir, "extracted")
        os.makedirs(extract_dir, exist_ok=True)
        
        if archive_path.endswith('.tar.gz'):
            with tarfile.open(archive_path, 'r:gz') as tar:
                tar.extractall(extract_dir)
        elif archive_path.endswith('.zip'):
            with zipfile.ZipFile(archive_path, 'r') as zip_file:
                zip_file.extractall(extract_dir)
        
        # Find PLY files recursively
        ply_files = []
        for root, dirs, files in os.walk(extract_dir):
            for file in files:
                if file.endswith('.ply'):
                    ply_files.append(os.path.join(root, file))
        
        logger.info(f"Found {len(ply_files)} PLY files in archive")
        return ply_files

class NumpyEncoder(json.JSONEncoder):
    """JSON encoder for numpy arrays"""
    def default(self, obj):
        import numpy as np
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        return super().default(obj)

if __name__ == "__main__":
    compressor = PlayCanvasSOGSCompressor()
    compressor.process_job() 