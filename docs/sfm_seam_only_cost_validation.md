# MD1 Seam-Only Cost Validation

## Goal

Prove that the hard MD1 `geometry_mix` probe can still pass after removing the old parent `*_merge_mapper` reruns, and measure the real cost delta on the live branch image.

Branch:

- `agent-86041273-sfm-seam-only-cost`

Proof commit:

- `b9289a2b` (`fix: skip redundant parent seam work`)

Live branch image:

- `975050048887.dkr.ecr.us-west-2.amazonaws.com/spaceport/sfm@sha256:bdb5a96884e876355bb1e7e8a0e7119dc7fd52f3e86d8be6db9673e8e1588756`

## Control vs Seam-Only Result

Control job:

- `md1candg15-1775878097`
- planner: `footprint_graph_v1`
- parent merge behavior: old parent mapper reruns
- result: `467/467` images registered
- runtime: `11116.88s`

Seam-only job:

- `md1seamgeomcost-1775942924`
- planner: `footprint_graph_v1`
- parent merge mode: `seam_only_v1`
- result: `467/467` images registered
- runtime: `6761.67s`

Measured delta:

- total runtime reduced by `4355.21s` (`39.18%`)
- chunk mapper time reduced from `8328.17s` to `3587.85s` (`56.92%`)
- quality gate still passed
- parent `adjacent_merge_mapper` stages: `0`
- parent `merge_bridge_mapper` stages: `0`

## Hard Proof

The live CloudWatch log for `md1seamgeomcost-1775942924` contains:

- `Skipping parent seam refinement for merge 2; raw model_merger retained all 380 source images`
- `Skipping parent seam refinement for merge 3; raw model_merger retained all 467 source images`
- `🖼️ Images registered: 467`
- `🎯 3D points: 365474`
- `⏱️ Processing time: 6761.67 seconds`

The machine-readable metadata confirms:

- `parent_merge_mode: seam_only_v1`
- `chunk_recovery_mode: seam_only_leaf_partial`
- `adjacent_chunk_merge_triggered: false`
- `merge_bridge_recovery_triggered: true`
- `parent_seam_registration_cycles: 2`
- `chunk_merge_proof.pre_merge_retention_ratio: 1.0`
- `timings` contains seam-only parent stages:
  - `chunk_01_02_merge_bridge_image_registrator_01_seconds`
  - `chunk_01_02_merge_bridge_point_triangulator_01_seconds`
  - `chunk_01_02_merge_bridge_image_registrator_02_seconds`
  - `chunk_01_02_merge_bridge_point_triangulator_02_seconds`
  - `chunk_01_02_merge_bridge_bundle_adjuster_seconds`
- `timings` contains no parent mapper stages named:
  - `adjacent_merge_mapper`
  - `merge_bridge_mapper`

## What Changed In Cost Distribution

Old passing control:

- leaf and parent mapper time dominated the run
- parent bridge mapper alone cost `3354.11s`
- adjacent merge mapper cost another `1618.87s`
- raw merge itself cost only `42.64s`

New seam-only run:

- leaf mapper time still dominates, but parent mapper reruns are gone
- seam-only parent work shifted to:
  - pair import
  - `image_registrator`
  - `point_triangulator`
  - local bridge bundle adjustment
  - final global bundle adjustment
- raw merge plus seam-only parent work cost `677.03s`
- final global bundle adjustment still cost `350.80s`

So the win came from deleting redundant parent reconstruction, not from making the leaf chunks smaller.

## Sparse Cleanup Result

The seam-only run now writes filtered sparse output by default:

- raw sparse points: `396143`
- filtered sparse points: `365474`
- removed weak points: `30669` (`7.74%`)
- core filtered points: `329021`
- far context points preserved: `36453`

The far-context layer keeps low-support distant context points under tighter reprojection filtering instead of deleting all far points blindly.

## Limits Of This Proof

What this proof does establish:

- the hard `geometry_mix` probe still passes
- the old parent mapper reruns are removed on the live branch image
- runtime improved materially on the same dataset slice

What this proof does not establish:

- it is not the `10x` target
- it is not a full `5000`-image MD1 proof
- it does not yet prove efficient scaling to the future full dataset ladder

## Next Step

Run the same seam-only path on the `1000`-image and `2000`-image MD1 ladders. If mapper time still dominates there, the next optimization target is leaf-chunk pair density and the final global bundle adjustment, not parent merge redundancy.
