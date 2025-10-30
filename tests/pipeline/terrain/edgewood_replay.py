from __future__ import annotations

import math
from importlib import import_module
from pathlib import Path

_lambda_module = import_module('infrastructure.spaceport_cdk.lambda.drone_path.lambda_function')
AglConstraints = getattr(_lambda_module, 'AglConstraints')
build_sampler_config_from_env = getattr(_lambda_module, 'build_sampler_config_from_env')

from .dem_provider import SyntheticDemProvider, load_dem_dataset
from .tuner import run_sampler


def load_edgewood_path() -> list[tuple[float, float, float]]:
  radius = 1800.0
  points = []
  for i in range(180):
    angle = (i / 180.0) * 2 * math.pi
    x = math.cos(angle) * radius
    y = math.sin(angle) * radius
    altitude_ft = 450.0 + 120.0 * math.sin(angle * 2)
    points.append((x, y, altitude_ft))
  return points


def replay_edgewood(dem_id: str = 'mixed', point_budget: int = 140) -> dict:
  dataset = load_dem_dataset(dem_id, repo_root=Path(__file__).resolve().parents[2])
  provider = SyntheticDemProvider(dataset)
  path_ft = load_edgewood_path()
  config = build_sampler_config_from_env()
  metrics, agl_summary = run_sampler(path_ft, provider, config, AglConstraints(min_agl_ft=120.0, max_agl_ft=400.0), point_budget)
  return {'metrics': metrics, 'agl': agl_summary}


__all__ = ['replay_edgewood']
