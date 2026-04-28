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
  --replacement-tile tile_02 \
  --replacement-tile tile_04 \
  --replacement-tile tile_06 \
  --replacement-mode replace \
  --opacity-policy none \
  --preserve-context-tile tile_02 \
  --preserve-context-tile tile_04 \
  --preserve-context-tile tile_06 \
  --context-padding-ratio 0.0 \
  --merge-mode support_weighted_overlap \
  --label r5_teacher_context_020406 \
  --purpose 'Repair R5 smoke horizon regression by restoring promoted teacher/context splats for the strongest R5 horizon-support tiles before any promotion.' \
  > /opt/ml/processing/output/artifact/build_stdout.json

cp "$work/artifact/model.tar.gz" /opt/ml/processing/output/artifact/model.tar.gz
cp "$work/artifact/hybrid_summary.json" /opt/ml/processing/output/artifact/hybrid_summary.json
cp "$work/artifact/training_metadata.json" /opt/ml/processing/output/artifact/training_metadata.json
cp "$work/artifact/tiled_pipeline_summary.json" /opt/ml/processing/output/artifact/tiled_pipeline_summary.json
mkdir -p /opt/ml/processing/output/artifact/merged
cp "$work/artifact/merged/merge_report.json" /opt/ml/processing/output/artifact/merged/merge_report.json
