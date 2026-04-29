#!/usr/bin/env bash
set -euo pipefail

work=/opt/ml/processing/work
mkdir -p "$work/historical" "$work/replacement" "$work/artifact" /opt/ml/processing/output/artifact

hist=$(find /opt/ml/processing/input/historical -name 'model.tar.gz' | head -n 1)
rep=$(find /opt/ml/processing/input/replacement -name 'model.tar.gz' | head -n 1)

tar -xzf "$hist" -C "$work/historical"
tar -xzf "$rep" -C "$work/replacement"

python3 /opt/ml/processing/input/scripts/build_md1_hybrid_artifact.py \
  --historical-root "$work/historical" \
  --replacement-root "$work/replacement" \
  --output-dir "$work/artifact" \
  --replacement-tile tile_00 \
  --replacement-tile tile_02 \
  --replacement-tile tile_04 \
  --replacement-tile tile_05 \
  --replacement-tile tile_06 \
  --replacement-mode replace \
  --opacity-policy none \
  --preserve-context-tile tile_00 \
  --preserve-context-tile tile_01 \
  --preserve-context-tile tile_02 \
  --preserve-context-tile tile_04 \
  --preserve-context-tile tile_05 \
  --preserve-context-tile tile_06 \
  --force-overlap-tile tile_04 \
  --context-padding-ratio 0.0 \
  --merge-mode support_weighted_overlap \
  --label r5_teacher_context_v12_tile04overlap_v13 \
  --purpose 'Start from V12 best blocked repair and force ownership of tile_04 overlap candidates to test whether the 8200 dropped horizon-owner teacher gaussians close the remaining horizon PSNR-only miss.' \
  > /opt/ml/processing/output/artifact/build_stdout.json

cp "$work/artifact/model.tar.gz" /opt/ml/processing/output/artifact/model.tar.gz
cp "$work/artifact/hybrid_summary.json" /opt/ml/processing/output/artifact/hybrid_summary.json
cp "$work/artifact/training_metadata.json" /opt/ml/processing/output/artifact/training_metadata.json
cp "$work/artifact/tiled_pipeline_summary.json" /opt/ml/processing/output/artifact/tiled_pipeline_summary.json
mkdir -p /opt/ml/processing/output/artifact/merged
cp "$work/artifact/merged/merge_report.json" /opt/ml/processing/output/artifact/merged/merge_report.json
