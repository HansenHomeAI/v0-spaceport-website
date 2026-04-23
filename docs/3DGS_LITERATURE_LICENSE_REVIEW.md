# 3DGS Literature License Review

This branch uses papers as behavioral guidance only. No external implementation code has been copied, vendored, ported, or translated.

| Reference | URL | Use in this branch | External code used | License / approval status |
| --- | --- | --- | --- | --- |
| CityGaussian | https://www.ecva.net/papers/eccv_2024/papers_ECCV/papers/02472.pdf | Coarse global prior and scaffold-to-leaf initialization strategy | None | Paper guidance only; no code approval required |
| VastGaussian | https://openaccess.thecvf.com/content/CVPR2024/papers/Lin_VastGaussian_Vast_3D_Gaussians_for_Large_Scene_Reconstruction_CVPR_2024_paper.pdf | Visibility-aware partitioning and support statistics | None | Paper guidance only; no code approval required |
| BlockGaussian | https://arxiv.org/abs/2504.09048 | Content-aware block support, load balance, and geometry-first gates | None | Paper guidance only; no code approval required |
| Consistency-preserving GS | https://www.sciencedirect.com/science/article/pii/S0097849325003346 | Overlap and boundary consistency scoring | None | Paper guidance only; no code approval required |
| Horizon-GS | https://openaccess.thecvf.com/content/CVPR2025/html/Jiang_Horizon-GS_Unified_3D_Gaussian_Splatting_for_Large-Scale_Aerial-to-Ground_Scenes_CVPR_2025_paper.html | Conditional horizon/far-field review trigger | None | Paper guidance only; no code approval required |
| Momentum-GS | https://arxiv.org/abs/2412.04887 | Conditional global-teacher fallback concept only | None | Paper guidance only; no code approval required |
| CityGaussianV2 | https://dekuliutesla.github.io/CityGaussianV2/static/paper/CityGaussianV2.pdf | Conditional geometry-regularization pivot concept | None | Paper guidance only; no code approval required |
| GeoGaussian | https://www.ecva.net/papers/eccv_2024/papers_ECCV/papers/05218.pdf | Conditional depth/normal regularization pivot concept | None | Paper guidance only; no code approval required |

Implementation note: all code changes are local Spaceport pipeline logic: manifest support metadata, scaffold PLY filtering, offline merge arbitration, and comparative review gates.
