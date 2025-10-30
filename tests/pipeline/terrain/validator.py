from __future__ import annotations

import math
from typing import Iterable, Sequence

from .dem_provider import DemDataset, bilinear_sample


def enforce_spacing(points: Sequence[tuple[float, float]], min_spacing_ft: float) -> bool:
  min_sq = min_spacing_ft ** 2
  for i in range(len(points)):
    for j in range(i + 1, len(points)):
      dx = points[i][0] - points[j][0]
      dy = points[i][1] - points[j][1]
      if dx * dx + dy * dy + 1e-6 < min_sq:
        return False
  return True


def check_agl_bounds(
  path: Sequence[tuple[float, float, float]],
  dem: DemDataset,
  min_agl_ft: float,
  max_agl_ft: float | None,
) -> dict[str, float]:
  violations = 0
  max_deficit = 0.0
  for x, y, altitude_ft in path:
    ground_ft = bilinear_sample(dem, x, y)
    agl = altitude_ft - ground_ft
    if agl + 1e-6 < min_agl_ft:
      violations += 1
      max_deficit = max(max_deficit, min_agl_ft - agl)
    if max_agl_ft is not None and agl > max_agl_ft + 1e-6:
      violations += 1
  return {'violations': violations, 'max_deficit_ft': max_deficit}


def summarize_hazards(hazards: Iterable[dict]) -> dict[str, float]:
  count = 0
  worst = 0.0
  for hazard in hazards:
    count += 1
    worst = max(worst, float(hazard.get('severity', 0.0)))
  return {'count': count, 'max_severity': worst}


__all__ = ['enforce_spacing', 'check_agl_bounds', 'summarize_hazards']
