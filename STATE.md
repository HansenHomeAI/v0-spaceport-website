reason: rebuilding the SfM image for the monolithic global_mapper benchmark so GPU bundle adjustment and global positioning are actually available before the next AWS proof
last_step: confirmed the new CUDA/cuDSS image compiled Ceres CUDA objects in CodeBuild, identified the next blocker as missing OpenEXR development headers during COLMAP configure, patched Dockerfile.base with libopenexr-dev, and added a stop-after-seconds kill switch plus unit coverage to the direct SageMaker benchmark launcher so subset/full jobs can self-stop when they miss the speed gate
next_unblocked_step: commit and push the OpenEXR plus benchmark-stop-gate changes, wait for Trigger ML Container Build plus Pages and CDK workflows on the new head to finish green, then run one capability snapshot against the rebuilt branch image before any new geometry_mix GPU benchmark
owner_action_needed: none
updated: 2026-04-18T00:31:50Z
