from __future__ import annotations

import math
import unittest
from importlib import import_module

_lambda_module = import_module('infrastructure.spaceport_cdk.lambda.drone_path.lambda_function')
AglConstraints = getattr(_lambda_module, 'AglConstraints')
build_sampler_config_from_env = getattr(_lambda_module, 'build_sampler_config_from_env')
haversine_ft = getattr(_lambda_module, 'haversine_ft')

from tests.pipeline.terrain.dem_provider import SyntheticDemProvider, load_dem_dataset
from tests.pipeline.terrain.tuner import run_sampler


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
    )
    self.assertLess(result.metrics['total_points_used'], 400)
    self.assertEqual(result.metrics['hazards_detected'], len(result.hazards))
    self.assertEqual(result.metrics['safety_waypoints'], len(result.safety_waypoints))
    if result.safety_waypoints:
      min_distance = min(
        haversine_ft(result.safety_waypoints[i]['lat'], result.safety_waypoints[i]['lon'], result.safety_waypoints[j]['lat'], result.safety_waypoints[j]['lon'])
        for i in range(len(result.safety_waypoints))
        for j in range(i + 1, len(result.safety_waypoints))
      ) if len(result.safety_waypoints) > 1 else config.min_safety_spacing_ft
      self.assertGreaterEqual(min_distance + 1e-6, config.min_safety_spacing_ft)


if __name__ == '__main__':
  unittest.main()
