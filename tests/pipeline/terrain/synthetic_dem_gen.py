from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Callable

from .dem_provider import DemDataset

@dataclass
class DemSpec:
  id: str
  name: str
  description: str
  generator: Callable[[float, float], float]


def _make_dataset(spec: DemSpec, size: int = 48, cell_size_ft: float = 150.0) -> DemDataset:
  half = (size - 1) / 2.0
  elevations: list[list[float]] = []
  for j in range(size):
    row: list[float] = []
    for i in range(size):
      dx = (i - half) * cell_size_ft
      dy = (j - half) * cell_size_ft
      row.append(round(spec.generator(dx, dy), 3))
    elevations.append(row)
  origin = (- (size // 2) * cell_size_ft, - (size // 2) * cell_size_ft)
  return DemDataset(
    id=spec.id,
    name=spec.name,
    description=spec.description,
    cell_size_ft=cell_size_ft,
    grid_size=(size, size),
    origin_ft=origin,
    elevations_ft=elevations,
  )


DEMO_LIBRARY = {
  spec.id: spec
  for spec in [
    DemSpec('flat', 'Flat Prairie', 'Baseline plane for sanity checks.', lambda dx, dy: 4300.0),
    DemSpec('sinusoid', 'Sinusoid Hills', 'Smooth rolling sine/cosine terrain.', lambda dx, dy: 4200.0 + 180.0 * math.sin(dx / 1200.0) * math.cos(dy / 900.0)),
    DemSpec(
      'ridge',
      'Knife Ridge',
      'Sharp ridge running north-south.',
      lambda dx, dy: 4100.0 + 600.0 * math.exp(-(dx ** 2) / (2 * (400.0 ** 2))) - 180.0 * math.exp(-(dy ** 2) / (2 * (1700.0 ** 2))),
    ),
    DemSpec(
      'mountain',
      'Mountain Range',
      'Twin peaks with saddle valley.',
      lambda dx, dy: 4000.0
      + 900.0 * math.exp(-(((dx + 1200.0) ** 2 + (dy + 800.0) ** 2) / (2 * (700.0 ** 2))))
      + 1100.0 * math.exp(-(((dx - 900.0) ** 2 + (dy - 600.0) ** 2) / (2 * (600.0 ** 2))))
      - 250.0 * math.exp(-(((dx) ** 2 + (dy) ** 2) / (2 * (1500.0 ** 2)))),
    ),
    DemSpec(
      'cliff',
      'Mesa Cliff',
      'Abrupt escarpment with gentle ramp.',
      lambda dx, dy: 3900.0 + (600.0 if dx < -300.0 else 50.0 * math.exp(-(dx - 200.0) / 400.0)) - 120.0 * math.exp(-(dy ** 2) / (2 * (1000.0 ** 2))),
    ),
    DemSpec(
      'mixed',
      'Mixed Badlands',
      'Interleaved bluffs, gullies, and plateaus.',
      lambda dx, dy: 3700.0
      + 220.0 * math.sin((dx + dy) / 700.0)
      + 160.0 * math.cos((dx - dy) / 900.0)
      + 400.0 * math.exp(-(((dx - 800.0) ** 2 + (dy + 500.0) ** 2) / (2 * (500.0 ** 2))))
      - 500.0 * math.exp(-(((dx + 700.0) ** 2 + (dy - 1000.0) ** 2) / (2 * (450.0 ** 2))))
      + 90.0 * math.sin(dx / 450.0),
    ),
  ]
}


def generate_dem(dem_id: str, size: int = 48, cell_size_ft: float = 150.0) -> DemDataset:
  if dem_id not in DEMO_LIBRARY:
    raise KeyError(f'Unknown synthetic DEM id: {dem_id}')
  return _make_dataset(DEMO_LIBRARY[dem_id], size=size, cell_size_ft=cell_size_ft)


__all__ = ['generate_dem', 'DEMO_LIBRARY']
