reason: validating whether monolithic `global_mapper` can beat the ladder_2000 chunked baseline once the shipped SfM image has real GPU sparse bundle adjustment and GPU global positioning enabled
last_step: pushed `8a7a1eca`, watched Trigger ML Container Build fail in CodeBuild 622 before the real rebuild even started because the Dockerfile parsed `c++` as a new instruction; the preprocessor-check verifier logic was fine, but the heredoc split the `RUN` step. Patched `infrastructure/containers/sfm/Dockerfile.base` to generate `/tmp/check_ceres_config.cc` with `printf` inside the same shell command instead of a heredoc
next_unblocked_step: bump `web/trigger-dev-build.txt`, commit and push the Dockerfile syntax fix, watch Pages/CDK/Trigger ML Container Build for the new SHA, confirm the image actually publishes, rerun the cheap capability snapshot only if the image build succeeds, and only then spend on another real-graph benchmark
owner_action_needed: none
updated: 2026-04-18T05:43:05Z
