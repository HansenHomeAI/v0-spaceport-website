Evidence stamp (UTC): 20260524T104511Z
Run: friday-mtc-20260524T0001Z
Input: s3://spaceport-uploads-staging/1779580731329-friday-20260522-new-property-flat.zip (expected images: 1776)

SfM processing
- job: friday-mtc-20260524T0001Z-sfm
- status: Completed
- started: 2026-05-23T18:03:51.397000-06:00
- ended: 2026-05-24T02:33:44.726000-06:00
- output: s3://spaceport-ml-processing-staging/manual-validations/friday-mtc-20260524T0001Z/colmap

3DGS training
- job: friday-mtc-20260524T0001Z-3dgs
- status: InProgress (secondary: Training)
- started: 2026-05-24T03:06:51.507000-06:00
- last_modified: 2026-05-24T03:08:53-06:00
- output: s3://spaceport-ml-processing-staging/3dgs/friday-mtc-20260524T0001Z/
- image: 975050048887.dkr.ecr.us-west-2.amazonaws.com/spaceport/3dgs@sha256:482c1789b2d885beccf351b68d50e4b8135c43d5921c2379b0ba5fb152ed15db
- cw: /aws/sagemaker/TrainingJobs stream friday-mtc-20260524T0001Z-3dgs/algo-1-1779613610
- last_cw_event_utc (from state): 2026-05-24T09:14:16.268000Z
