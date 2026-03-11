#!/usr/bin/env python3
"""
Validate the calibrated estimator:
1. Fixed-param check: N=9, rHold=1523, slices=3 → should be ~23 min
2. Optimizer compliance: no battery overages across all configs
3. Reasonable rHold values (not too small)
"""
import sys, os, math, types

requests_stub = types.ModuleType('requests')
requests_stub.get = lambda *a, **k: None
sys.modules['requests'] = requests_stub

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'infrastructure', 'spaceport_cdk', 'lambda', 'drone_path'))
from lambda_function import SpiralDesigner

designer = SpiralDesigner()
print("=" * 70)
print("CALIBRATED CONSTANTS:")
print(f"  A_LINEAR      = {designer.A_LINEAR} m/s²")
print(f"  A_CENTRIPETAL  = {designer.A_CENTRIPETAL} m/s²")
print(f"  V_MIN_TURN     = {designer.V_MIN_TURN} m/s")
print(f"  WP_DWELL_S     = {designer.WP_DWELL_S} s")
print(f"  FLIGHT_SPEED   = {designer.FLIGHT_SPEED_MPS} m/s")
print(f"  OVERHEAD       = {designer.TAKEOFF_LANDING_OVERHEAD_MINUTES} min")
print("=" * 70)

# 1. Fixed-param validation against Litchi
fixed = {'slices': 3, 'N': 9, 'r0': 200, 'rHold': 1523}
est_fixed = designer.estimate_flight_time_minutes(fixed, 41.0, -111.0)
print(f"\nFIXED PARAM CHECK (N=9, rHold=1523, slices=3):")
print(f"  Our estimate:   {est_fixed:.2f} min")
print(f"  Litchi actual:  23.00 min")
print(f"  Delta:          {est_fixed - 23.0:+.2f} min  {'✓' if abs(est_fixed - 23) < 0.5 else '✗'}")

# 2. Optimizer compliance across all configs
print(f"\n{'='*70}")
print("OPTIMIZER COMPLIANCE (should never exceed battery)")
print(f"{'='*70}")
print(f"{'Battery':>7} {'Sl':>2} {'N':>3} {'rHold':>7} {'Est':>7} {'Margin':>7} {'Status':>8}")
print("-" * 55)

all_ok = True
for batt in [8, 10, 15, 20, 25, 30, 45]:
    for sl in [1, 2, 3, 6]:
        opt = designer.optimize_spiral_for_battery(batt, sl, 41.0, -111.0)
        params = {'slices': opt['slices'], 'N': opt['N'],
                  'r0': opt.get('r0', 200), 'rHold': opt['rHold']}
        est = designer.estimate_flight_time_minutes(params, 41.0, -111.0)
        margin = batt - est
        ok = margin >= 0
        if not ok:
            all_ok = False
        status = "OK" if ok else "OVER"
        print(f"  {batt:4d}m  {sl:2d}  {params['N']:3d}  {params['rHold']:7.0f}  "
              f"{est:6.2f}  {margin:+6.2f}  {status}")

print(f"\nAll within budget: {'YES ✓' if all_ok else 'NO ✗'}")

# 3. Ratio check: how much of the battery is used?
print(f"\n{'='*70}")
print("BATTERY UTILIZATION")
print(f"{'='*70}")
for batt in [10, 15, 20, 25, 30]:
    for sl in [1, 3]:
        opt = designer.optimize_spiral_for_battery(batt, sl, 41.0, -111.0)
        params = {'slices': opt['slices'], 'N': opt['N'],
                  'r0': opt.get('r0', 200), 'rHold': opt['rHold']}
        est = designer.estimate_flight_time_minutes(params, 41.0, -111.0)
        util = est / batt * 100
        print(f"  {batt:2d}min {sl}sl  →  rHold={params['rHold']:6.0f}ft  "
              f"est={est:.1f}min  utilization={util:.1f}%")
