<!-- a94faee5-a048-485c-82fd-65beaede4780 cb4642b6-c602-49e8-947d-15faa83cf872 -->
# Robust Terrain Avoidance System — Two‑Pass Adaptive Sampling with Shape Lab Visual Validation

### Goal (brief)

- Build the two‑pass adaptive terrain sampler and first validate it visually in the Shape Lab page against selectable synthetic 3D DEMs. Expose controls (DEM type, AGL min/max, thresholds, intervals, budgets) and overlays (path, samples, hazards, safety waypoints, AGL bands). After initial parameters stabilize, run an automated tuning phase over synthetic DEM suites to “learn” efficient parameters that preserve 100% AGL compliance.

### Scope & Decisions

- Provider model: per‑point metered; optimize total sampled points, not request count
- Constraints: user‑provided min/max AGL (optional; unset disables that constraint)
- Budgeting: discovery ≈ 30% of total points, refinement ≈ 70%; clamp to provider caps
- Smoothing: median + SG‑like windows to stabilize gradients/curvature
- Visual validation first: integrate into Shape Lab with selectable synthetic DEMs and live overlays
- Tuning later: automated learning from synthetic DEM suites to minimize points while keeping 100% AGL safety

### Files to Change

- Backend:
  - `infrastructure/spaceport_cdk/lambda/drone_path/lambda_function.py`
  - (Optional) `infrastructure/spaceport_cdk/lambda/drone_path/elevation_provider.py` (new)
- Frontend (Shape Lab):
  - `web/app/shape-lab/page.tsx` (wire controls and 3D preview)
  - Components (new):
    - `web/components/shape-lab/TerrainDemo.tsx` (3D scene, overlays)
    - `web/components/shape-lab/DemSelector.tsx` (terrain selector)
    - `web/components/shape-lab/ParamsPanel.tsx` (AGL + thresholds/budgets)
    - `web/components/shape-lab/HudMetrics.tsx` (samples used, hazards, AGL violations)
  - Data: `web/public/dem/*.json` (synthetic DEM fixtures)
- Tests/mocks: `tests/pipeline/terrain/` (new)

### Config (env or injected cfg)

- Distances (ft): `SPARSE_DISCOVERY_INTERVAL=450`, `DENSE=40`, `MEDIUM=120`, `SPARSE=300`
- Gradient thresholds (ft/100ft): `MEDIUM=10`, `HIGH=20`, `CRITICAL=40`
- Budget fractions: `DISCOVERY=0.3`, `REFINEMENT=0.7`
- Safety: `MIN_SAFETY_WAYPOINT_SPACING=50`
- AGL constraints (user input): `minAglFt?`, `maxAglFt?`

### Interfaces

- Elevation provider (prod and mock):
```ts
interface ElevationProvider {
  sample(points: LatLon[]): Promise<number[]>; // meters AMSL
  maxBatchSize(): number;
}
```

- Sampler inputs:
```ts
type SamplerConfig = {
  discoveryIntervalFt: number;
  denseIntervalFt: number;
  mediumIntervalFt: number;
  sparseIntervalFt: number;
  gradMediumFtPer100: number;
  gradHighFtPer100: number;
  gradCriticalFtPer100: number;
  discoveryFraction: number;
  minSafetySpacingFt: number;
};

type AglConstraints = { minAglFt?: number; maxAglFt?: number };
```


### Backend Function Additions (Python)

- In `lambda_function.py`:
```python
def two_pass_adaptive_sampling(path_ll, provider, cfg, agl, point_budget): ...

def sparse_discovery_scan(path_ll, provider, cfg, budget_points): ...

def calculate_elevation_gradient(amls_ft, distances_ft, window_ft): ...

def calculate_terrain_curvature(amls_ft, distances_ft, windows_ft): ...

def rank_segments_by_risk(samples): ...

def adaptive_refinement_sampling(queue, provider, cfg, budget_points): ...

def detect_peak_elevation(bracket, provider, cfg): ...

def generate_terrain_feature_waypoints(hazards, agl, cfg, path_ll): ...
```

- Modify:
  - Replace `adaptive_terrain_sampling(...)` with `two_pass_adaptive_sampling(...)`
  - Update `insert_safety_waypoints(...)` to enforce spacing and AGL constraints

### Shape Lab Frontend (visual validation)

- DEM selector: flat, sinusoid hills, sharp ridge, mountain range, cliff, mixed (load from `web/public/dem/*.json`)
- Parameter panel: min/max AGL, interval/threshold sliders, point budget, feature flag for v1/v2 comparison
- 3D visualization: render DEM mesh/heightfield, flight polyline, sampled points (color by phase), hazard markers, safety waypoints, AGL bands
- Metrics HUD: total points used, samples/mi, hazards found, AGL violations, time
- Run locally in browser using a mock elevation provider backed by the chosen DEM; no prod API used for Shape Lab runs

### Algorithm Details

- Discovery: sample at `discoveryIntervalFt` within `discoveryFraction * budget`, smooth elevations, compute gradients/curvature/relief, score segments, push to max‑heap
- Refinement: pop highest risk, choose interval by gradient band, sample more points, update risk with diminishing returns, re‑queue; for high gradient, bracket + ternary search to locate peaks within `DENSE` resolution
- Safety: compute required altitude for `minAglFt`, clamp to `maxAglFt` if set; mark UNSATISFIED if infeasible; dedupe within spacing window; snap within segment bounds

### Telemetry & Logging

- Counters: points used, heap operations, hazards, AGL violations, timing
- Persist browser session configs (URL or localStorage) for easy repro
- Summaries under `logs/` for backend test runs

### Tests & Tuning Harness

- `tests/pipeline/terrain/`:
  - `dem_provider.py` (mock reading JSON/GeoTIFF)
  - `synthetic_dem_gen.py` (all terrain cases)
  - `validator.py` (AGL/collision/spacing checks)
  - `tuner.py` (grid/BO over thresholds/intervals; score = 0.7 safety + 0.3 efficiency)
  - `edgewood_replay.py` (baseline comparison)
- Output metrics and best‑param profiles to `logs/` and `tests/pipeline/terrain/results/*.json`

### Rollout

1) Provider abstraction + mock DEM provider

2) Backend discovery + refinement + waypoints with telemetry

3) Shape Lab UI: DEM selector, params panel, 3D overlays, metrics HUD

4) Wire v1 vs v2 switch; test visually in browser often until overlays match expected behavior

5) Integrate backend entrypoint; keep Shape Lab using mock provider

6) Build tests, generate DEMs, run tuner; export learned param profiles

7) Compare Edgewood; if green, enable v2 by default

### To-dos

- [ ] Add ElevationProvider interface and prod/mock implementations
- [ ] Implement sparse discovery scan with smoothing and scoring
- [ ] Build priority queue and risk score normalization
- [ ] Implement adaptive refinement loop with diminishing returns
- [ ] Add bounded ternary search peak detector for high gradients
- [ ] Generate deduped safety waypoints with AGL constraint enforcement
- [ ] Replace sampler entrypoint and gate via TERRAIN_SAMPLER=v2
- [ ] Create DEM mock provider, generators, validator, tuner, Edgewood replay
- [ ] Add telemetry counters and logs to logs/ with summaries
- [ ] Run parameter grid search and record best configs