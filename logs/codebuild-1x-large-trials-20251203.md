# CodeBuild 1x-large Trials (app-layer)

Branch: agent-12837465-codebuild-efficiency
Date: $(date -Iseconds)

## Results
- sfm: SUCCEEDED, compute BUILD_GENERAL1_LARGE, BUILD phase ~784s (~13.1m), build id spaceport-ml-containers:7c2eb33b-74bf-4620-a160-04307c6a44d1
- 3dgs: SUCCEEDED, compute BUILD_GENERAL1_LARGE, BUILD phase ~826s (~13.8m), build id spaceport-ml-containers:fd001ef0-6867-471b-a8f2-bef428919573
- compressor: SUCCEEDED, compute BUILD_GENERAL1_LARGE, BUILD phase ~1324s (~22.1m), build id spaceport-ml-containers:50f08b5d-3ad4-40ee-a60c-de98555b9f16

## Notes
- All app-layer builds completed within the 45m window on 1x-large using cached base layers from ECR.
- Base rebuilds still expected to use 2x-large via workflow override when `base_only` is true or when a higher compute override is explicitly passed.
