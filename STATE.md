reason: HMC Montana time capsule monitor (SfM -> 3DGS -> compress -> viewer gates)
last_step: 2026-05-21T11:58Z committed+pushed latest SfM poll artifacts to `agent-40136728-montana-time-capsule` (head [skip ci]; exact-head GH runs=0), keeping the canonical SageMaker SfM job untouched (still InProgress, CW last event 2026-05-21T00:01:36.365Z, S3 KeyCount=0). Details in logs/montana-time-capsule/STATE.md.
next_unblocked_step: poll SageMaker job `hmc-mtc-20260520T2015Z-sfm` until Completed; then run `python3 scripts/montana_time_capsule/cv_hr_time_capsule.py --dataset-id HMC --run-prefix hmc-mtc --subset-strategy hmc_full_2063_montana_time_capsule --input-s3-uri s3://spaceport-uploads/1778952912508-hmc-high-mountain-camp-images-flat.zip --expected-image-count 2063 --state-file logs/montana-time-capsule/hmc-state.json --profile brass-chunked --launch` exactly once to launch pinned 3DGS
owner_action_needed: none
updated: 2026-05-21T11:58Z
