# Spaceport SOTA Gaussian Splat Plan

_Source: captured from the original Codex agent tmux output (fx-v0-spaceport-website:2.0) on 2026-02-26. This is the most recent “final/ultimate” plan: the paper-grade benchmarking + AWS dataset program, plus the NDVS-only execution plan with Gabe’s constraints baked in._

## 0) Why this plan exists

- We want **paper-grade, objective targets** for quality (PSNR/SSIM/LPIPS) and **hard reliability** around the SfM axis/orientation failure (“sideways splat”) with **no human-in-the-loop visual QA**.
- We anchor on canonical 3DGS-family evaluation protocols and datasets.
- We keep execution **agentic**, but **compute-disciplined** and auditable.

---

## 1) Benchmark Datasets (paper-aligned, automatable)

### 1.1 Core paper set (must-have)

- **Mip-NeRF 360**: bicycle, garden, stump, counter, kitchen, room, bonsai (plus restricted/extra scenes if license allows)
- **Tanks & Temples**: truck, train
- **Deep Blending**: playroom, drjohnson

### 1.2 Large-scale set (scalability/generalization)

- **Zip-NeRF (undistorted)**: alameda, berlin, london, nyc

### 1.3 Geometry stress set (optional but recommended)

- **DTU + Tanks&Temples geometry protocol** (Chamfer/F1 track via 2DGS-style eval scripts)

---

## 2) AWS Data Acquisition Plan (no manual steps)

### 2.1 S3 layout

- `s3://spaceport-ml-benchmarks/raw/<dataset>/<scene>/...`
- `s3://spaceport-ml-benchmarks/processed/<dataset>/<scene>/...`
- `s3://spaceport-ml-benchmarks/manifests/<dataset>/<scene>.json`
- `s3://spaceport-ml-benchmarks/results/<run_id>/...`

### 2.2 Single ingestion job (SageMaker Processing or Batch)

- Download from official URLs
- Normalize image folders to paper conventions:
  - Mip-NeRF360: `images_4` outdoor, `images_2` indoor
  - Zip-NeRF large scenes: `images_4`
- Compute:
  - sha256
  - file count
  - image count
  - resolution stats
- Emit immutable manifest JSON with:
  - `source_url`
  - `download_timestamp`
  - `license_url`

### 2.3 Strict reproducibility checks

- Fail ingestion if checksum drift appears between runs
- Fail if scene image count changes unexpectedly
- Fail if required COLMAP artifacts/splits are missing

---

## 3) Metrics Protocol (paper-style + pipeline safety)

### 3.1 Primary NVS metrics

- PSNR (higher is better)
- SSIM (higher is better)
- LPIPS-VGG (lower is better)

### 3.2 Split/eval rules

- Fixed train/test split manifest per scene
- Lock split seed and holdout policy (no random split drift)
- Evaluate only on test views

### 3.3 Full-pipeline quality/safety metrics (axis issue coverage)

- Up-axis alignment cosine
- Camera-up consistency
- Heading-consistency error vs priors
- Reconstruction success rate
- Registered-image ratio

### 3.4 Efficiency metrics

- Training wall-clock time
n- GPU peak memory
- Final gaussian count
- Cost per successful scene

---

## 4) Verifiable Targets (numerical gates)

Using current nvs-bench snapshot (as of **2026-02-26**) on a 9-scene subset:

Scenes: bicycle, garden, stump, counter, truck, train, playroom, drjohnson, alameda

### 4.1 Reference baselines

- gaussian-splatting baseline avg:
  - PSNR 26.505
  - SSIM 0.842
  - LPIPS 0.248

- best-per-scene frontier avg:
  - PSNR 26.958
  - SSIM 0.861
  - LPIPS 0.202

### 4.2 Gates

1) **Parity gate**
- Reach at least baseline on all 3 primary scenes (garden, truck, playroom)
- And **no axis failures**

2) **Progress gate**
- PSNR >= 26.70
- SSIM >= 0.850
- LPIPS <= 0.230
(on the 9-scene subset)

3) **Frontier gate**
- PSNR >= 26.85
- SSIM >= 0.857
- LPIPS <= 0.215
- Cost increase capped to <= 25% vs parity baseline

4) **Reliability gate**
- 0 sideways-splat failures across 3 consecutive full benchmark runs
- Re-run variance (stddev) <= 0.15 PSNR on repeated scenes

---

## 5) Phased Execution (fully agentic)

### Phase A — Benchmark plumbing

- Add dataset sync job, manifests, and fixed split manifests
- Exit criteria: deterministic re-download + manifest diff = clean

### Phase B — Baseline reproduction

- Run 3DGS-only track (paper datasets with provided COLMAP)
- Exit criteria: baseline metrics table generated automatically

### Phase C — Full pipeline baseline

- Run SfM + 3DGS on same scenes
- Exit criteria: orientation metrics + NVS metrics emitted per scene

### Phase D — Axis/orientation hardening

- Fix runtime config alignment gap
- Add canonical frame normalization
- Exit criteria: no sideways failures + axis gates pass

### Phase E — Quality upgrades (ablation)

- Introduce Mip-Splatting-style anti-alias settings
- Introduce AbsGS-style densification logic
- Add robust exposure handling
- Exit criteria: progress/frontier gates pass without cost blowout

### Phase F — Large-scale robustness

- Run Zip-NeRF scenes
- Exit criteria: stable memory/time with no quality collapse

### Phase G — Continuous autonomous loop

- Nightly benchmark Step Function
- Automatic leaderboard update
- Automatic rollback on gate failure

---

## 6) Where this plugs into the current repo

- Training/eval hook point:
  - `infrastructure/containers/3dgs/train_nerfstudio_production.py`
- SfM config/orientation hook point:
  - `infrastructure/containers/sfm/run_opensfm_gps.py`
- Pipeline env wiring point:
  - `infrastructure/spaceport_cdk/spaceport_cdk/ml_pipeline_stack.py`

---

## 7) Updated Plan (with Gabe’s constraints baked in)

### Hard Operating Rules

1) All benchmark testing runs through **NDVS only** (same harness every run, no ad-hoc local eval).
2) Commit frequently: one commit per meaningful change, at least every 60–90 minutes during active iteration, and after each green benchmark gate.
3) Never build containers locally. Any container change is validated only via GitHub Actions + CodeBuild.
4) Work loop: code change → commit → push → watch workflows → run NDVS benchmark → compare metrics → next change.

### Phase 1: Benchmark Foundation

1) Add benchmark manifest registry in repo for datasets, splits, expected file counts, checksums, and licenses.
2) Add NDVS runner wrapper script that takes scene, config, run_id, and writes standardized metrics JSON.
3) Gate: deterministic rerun on same commit produces identical split selection and near-identical metrics variance bounds.

### Phase 2: Dataset Ingestion to AWS

1) Ingest Mip-NeRF360, Tanks&Temples (truck/train), DeepBlending (playroom/drjohnson), and Zip-NeRF into S3 benchmark buckets.
2) Normalize folder structure and naming exactly once in ingestion pipeline.
3) Emit scene manifests with checksums and source provenance.
4) Gate: manifest validation passes for every scene; ingestion fails automatically on drift.

### Phase 3: Baseline Reproduction (NDVS-only)

1) Run current pipeline on benchmark subset via NDVS.
2) Record baseline table for PSNR, SSIM, LPIPS, time, GPU memory, gaussian count, success rate.
3) Gate: baseline is reproducible across 2 consecutive runs.

### Phase 4: SfM Orientation/Axis Reliability

1) Fix runtime SfM config path so alignment settings are guaranteed applied.
2) Add automated orientation validator before training (camera-up consistency, heading consistency, axis sanity).
3) Hard-fail any run with sideways/invalid axis signatures.
4) Gate: zero orientation failures across 3 full NDVS benchmark passes.

### Phase 5: Quality Upgrades (Ablation-driven)

1) Introduce one improvement at a time (anti-aliasing controls, densification strategy improvements, robust exposure handling).
2) Every change runs full NDVS benchmark and is accepted only if metrics improve with bounded cost increase.
3) Gate targets on 9-scene control set:
- PSNR >= 26.70
- SSIM >= 0.850
- LPIPS <= 0.230
- Cost increase <= 25% vs baseline

### Phase 6: Frontier Push

1) Continue ablations to approach best-per-scene frontier.
2) Promotion target:
- PSNR >= 26.85
- SSIM >= 0.857
- LPIPS <= 0.215
- Orientation failure rate = 0%
3) Gate: pass 3 nightly NDVS runs in a row.

### Phase 7: Continuous Autonomous Loop

1) Nightly NDVS benchmark workflow on fixed dataset suite.
2) Auto-publish leaderboard artifact and regression report.
3) Auto-rollback trigger on metric regression, orientation failures, or cost-per-success breach.

### Commit + CI Cadence Policy

1) Commit after each atomic change (config plumbing, axis gate, eval hook, each ablation).
2) Push immediately so Actions/CodeBuild run.
3) Do not continue experimentation while required workflows are red.
4) Keep benchmark artifacts versioned by run_id and commit SHA for full traceability.

### Container Policy (explicit)

1) No local docker build.
2) Container modifications are commit-only.
3) Build/validation path is GitHub Actions → CodeBuild → deploy/test via NDVS.

---

## 8) Sources (links captured in the agent output)

- 3DGS repo/eval protocol: https://github.com/graphdeco-inria/gaussian-splatting
- 3DGS full_eval scene definitions: https://raw.githubusercontent.com/graphdeco-inria/gaussian-splatting/main/full_eval.py
- 3DGS dataset links (Mip-NeRF360, T&T+DB): https://raw.githubusercontent.com/graphdeco-inria/gaussian-splatting/main/README.md
- Mip-Splatting: https://github.com/autonomousvision/mip-splatting
- Scaffold-GS: https://github.com/city-super/Scaffold-GS
- AbsGS: https://github.com/TY424/AbsGS
- StopThePop: https://github.com/r4dl/StopThePop
- 3DGS-MCMC: https://github.com/ubc-vision/3dgs-mcmc
- 2DGS: https://github.com/hbb1/2d-gaussian-splatting
- NVS-Bench datasets/results snapshot: https://github.com/nvs-bench/nvs-bench
- Nerfstudio eval command: https://raw.githubusercontent.com/nerfstudio-project/nerfstudio/main/nerfstudio/scripts/eval.py
- Nerfstudio splatfacto metrics keys (psnr/ssim/lpips): https://raw.githubusercontent.com/nerfstudio-project/nerfstudio/main/nerfstudio/models/splatfacto.py
