#!/usr/bin/env bash
set -euo pipefail

INPUT="${MD1_SOURCE_PLY:-/opt/ml/processing/input/merged_splat.ply}"
SKYBOX_INPUT="${MD1_SOURCE_SKYBOX:-/opt/ml/processing/input/background_skybox.webp}"
SOURCE_LABEL="${MD1_SOURCE_LINEAGE_LABEL:-md1-v18-promoted-raw-ply}"
WORK="${MD1_WORK_DIR:-/opt/ml/processing/work}"
OUT="${MD1_OUTPUT_BUNDLE_DIR:-/opt/ml/processing/output/supersplat_bundle}"
DEVICE="${SOGS_DEVICE:-cpu}"
LOD_DECIMATION="${SOGS_LOD_DECIMATION:-30%,10%,3%}"
LOD_CHUNK_COUNT="${SOGS_LOD_CHUNK_COUNT:-256}"
LOD_CHUNK_EXTENT="${SOGS_LOD_CHUNK_EXTENT:-32}"

mkdir -p "$WORK" "$OUT"
splat-transform --version

IFS=',' read -r -a DECIMATIONS <<< "$LOD_DECIMATION"
LEVEL=1
for DECIMATION in "${DECIMATIONS[@]}"; do
  TRIMMED="$(echo "$DECIMATION" | xargs)"
  if [[ -z "$TRIMMED" ]]; then
    continue
  fi
  splat-transform -w "$INPUT" -F "$TRIMMED" "$WORK/lod${LEVEL}.ply"
  LEVEL=$((LEVEL + 1))
done

COMMAND=(splat-transform -w -g "$DEVICE" -C "$LOD_CHUNK_COUNT" -X "$LOD_CHUNK_EXTENT" "$INPUT" -l 0)
for LOD in $(seq 1 $((LEVEL - 1))); do
  COMMAND+=("$WORK/lod${LOD}.ply" -l "$LOD")
done
COMMAND+=("$OUT/lod-meta.json")
"${COMMAND[@]}"

python3 - <<'PY'
import json
import os
import shutil
from pathlib import Path

root = Path("/opt/ml/processing/output")
bundle = root / "supersplat_bundle"
skybox_input = Path(os.environ.get("MD1_SOURCE_SKYBOX", "/opt/ml/processing/input/background_skybox.webp"))
source_label = os.environ.get("MD1_SOURCE_LINEAGE_LABEL", "md1-v18-promoted-raw-ply")
source_ply = os.environ.get("MD1_SOURCE_PLY", "/opt/ml/processing/input/merged_splat.ply")

skybox = None
if skybox_input.exists():
    skybox_dir = bundle / "skybox"
    skybox_dir.mkdir(parents=True, exist_ok=True)
    skybox_path = skybox_dir / "background_skybox.webp"
    shutil.copyfile(skybox_input, skybox_path)
    skybox = {"type": "equirect", "path": "skybox/background_skybox.webp"}

(bundle / "spaceport_bundle.json").write_text(json.dumps({
    "version": 1,
    "skybox": skybox,
    "entrypoints": {"default": "lod-meta.json", "lod": "lod-meta.json"},
    "streaming": {"enabled": True}
}, indent=2), encoding="utf-8")

(bundle / "settings.json").write_text(json.dumps({
    "camera": {"position": [0, 0, 3], "target": [0, 0, 0]},
    "background": {"type": "skybox" if skybox else "color"}
}, indent=2), encoding="utf-8")

files = [path for path in bundle.rglob("*") if path.is_file()]
summary = {
    "compressor": "@playcanvas/splat-transform",
    "mode": "lod-only",
    "source": source_label,
    "sourcePly": source_ply,
    "skybox": skybox,
    "bundleDir": "supersplat_bundle",
    "lodMeta": "supersplat_bundle/lod-meta.json",
    "fileCount": len(files),
    "bundleSizeBytes": sum(path.stat().st_size for path in files),
}
(root / "sogs_compression_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
PY

find /opt/ml/processing/output -type f -printf "%P %s\n" | sort | tail -200
