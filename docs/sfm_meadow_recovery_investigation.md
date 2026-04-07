# Meadow Ln SfM Recovery Investigation

## Scope

This note covers the chunked COLMAP pipeline in `infrastructure/containers/sfm/run_colmap_sfm.py`, the completed Brass Lantern run `brassfullchunka-1775237679`, and the stopped Meadow Ln run `meadowfullchunka-1775512223`.

## Verified Runtime Facts

- Brass Lantern completed on `ml.g4dn.xlarge` with `1285/1288` registered images, `959217` points, `8` chunks, and no chunk boundary recovery.
- Meadow Ln ran on the same container image and instance type, started at `2026-04-06T21:51:04Z`, stopped at `2026-04-07T12:21:27Z`, and ran for `52223` seconds.
- Meadow Ln emitted its last CloudWatch log event at `2026-04-07T00:08:34.979Z` while inside `vocab_tree_builder`, leaving `43971.047` seconds with no further container log output before the job ended.
- Meadow Ln never uploaded `sfm_metadata.json` to S3 because the container did not finish and `run_sfm.sh` only validates and uploads outputs after the Python pipeline exits successfully.

## What Metadata The Current Pipeline Actually Uses

- EXIF GPS is loaded for every image and converted to local XYZ coordinates.
- Heading is parsed from `GimbalYawDegree`, then `GPSImgDirection`, then `FlightYawDegree`.
- Gimbal pitch, gimbal roll, flight pitch, and flight roll are parsed but are not consumed anywhere else in `run_colmap_sfm.py`.
- GPS position priors are written into COLMAP's `pose_priors` table, but this pipeline does not call `pose_prior_mapper`.
- Heading is only used by Spaceport's chunking heuristics:
  - cluster scoring
  - chunk ordering/projection tie-breaking
  - overlap image selection at chunk boundaries
- Matching still depends on visual correspondences:
  - `spatial_matcher` uses GPS-based proximity limits
  - `sequential_matcher` uses capture order
  - recovery adds `vocab_tree_matcher`
- The mapper stage is still `colmap mapper`, so registration success remains dependent on the matched view graph, not on heading or gimbal pitch.

## Meadow Ln Failure Sequence

- Meadow Ln extracted `1456` images.
- Meadow Ln detected GPS EXIF on `1456/1456` images and orientation priors on `1456/1456` images.
- COLMAP reported pose priors for `1456/1456` GPS-tagged images with `100%` coverage and source `feature_extractor`.
- Chunks 0 through 3 registered cleanly:
  - chunk 0: `175/175`
  - chunk 1: `198/198`
  - chunk 2: `187/188`
  - chunk 3: `188/189`
- Chunk 4 used `198` images, with `1380` verified spatial pairs and `898` verified sequential pairs before mapping.
- Chunk 4 mapper produced at least two sparse models:
  - model 0: `18/198` images, `15872` points
  - model 1: `173/198` images, `122492` points
- Chunk 4 failed both acceptance gates:
  - total registered ratio: `173/198 = 87.37%`
  - core registered ratio: `142/162 = 87.65%`
- Recovery widened spatial matching to `18` neighbors and `300.0` meters, then added `705` more verified image pairs.
- Recovery then ran `vocab_tree_builder`.
- The current runtime rejected `--max_num_images`, retried without it, loaded `1925289` descriptors, and last logged `Building index for visual words...`.
- No later log lines were emitted from the container after that point.

## Why GPS Did Not Guarantee Registration

- The current pipeline does not use heading or pitch as hard registration constraints.
- The current pipeline does not switch to a pose-prior-aware mapper when visual registration becomes ambiguous.
- Meadow Ln proves that `100%` GPS prior coverage and `100%` orientation prior coverage are not sufficient by themselves for this implementation to avoid an expensive visual-retrieval fallback.

## Top Three Robustness Options

### 1. Remove local vocab-tree building from chunk recovery and cap recovery to GPS-bounded retries only

- Replace the current recovery path with bounded retries that reuse existing descriptors and only vary:
  - spatial neighbor count
  - spatial radius
  - sequential overlap
- Add explicit per-stage wall-clock limits around recovery steps, especially `vocab_tree_builder`, `vocab_tree_matcher`, and recovery mapper.
- If recovery times out or exceeds a pair-growth threshold without improving registration, keep the initial chunk result and continue.

Why this is attractive:
- Lowest implementation risk.
- Directly addresses the observed multi-hour stall.
- Cheapest to test because it only changes fallback behavior.

Tradeoff:
- It prevents the hang, but it may not recover the missing Meadow images if visual ambiguity truly needs a broader retrieval step.

### 2. Upgrade the recovery path to a pose-prior-aware reconstruction path

- Use a COLMAP path that explicitly reconstructs from pose priors instead of only using priors to choose candidate matches.
- This is the option that best aligns with the user's stated expectation that GPS should act like a "cheat code" for spatial placement.

Why this is attractive:
- It changes the failure mode from "GPS-guided matching plus ordinary mapper" to a reconstruction method that is actually prior-aware.
- It is the most direct way to make GPS matter more than it does today.

Tradeoff:
- Highest compatibility risk because it depends on the exact COLMAP build in the runtime image.
- Requires a careful benchmark because it changes reconstruction behavior, not just fallback mechanics.

### 3. Make chunking itself more prior-aware so ambiguous boundary images land in better local problems

- Rework chunk construction and recovery triggering around prior geometry instead of only centroid distance plus heading:
  - stronger boundary duplication for low-confidence edge regions
  - chunk-level health metrics based on connected components and missing-core clustering
  - targeted re-chunking of only the failing region instead of escalating to vocab-tree retrieval
- Meadow Ln's missing images cluster around specific filename bands, which is consistent with a localized chunk-boundary weakness.

Why this is attractive:
- Keeps the fast chunked architecture that already worked on Brass Lantern.
- Attacks the Meadow failure where it first appears: a single unhealthy chunk.

Tradeoff:
- More design work than option 1.
- Still does not make heading or pitch a hard registration constraint by itself.

## Lowest-Cost Test Strategy

- Keep all testing on the Meadow Ln archive but avoid full end-to-end runs until a candidate looks promising.
- First test only chunk 4 logic offline by reproducing the same chunk database size and recovery path on a reduced harness.
- Add mandatory stage timers and emit per-stage elapsed time so a failed experiment terminates in minutes, not hours.
- Use a cheap acceptance ladder:
  - no hangs
  - chunk 4 completes recovery
  - chunk 4 improves beyond `173/198` or avoids regression
  - only then rerun a full Meadow job
- Keep Brass Lantern as the regression guardrail and only rerun the full Brass dataset after Meadow-targeted changes pass smaller checks.
