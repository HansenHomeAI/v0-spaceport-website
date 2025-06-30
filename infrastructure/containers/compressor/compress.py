#!/usr/bin/env python3
"""
Production PlayCanvas SOGS Compression Container
Real Self-Organizing Gaussian Splats implementation from https://github.com/playcanvas/sogs
"""

import os
import sys
import json
import logging
import tarfile
import tempfile
import zipfile
from pathlib import Path
from typing import Dict, List, Any, Callable
import boto3
import numpy as np

# Import SOGS dependencies at module level
try:
    import torch
    import torch.nn.functional as F
    from torchpq.clustering import KMeans
    from torch import Tensor
    from plas import sort_with_plas
    from plyfile import PlyData, PlyElement
    from PIL import Image
    SOGS_DEPENDENCIES_AVAILABLE = True
except ImportError as e:
    print(f"CRITICAL: SOGS dependencies not available: {e}")
    print("This container requires GPU with CUDA and all SOGS dependencies!")
    sys.exit(1)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class PlayCanvasSOGSCompressor:
    """Real PlayCanvas SOGS Compression Implementation"""
    
    def __init__(self):
        self.s3_client = boto3.client('s3')
        self.input_dir = "/opt/ml/processing/input"
        self.output_dir = "/opt/ml/processing/output"
        
        # Verify GPU availability
        if not torch.cuda.is_available():
            logger.error("GPU not available - SOGS requires CUDA GPU!")
            sys.exit(1)
        
        logger.info("✅ GPU available and PlayCanvas SOGS dependencies verified")
    
    def compress_gaussian_splats(self, input_ply_files: List[str], output_dir: str) -> Dict[str, Any]:
        """
        Compress Gaussian splats using real PlayCanvas SOGS algorithm
        
        Args:
            input_ply_files: List of PLY file paths to compress
            output_dir: Directory to save compressed output
            
        Returns:
            Dict containing compression results and metadata
        """
        logger.info(f"🚀 Starting PlayCanvas SOGS compression on {len(input_ply_files)} PLY files")
        
        results = {
            'method': 'playcanvas_sogs_real',
            'gpu_accelerated': True,
            'input_files': input_ply_files,
            'output_files': [],
            'compression_stats': {}
        }
        
        for i, ply_file in enumerate(input_ply_files):
            logger.info(f"Processing PLY file {i+1}/{len(input_ply_files)}: {ply_file}")
            
            try:
                # Load Gaussian splat data using PlayCanvas reader
                splats = self.read_ply(ply_file)
                
                # Create output directory for this PLY file
                compress_dir = os.path.join(output_dir, f"compressed_{i}")
                os.makedirs(compress_dir, exist_ok=True)
                
                # Apply PlayCanvas SOGS compression
                self.run_compression(compress_dir, splats)
                
                # Collect output files
                output_files = []
                for file in os.listdir(compress_dir):
                    full_path = os.path.join(compress_dir, file)
                    output_files.append(full_path)
                
                results['output_files'].extend(output_files)
                
                # Calculate compression statistics
                original_size = os.path.getsize(ply_file)
                compressed_size = sum(os.path.getsize(f) for f in output_files)
                compression_ratio = original_size / compressed_size if compressed_size > 0 else 0
                
                results['compression_stats'][f'file_{i}'] = {
                    'original_size_mb': original_size / (1024 * 1024),
                    'compressed_size_mb': compressed_size / (1024 * 1024),
                    'compression_ratio': compression_ratio,
                    'output_files': len(output_files)
                }
                
                logger.info(f"✅ File {i+1} compressed: {compression_ratio:.2f}x ratio, {len(output_files)} output files")
            
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
        results['total_output_files'] = len(results['output_files'])
        
        logger.info(f"🎯 PlayCanvas SOGS Compression Complete: {overall_ratio:.2f}x overall compression")
        logger.info(f"📁 Generated {results['total_output_files']} output files")
        
        return results

    @torch.no_grad()
    def read_ply(self, path):
        """
        Reads a .ply file and reconstructs a dictionary of PyTorch tensors on GPU.
        Exact implementation from PlayCanvas SOGS repository.
        """
        logger.info(f"Loading PLY file: {path}")
        
        plydata = PlyData.read(path)
        vd = plydata['vertex'].data

        def has_col(col_name):
            return col_name in vd.dtype.names

        xyz = np.stack([vd['x'], vd['y'], vd['z']], axis=-1)
        f_dc = np.stack([vd[f"f_dc_{i}"] for i in range(3)], axis=-1)

        rest_cols = [c for c in vd.dtype.names if c.startswith('f_rest_')]
        rest_cols_sorted = sorted(rest_cols, key=lambda c: int(c.split('_')[-1]))
        if len(rest_cols_sorted) > 0:
            f_rest = np.stack([vd[c] for c in rest_cols_sorted], axis=-1)
        else:
            f_rest = np.empty((len(vd), 0), dtype=np.float32)

        opacities = vd['opacity']
        scale = np.stack([vd[f"scale_{i}"] for i in range(3)], axis=-1)
        rotation = np.stack([vd[f"rot_{i}"] for i in range(4)], axis=-1)

        splats = {}
        splats["means"] = torch.from_numpy(xyz).float().cuda()
        splats["opacities"] = torch.from_numpy(opacities).float().cuda()
        splats["scales"] = torch.from_numpy(scale).float().cuda()
        splats["quats"] = torch.from_numpy(rotation).float().cuda()

        sh0_tensor = torch.from_numpy(f_dc).float()
        sh0_tensor = sh0_tensor.unsqueeze(-1).transpose(1, 2)
        splats["sh0"] = sh0_tensor.cuda()

        if f_rest.any():
            if f_rest.shape[1] % 3 != 0:
                raise ValueError(f"Number of f_rest columns ({f_rest.shape[1]}) not divisible by 3.")
            num_rest_per_channel = f_rest.shape[1] // 3
            shn_tensor = torch.from_numpy(
                f_rest.reshape(-1, 3, num_rest_per_channel)
            ).float().transpose(1, 2)
            splats["shN"] = shn_tensor.cuda()

        logger.info(f"Loaded {len(splats['means'])} Gaussian splats")
        return splats

    def run_compression(self, compress_dir: str, splats: Dict[str, Tensor]) -> None:
        """
        Run PlayCanvas SOGS compression algorithm.
        Exact implementation from PlayCanvas SOGS repository.
        """
        logger.info("🚀 Running PlayCanvas SOGS compression algorithm")

        # Param-specific preprocessing
        splats["means"] = self.log_transform(splats["means"])
        splats["quats"] = F.normalize(splats["quats"], dim=-1)
        neg_mask = splats["quats"][..., 3] < 0
        splats["quats"][neg_mask] *= -1
        splats["sh0"] = splats["sh0"].clamp(-3.0, 3.0)
        if "shN" in splats:
            splats["shN"] = splats["shN"].clamp(-6.0, 6.0)

        n_gs = len(splats["means"])
        n_sidelen = int(n_gs**0.5)
        n_crop = n_gs - n_sidelen**2
        if n_crop != 0:
            splats = self._crop_n_splats(splats, n_crop)
            logger.info(f"Warning: Number of Gaussians was not square. Removed {n_crop} Gaussians.")

        meta: Dict[str, Any] = {}

        # Sort splats using PLAS
        logger.info("Sorting splats with PLAS...")
        splats = self.sort_splats(splats)

        # Extract opacities and merge into sh0
        opacities = splats.pop("opacities")

        # Compress each parameter
        for param_name in splats.keys():
            logger.info(f"Compressing parameter: {param_name}")
            if param_name == "sh0":
                meta["sh0"] = self._compress_sh0_with_opacity(
                    compress_dir, "sh0", splats["sh0"], opacities, n_sidelen
                )
            else:
                compress_fn = self._get_compress_fn(param_name)
                meta[param_name] = compress_fn(
                    compress_dir, param_name, splats[param_name], n_sidelen=n_sidelen
                )

        # Save metadata
        with open(os.path.join(compress_dir, "meta.json"), "w") as f:
            json.dump(meta, f, indent=2)
        
        logger.info("✅ PlayCanvas SOGS compression completed")

    def log_transform(self, x):
        """Log transform from PlayCanvas SOGS"""
        return torch.sign(x) * torch.log1p(torch.abs(x))

    def write_image(self, compress_dir, param_name, img, lossless: bool = True, quality: int = 100):
        """
        Compresses the image as lossless webp.
        Exact implementation from PlayCanvas SOGS repository.
        """
        filename = f"{param_name}.webp"
        Image.fromarray(img).save(
            os.path.join(compress_dir, filename),
            format="webp",
            lossless=lossless,
            quality=quality if not lossless else 100,
            method=6,
            exact=True
        )
        logger.info(f"✓ {filename}")
        return filename

    def _crop_n_splats(self, splats: Dict[str, Tensor], n_crop: int) -> Dict[str, Tensor]:
        """Crop lowest opacity splats"""
        opacities = splats["opacities"]
        keep_indices = torch.argsort(opacities, descending=True)[:-n_crop]
        for k, v in splats.items():
            splats[k] = v[keep_indices]
        return splats

    def _get_compress_fn(self, param_name: str) -> Callable:
        """Get compression function for parameter"""
        compress_fn_map = {
            "means": self._compress_16bit,
            "scales": self._compress,
            "quats": self._compress_quats,
            "sh0": self._compress,  # placeholder, actual handling in run_compression
            "shN": self._compress_kmeans,
        }
        return compress_fn_map[param_name]

    def _compress(self, compress_dir: str, param_name: str, params: Tensor, n_sidelen: int) -> Dict[str, Any]:
        """Compress parameters with 8-bit quantization and lossless WebP compression."""
        grid = params.reshape((n_sidelen, n_sidelen, -1))
        mins = torch.amin(grid, dim=(0, 1))
        maxs = torch.amax(grid, dim=(0, 1))
        grid_norm = (grid - mins) / (maxs - mins)
        img_norm = grid_norm.detach().cpu().numpy()

        img = (img_norm * (2**8 - 1)).round().astype(np.uint8)
        img = img.squeeze()

        meta = {
            "shape": list(params.shape),
            "dtype": str(params.dtype).split(".")[1],
            "mins": mins.tolist(),
            "maxs": maxs.tolist(),
            "files": [self.write_image(compress_dir, param_name, img)]
        }
        return meta

    def _compress_16bit(self, compress_dir: str, param_name: str, params: Tensor, n_sidelen: int) -> Dict[str, Any]:
        """Compress parameters with 16-bit quantization and WebP compression."""
        grid = params.reshape((n_sidelen, n_sidelen, -1))
        mins = torch.amin(grid, dim=(0, 1))
        maxs = torch.amax(grid, dim=(0, 1))
        grid_norm = (grid - mins) / (maxs - mins)
        img_norm = grid_norm.detach().cpu().numpy()
        img = (img_norm * (2**16 - 1)).round().astype(np.uint16)
        img_l = img & 0xFF
        img_u = (img >> 8) & 0xFF

        meta = {
            "shape": list(params.shape),
            "dtype": str(params.dtype).split(".")[1],
            "mins": mins.tolist(),
            "maxs": maxs.tolist(),
            "files": [
                self.write_image(compress_dir, f"{param_name}_l", img_l.astype(np.uint8)),
                self.write_image(compress_dir, f"{param_name}_u", img_u.astype(np.uint8))
            ]
        }
        return meta

    def _compress_sh0_with_opacity(self, compress_dir: str, param_name: str, sh0: Tensor, opacities: Tensor, n_sidelen: int) -> Dict[str, Any]:
        """Combine sh0 (RGB) and opacities as alpha channel into a single RGBA texture."""
        # Reshape to spatial grid
        grid_sh0 = sh0.reshape((n_sidelen, n_sidelen, -1))
        grid_opac = opacities.reshape((n_sidelen, n_sidelen, 1))
        grid = torch.cat([grid_sh0, grid_opac], dim=-1)

        mins = torch.amin(grid, dim=(0, 1))
        maxs = torch.amax(grid, dim=(0, 1))
        grid_norm = (grid - mins) / (maxs - mins)
        img_norm = grid_norm.detach().cpu().numpy()

        img = (img_norm * (2**8 - 1)).round().astype(np.uint8)
        filename = self.write_image(compress_dir, param_name, img)

        meta = {
            # New channel count = original 3 + opacity = 4
            "shape": [*list(sh0.shape[:-1]), sh0.shape[-1] + 1],
            "dtype": str(sh0.dtype).split(".")[1],
            "mins": mins.tolist(),
            "maxs": maxs.tolist(),
            "files": [filename]
        }
        return meta

    def _compress_kmeans(self, compress_dir: str, param_name: str, params: Tensor, n_sidelen: int, quantization: int = 8) -> Dict[str, Any]:
        """Run K-means clustering on parameters and save centroids and labels as images."""
        params = params.reshape(params.shape[0], -1)
        dim = params.shape[1]
        n_clusters = round((len(params) >> 2) / 64) * 64
        n_clusters = min(n_clusters, 2 ** 16)

        kmeans = KMeans(n_clusters=n_clusters, distance="manhattan", verbose=True)
        labels = kmeans.fit(params.permute(1, 0).contiguous())
        labels = labels.detach().cpu().numpy()
        centroids = kmeans.centroids.permute(1, 0)

        mins = torch.min(centroids)
        maxs = torch.max(centroids)
        centroids_norm = (centroids - mins) / (maxs - mins)
        centroids_norm = centroids_norm.detach().cpu().numpy()
        centroids_quant = (
            (centroids_norm * (2**quantization - 1)).round().astype(np.uint8)
        )

        # sort centroids for compact atlas layout
        sorted_indices = np.lexsort(centroids_quant.T)
        sorted_indices = sorted_indices.reshape(64, -1).T.reshape(-1)
        sorted_centroids_quant = centroids_quant[sorted_indices]
        inverse = np.argsort(sorted_indices)

        centroids_packed = sorted_centroids_quant.reshape(-1, int(dim * 64 / 3), 3)
        labels = inverse[labels].astype(np.uint16).reshape((n_sidelen, n_sidelen))
        labels_l = labels & 0xFF
        labels_u = (labels >> 8) & 0xFF

        # Combine low and high bytes into single texture: R=labels_l, G=labels_u, B=0
        labels_combined = np.zeros((n_sidelen, n_sidelen, 3), dtype=np.uint8)
        labels_combined[..., 0] = labels_l.astype(np.uint8)
        labels_combined[..., 1] = labels_u.astype(np.uint8)

        meta = {
            "shape": list(params.shape),
            "dtype": str(params.dtype).split(".")[1],
            "mins": mins.tolist(),
            "maxs": maxs.tolist(),
            "quantization": quantization,
            "files": [
                self.write_image(compress_dir, f"{param_name}_centroids", centroids_packed),
                self.write_image(compress_dir, f"{param_name}_labels", labels_combined)
            ]
        }
        return meta

    def pack_quaternion_to_rgba_tensor(self, q: Tensor) -> Tensor:
        """
        Packs a batch of quaternions into RGBA channels.
        Exact implementation from PlayCanvas SOGS repository.
        """
        abs_q = q.abs()
        max_idx = abs_q.argmax(dim=-1)  # (...)

        # ensure largest component is positive
        max_vals = q.gather(-1, max_idx.unsqueeze(-1)).squeeze(-1)
        sign = max_vals.sign()
        sign[sign == 0] = 1
        q_signed = q * sign.unsqueeze(-1)

        # build variants dropping each component
        variants = []
        for i in range(4):
            dims = list(range(4))
            dims.remove(i)
            variants.append(q_signed[..., dims])  # (...,3)
        stacked = torch.stack(variants, dim=-2)  # (...,4,3)

        # select the appropriate 3-vector based on max_idx
        idx_exp = max_idx.unsqueeze(-1).unsqueeze(-1).expand(*max_idx.shape, 1, 3)
        small = torch.gather(stacked, dim=-2, index=idx_exp).squeeze(-2)  # (...,3)

        # scale by sqrt(2) to normalize range to [-1,1]
        small = small * torch.sqrt(torch.tensor(2.0, device=small.device, dtype=small.dtype))

        # map from [-1,1] to [0,1]
        rgb = small * 0.5 + 0.5
        a = (252.0 + max_idx.to(torch.float32)) / 255.0
        return torch.cat([rgb, a.unsqueeze(-1)], dim=-1)

    def _compress_quats(self, compress_dir: str, param_name: str, params: Tensor, n_sidelen: int) -> Dict[str, Any]:
        """Compress quaternions by packing into RGBA and saving as an 8-bit image."""
        # params: (n_splats,4)
        rgba = self.pack_quaternion_to_rgba_tensor(params)
        img = (rgba.view(n_sidelen, n_sidelen, 4).cpu().numpy() * 255.0).round().astype(np.uint8)
        filename = self.write_image(compress_dir, f"{param_name}", img)

        meta = {
            "shape": list(params.shape),
            "dtype": "uint8",
            "encoding": "quaternion_packed",
            "files": [filename]
        }
        return meta

    def sort_splats(self, splats: Dict[str, Tensor], verbose: bool = True) -> Dict[str, Tensor]:
        """
        Sort splats with Parallel Linear Assignment Sorting from the paper.
        Exact implementation from PlayCanvas SOGS repository.
        """
        n_gs = len(splats["means"])
        n_sidelen = int(n_gs**0.5)
        assert n_sidelen**2 == n_gs, "Must be a perfect square"

        sort_keys = [k for k in splats if k != "shN"]
        params_to_sort = torch.cat([splats[k].reshape(n_gs, -1) for k in sort_keys], dim=-1)
        shuffled_indices = torch.randperm(
            params_to_sort.shape[0], device=params_to_sort.device
        )
        params_to_sort = params_to_sort[shuffled_indices]
        grid = params_to_sort.reshape((n_sidelen, n_sidelen, -1))
        _, sorted_indices = sort_with_plas(
            grid.permute(2, 0, 1), improvement_break=1e-4, verbose=verbose
        )
        sorted_indices = sorted_indices.squeeze().flatten()
        sorted_indices = shuffled_indices[sorted_indices]
        for k, v in splats.items():
            splats[k] = v[sorted_indices]
        return splats

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
            
            # Compress using PlayCanvas SOGS
            results = self.compress_gaussian_splats(ply_files, self.output_dir)
            
            # Save compression summary
            summary_path = os.path.join(self.output_dir, "compression_summary.json")
            with open(summary_path, 'w') as f:
                json.dump(results, f, indent=2, cls=NumpyEncoder)
            
            logger.info(f"✅ PlayCanvas SOGS compression completed successfully")
            logger.info(f"📊 Overall compression ratio: {results['overall_compression_ratio']:.2f}x")
            logger.info(f"📁 Output files: {results['total_output_files']}")
            
        except Exception as e:
            logger.error(f"Compression job failed: {e}")
            raise

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
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        return super().default(obj)

if __name__ == "__main__":
    compressor = PlayCanvasSOGSCompressor()
    compressor.process_job() 