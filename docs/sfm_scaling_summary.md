# SfM Scaling Notes (Full Dataset, Dec 2025)

- **Goal**: get ~286-image drone SfM to finish within 60m while keeping cost low.
- **Container change**: OpenSfM no-CSV profile now scales `processes` up to 16 cores (min 4) to leverage larger instances.
- **Best result**: `ml.c6i.4xlarge`, processes≈8 (auto), 60m cap; completed in ~55m (3299.7s). Outputs validated: 286/286 images registered, ~301k points, COLMAP ready. S3: `s3://spaceport-ml-processing-staging/colmap/2e4049c9-de03-47f8-b895-251986ebb6dc/`.
- **Cost estimate**: c6i.4xlarge processing on-demand ~\$0.65–\$0.70/hr; 0.92 hr wall time → ~\$0.60–\$0.65.
- **Other runs**:
  - c6i.2xlarge (processes=1) hit the 60m timeout earlier (242 shots) — too slow.
  - c6i.4xlarge (processes=4) stopped at 286 shots due to 60m cap before validation.
  - c6i.8xlarge benchmark aborted mid-run (Amdahl’s Law: serial reconstruction limited gains; higher hourly rate not justified without >50% speedup).
- **Recommendation**: continue with `ml.c6i.4xlarge` + processes up to 8–10; keep 60m cap. Only retest larger instances if targeting <30m wall time and willing to pay ~2× hourly for potential ~2× speedup.
