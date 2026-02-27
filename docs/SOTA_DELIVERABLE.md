# SOTA Deliverable

## Deliverable
- A reproducible NDVS-gated SOTA loop for 3DGS improvements with auditable artifacts per run.
- Promotion decisions are based only on NDVS scorecards (`parity`, `progress`, `frontier`) plus orientation reliability checks.
- Every ablation is tracked with: knob changed, commit SHA, NDVS run URL/ID, and metric delta vs baseline.

## Runbook

### Trigger NDVS
1. Update `benchmarks/ndvs/trigger-run.txt` with a new timestamped line.
2. Commit and push on an `agent-*` branch.
3. Watch runs:
   - `gh run list --branch <branch>`
   - `gh run watch <run-id> --exit-status`

### Where Artifacts Land
- GitHub artifact name pattern: `ndvs-benchmark-<run_id>-<attempt>`.
- Artifact path contents:
  - `logs/ndvs/<run_id>-<attempt>/ndvs_results.json`
  - `logs/ndvs/<run_id>-<attempt>/scorecard.json`
- Optional local mirror path used in this repo:
  - `logs/ndvs-artifacts/run-<run_id>/...`

### How To Interpret `scorecard.json`
- `aggregates`: control metrics for selected subset (`psnr`, `ssim`, `lpips`, `time`, `max_gpu_memory`).
- `deltas`: difference vs configured baseline in `benchmarks/ndvs/benchmark_config.json`.
- `gate.passed`: authoritative pass/fail for the selected gate.
- `gate.checks[]`: per-threshold outcomes.

### Gate Semantics
- `parity`: reliability gate for push-triggered NDVS runs.
- `progress`: quality improvement target on `control9`.
- `frontier`: aggressive SOTA target with bounded cost increase.

### Promotion Rule
- Only promote an ablation when NDVS gate passes and no orientation failures are reported.
