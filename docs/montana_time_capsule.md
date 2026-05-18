# Montana Time Capsule Stack

This branch preserves the Montana-era training stack without using mutable
`latest` images or later production-spine container changes.

## Default CV-HR Profile

The default profile is `brass-chunked` because it is the strongest exact SfM
digest from the published Montana viewer lineage:

- SfM: `975050048887.dkr.ecr.us-west-2.amazonaws.com/spaceport/sfm@sha256:8fe38e3413e09954dcad77b8436c2a04defd20a39bdae1b3df573c504ef98811`
- 3DGS: `975050048887.dkr.ecr.us-west-2.amazonaws.com/spaceport/3dgs@sha256:482c1789b2d885beccf351b68d50e4b8135c43d5921c2379b0ba5fb152ed15db`
- Compression: `975050048887.dkr.ecr.us-west-2.amazonaws.com/spaceport/compressor@sha256:a0784727da1870ce9caa4774dc831a32fb96cd1574df389cf9093fbf18f4f4ab`

The runner launches each stage directly in SageMaker so the historical SfM
environment is preserved. The deployed Step Functions stack is not used for SfM
because it currently hardcodes a different SfM environment.

## CV-HR Automation Command

```bash
python3 scripts/montana_time_capsule/cv_hr_time_capsule.py --launch
```

The command is idempotent through `logs/montana-time-capsule/cv-hr-state.json`:

1. Search `s3://spaceport-uploads-staging/` for a CV-HR zip.
2. Read only the ZIP central directory and require exactly `1710` image files.
3. Launch SfM with the pinned Montana profile.
4. On later runs, advance from completed SfM to 3DGS, then compression.
5. Stop with an explicit failed state if any SageMaker stage fails.

Use `--profile horsetail-gps` for the exact Horsetail SfM fallback. The
`meadow-tag-only` profile is intentionally not exact because the historical
SageMaker job recorded only a mutable tag.
