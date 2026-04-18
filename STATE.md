reason: rebuilding the SfM image for the monolithic global_mapper benchmark so GPU bundle adjustment and global positioning are actually available before the next AWS proof
last_step: reran the SfM image rebuild after adding `openimageio-tools`, confirmed CodeBuild 614 compiled and installed both Ceres CUDA/cuDSS and COLMAP successfully, then hit a post-build verifier false-negative in Dockerfile.base and separately found that the direct benchmark launcher still lacked the shared-staging ML stack fallback this branch relies on; patched both and reran focused unit tests plus py_compile successfully
next_unblocked_step: commit and push the verifier-plus-benchmark-fallback fixes, wait for the fresh Trigger ML Container Build plus Pages and CDK workflows to finish green, then run one capability snapshot against the rebuilt branch image before any new geometry_mix GPU benchmark
owner_action_needed: none
updated: 2026-04-18T01:09:49Z
