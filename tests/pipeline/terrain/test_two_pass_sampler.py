from __future__ import annotations

import math
import unittest
from importlib import import_module

_lambda_module = import_module('infrastructure.spaceport_cdk.lambda.drone_path.lambda_function')
AglConstraints = getattr(_lambda_module, 'AglConstraints')
build_sampler_config_from_env = getattr(_lambda_module, 'build_sampler_config_from_env')

from tests.pipeline.terrain.dem_provider import DEG_LAT_FT, SyntheticDemProvider, load_dem_dataset
from tests.pipeline.terrain.tuner import run_sampler
from tests.pipeline.terrain.validator import enforce_spacing


def build_test_path(radius_ft: float = 2000.0, altitude_ft: float = 420.0, samples: int = 140) -> list[tuple[float, float, float]]:
  nodes: list[tuple[float, float, float]] = []
  for i in range(samples):
    angle = (i / samples) * 2 * math.pi
    x = math.cos(angle) * radius_ft
    y = math.sin(angle) * radius_ft
    altitude = altitude_ft + 60.0 * math.sin(angle * 2)
    nodes.append((x, y, altitude))
  return nodes


class TerrainSamplerIntegrationTest(unittest.TestCase):
  def setUp(self) -> None:
    self.dataset = load_dem_dataset('ridge')
    self.provider = SyntheticDemProvider(self.dataset)

  def test_sampler_produces_spacing_compliant_safety_waypoints(self) -> None:
    path_ft = build_test_path()
    config = build_sampler_config_from_env()
    result, _ = run_sampler(
      path_ft,
      self.provider,
      config,
      AglConstraints(min_agl_ft=140.0, max_agl_ft=420.0),
      point_budget=110,
    )
    self.assertLessEqual(result.metrics['total_points_used'], 110)
    self.assertEqual(result.metrics['hazards_detected'], len(result.hazards))
    self.assertEqual(result.metrics['safety_waypoints'], len(result.safety_waypoints))
    safety_points = []
    for wp in result.safety_waypoints:
      x = (wp['lon'] - self.provider.anchor_lon) * self.provider.lon_scale_ft
      y = (wp['lat'] - self.provider.anchor_lat) * DEG_LAT_FT
      safety_points.append((x, y))
    if safety_points:
      self.assertTrue(enforce_spacing(safety_points, config.min_safety_spacing_ft))


if __name__ == '__main__':
  unittest.main()
