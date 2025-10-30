from __future__ import annotations

import itertools
from dataclasses import dataclass, replace
from importlib import import_module
from typing import Iterable, Sequence

_lambda_module = import_module('infrastructure.spaceport_cdk.lambda.drone_path.lambda_function')
AglConstraints = getattr(_lambda_module, 'AglConstraints')
SamplerConfig = getattr(_lambda_module, 'SamplerConfig')
build_sampler_config_from_env = getattr(_lambda_module, 'build_sampler_config_from_env')
two_pass_adaptive_sampling = getattr(_lambda_module, 'two_pass_adaptive_sampling')

from .dem_provider import DEG_LAT_FT, SyntheticDemProvider, deg_lon_ft_at_lat
from .validator import check_agl_bounds, enforce_spacing


@dataclass
class TuningResult:
  config: SamplerConfig
  metrics: dict
  agl_summary: dict[str, float]


def path_xy_to_latlon(
  path_ft: Sequence[tuple[float, float, float]],
  anchor_lat: float,
  anchor_lon: float,
) -> list[dict]:
  lon_scale_ft = deg_lon_ft_at_lat(anchor_lat)
  converted = []
  for index, (x_ft, y_ft, altitude_ft) in enumerate(path_ft):
    lat = anchor_lat + y_ft / DEG_LAT_FT
    lon = anchor_lon + x_ft / lon_scale_ft
    converted.append({'lat': lat, 'lon': lon, 'index': index, 'altitude': altitude_ft})
  return converted


def run_sampler(
  path_ft: Sequence[tuple[float, float, float]],
  provider: SyntheticDemProvider,
  config: SamplerConfig,
  agl: AglConstraints,
) -> tuple[dict, dict[str, float]]:
  path_latlon = path_xy_to_latlon(path_ft, provider.anchor_lat, provider.anchor_lon)
  result = two_pass_adaptive_sampling(path_latlon, provider, config, agl)
  agl_summary = check_agl_bounds(
    [(path_ft[i][0], path_ft[i][1], path_ft[i][2]) for i in range(len(path_ft))],
    provider.dataset,
    agl.min_agl_ft or 0,
    agl.max_agl_ft,
  )
  return result, agl_summary


def grid_search(
  path_ft: Sequence[tuple[float, float, float]],
  provider: SyntheticDemProvider,
  base_config: SamplerConfig,
  agl: AglConstraints,
  discovery_intervals: Iterable[float],
  dense_intervals: Iterable[float],
) -> list[TuningResult]:
  results: list[TuningResult] = []
  for discovery, dense in itertools.product(discovery_intervals, dense_intervals):
    cfg = replace(base_config, discovery_interval_ft=discovery, dense_interval_ft=dense)
    result, agl_summary = run_sampler(path_ft, provider, cfg, agl)
    results.append(TuningResult(config=cfg, metrics=result.metrics, agl_summary=agl_summary))
  return results


__all__ = ['TuningResult', 'run_sampler', 'grid_search']
