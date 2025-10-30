from __future__ import annotations

import json
import math
from dataclasses import dataclass
from importlib import import_module
from pathlib import Path
from typing import List, Sequence, Tuple

_elevation_module = import_module('infrastructure.spaceport_cdk.lambda.drone_path.elevation_provider')
ElevationProvider = getattr(_elevation_module, 'ElevationProvider')
LatLon = getattr(_elevation_module, 'LatLon')

DEG_LAT_FT = 364000.0


def deg_lon_ft_at_lat(latitude_deg: float) -> float:
  return 288200.0 * math.cos(math.radians(latitude_deg))


@dataclass
class DemDataset:
  id: str
  name: str
  description: str
  cell_size_ft: float
  grid_size: Tuple[int, int]
  origin_ft: Tuple[float, float]
  elevations_ft: List[List[float]]

  @property
  def min_elevation_ft(self) -> float:
    return min(min(row) for row in self.elevations_ft)

  @property
  def max_elevation_ft(self) -> float:
    return max(max(row) for row in self.elevations_ft)


def load_dem_dataset(dem_id: str, repo_root: Path | None = None) -> DemDataset:
  root = repo_root or Path(__file__).resolve().parents[3]
  dem_path = root / 'web' / 'public' / 'dem' / f'{dem_id}.json'
  if not dem_path.exists():
    raise FileNotFoundError(f'Synthetic DEM not found: {dem_path}')
  payload = json.loads(dem_path.read_text())
  return DemDataset(
    id=payload['id'],
    name=payload['name'],
    description=payload['description'],
    cell_size_ft=float(payload['cellSizeFt']),
    grid_size=(int(payload['gridSize'][0]), int(payload['gridSize'][1])),
    origin_ft=(float(payload['originFt'][0]), float(payload['originFt'][1])),
    elevations_ft=[[float(v) for v in row] for row in payload['elevationsFt']],
  )


def bilinear_sample(dataset: DemDataset, x_ft: float, y_ft: float) -> float:
  cols, rows = dataset.grid_size
  local_x = (x_ft - dataset.origin_ft[0]) / dataset.cell_size_ft
  local_y = (y_ft - dataset.origin_ft[1]) / dataset.cell_size_ft

  ix = math.floor(local_x)
  iy = math.floor(local_y)
  fx = local_x - ix
  fy = local_y - iy

  ix0 = max(0, min(cols - 1, ix))
  iy0 = max(0, min(rows - 1, iy))
  ix1 = max(0, min(cols - 1, ix0 + 1))
  iy1 = max(0, min(rows - 1, iy0 + 1))

  v00 = dataset.elevations_ft[iy0][ix0]
  v10 = dataset.elevations_ft[iy0][ix1]
  v01 = dataset.elevations_ft[iy1][ix0]
  v11 = dataset.elevations_ft[iy1][ix1]

  interp_x0 = v00 * (1 - fx) + v10 * fx
  interp_x1 = v01 * (1 - fx) + v11 * fx
  return interp_x0 * (1 - fy) + interp_x1 * fy


class SyntheticDemProvider(ElevationProvider):
  """Elevation provider that samples DEM grids bundled with the repository."""

  def __init__(self, dataset: DemDataset, anchor_lat: float = 37.62131, anchor_lon: float = -122.37896) -> None:
    self.dataset = dataset
    self.anchor_lat = anchor_lat
    self.anchor_lon = anchor_lon
    self.lon_scale_ft = deg_lon_ft_at_lat(anchor_lat)

  def sample(self, points: Sequence[LatLon]) -> List[float]:  # meters AMSL
    elevations_m: List[float] = []
    for lat, lon in points:
      x_ft = (lon - self.anchor_lon) * self.lon_scale_ft
      y_ft = (lat - self.anchor_lat) * DEG_LAT_FT
      ground_ft = bilinear_sample(self.dataset, x_ft, y_ft)
      elevations_m.append(ground_ft * 0.3048)
    return elevations_m

  def max_batch_size(self) -> int:
    return 256


__all__ = [
  'DemDataset',
  'SyntheticDemProvider',
  'load_dem_dataset',
  'bilinear_sample',
]
