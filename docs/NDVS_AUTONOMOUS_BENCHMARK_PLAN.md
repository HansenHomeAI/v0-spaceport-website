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

3. Gate evaluation:
- Run `scripts/benchmarks/ndvs_scorecard.py` against NDVS result rows.
- Enforce `--strict-scenes --fail-on-gate` for promotion.

4. Iterate:
- Change one factor at a time (SfM orientation, densification policy, anti-aliasing, etc.).
- Re-run NDVS and compare scorecard deltas.

## Suggested Commands
```bash
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
```
