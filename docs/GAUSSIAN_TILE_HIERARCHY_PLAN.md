# Gaussian Tile Hierarchy Plan

## Goal

Design a robust, fast-to-iterate path for training very large Gaussian splat scenes in overlapping tiles, merging them without an expensive full-scene alignment pass, and preserving horizon quality for shallow-angle and long-baseline views.

This plan is optimized for the current Spaceport stack:

- Chunk-aware SfM already exists in [infrastructure/containers/sfm/run_colmap_sfm.py](/Users/gabrielhansen/worktrees/agent-86580563-hierarchical-splat-merge-plan/infrastructure/containers/sfm/run_colmap_sfm.py)
- Local 3DGS training already uses `splatfacto-w-light` in [infrastructure/containers/3dgs/train_nerfstudio_production.py](/Users/gabrielhansen/worktrees/agent-86580563-hierarchical-splat-merge-plan/infrastructure/containers/3dgs/train_nerfstudio_production.py)
- Current quality knobs already exist in [infrastructure/containers/3dgs/nerfstudio_config.yaml](/Users/gabrielhansen/worktrees/agent-86580563-hierarchical-splat-merge-plan/infrastructure/containers/3dgs/nerfstudio_config.yaml) and [infrastructure/containers/3dgs/progressive_config.yaml](/Users/gabrielhansen/worktrees/agent-86580563-hierarchical-splat-merge-plan/infrastructure/containers/3dgs/progressive_config.yaml)
- Skybox export and far-field handling are already part of the export path in [infrastructure/containers/3dgs/export_splatfacto_w_assets.py](/Users/gabrielhansen/worktrees/agent-86580563-hierarchical-splat-merge-plan/infrastructure/containers/3dgs/export_splatfacto_w_assets.py)

## Recommendation

Use a phased hybrid:

1. `P0`: cheap global scaffold over the full scene.
2. `P1`: visibility-aware overlapping leaf tiles trained with `splatfacto-w-light`.
3. `P2`: deterministic merge by core ownership first, then importance-based overlap arbitration.
4. `P3`: shallow parent LOD nodes for far-field and horizon-heavy regions only.

This is the best fit-effort ratio for `md1`.

It deliberately avoids starting with full ADMM consensus, deep octrees, or out-of-core streaming.

Keep the local trainer path fixed during the first benchmark ladder. Change tiling, overlap, and merge policy first. Do not mix trainer changes into the same rung or attribution will get muddy.

## Why This Wins

### What to borrow from the literature

- `CityGaussian`: cheap global prior plus adaptive training data selection.
- `VastGaussian`: visibility-aware cell assignment and overlap as supervision.
- `BlockGaussian`: stronger content-aware partitioning and boundary robustness.
- `Momentum-GS`: overlap-only teacher guidance if seams remain after P2.
- `Hierarchical 3D Gaussians`: parent nodes for distant rendering and hierarchy-based scaling.
- `Octree-GS` and `Scaffold-GS`: light inspiration for shallow LOD, not a full rewrite.
- `Horizon-GS`: treat distant, low-angle, multi-scale views as a separate quality target.

### What not to do first

- Do not start with naive XY tiling.
- Do not start with full global post-merge optimization.
- Do not start with distributed consensus everywhere.
- Do not start with out-of-core runtime architecture.

Those all add too much system complexity before the seam, overlap, and horizon failure modes are measured on `md1`.

## Three Strategy Options

### Strategy A: Coarse Prior + Overlapping Tiles + Ownership Merge

This is the recommended first implementation.

Pipeline:

1. Train a cheap full-scene scaffold using downsampled images and a capped Gaussian budget.
2. Partition the scene into 4 to 8 leaf tiles using spatial-heading SfM coverage and visibility.
3. Give each tile:
   - a core region
   - a 15% to 25% overlap band
   - base cameras inside the core
   - border cameras that supervise the overlap band
4. Train each tile independently with `splatfacto-w-light`.
5. Merge with a deterministic rule:
   - keep only core-owned Gaussians in `v1`
   - drop overlap-only Gaussians after training
6. Measure seams and horizon quality before adding more sophistication.

Why this first:

- Fastest to prototype on the current stack.
- Deterministic failure signals.
- Lowest integration risk.
- Reuses the current chunked-SfM and splatfacto-w-light pipeline directly.

Main weakness:

- Some overlap detail is thrown away.
- Boundary quality may plateau if ownership is too hard-edged.

### Strategy B: Strategy A + Importance-Based Overlap Arbitration + Optional Teacher

This is the best second step.

Changes from Strategy A:

1. Keep overlap Gaussians temporarily after tile training.
2. Score overlap Gaussians by visibility/contribution in shared cameras.
3. Retain the best overlap primitives and prune duplicates.
4. If seams remain, add teacher guidance only in overlap bands.

Why this second:

- Better use of the Gaussian budget already spent in the overlap band.
- Raises boundary quality without introducing a full global solve.
- Lets the system stay leaf-tile centric.

Main weakness:

- Scoring and pruning must be stable or merge quality becomes noisy.
- Teacher guidance can over-regularize if applied too broadly.

### Strategy C: Strategy B + Shallow Parent LOD Nodes

This is the long-term target for the larger eventual dataset.

Changes from Strategy B:

1. Build one coarse parent layer above leaf tiles.
2. Populate parent nodes from:
   - retained overlap Gaussians
   - far-field structures
   - horizon-heavy content
3. Render near views from leaves and distant views from parents.

Why this third:

- Best answer to the far-field quality vs. cost paradox.
- Stops burning leaf Gaussian budget on content that should render at coarser granularity.
- Matches the repo's skybox and viewer direction better than a full runtime rewrite.

Main weakness:

- Adds hierarchy management and transition logic.
- Parent fusion can oversmooth thin distant structures if done too early.

## Final Choice

Build `Strategy A`, plan for `Strategy B`, and reserve `Strategy C` for the second major iteration.

That is the most robust plan because it separates three risks:

- tile partitioning risk
- overlap merge risk
- far-field hierarchy risk

Each risk gets isolated and measured before the next layer is added.

## Tile Design for `md1`

### Partition policy

Use chunk-aware SfM output as the partition backbone.

Partition by:

- spatial locality
- camera heading
- co-visibility
- expected visible-Gaussian load

Avoid a pure ground-plane grid.

### Starting layout

- `4 tiles` for the first control run
- `8 tiles` for the first real stress run
- `15% overlap` minimum
- `20% overlap` preferred baseline
- `25% overlap` only if boundary PSNR is still weak

### Camera assignment

Each tile should receive:

- `base cameras`: camera center inside the core region
- `border cameras`: camera center or frustum intersects the overlap band
- `context cameras`: limited number of high-visibility cameras just outside the tile

This keeps the tile locally stable without training the whole scene repeatedly.

## Merge Policy

### Version 1

Use strict core ownership.

Rules:

- Gaussians outside the tile core are training support only.
- Final merged scene keeps core-owned Gaussians only.
- Track how many Gaussians are dropped per tile and where.

Why:

- Easy to debug.
- No merge ambiguity.
- Clean baseline for seam analysis.

### Version 2

Promote to importance-based arbitration.

Rules:

- Score overlap Gaussians by shared-view contribution.
- Keep the best-scoring primitive set in each overlap band.
- Reject duplicates with low contribution or unsupported depth.

Why:

- Recovers overlap value without global optimization.
- Usually the best practical upgrade after `v1`.

### Version 3

Add overlap-only teacher guidance if `v2` still leaves seams.

Rules:

- Teacher loss applies only in overlap bands.
- Do not regularize full tiles.
- Use the scaffold as the initial teacher, then momentum-update from accepted overlap primitives.

Why:

- Keeps system complexity bounded.
- Targets the only area that needs cross-tile consistency.

## Horizon and Far-Field Policy

Treat horizon quality as a separate product requirement, not as a side effect of tile quality.

### Requirements

- Distant skyline should stay consistent across adjacent tiles.
- Low-angle gimbal shots should not show tile ownership changes.
- Distant structures should not force leaf tiles to retain excessive Gaussian counts.

### Implementation

1. Keep the global scaffold alive as a low-frequency world model.
2. Keep the current skybox/background export path in the loop.
3. Add shallow parent nodes only for:
   - skyline
   - very distant terrain
   - overlap-heavy far structures

Do not attempt a deep hierarchy in the first `md1` phase.

## Cheapest Useful Benchmark Ladder

### Dataset slices

Create three held-out view buckets for `md1`:

- `near-detail`: close geometry and fine structure
- `boundary`: views centered on tile borders
- `horizon`: low-angle long-baseline views with distant skyline

### Run matrix

Run these in order:

1. `M0`: monolithic `splatfacto-w-light` baseline
2. `T1`: tiled-only with strict core merge
3. `T2`: tiled + global scaffold + strict core merge
4. `T3`: tiled + global scaffold + importance merge
5. `T4`: tiled + global scaffold + importance merge + shallow parent layer

Use the same trainer configuration across `M0` through `T4`, reusing the current `splatfacto-w-light` path and the existing validation cadence from the production configs.

### Keep two comparison modes

- `fixed wall-clock`
- `fixed GPU-hours`

Do not compare only by iterations.

### Metrics

Primary:

- PSNR
- SSIM
- LPIPS
- peak VRAM
- training wall-clock
- GPU-hours
- final Gaussian count
- model size
- render FPS

Boundary-specific:

- boundary PSNR gap vs. interior views
- boundary LPIPS gap vs. interior views
- duplicate density in overlap bands
- unsupported-depth floater rate

Horizon-specific:

- horizon crop PSNR
- horizon crop LPIPS
- skyline stability across adjacent tile traversals

### Success gates

`T2` should beat `T1` on boundary views without materially raising wall-clock.

`T3` should improve boundary quality over `T2` without increasing duplicate density beyond 15%.

`T4` is only worth keeping if it improves horizon metrics and render cost together.

If `T4` improves horizon quality but hurts near-detail, keep parent nodes horizon-only.

Stop climbing the ladder when the next rung buys less than `0.5 dB` global PSNR or less than `5%` seam or horizon improvement per `+20%` GPU-hours.

## Stop Conditions

Stop the first phase when all of these are true:

- boundary PSNR gap is within `0.5 dB`
- boundary LPIPS gap is within `10%`
- overlap duplicate density is within `15%` of core median
- horizon crop quality matches or exceeds monolithic baseline at lower total compute
- tiled run shows better cost scaling than monolithic on `md1`

## Implementation Order

### Phase 1

- Add a full-scene scaffold training mode.
- Emit tile manifests from chunk-aware SfM output.
- Emit tile camera lists and overlap bands.

### Phase 2

- Train leaf tiles with current `splatfacto-w-light`.
- Export per-tile splat stats.
- Merge with strict core ownership.

### Phase 3

- Add overlap arbitration.
- Add seam-specific evaluation.
- Add horizon-specific evaluation.

### Phase 4

- Add one shallow parent layer for far-field content.
- Compare parent-enabled runs against leaf-only runs.

## Rejected Early Alternatives

### Full consensus training everywhere

Rejected for `md1` because it is too invasive before basic overlap behavior is measured.

### Deep octree runtime rewrite

Rejected for `md1` because the current stack already has a workable leaf trainer and skybox path.

### Out-of-core first

Rejected for `md1` because it solves a later scaling problem before the merge policy is proven.

## Sources

- [CityGaussian](https://arxiv.org/abs/2404.01133)
- [CityGaussianV2](https://arxiv.org/abs/2411.00771)
- [VastGaussian](https://arxiv.org/abs/2402.17427)
- [BlockGaussian](https://arxiv.org/abs/2504.09048)
- [Momentum-GS](https://arxiv.org/abs/2412.04887)
- [DoGaussian / DOGS](https://arxiv.org/abs/2405.13943)
- [A Hierarchical 3D Gaussian Representation](https://arxiv.org/abs/2406.12080)
- [Octree-GS](https://github.com/city-super/Octree-GS)
- [Scaffold-GS](https://github.com/city-super/Scaffold-GS)
- [Horizon-GS](https://arxiv.org/abs/2412.01745)
- [A LoD of Gaussians](https://arxiv.org/abs/2507.01110)
- [LODGE](https://arxiv.org/abs/2505.23158)
- [Nerfstudio Splatfacto](https://docs.nerf.studio/nerfology/methods/splat.html)
- [Nerfstudio Splatfacto-W](https://docs.nerf.studio/nerfology/methods/splatw.html)
