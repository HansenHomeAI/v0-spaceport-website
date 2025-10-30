from __future__ import annotations

import itertools
import json
from dataclasses import dataclass, replace
from datetime import datetime
from importlib import import_module
from pathlib import Path
from typing import Iterable, Sequence

import sys

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tests.pipeline.terrain.dem_provider import (
    DEG_LAT_FT,
    SyntheticDemProvider,
    bilinear_sample,
    load_dem_dataset,
)
from tests.pipeline.terrain.tuner import run_sampler

_lambda_module = import_module('infrastructure.spaceport_cdk.lambda.drone_path.lambda_function')
SamplerConfig = getattr(_lambda_module, 'SamplerConfig')
AglConstraints = getattr(_lambda_module, 'AglConstraints')
SpiralDesigner = getattr(_lambda_module, 'SpiralDesigner')


@dataclass
class PathNode:
    x: float
    y: float
    phase: str
    distance: float


def map_battery_to_bounces(minutes: float) -> int:
    n = round(5 + 0.3 * (minutes - 10))
    return min(12, max(3, n))


def calculate_hold_radius(battery_minutes: float) -> float:
    base_rhold = 1595.0
    base_battery = 10.0
    return base_rhold * (battery_minutes / base_battery)


def build_spiral_waypoints(slices: int, battery_minutes: float) -> list[PathNode]:
    designer = SpiralDesigner()
    N = map_battery_to_bounces(battery_minutes)
    params = {
        'slices': slices,
        'N': N,
        'r0': 150.0,
        'rHold': calculate_hold_radius(battery_minutes),
    }
    spiral_slices = designer.compute_waypoints(params)
    nodes: list[PathNode] = []
    for slice_idx, slice_waypoints in enumerate(spiral_slices):
        for wp in slice_waypoints:
            distance = (wp.get('distance', 0.0) if 'distance' in wp else (wp['x'] ** 2 + wp['y'] ** 2) ** 0.5)
            nodes.append(PathNode(x=wp['x'], y=wp['y'], phase=wp.get('phase', f'slice_{slice_idx}'), distance=distance))
    return nodes


def desired_agl_profile(node: PathNode, first_distance: float, max_outbound_state: dict, min_agl: float, max_agl: float | None) -> float:
    dist_from_center = (node.x ** 2 + node.y ** 2) ** 0.5
    if node.phase.startswith('outbound_start'):
        max_outbound_state['altitude'] = min_agl
        max_outbound_state['distance'] = dist_from_center
        desired_agl = min_agl
    elif 'outbound' in node.phase or 'hold' in node.phase:
        additional = max(0.0, dist_from_center - first_distance)
        desired_agl = min_agl + additional * 0.20
        if desired_agl > max_outbound_state['altitude']:
            max_outbound_state['altitude'] = desired_agl
            max_outbound_state['distance'] = dist_from_center
    elif 'inbound' in node.phase:
        dist_from_max = max(0.0, max_outbound_state['distance'] - dist_from_center)
        desired_agl = max(min_agl, max_outbound_state['altitude'] + dist_from_max * 0.10)
    else:
        additional = max(0.0, dist_from_center - first_distance)
        desired_agl = min_agl + additional * 0.20
    if max_agl is not None:
        desired_agl = min(desired_agl, max_agl)
    return max(min_agl, desired_agl)


def build_path_for_dataset(dataset, slices: int, battery_minutes: float, min_agl: float, max_agl: float | None) -> list[tuple[float, float, float]]:
    nodes = build_spiral_waypoints(slices, battery_minutes)
    if not nodes:
        return []
    first_distance = (nodes[0].x ** 2 + nodes[0].y ** 2) ** 0.5
    state = {'altitude': min_agl, 'distance': first_distance}
    path: list[tuple[float, float, float]] = []
    for node in nodes:
        desired_agl = desired_agl_profile(node, first_distance, state, min_agl, max_agl)
        ground_ft = bilinear_sample(dataset, node.x, node.y)
        altitude_ft = ground_ft + desired_agl
        path.append((node.x, node.y, altitude_ft))
    return path


def iter_configs(base: SamplerConfig) -> Iterable[SamplerConfig]:
    yield base
    discovery_values = [360.0, 400.0, 450.0]
    dense_values = [30.0, 35.0, 40.0]
    medium_values = [100.0, 120.0, 140.0]
    sparse_values = [260.0, 300.0, 360.0]
    discovery_fraction_values = [0.25, 0.30, 0.35]
    for discovery, dense, medium, sparse, fraction in itertools.product(
        discovery_values, dense_values, medium_values, sparse_values, discovery_fraction_values
    ):
        yield replace(
            base,
            discovery_interval_ft=discovery,
            dense_interval_ft=dense,
            medium_interval_ft=medium,
            sparse_interval_ft=sparse,
            discovery_fraction=fraction,
            refinement_fraction=max(0.05, 1.0 - fraction),
        )


def tune_for_dems(dem_ids: Sequence[str], slices: int = 3, battery_minutes: float = 18.0,
                  min_agl: float = 120.0, max_agl: float | None = 400.0, point_budget: int = 120) -> dict:
    base_config = getattr(_lambda_module, 'build_sampler_config_from_env')()
    agl = AglConstraints(min_agl_ft=min_agl, max_agl_ft=max_agl)
    best_config: SamplerConfig | None = None
    best_score: float | None = None
    best_metrics: dict[str, list] = {}

    for candidate in iter_configs(base_config):
        totals = []
        hazards = []
        violations = 0
        for dem_id in dem_ids:
            dataset = load_dem_dataset(dem_id)
            provider = SyntheticDemProvider(dataset)
            path = build_path_for_dataset(dataset, slices, battery_minutes, min_agl, max_agl)
            result, agl_summary = run_sampler(path, provider, candidate, agl, point_budget)
            if agl_summary['violations'] > 0:
                violations += agl_summary['violations']
                break
            totals.append(result.metrics['total_points_used'])
            hazards.append(result.metrics['hazards_detected'])
        if violations > 0 or not totals:
            continue
        score = sum(totals) / len(totals) + 0.5 * (sum(hazards) / len(hazards))
        if best_score is None or score < best_score:
            best_score = score
            best_config = candidate
            best_metrics = {
                'avg_total_points': sum(totals) / len(totals),
                'avg_hazards': sum(hazards) / len(hazards),
                'per_dem': [{'dem': dem_id, 'total_points': total, 'hazards': hz} for dem_id, total, hz in zip(dem_ids, totals, hazards)],
            }
    if best_config is None:
        raise RuntimeError('No configuration satisfied AGL constraints across DEMs')
    return {
        'config': best_config,
        'score': best_score,
        'metrics': best_metrics,
        'dems': list(dem_ids),
        'point_budget': point_budget,
        'min_agl': min_agl,
        'max_agl': max_agl,
    }


def main() -> None:
    dem_ids = ['flat', 'sinusoid', 'ridge', 'mountain', 'cliff', 'mixed', 'dunes', 'volcano', 'canyon', 'plateau']
    result = tune_for_dems(dem_ids)
    config: SamplerConfig = result['config']
    payload = {
        'timestamp': datetime.utcnow().isoformat() + 'Z',
        'config': {
            'discovery_interval_ft': config.discovery_interval_ft,
            'dense_interval_ft': config.dense_interval_ft,
            'medium_interval_ft': config.medium_interval_ft,
            'sparse_interval_ft': config.sparse_interval_ft,
            'grad_medium_ft_per_100': config.grad_medium_ft_per_100,
            'grad_high_ft_per_100': config.grad_high_ft_per_100,
            'grad_critical_ft_per_100': config.grad_critical_ft_per_100,
            'discovery_fraction': config.discovery_fraction,
            'refinement_fraction': config.refinement_fraction,
            'min_safety_spacing_ft': config.min_safety_spacing_ft,
            'safety_buffer_ft': config.safety_buffer_ft,
        },
        'score': result['score'],
        'metrics': result['metrics'],
        'dems': result['dems'],
    }
    logs_dir = Path('logs')
    logs_dir.mkdir(exist_ok=True)
    output_path = logs_dir / f'terrain_tuning_{datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")}.json'
    output_path.write_text(json.dumps(payload, indent=2))
    print(json.dumps(payload, indent=2))


if __name__ == '__main__':
    main()
