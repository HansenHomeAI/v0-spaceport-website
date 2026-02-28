# NDVS Autonomous Benchmark Plan

Updated: 2026-02-26

## Non-Negotiable Operating Rules
- Run all benchmark evaluation through `NDVS` harness only.
- Commit small, reviewable changes frequently (at least once per meaningful step).
- Never build containers locally; container validation must happen through GitHub Actions + CodeBuild.
- Do not promote pipeline changes unless NDVS gate metrics pass.

## Objective Targets
- Control subset: `control9` from `benchmarks/ndvs/benchmark_config.json`
- Baseline reference (`gaussian-splatting` on NDVS snapshot):
  - PSNR: `26.5048`
  - SSIM: `0.8417`
  - LPIPS: `0.2482`
- Promotion gates:
  - `parity` on `primary3`
  - `progress` on `control9`
  - `frontier` on `control9`

## Phase Execution
1. Dataset mirror:
- Use `scripts/benchmarks/ndvs_dataset_mirror.py` to download, normalize, and upload benchmark datasets/manifests to S3.
- Keep scene manifests for reproducibility and drift detection.

2. NDVS benchmark run:
- Execute NDVS method runs on defined subsets.
- Export scene-level result rows containing `method_name`, `dataset_name`, `scene_name`, `psnr`, `ssim`, `lpips`, `time`, `max_gpu_memory`.
- Orchestrate with `scripts/benchmarks/run_ndvs_benchmark.py` (single command for run + gate).
- Optional CI driver: `.github/workflows/ndvs-benchmark.yml` (`workflow_dispatch`).

3. Gate evaluation:
- Run `scripts/benchmarks/ndvs_scorecard.py` against NDVS result rows.
- Enforce `--strict-scenes --fail-on-gate` for promotion.

4. Iterate:
- Change one factor at a time (SfM orientation, densification policy, anti-aliasing, etc.).
- Re-run NDVS and compare scorecard deltas.

## Suggested Commands
```bash
# 0) Deterministic CI trigger on feature branches (avoids workflow_dispatch 404 when workflow is not on default)
printf 'ndvs control9 progress %s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" > benchmarks/ndvs/trigger-run.txt
git add benchmarks/ndvs/trigger-run.txt
git commit -m "chore: trigger ndvs benchmark gate run"
git push origin <your-agent-branch>

# 1) Prepare and upload paper-aligned datasets (dry run first)
python3 scripts/benchmarks/ndvs_dataset_mirror.py \
  --dry-run \
  --skip-upload

# 2) Evaluate NDVS result rows for a run
python3 scripts/benchmarks/ndvs_scorecard.py \
  --results-json path/to/ndvs_results.json \
  --method-name spaceport \
  --subset control9 \
  --gate progress \
  --strict-scenes \
  --fail-on-gate \
  --output-json logs/ndvs-scorecard-progress.json

# 3) Orchestrate NDVS run + gate (no manual scorecard step)
python3 scripts/benchmarks/run_ndvs_benchmark.py \
  --method-name spaceport \
  --subset control9 \
  --gate progress \
  --results-json path/to/ndvs_results.json
```
