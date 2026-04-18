reason: rebuilding the SfM image for the monolithic global_mapper benchmark so GPU bundle adjustment and global positioning are actually available before the next AWS proof
last_step: confirmed from Ubuntu jammy package metadata that `/usr/bin/iconvert` is provided by `openimageio-tools`, then patched Dockerfile.base to install it after CodeBuild 613 failed during COLMAP configure with `OpenImageIO::iconvert` pointing at a missing binary
next_unblocked_step: commit and push the iconvert package fix, wait for Trigger ML Container Build plus Pages and CDK workflows on the new head to finish green, then run one capability snapshot against the rebuilt branch image before any new geometry_mix GPU benchmark
owner_action_needed: none
updated: 2026-04-18T00:46:33Z
