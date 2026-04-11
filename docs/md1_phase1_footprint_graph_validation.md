# MD1 Phase 1 Footprint-Graph Validation

## Scope

This note records the phase-1 MD1 probe validation for the EXIF-driven `footprint_graph_v1` chunk planner on branch `agent-70148362-investigate-sfm-recovery`.

Phase 1 scope was limited to better leaf chunking, pair-list matching, and bounded chunk/bridge recovery. It did not attempt the larger hierarchical merge architecture for full-dataset scaling.

## Baseline Control

The baseline control was the pre-phase-1 chunked runtime on the same MD1 probe snapshot:

- `geometry_mix` baseline job `md1phase1basegeome-1775767866`
- `cross_pass` baseline job `md1basecross-1775769745`
- `horizon_context` baseline job `md1basehoriz-1775769991`

Verified baseline results:

- `geometry_mix`: failed quality gate at `453/467` images with `2633` verified pairs and `2` chunks `[239, 236]`
- `cross_pass`: passed at `477/485` images, `290602` points, `3200.64s`
- `horizon_context`: passed at `467/467` images, `323435` points, `3352.70s`

## Candidate Runtime

The final geometry proof rerun used branch image digest:

- `sha256:d4bb9034c37ffb138c91c737ddc6572135b8a9c4e168e510129ed0bfe4b75c3b`

This rerun included the final bridge-timeout/runtime fix from commit `d18c090d03c6e61cc21c13ab41ac3a3cee36b897`.

## Verified Phase-1 Results

### 1. Geometry Mix

Job:

- `md1candg15-1775878097`

Verified results from `sfm_metadata.json` and the completed SageMaker job:

- `467/467` registered images
- `415870` points
- `quality_check_passed=true`
- `timed_out=false`
- `chunk_planner=footprint_graph_v1`
- `chunk_matcher_strategy=pair_list`
- `sequential_matcher_enabled=false`
- `verified_pairs_total=16577`
- `3` chunks: `[127, 185, 235]`
- bridge recovery triggered and succeeded
- bridge model stage `chunk_01_02_merge_bridge_mapper_initial` completed at `467/467` with `400109` points
- merged output retained `467/467` pre-merge registered images
- total runtime `11116.88s`

This is the decisive fix proof. The same geometry probe had previously failed at the bridge mapper stage after timing out around `2700s`. On the final image it ran through the same stage, completed it in `3354.11s`, and produced a full passing reconstruction.

### 2. Cross Pass

Job:

- `md1candx8-1775802834`

Verified results:

- `485/485` registered images
- `357637` points
- `quality_check_passed=true`
- `timed_out=false`
- `chunk_planner=footprint_graph_v1`
- `chunk_matcher_strategy=pair_list`
- `verified_pairs_total=10802`
- `3` chunks: `[253, 120, 247]`
- adjacent merge recovery triggered and succeeded
- merged output retained `485/485` pre-merge registered images
- total runtime `5711.40s`

### 3. Horizon Context

Job:

- `md1candh14-1775865817`

Verified results:

- `467/467` registered images
- `372037` points
- `quality_check_passed=true`
- `timed_out=false`
- `chunk_planner=footprint_graph_v1`
- `chunk_matcher_strategy=pair_list`
- `verified_pairs_total=11840`
- `4` chunks: `[126, 188, 232, 120]`
- bridge recovery triggered and succeeded
- merged output retained `467/467` pre-merge registered images
- total runtime `7569.93s`

## What Phase 1 Proved

- The old time-led assumptions are no longer required for these MD1 probes to reconstruct.
- The footprint-graph planner plus pair-list matching can reconstruct all three MD1 probe subsets successfully.
- The geometry probe, which failed under the baseline planner at `453/467`, now passes cleanly at `467/467`.
- The bridge-runtime fixes were necessary and correct:
  - the prior geometry candidate died in `chunk_01_02_merge_bridge_mapper_initial`
  - the final geometry candidate completed that exact stage and finished the job successfully
- Merge retention remained intact on the successful candidate probes:
  - geometry `467/467`
  - cross-pass `485/485`
  - horizon `467/467`

## What Phase 1 Did Not Prove

- It did not reduce compute spend yet.
- On these probes, the candidate planner was materially slower than baseline on the already-passing `cross_pass` and `horizon_context` slices.
- The geometry probe quality improvement is real, but it came with a much larger pair graph and longer bridge reconstruction time.

So the truthful phase-1 outcome is:

- robustness and quality improved enough to pass the MD1 probe ladder
- compute efficiency is not yet where it needs to be for a final large-scale rollout

## Hard Assessment

Phase 1 is complete as a robustness proof, not as a compute-optimization proof.

The branch now has hard evidence that EXIF-driven footprint-graph chunking can recover MD1 probe slices that the old planner could not. The remaining work is a phase-1.5 / phase-2 style optimization pass that reduces pair density and bridge cost before attempting the full MD1 dataset.
