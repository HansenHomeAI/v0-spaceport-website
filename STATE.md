reason: rebuilding the SfM image for the monolithic global_mapper benchmark so GPU bundle adjustment and global positioning are actually available before the next AWS proof
last_step: replaced the SfM base build with a source-built COLMAP 4.0.3 plus Ceres CUDA/cuDSS image, added content-addressed base-image selection in deploy.sh, and wired runtime GPU-BA preflight plus mapper/global-mapper GPU flags; focused local tests and syntax checks are green
next_unblocked_step: commit and push agent-39418949-sfm-global-mapper-benchmark, wait for Trigger ML Container Build plus Pages and CDK workflows to finish green, then run one capability snapshot against the rebuilt branch image before any new geometry_mix GPU benchmark
owner_action_needed: none
updated: 2026-04-17T22:45:42Z
