reason: Montana time capsule monitor (SfM -> 3DGS -> compress -> viewer gates)
last_step: 2026-05-26T09:25:23Z HMC canonical run re-verified terminal (SfM/3DGS/compression Completed); SageMaker InProgress=0/0; S3 outputs present (staging+prod); prod meta HTTP 200 (+Origin); hosted preview viewer base/sky/no-sky HTTP 200; GH branch snapshot shows latest Pages+CDK green; exact-head runs=0 (head [skip ci]); evidence stamp 20260526T092523Z recorded in logs/montana-time-capsule/.
next_unblocked_step: no compute to launch; optional deeper viewer QA (camera/sky artifacts + input-vs-render checks) before PR/closeout; otherwise idle monitor.
[2026-05-22T15:36:42Z] heartbeat -> terminal reconfirmed (no spend) -> idle
[2026-05-22T15:37:51Z] heartbeat -> fresh reconfirmed (no spend) -> commit+push evidence
[2026-05-22T15:38:34Z] heartbeat -> fresh reconfirmed (no spend) -> commit+push evidence
[2026-05-22T15:47:04Z] heartbeat -> no-spend; no new jobs launched -> commit/push ledger
[2026-05-23T10:14:00Z] heartbeat -> terminal + S3 bundle + viewer/proxy HTTP200 + CI proof -> commit+push ledger
[2026-05-23T10:26:30Z] heartbeat -> terminal + S3 bundle + viewer/proxy HTTP200 -> commit+push ledger
[2026-05-23T10:31:23Z] post-heartbeat -> recorded git head + exact-head GH runs -> commit+push ledger
[2026-05-23T12:23:12Z] heartbeat -> boto3 aws/sm/s3 + viewer/proxy HTTP200 + GH REST snapshot -> commit+push ledger
[2026-05-23T13:04:40Z] heartbeat -> awscli sm/s3 + viewer/proxy HTTP200 + gh snapshot -> idle
[2026-05-23T13:06:43Z] postpush -> recorded gh runs for new head -> idle
[2026-05-23T14:04:11Z] heartbeat -> awscli sm/s3 + viewer/proxy HTTP200 + gh snapshot -> commit+push ledger
[2026-05-23T14:05:08Z] postpush -> recorded gh runs for new head -> idle
[2026-05-23T18:23:52Z] heartbeat -> awscli sm/s3 + viewer/proxy HTTP200 + gh snapshot -> commit+push ledger
[2026-05-23T18:25:50Z] postpush -> recorded gh runs for new head -> idle
[2026-05-24T10:05:12Z] heartbeat -> SfM Completed; 3DGS InProgress; S3+GH snapshots -> commit+push ledger
[2026-05-24T17:07:48Z] heartbeat -> HMC terminal reconfirm + viewer HTTP check + GH exact-head snapshot -> idle
[2026-05-24T17:09:25Z] postpush -> recorded gh runs for new head (30f84f0df76cda20c74c63f0ac437cd3db45e52f) -> idle
[2026-05-24T17:10:33Z] postpush -> recorded gh runs for new head (3f8446bba0db593d81cde261060c9d06a9d7d4e5) -> idle
[2026-05-24T17:11:10Z] postpush -> recorded gh runs for new head (657b12f5c629e7c61566c39c4972e7d24787f535) -> idle
[2026-05-24T20:25:02Z] heartbeat -> friday-mtc terminal + public meta HTTP200 + viewer screenshots -> next: optional deeper visual QA
[2026-05-24T20:46:31Z] heartbeat -> friday-mtc terminal + public meta HTTP200 + viewer sky/no-sky HTTP200 + exact-head CI 0 ([skip ci]) -> next: optional deeper visual QA
[2026-05-24T21:28:39Z] heartbeat -> friday-mtc terminal + public meta HTTP200 + viewer sky/no-sky HTTP200 -> next: optional deeper visual QA
[2026-05-24T22:05:20Z] heartbeat -> friday-mtc terminal reconfirm (no spend); InProgress=0; S3 present; gh snapshot -> commit+push ledger
[2026-05-24T22:48:33Z] heartbeat -> friday-mtc terminal reconfirm (no spend); InProgress=0; meta+viewer reachable; gh snapshot -> commit+push ledger
[2026-05-24T23:07:29Z] heartbeat -> friday-mtc terminal reconfirm; ran guarded cv_hr_time_capsule --launch (status=completed, no dupes); evidence stamp 20260524T230543Z -> idle
[2026-05-25T01:45:20Z] heartbeat -> hmc-mtc terminal reconfirm (no spend); InProgress=0; staging meta + viewer/proxy HTTP200; exact-head CI 0 ([skip ci]) -> commit+push ledger
[2026-05-25T01:47:31Z] postpush -> recorded gh runs for new head (e0978b91c4fa0ad9139e0d931241c4f1bc40638c) -> idle
[2026-05-25T01:47:31Z] heartbeat -> friday-mtc terminal reconfirm; public meta+viewer HTTP200; cv_hr_time_capsule --launch ran (no dupes); inprogress 0/0 -> next: optional deeper visual QA
[2026-05-25T07:11:03Z] heartbeat -> friday-mtc terminal reconfirm (no spend); InProgress=0/0; public meta+viewer HTTP200; new evidence stamp 20260525T071103Z -> next: idle
[2026-05-25T07:13:27Z] postpush -> recorded gh runs for new head (ef1d4f2c7d61a3f50c87681215a38ab5183e73b5); exact-head expected 0 ([skip ci]) -> idle
[2026-05-25T13:06:54Z] heartbeat -> friday-mtc terminal reconfirm (no spend); InProgress=0/0; S3 present; exact-head GH snapshot -> commit/push ledger
[2026-05-25T13:29:56Z] heartbeat -> hmc-mtc terminal reconfirm (no spend); InProgress=0/0; public meta HTTP200; hosted viewer bundle URLs HTTP200; latest Pages+CDK green -> commit/push ledger
[2026-05-25T17:45:42Z] heartbeat -> hmc-mtc terminal reconfirm (no spend); InProgress=0/0; S3 present; prod meta+viewer HTTP200; gh branch+exact-head snapshots -> next: idle
[2026-05-25T17:48:33Z] postpush -> recorded gh runs for new head (67647a42; skip ci); exact-head workflows 0 -> next: idle
[2026-05-26T04:45:25Z] heartbeat -> hmc-mtc terminal reconfirm (no spend); InProgress=0/0; S3 present; prod meta+viewer HTTP200; gh branch+exact-head snapshots -> next: idle
[2026-05-26T07:47:57Z] heartbeat -> hmc-mtc terminal reconfirm (no spend); InProgress=0/0; S3 present; prod meta HTTP200; viewer base/sky/no-sky HTTP200; gh snapshot -> commit+push ledger
[2026-05-26T09:25:23Z] heartbeat -> hmc-mtc terminal reconfirm (no spend); InProgress=0/0; S3 present; prod meta HTTP200 (+Origin); viewer base/sky/no-sky HTTP200; gh snapshot -> commit+push ledger
[2026-05-26T09:29:46Z] postpush -> recorded exact-head GH runs for 69fd4410 (expected empty; [skip ci]) -> idle
[2026-05-26T09:30:52Z] postpush -> recorded exact-head GH runs for c7be51fc (expected empty; [skip ci]) -> idle
[2026-05-26T09:31:45Z] postpush -> recorded exact-head GH runs for 1dbc1abc (expected empty; [skip ci]) -> idle
