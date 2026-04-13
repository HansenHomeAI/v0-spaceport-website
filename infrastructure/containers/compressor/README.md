# SuperSplat Compression Container

## Overview
This container uses `@playcanvas/splat-transform` to generate the current PlayCanvas
SOG output formats:

- `meta.json` for single-bundle fallback loading
- `lod-meta.json` plus chunk directories for streamed LOD loading

The SageMaker entrypoint remains `python3 /opt/ml/code/compress.py`.

## Input and Output
- Input: `.lcc`, `.ply`, `.tar.gz`, or `.zip`
- Output: `supersplat_bundle/` containing `meta.json`, `lod-meta.json`, chunk folders, viewer settings, and skybox metadata

## Defaults
- Device: CPU
- LOD decimation: `30%,10%,3%`
- Chunk count: `1024` (thousands of splats)
- Chunk extent: `32`

Override with:
- `SOGS_DEVICE`
- `SOGS_LOD_DECIMATION`
- `SOGS_LOD_CHUNK_COUNT`
- `SOGS_LOD_CHUNK_EXTENT`
- `SPLAT_TRANSFORM_BIN`

## Local smoke check
```bash
docker build -t spaceport/compressor:local infrastructure/containers/compressor
docker run --rm spaceport/compressor:local splat-transform --version
```
