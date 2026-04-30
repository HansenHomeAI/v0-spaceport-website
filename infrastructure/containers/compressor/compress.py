#!/usr/bin/env python3
"""
Spaceport SuperSplat compression container.

The current PlayCanvas path for large streamed scenes is `@playcanvas/splat-transform`,
not the archived `playcanvas/sogs` package. This entrypoint keeps the existing SageMaker
contract, but now generates:

- `supersplat_bundle/meta.json` for single-bundle fallback loading
- `supersplat_bundle/lod-meta.json` plus chunk directories for streamed LOD loading
"""

from __future__ import annotations

import json
import logging
import os
import shlex
import shutil
import subprocess
import sys
import tarfile
import tempfile
import zipfile
from pathlib import Path
from typing import Any, Dict, Iterable, List, Sequence

try:
    import boto3
except ModuleNotFoundError:  # pragma: no cover - local smoke environments can omit boto3.
    boto3 = None


logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

SKYBOX_SOURCE_ASSET_NAME = "kloppenheim_06_puresky_equirect.png"
SKYBOX_SOURCE_BUNDLE_RELATIVE_PATH = f"skybox/{SKYBOX_SOURCE_ASSET_NAME}"
SKYBOX_GENERATED_ASSET_NAME = "kloppenheim_06_puresky_equirect.webp"
SKYBOX_BUNDLE_RELATIVE_PATH = f"skybox/{SKYBOX_GENERATED_ASSET_NAME}"
SKYBOX_WEBP_QUALITY = 80
CONTAINER_SKYBOX_SOURCE = Path(__file__).resolve().parent / "assets" / "skybox" / SKYBOX_SOURCE_ASSET_NAME

DEFAULT_LOD_DECIMATION = ("30%", "10%", "3%")
DEFAULT_LOD_CHUNK_COUNT = 1024
DEFAULT_LOD_CHUNK_EXTENT = 32
DEFAULT_SOG_SETTINGS = {
    "background": {"color": [0, 0, 0, 1]},
    "camera": {
        "fov": 60,
        "position": [0, 0.5, -2],
        "target": [0, 0, 0],
        "startAnim": "orbit",
    },
}


class InputSource:
    def __init__(self, kind: str, path: Path, root: Path, supporting_files: list[Path] | None = None):
        self.kind = kind
        self.path = path
        self.root = root
        self.supporting_files = list(supporting_files or [])


def _convert_skybox_to_webp(source_path: Path, destination_path: Path) -> bool:
    if source_path.suffix.lower() == ".webp":
        shutil.copy2(source_path, destination_path)
        return True

    try:
        subprocess.run(
            [
                "cwebp",
                "-quiet",
                "-q",
                str(SKYBOX_WEBP_QUALITY),
                str(source_path),
                "-o",
                str(destination_path),
            ],
            check=True,
            capture_output=True,
            text=True,
        )
        return True
    except (FileNotFoundError, subprocess.CalledProcessError) as exc:
        logger.warning("Failed to convert bundled skybox to WebP: %s", exc)
        return False


def _bundle_skybox_asset(bundle_dir: Path) -> str | None:
    if not CONTAINER_SKYBOX_SOURCE.exists():
        logger.warning("Bundled skybox asset not found at %s", CONTAINER_SKYBOX_SOURCE)
        return None

    skybox_dir = bundle_dir / "skybox"
    skybox_dir.mkdir(parents=True, exist_ok=True)
    generated_destination = skybox_dir / SKYBOX_GENERATED_ASSET_NAME
    if _convert_skybox_to_webp(CONTAINER_SKYBOX_SOURCE, generated_destination):
        logger.info("Bundled optimized skybox %s into SuperSplat bundle", SKYBOX_GENERATED_ASSET_NAME)
        return SKYBOX_BUNDLE_RELATIVE_PATH

    fallback_destination = skybox_dir / SKYBOX_SOURCE_ASSET_NAME
    shutil.copy2(CONTAINER_SKYBOX_SOURCE, fallback_destination)
    logger.info("Bundled fallback skybox %s into SuperSplat bundle", SKYBOX_SOURCE_ASSET_NAME)
    return SKYBOX_SOURCE_BUNDLE_RELATIVE_PATH


def _count_tree_nodes(node: dict[str, Any] | None) -> int:
    if not isinstance(node, dict):
        return 0
    children = node.get("children")
    if not isinstance(children, list) or not children:
        return 1 if isinstance(node.get("lods"), dict) else 0
    return sum(_count_tree_nodes(child) for child in children)


class PlayCanvasSOGSCompressor:
    """SageMaker entrypoint that builds streamed SuperSplat bundles via splat-transform."""

    def __init__(self):
        self.s3_client = boto3.client("s3") if boto3 else None
        self.input_dir = "/opt/ml/processing/input"
        self.output_dir = "/opt/ml/processing/output"
        self.device = (os.environ.get("SOGS_DEVICE") or "cpu").strip() or "cpu"
        self.lod_decimation = self._read_lod_decimation()
        self.lod_chunk_count = int(os.environ.get("SOGS_LOD_CHUNK_COUNT", DEFAULT_LOD_CHUNK_COUNT))
        self.lod_chunk_extent = int(os.environ.get("SOGS_LOD_CHUNK_EXTENT", DEFAULT_LOD_CHUNK_EXTENT))
        self.transform_bin = self._resolve_transform_bin()
        self.version = self._get_splat_transform_version()
        logger.info(
            "Using splat-transform %s (device=%s, lod_decimation=%s, chunk_count=%sK, chunk_extent=%s)",
            self.version,
            self.device,
            ",".join(self.lod_decimation),
            self.lod_chunk_count,
            self.lod_chunk_extent,
        )

    def _resolve_transform_bin(self) -> list[str]:
        override = (os.environ.get("SPLAT_TRANSFORM_BIN") or "").strip()
        if override:
            return shlex.split(override)
        return ["splat-transform"]

    def _read_lod_decimation(self) -> list[str]:
        raw = (os.environ.get("SOGS_LOD_DECIMATION") or "").strip()
        if not raw:
            return list(DEFAULT_LOD_DECIMATION)
        values = [value.strip() for value in raw.split(",") if value.strip()]
        return values or list(DEFAULT_LOD_DECIMATION)

    def _run_command(
        self,
        command: Sequence[str],
        *,
        cwd: Path | None = None,
        timeout: int = 3600,
        log_stdout: bool = True,
    ) -> subprocess.CompletedProcess[str]:
        logger.info("Executing: %s", " ".join(shlex.quote(part) for part in command))
        result = subprocess.run(
            list(command),
            cwd=str(cwd) if cwd else None,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
        if result.returncode != 0:
            logger.error("Command failed (%s): %s", result.returncode, " ".join(command))
            if result.stdout:
                logger.error("STDOUT:\n%s", result.stdout)
            if result.stderr:
                logger.error("STDERR:\n%s", result.stderr)
            raise RuntimeError(f"Command failed with exit code {result.returncode}: {' '.join(command)}")
        if log_stdout and result.stdout.strip():
            logger.info(result.stdout.strip())
        if result.stderr.strip():
            logger.info(result.stderr.strip())
        return result

    def _get_splat_transform_version(self) -> str:
        try:
            result = self._run_command([*self.transform_bin, "--version"], timeout=30, log_stdout=False)
        except Exception:
            return "unknown"
        output = (result.stdout or result.stderr).strip()
        return output.splitlines()[0].strip() if output else "unknown"

    def _extract_archive(self, archive_path: Path, destination: Path) -> None:
        destination.mkdir(parents=True, exist_ok=True)
        if archive_path.name.endswith(".tar.gz"):
            with tarfile.open(archive_path, "r:gz") as tar:
                self._safe_extract_tar(tar, destination)
            return
        if archive_path.suffix.lower() == ".zip":
            with zipfile.ZipFile(archive_path, "r") as zip_file:
                zip_file.extractall(destination)
            return
        raise ValueError(f"Unsupported archive type: {archive_path}")

    def _safe_extract_tar(self, tar: tarfile.TarFile, destination: Path) -> None:
        dest_root = destination.resolve()
        for member in tar.getmembers():
            member_path = (destination / member.name).resolve()
            if not str(member_path).startswith(str(dest_root)):
                raise ValueError(f"Unsafe archive member path: {member.name}")
        tar.extractall(destination)

    def _scan_root_for_inputs(self, root: Path) -> tuple[list[Path], list[Path], list[Path]]:
        lcc_files: list[Path] = []
        ply_files: list[Path] = []
        supporting_files: list[Path] = []
        for path in root.rglob("*"):
            if not path.is_file():
                continue
            lower_name = path.name.lower()
            lower_path = str(path).lower()
            if lower_name == "training_metadata.json":
                supporting_files.append(path)
            if path.suffix.lower() == ".lcc":
                lcc_files.append(path)
            elif path.suffix.lower() == ".ply" and "__macosx" not in lower_path:
                ply_files.append(path)
        return lcc_files, ply_files, supporting_files

    def _pick_best_input(self, files: list[Path], *, kind: str) -> Path:
        def rank(path: Path) -> tuple[int, int, str]:
            name = path.name.lower()
            if kind == "lcc":
                preferred = 0 if name.endswith(".lcc") else 1
            else:
                if name == "splat.ply":
                    preferred = 0
                elif "final_model" in name:
                    preferred = 1
                else:
                    preferred = 2
            try:
                size = -path.stat().st_size
            except OSError:
                size = 0
            return (preferred, size, str(path))

        return sorted(files, key=rank)[0]

    def _discover_input_source(self) -> InputSource:
        input_root = Path(self.input_dir)
        extraction_root = input_root / "__extracted_archives"
        extraction_root.mkdir(parents=True, exist_ok=True)

        archives = sorted(
            [
                path
                for path in input_root.rglob("*")
                if path.is_file() and (path.name.endswith(".tar.gz") or path.suffix.lower() == ".zip")
            ]
        )
        for index, archive in enumerate(archives):
            destination = extraction_root / f"{index:02d}-{archive.stem.replace('.', '-')}"
            logger.info("Extracting archive %s -> %s", archive, destination)
            self._extract_archive(archive, destination)

        search_roots = [input_root]
        if extraction_root.exists():
            search_roots.extend([path for path in extraction_root.iterdir() if path.is_dir()])

        lcc_candidates: list[tuple[Path, Path, list[Path]]] = []
        ply_candidates: list[tuple[Path, Path, list[Path]]] = []
        for root in search_roots:
            lcc_files, ply_files, supporting_files = self._scan_root_for_inputs(root)
            for path in lcc_files:
                lcc_candidates.append((path, root, supporting_files))
            for path in ply_files:
                ply_candidates.append((path, root, supporting_files))

        if lcc_candidates:
            best = self._pick_best_input([entry[0] for entry in lcc_candidates], kind="lcc")
            for candidate, root, supporting_files in lcc_candidates:
                if candidate == best:
                    return InputSource("lcc", candidate, root, supporting_files)

        if ply_candidates:
            best = self._pick_best_input([entry[0] for entry in ply_candidates], kind="ply")
            for candidate, root, supporting_files in ply_candidates:
                if candidate == best:
                    return InputSource("ply", candidate, root, supporting_files)

        raise RuntimeError(f"No .lcc or .ply source found under {self.input_dir}")

    def _copy_supporting_files(self, supporting_files: Iterable[Path], bundle_dir: Path) -> list[str]:
        copied: list[str] = []
        for path in supporting_files:
            destination = bundle_dir / path.name
            if destination.exists():
                continue
            shutil.copy2(path, destination)
            copied.append(path.name)
        return copied

    def _validate_ply_for_sogs(self, ply_file: str) -> bool:
        try:
            with open(ply_file, "rb") as file_obj:
                header = file_obj.read(4096).decode("utf-8", errors="ignore")
            required_fields = ["f_dc_0", "f_dc_1", "f_dc_2", "opacity", "scale_0", "scale_1", "scale_2"]
            missing = [field for field in required_fields if field not in header]
            if missing:
                logger.error("Missing required PLY fields %s in %s", missing, ply_file)
                return False
            return True
        except Exception as exc:
            logger.error("Failed to validate PLY file %s: %s", ply_file, exc)
            return False

    def _build_single_bundle(self, source: Path, bundle_dir: Path) -> None:
        bundle_dir.mkdir(parents=True, exist_ok=True)
        output = bundle_dir / "meta.json"
        if source.suffix.lower() == ".lcc":
            command = [*self.transform_bin, "-w", "-g", self.device, "-O", "0", str(source), str(output)]
        else:
            command = [*self.transform_bin, "-w", "-g", self.device, str(source), str(output)]
        self._run_command(command)

    def _build_lod_inputs_from_ply(self, source: Path, work_dir: Path) -> list[tuple[int, Path]]:
        work_dir.mkdir(parents=True, exist_ok=True)
        lod_inputs: list[tuple[int, Path]] = [(0, source)]
        for level, decimation in enumerate(self.lod_decimation, start=1):
            output = work_dir / f"lod{level}.ply"
            command = [*self.transform_bin, "-w", str(source), "-F", decimation, str(output)]
            self._run_command(command)
            lod_inputs.append((level, output))
        return lod_inputs

    def _build_lod_bundle_from_lcc(self, source: Path, bundle_dir: Path) -> None:
        bundle_dir.mkdir(parents=True, exist_ok=True)
        levels = ",".join(str(level) for level in range(len(self.lod_decimation) + 1))
        command = [
            *self.transform_bin,
            "-w",
            "-g",
            self.device,
            "-O",
            levels,
            "-C",
            str(self.lod_chunk_count),
            "-X",
            str(self.lod_chunk_extent),
            str(source),
            str(bundle_dir / "lod-meta.json"),
        ]
        self._run_command(command, timeout=7200)

    def _build_lod_bundle_from_inputs(self, lod_inputs: Sequence[tuple[int, Path]], bundle_dir: Path) -> None:
        bundle_dir.mkdir(parents=True, exist_ok=True)
        command = [
            *self.transform_bin,
            "-w",
            "-g",
            self.device,
            "-C",
            str(self.lod_chunk_count),
            "-X",
            str(self.lod_chunk_extent),
        ]
        for level, path in lod_inputs:
            command.extend([str(path), "-l", str(level)])
        command.append(str(bundle_dir / "lod-meta.json"))
        self._run_command(command, timeout=7200)

    def _collect_bundle_metrics(self, bundle_dir: Path) -> dict[str, Any]:
        metrics: dict[str, Any] = {
            "bundleDir": str(bundle_dir),
            "fileCount": 0,
            "bundleSizeBytes": 0,
            "hasMetaJson": False,
            "hasLodMetaJson": False,
            "splatCount": None,
            "lodLevels": None,
            "chunkFiles": 0,
            "lodTreeNodes": 0,
            "bounds": None,
        }

        if not bundle_dir.exists():
            return metrics

        files = [path for path in bundle_dir.rglob("*") if path.is_file()]
        metrics["fileCount"] = len(files)
        metrics["bundleSizeBytes"] = sum(path.stat().st_size for path in files)

        meta_path = bundle_dir / "meta.json"
        if meta_path.exists():
            metrics["hasMetaJson"] = True
            try:
                meta = json.loads(meta_path.read_text(encoding="utf-8"))
                shape = meta.get("means", {}).get("shape")
                if isinstance(shape, list) and shape:
                    metrics["splatCount"] = shape[0]
            except json.JSONDecodeError:
                logger.warning("Failed to parse %s", meta_path)

        lod_meta_path = bundle_dir / "lod-meta.json"
        if lod_meta_path.exists():
            metrics["hasLodMetaJson"] = True
            try:
                lod_meta = json.loads(lod_meta_path.read_text(encoding="utf-8"))
                metrics["lodLevels"] = lod_meta.get("lodLevels")
                filenames = lod_meta.get("filenames")
                if isinstance(filenames, list):
                    metrics["chunkFiles"] = len(filenames)
                tree = lod_meta.get("tree")
                metrics["lodTreeNodes"] = _count_tree_nodes(tree)
                if isinstance(tree, dict) and isinstance(tree.get("bound"), dict):
                    metrics["bounds"] = tree["bound"]
            except json.JSONDecodeError:
                logger.warning("Failed to parse %s", lod_meta_path)

        return metrics

    def compress_gaussian_splats(self, input_sources: List[str], output_dir: str) -> Dict[str, Any]:
        if not input_sources:
            raise ValueError("compress_gaussian_splats requires at least one input source")

        source = Path(input_sources[0])
        bundle_source_dir = Path(output_dir) / "generated_bundle"
        bundle_source_dir.mkdir(parents=True, exist_ok=True)

        if source.suffix.lower() == ".lcc":
            self._build_single_bundle(source, bundle_source_dir)
            self._build_lod_bundle_from_lcc(source, bundle_source_dir)
        else:
            if not self._validate_ply_for_sogs(str(source)):
                raise RuntimeError(f"PLY file is not compatible with splat-transform SOG output: {source}")
            self._build_single_bundle(source, bundle_source_dir)
            lod_inputs = self._build_lod_inputs_from_ply(source, Path(output_dir) / "lod_inputs")
            self._build_lod_bundle_from_inputs(lod_inputs, bundle_source_dir)

        metrics = self._collect_bundle_metrics(bundle_source_dir)
        original_size = source.stat().st_size
        compressed_size = metrics["bundleSizeBytes"]
        ratio = round(original_size / compressed_size, 4) if compressed_size else None

        return {
            "method": "playcanvas_splat_transform",
            "version": self.version,
            "gpu_accelerated": self.device != "cpu",
            "device": self.device,
            "lodDecimation": list(self.lod_decimation),
            "lodChunkCount": self.lod_chunk_count,
            "lodChunkExtent": self.lod_chunk_extent,
            "input_files": input_sources,
            "bundle_source_dir": str(bundle_source_dir),
            "compressed_outputs": [
                {
                    "input_file": str(source),
                    "output_dir": str(bundle_source_dir),
                    "original_size_mb": round(original_size / (1024 * 1024), 3),
                    "compressed_size_mb": round(compressed_size / (1024 * 1024), 3),
                    "compression_ratio": ratio,
                }
            ],
            "overall_compression_ratio": ratio,
            "bundle_metrics": metrics,
        }

    def _create_supersplat_bundle(self, results: Dict[str, Any]) -> None:
        source_dir_value = results.get("bundle_source_dir")
        if source_dir_value:
            source_dir = Path(source_dir_value)
        else:
            outputs = results.get("compressed_outputs") or []
            if not outputs:
                raise ValueError("No compressed outputs to package")
            source_dir = Path(outputs[0]["output_dir"])

        bundle_dir = Path(self.output_dir) / "supersplat_bundle"
        if bundle_dir.exists():
            shutil.rmtree(bundle_dir)
        bundle_dir.mkdir(parents=True, exist_ok=True)

        for path in source_dir.rglob("*"):
            relative = path.relative_to(source_dir)
            destination = bundle_dir / relative
            if path.is_dir():
                destination.mkdir(parents=True, exist_ok=True)
            else:
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(path, destination)

        skybox_manifest_path = _bundle_skybox_asset(bundle_dir)

        with open(bundle_dir / "settings.json", "w", encoding="utf-8") as file_obj:
            json.dump(DEFAULT_SOG_SETTINGS, file_obj, indent=2)

        bundle_metrics = self._collect_bundle_metrics(bundle_dir)
        entrypoints: dict[str, Any] = {
            "default": "lod-meta.json" if bundle_metrics["hasLodMetaJson"] else "meta.json",
            "fallback": "meta.json" if bundle_metrics["hasMetaJson"] else None,
        }
        bundle_manifest = {
            "version": 1,
            "skybox": {"type": "equirect", "path": skybox_manifest_path} if skybox_manifest_path else None,
            "entrypoints": entrypoints,
            "streaming": {
                "enabled": bool(bundle_metrics["hasLodMetaJson"]),
                "lodLevels": bundle_metrics["lodLevels"],
                "chunkFiles": bundle_metrics["chunkFiles"],
                "bounds": bundle_metrics["bounds"],
            },
        }
        with open(bundle_dir / "spaceport_bundle.json", "w", encoding="utf-8") as file_obj:
            json.dump(bundle_manifest, file_obj, indent=2)

    def process_job(self) -> None:
        logger.info("Starting SuperSplat compression job")
        os.makedirs(self.output_dir, exist_ok=True)

        source = self._discover_input_source()
        logger.info("Selected %s source: %s", source.kind, source.path)
        logger.info("Supporting files discovered: %s", [path.name for path in source.supporting_files])

        with tempfile.TemporaryDirectory(prefix="sogs-work-") as temp_dir:
            results = self.compress_gaussian_splats([str(source.path)], temp_dir)
            self._create_supersplat_bundle(results)

        bundle_dir = Path(self.output_dir) / "supersplat_bundle"
        copied_supporting_files = self._copy_supporting_files(source.supporting_files, bundle_dir)
        results["copied_supporting_files"] = copied_supporting_files
        results["source_kind"] = source.kind
        results["source_path"] = str(source.path)
        results["bundle_metrics"] = self._collect_bundle_metrics(bundle_dir)

        summary_path = Path(self.output_dir) / "sogs_compression_summary.json"
        with open(summary_path, "w", encoding="utf-8") as file_obj:
            json.dump(results, file_obj, indent=2)

        logger.info("Compression complete")
        logger.info("Bundle output: %s", bundle_dir)
        logger.info("Bundle metrics: %s", json.dumps(results["bundle_metrics"], indent=2))


if __name__ == "__main__":
    try:
        PlayCanvasSOGSCompressor().process_job()
    except Exception as exc:
        logger.error("Compression job failed: %s", exc)
        sys.exit(1)
