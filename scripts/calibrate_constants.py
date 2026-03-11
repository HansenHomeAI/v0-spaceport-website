#!/usr/bin/env python3
"""
Sweep physics constants to find the combination that matches
Litchi's reported 23 min for a 20-minute battery, 3-slice flight.
"""
import sys, os, math, types

requests_stub = types.ModuleType('requests')
requests_stub.get = lambda *a, **k: None
sys.modules['requests'] = requests_stub

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'infrastructure', 'spaceport_cdk', 'lambda', 'drone_path'))
from lambda_function import SpiralDesigner

LITCHI_TARGET = 23.0


def estimate_with_params(a_linear, a_cent, v_min, wp_dwell,
                         arc_model='none', arc_v_method='segment'):
    """Compute estimated flight time for 20min/3-slice with given constants."""
    d = SpiralDesigner()
    d.A_LINEAR = a_linear
    d.A_CENTRIPETAL = a_cent
    d.V_MIN_TURN = v_min
    d.WP_DWELL_S = wp_dwell

    opt = d.optimize_spiral_for_battery(20, 3, 41.0, -111.0)
    params = {'slices': opt['slices'], 'N': opt['N'],
              'r0': opt.get('r0', 200), 'rHold': opt['rHold']}

    wps = d.build_slice(0, params)
    n = len(wps)
    V = d.FLIGHT_SPEED_MPS

    wp_speeds = [d._waypoint_turn_speed(wps, i) for i in range(n)]

    flight_s = 0.0
    for i in range(n - 1):
        dx = wps[i+1]['x'] - wps[i]['x']
        dy = wps[i+1]['y'] - wps[i]['y']
        d_m = math.sqrt(dx*dx + dy*dy) * d.FT2M
        flight_s += d._segment_time(d_m, wp_speeds[i], wp_speeds[i+1],
                                     V, a_linear)

    n_interior = max(0, n - 2)
    dwell_s = n_interior * wp_dwell

    base_min = (flight_s + dwell_s) / 60.0 + d.TAKEOFF_LANDING_OVERHEAD_MINUTES
    return base_min, params, n


# Sweep: find what a_linear value matches Litchi at 23 min
print("=" * 70)
print("SWEEP A_LINEAR (other params: a_cent=2.5, v_min=0.5, dwell=0.8)")
print("=" * 70)
for a_lin_10 in range(3, 15):
    a_lin = a_lin_10 / 10.0
    est, params, n = estimate_with_params(a_lin, 2.5, 0.5, 0.8)
    delta = est - LITCHI_TARGET
    marker = " <-- MATCH" if abs(delta) < 0.3 else ""
    print(f"  a_linear={a_lin:.1f}  →  est={est:.2f} min  delta={delta:+.2f}{marker}")

# Sweep: dwell time
print("\n" + "=" * 70)
print("SWEEP WP_DWELL (other params: a_linear=1.0, a_cent=2.5, v_min=0.5)")
print("=" * 70)
for dwell_10 in range(0, 80, 5):
    dwell = dwell_10 / 10.0
    est, _, _ = estimate_with_params(1.0, 2.5, 0.5, dwell)
    delta = est - LITCHI_TARGET
    marker = " <-- MATCH" if abs(delta) < 0.3 else ""
    print(f"  dwell={dwell:.1f}s  →  est={est:.2f} min  delta={delta:+.2f}{marker}")

# Sweep: combined a_linear + dwell
print("\n" + "=" * 70)
print("SWEEP a_linear + dwell combinations targeting 23.0 min")
print("=" * 70)
best_delta = 999
best_combo = None
for a_lin_10 in range(3, 15):
    for dwell_10 in range(0, 60, 2):
        a_lin = a_lin_10 / 10.0
        dwell = dwell_10 / 10.0
        est, _, _ = estimate_with_params(a_lin, 2.5, 0.5, dwell)
        delta = abs(est - LITCHI_TARGET)
        if delta < best_delta:
            best_delta = delta
            best_combo = (a_lin, dwell, est)
        if delta < 0.2:
            print(f"  a_linear={a_lin:.1f}  dwell={dwell:.1f}s  →  "
                  f"est={est:.2f} min  delta={est-LITCHI_TARGET:+.2f}")

if best_combo:
    print(f"\nBest: a_linear={best_combo[0]:.1f}  dwell={best_combo[1]:.1f}s  "
          f"→  est={best_combo[2]:.2f} min  |delta|={best_delta:.2f}")

# Validate best combo across multiple battery durations
a_best, dwell_best = best_combo[0], best_combo[1]
print(f"\n{'='*70}")
print(f"VALIDATION with a_linear={a_best}, dwell={dwell_best}s across batteries")
print(f"{'='*70}")
for batt in [8, 10, 15, 20, 25, 30, 45]:
    for sl in [1, 2, 3]:
        d = SpiralDesigner()
        d.A_LINEAR = a_best
        d.WP_DWELL_S = dwell_best
        opt = d.optimize_spiral_for_battery(batt, sl, 41.0, -111.0)
        params = {'slices': opt['slices'], 'N': opt['N'],
                  'r0': opt.get('r0', 200), 'rHold': opt['rHold']}
        est = d.estimate_flight_time_minutes(params, 41.0, -111.0)
        over = "*** OVER ***" if est > batt else ""
        print(f"  {batt:2d}min {sl}sl  N={params['N']:2d}  "
              f"rHold={params['rHold']:7.0f}  est={est:.2f} min  "
              f"margin={batt-est:.2f} {over}")
