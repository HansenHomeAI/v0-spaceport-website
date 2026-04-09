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

## Implemented Changes

- Removed chunked `vocab_tree_builder` / `vocab_tree_matcher` recovery from the GPS-first chunked path.
- Removed GPS-eligible fallback from the chunked path into the older monolithic visual-retrieval fallback.
- Added bounded per-stage timeouts and heartbeat logging to child COLMAP commands.
- Upgraded chunk planning to use:
  - local XYZ
  - altitude
  - yaw
  - pitch
  - capture time
- Added prior-aware capture grouping, flightline segmentation, and boundary overlap assignment.
- Added one bounded prior-aware retry for unhealthy chunks.
- Added one bounded adjacent-chunk merge retry for chunks that still fail after the prior-aware retry.
- Added metadata fields that expose:
  - failed chunk index
  - registered/core ratios
  - timeout state
  - whether adjacent merge was triggered
  - chunk group and segment counts

## Post-Change Validation

### Local Tests

- `python3 -m unittest tests.unit.test_colmap_gps_priors` passed with `31` tests after adding orientation-source selection coverage.
- The broader local SfM unit suite passed earlier with `36` tests after the prior-aware chunking and fast-fail changes landed.

### Meadow Chunk-4 Exact Subset

Subset archive:

- `s3://spaceport-ml-processing-staging/manual-validations/meadow_chunk4_subset_1775578610.zip`

This subset is the exact Meadow chunk-4 problem slice used for low-cost live validation.

#### 1. Monolithic fast-fail proof

Job:

- `meadowchunk4subsetmonofastfail-1775709702`

Verified results:

- completed in `812.02` seconds
- no `vocab_tree_builder` or `vocab_tree_matcher` executed
- registered `143/148` images
- failed decisively on the quality gate instead of hanging
- failure reason: `GPS-first mapper registered 143/148 images (96.62%), below 98.00% threshold`

This proves the slow hanging vocab fallback is removed from the GPS-first monolithic path.

#### 2. First chunked prior-aware retry proof

Job:

- `meadowchunk4subsetchunked-1775710814`

Verified results:

- completed in `1085.75` seconds
- no vocab-tree stage executed
- chunking used `2` chunks: `[69, 87]`
- chunk 1 initial result: `84/87`
- chunk 1 retry result: `84/87`
- final failure was bounded and explicit:
  - `failure_stage=chunk_01_recovery_failed`
  - `failed_chunk_registered_ratio=0.9655`
  - `failed_chunk_core_registered_ratio=0.6988`

This proves the first fast-fail chunked path removed the hang but still under-registered the hard region.

#### 3. Chunked adjacent-merge retry proof

Job:

- `meadowchunk4subsetchunked-1775713425`

Verified results:

- completed in `1908.32` seconds
- no vocab-tree stage executed
- `chunk_recovery_mode=prior_aware_retry_adjacent_merge_no_vocab`
- `adjacent_chunk_merge_triggered=true`
- chunk 0 initial model: `66/69`
- chunk 1 initial model: `84/87`
- chunk 1 retry model: `84/87`
- adjacent merged chunk initial model: `143/148`
- adjacent merged chunk retry model: `143/148`
- final failure was still bounded and explicit:
  - `failure_stage=chunk_00_01_adjacent_merge_recovery_failed`
  - `failed_chunk_registered_ratio=0.9662`
  - `failed_chunk_core_registered_ratio=0.8108`
  - `timed_out=false`

Missing-core images after the adjacent merge remained concentrated in specific filename bands:

- `DJI_0099.JPG` to `DJI_0101.JPG`
- `DJI_0362 2.JPG` to `DJI_0366 2.JPG`
- `DJI_0391 2.JPG` to `DJI_0403 2.JPG`
- `DJI_0418 2.JPG` to `DJI_0421 2.JPG`
- `DJI_0626 2.JPG` to `DJI_0627 2.JPG`
- `DJI_0647 2.JPG` to `DJI_0651 2.JPG`
- `DJI_0667 2.JPG` to `DJI_0668 2.JPG`

This proves the new prior-aware chunking and bounded adjacent merge materially improved the failing chunk's core registration from `58/83` to `120/148` on the exact Meadow problem subset, while still preserving deterministic failure instead of the original multi-hour hang.

### Root Cause Found: Meadow Was Using Degenerate Gimbal Orientation Priors

The next investigation step checked the raw Meadow EXIF orientation fields instead of assuming the first non-null field was informative.

Verified Meadow subset facts:

- `GimbalYawDegree` had `1` unique value across the failing slice: `0.0`
- `GimbalPitchDegree` had `1` unique value across the failing slice: `0.0`
- `FlightYawDegree` had `131` unique values across the same slice
- `FlightPitchDegree` had `110` unique values across the same slice

That means the runtime was technically seeing `100%` orientation coverage while still selecting a useless orientation source for Meadow.

Implemented fix:

- the runtime now records raw orientation candidates separately
- it computes coverage plus angular dispersion for each candidate source
- it selects the first heading/pitch source that is both sufficiently populated and sufficiently informative
- Meadow now selects:
  - `heading_prior_source=flight_yaw`
  - `pitch_prior_source=flight_pitch`

This changed the Meadow full-dataset chunk plan materially:

- previous chunk plan: `8` chunks with sizes `[290, 154, 139, 164, 148, 180, 192, 245]`
- corrected chunk plan: `6` chunks with sizes `[268, 299, 205, 196, 263, 266]`

### Corrected Meadow Chunk-4 Rebuild Proof

Corrected subset archive:

- `s3://spaceport-ml-processing-staging/manual-validations/meadow_chunk4_subset_fixed_1775754600.zip`

This subset was rebuilt from the corrected full Meadow chunk plan after the runtime switched from degenerate gimbal orientation to informative flight orientation.

Job:

- `meadowchunk4fixedchunked-1775749511`

Verified results:

- completed in `2740.53` seconds
- registered `343/343` images
- produced `233601` points
- `quality_check_passed=true`
- `fallback_triggered=false`
- `boundary_recovery_triggered=false`
- `adjacent_chunk_merge_triggered=false`
- `timed_out=false`
- `heading_prior_source=flight_yaw`
- `pitch_prior_source=flight_pitch`
- chunking used `2` chunks: `[181, 170]`
- chunk 0 initial model: `181/181`
- chunk 1 initial model: `169/170`
- chunk model merger succeeded and produced a merged reconstruction with `343` images
- final matcher mode remained `spatial_heading_chunked`
- no vocab-tree stage executed

Runtime performance for the successful corrected subset:

- total processing: `2740.53` seconds
- chunk mapper: `1630.70` seconds
- mapper seconds per registered image: `4.75`
- merged components: `1`

This is the first hard proof that the Meadow registration problem was not only about removing the hanging fallback. The pipeline was also leaving accuracy on the table by trusting degenerate gimbal orientation EXIF instead of the informative flight orientation EXIF. Once that source-selection bug was fixed, the rebuilt Meadow hard slice passed cleanly without any fallback or recovery escalation.

## Final Hard Assessment

- Proven:
  - the multi-hour hanging vocab-tree fallback is removed from the GPS-first Meadow recovery path
  - Meadow now fails decisively with explicit failure metadata instead of hanging indefinitely when a chunk is unhealthy
  - the Meadow archive had a real EXIF-prior-selection bug: degenerate gimbal yaw/pitch were being preferred over informative flight yaw/pitch
  - after fixing orientation-source selection, the corrected Meadow chunk-4 rebuild passed end-to-end at `343/343` registered images with no fallback, no recovery escalation, and no timeout
- Also proven:
  - the original `148`-image failing harness was built from the pre-fix chunk plan, so it remains useful as a regression artifact but it is no longer the authoritative representation of the corrected Meadow chunk-4 problem
  - the corrected prior-aware chunk plan is materially different, so future Meadow work should benchmark against the rebuilt corrected subset, not only the legacy failing slice
