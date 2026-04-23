reason: implementing a stock COLMAP hierarchical benchmark path on a fresh development-based branch so we can run the exact ladder_2000 input and compare it against the mature pipeline baseline
last_step: stockhier2000-1776969322 failed before mapping because the wrapper passed unsupported hierarchical_mapper --num_threads and accidentally used the 300-image test ZIP
next_unblocked_step: rebuild the branch image with the unsupported flag removed, then rerun stock hierarchical against the verified 2013-image ZIP at s3://spaceport-ml-processing-staging/manual-validations/stockhierprep-1776966189/prep/ladder_2000_exact.zip
owner_action_needed: none
updated: 2026-04-23T19:44:00Z
