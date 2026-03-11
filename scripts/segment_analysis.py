#!/usr/bin/env python3
"""
Validate the segment-profile estimator against expected Litchi times.
The user reported Litchi shows ~23min for a 20min battery, 3-slice flight.
"""
import sys, os, math, types

requests_stub = types.ModuleType('requests')
requests_stub.get = lambda *a, **k: None
sys.modules['requests'] = requests_stub

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'infrastructure', 'spaceport_cdk', 'lambda', 'drone_path'))
from lambda_function import SpiralDesigner

designer = SpiralDesigner()
V = designer.FLIGHT_SPEED_MPS
FT2M = designer.FT2M


def analyse(params, label, litchi_expected=None):
    wps = designer.build_slice(0, params)
    n = len(wps)
    est = designer.estimate_flight_time_minutes(params, 41.0, -111.0)
    wp_speeds = [designer._waypoint_turn_speed(wps, i) for i in range(n)]

    total_dist_m = 0.0
    short_segs = 0
    for i in range(n - 1):
        dx = wps[i+1]['x'] - wps[i]['x']
        dy = wps[i+1]['y'] - wps[i]['y']
        d = math.sqrt(dx*dx + dy*dy) * FT2M
        total_dist_m += d
        d_up = max(0, (V**2 - wp_speeds[i]**2) / (2*designer.A_LINEAR))
        d_dn = max(0, (V**2 - wp_speeds[i+1]**2) / (2*designer.A_LINEAR))
        if d_up + d_dn > d:
            short_segs += 1

    cruise_only = total_dist_m / V / 60 + designer.TAKEOFF_LANDING_OVERHEAD_MINUTES

    # Count slow waypoints
    slow_wps = sum(1 for s in wp_speeds if s < V * 0.9)
    min_speed = min(wp_speeds)

    print(f"\n{'='*70}")
    print(f"  {label}")
    print(f"  slices={params['slices']}  N={params['N']}  rHold={params['rHold']:.0f}")
    print(f"{'='*70}")
    print(f"  Waypoints:           {n}")
    print(f"  Path length:         {total_dist_m:,.0f} m")
    print(f"  Cruise-only time:    {cruise_only:.2f} min")
    print(f"  Segment-profile est: {est:.2f} min")
    print(f"  Slow waypoints:      {slow_wps} / {n}")
    print(f"  Min wp speed:        {min_speed:.2f} m/s")
    print(f"  Short segments:      {short_segs} / {n-1}")
    if litchi_expected:
        diff = est - litchi_expected
        print(f"  Litchi expected:     {litchi_expected:.1f} min")
        print(f"  Delta vs Litchi:     {diff:+.2f} min")


print("="*70)
print("PHYSICS CONSTANTS:")
print(f"  A_LINEAR      = {designer.A_LINEAR} m/s²")
print(f"  A_CENTRIPETAL  = {designer.A_CENTRIPETAL} m/s²")
print(f"  V_MIN_TURN     = {designer.V_MIN_TURN} m/s")
print(f"  WP_DWELL_S     = {designer.WP_DWELL_S} s")
print(f"  CRUISE SPEED   = {designer.FLIGHT_SPEED_MPS} m/s")
print(f"  OVERHEAD       = {designer.TAKEOFF_LANDING_OVERHEAD_MINUTES} min")
print("="*70)

# Primary validation: 20min battery, 3 slices (user tested, Litchi said 23)
for slices in [1, 2, 3]:
    opt = designer.optimize_spiral_for_battery(20, slices, 41.0, -111.0)
    p = {'slices': opt['slices'], 'N': opt['N'],
         'r0': opt.get('r0', 200), 'rHold': opt['rHold']}
    litchi_exp = 23.0 if slices == 3 else None
    analyse(p, f"20min battery, {slices} slice(s)", litchi_exp)

# Sweep more battery durations
for battery in [8, 10, 15, 25, 30, 45]:
    for slices in [1, 3]:
        opt = designer.optimize_spiral_for_battery(battery, slices, 41.0, -111.0)
        p = {'slices': opt['slices'], 'N': opt['N'],
             'r0': opt.get('r0', 200), 'rHold': opt['rHold']}
        analyse(p, f"{battery}min battery, {slices} slice(s)")

# Check optimizer doesn't exceed battery
print("\n" + "="*70)
print("OPTIMIZER BATTERY COMPLIANCE:")
print("="*70)
for battery in [8, 10, 15, 20, 25, 30, 45]:
    for slices in [1, 2, 3]:
        opt = designer.optimize_spiral_for_battery(battery, slices, 41.0, -111.0)
        p = {'slices': opt['slices'], 'N': opt['N'],
             'r0': opt.get('r0', 200), 'rHold': opt['rHold']}
        est = designer.estimate_flight_time_minutes(p, 41.0, -111.0)
        over = est > battery
        flag = " *** OVER ***" if over else ""
        print(f"  {battery:2d}min {slices}sl → est={est:.2f} min  "
              f"margin={battery - est:.2f} min{flag}")
