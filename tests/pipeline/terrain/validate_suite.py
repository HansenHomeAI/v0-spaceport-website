from __future__ import annotations

import json
from datetime import datetime
from importlib import import_module
from pathlib import Path
import sys

sys.path.insert(0, str(Path('.').resolve()))

from tests.pipeline.terrain.dem_provider import SyntheticDemProvider, load_dem_dataset
from tests.pipeline.terrain.tune_params import build_path_for_dataset
from tests.pipeline.terrain.tuner import run_sampler

_lambda_module = import_module('infrastructure.spaceport_cdk.lambda.drone_path.lambda_function')
build_sampler_config_from_env = getattr(_lambda_module, 'build_sampler_config_from_env')
AglConstraints = getattr(_lambda_module, 'AglConstraints')


def main() -> None:
    dem_ids = ['flat', 'sinusoid', 'ridge', 'mountain', 'cliff', 'mixed', 'dunes', 'volcano', 'canyon', 'plateau']
    config = build_sampler_config_from_env()
    agl = AglConstraints(min_agl_ft=120.0, max_agl_ft=400.0)
    report = {
        'timestamp': datetime.utcnow().isoformat() + 'Z',
        'config': {
            'discovery_interval_ft': config.discovery_interval_ft,
            'dense_interval_ft': config.dense_interval_ft,
            'medium_interval_ft': config.medium_interval_ft,
            'sparse_interval_ft': config.sparse_interval_ft,
            'discovery_fraction': config.discovery_fraction,
            'refinement_fraction': config.refinement_fraction,
        },
        'results': [],
        'violations': 0,
        'point_budget': 120,
    }
    for dem_id in dem_ids:
        dataset = load_dem_dataset(dem_id)
        provider = SyntheticDemProvider(dataset)
        path = build_path_for_dataset(dataset, slices=3, battery_minutes=18.0, min_agl=120.0, max_agl=400.0)
        result, agl_summary = run_sampler(path, provider, config, agl, 120)
        report['results'].append({
            'dem': dem_id,
            'total_points_used': result.metrics['total_points_used'],
            'discovery_points_used': result.metrics['discovery_points_used'],
            'refinement_points_used': result.metrics['refinement_points_used'],
            'hazards': result.metrics['hazards_detected'],
            'safety_waypoints': result.metrics['safety_waypoints'],
            'agl_violations': agl_summary['violations'],
            'max_deficit_ft': agl_summary['max_deficit_ft'],
        })
        report['violations'] += agl_summary['violations']
    logs_dir = Path('logs')
    logs_dir.mkdir(exist_ok=True)
    output_path = logs_dir / f'terrain_validation_{datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")}.json'
    output_path.write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2))
    if report['violations'] > 0:
        raise SystemExit('AGL violations detected during validation')


if __name__ == '__main__':
    main()
