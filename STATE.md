reason: project-level continuation toward production-ready huge-scene tiled SfM; automation is active and must remain active until final proof has no unresolved caveats or owner explicitly stops it.
last_step: 2026-05-13T03:04:14Z sample8 CPU-cache r2 canary md1-sample8-cpu-r2-1778634147 failed after training because ns-eval had zero eval images (IndexError list index out of range); model artifact preserved quality_eval/ns_eval_stdout.log and nerfstudio_config.yml; patched trainer to force fraction eval split with train_split_fraction=0.75 for tiny <=20 frame canaries; 25 focused tests and py_compile passed locally. Prior md1-sample8-cpu-qc-1778632320 was externally stopped before container start via StopTrainingJob CloudTrail.
next_unblocked_step: Commit/push the tiny-canary heldout split patch, wait exact-head CDK/container build, verify ECR digest changes, then relaunch only the cheap sample8 canary with NS_CACHE_IMAGES=cpu and the patched split.
owner_action_needed: none
active_jobs: []
active_workflows: []
active_codebuild: none
blocked_by_external_capacity: false
branch: agent-73948216-sfm-production-spine
head: bf279d3d7a88a029cabc42ca547cd9b9822521b4
updated: 2026-05-13T03:04:14Z
