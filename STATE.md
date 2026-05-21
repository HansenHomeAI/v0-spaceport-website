reason: HMC Montana time capsule monitor (SfM -> 3DGS -> compress -> viewer gates)
last_step: 2026-05-21T02:56Z verified git head (2456f84f), AWS identity, HMC S3 archive proof (8,646,557,673 bytes; LastModified=2026-05-16T17:35:27Z), and SageMaker SfM still InProgress with CloudWatch lastEvent still 2026-05-21T00:01:36Z; outputs empty (see logs/montana-time-capsule/STATE.md)
next_unblocked_step: poll SageMaker job `hmc-mtc-20260520T2015Z-sfm` until Completed; then run `python3 scripts/montana_time_capsule/hmc_time_capsule.py --launch` exactly once to launch pinned 3DGS
owner_action_needed: none
updated: 2026-05-21T02:56Z
