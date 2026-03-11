#!/usr/bin/env python3
"""
Calibrate against the exact flight the user tested in Litchi.
FIXED params: N=9, rHold=1523, slices=3 (20min battery optimizer output).
Litchi reported: 23 minutes.
"""
import sys, os, math, types

requests_stub = types.ModuleType('requests')
requests_stub.get = lambda *a, **k: None
sys.modules['requests'] = requests_stub

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'infrastructure', 'spaceport_cdk', 'lambda', 'drone_path'))
from lambda_function import SpiralDesigner

LITCHI_TARGET = 23.0
FIXED_PARAMS = {'slices': 3, 'N': 9, 'r0': 200, 'rHold': 1523}


def estimate_fixed(a_linear, a_cent, v_min, wp_dwell):
    d = SpiralDesigner()
    d.A_LINEAR = a_linear
    d.A_CENTRIPETAL = a_cent
    d.V_MIN_TURN = v_min
    d.WP_DWELL_S = wp_dwell
    return d.estimate_flight_time_minutes(FIXED_PARAMS, 41.0, -111.0)


# Sweep a_linear only (with FIXED flight params)
print("=" * 70)
print("FIXED PARAMS: N=9, rHold=1523, slices=3")
print("Litchi target: 23.0 min")
print("=" * 70)

print("\nSWEEP A_LINEAR:")
for a10 in range(3, 15):
    a = a10 / 10.0
    est = estimate_fixed(a, 2.5, 0.5, 0.8)
    delta = est - LITCHI_TARGET
    mark = " <--" if abs(delta) < 0.3 else ""
    print(f"  a={a:.1f}  →  {est:.2f} min  ({delta:+.2f}){mark}")

# Sweep per-waypoint dwell
print("\nSWEEP WP_DWELL (a_linear=1.0):")
for d10 in range(0, 80, 5):
    dw = d10 / 10.0
    est = estimate_fixed(1.0, 2.5, 0.5, dw)
    delta = est - LITCHI_TARGET
    mark = " <--" if abs(delta) < 0.3 else ""
    print(f"  dwell={dw:.1f}s  →  {est:.2f} min  ({delta:+.2f}){mark}")

# 2D sweep: a_linear × dwell
print("\n2D SWEEP (a_linear × dwell):")
print(f"{'a':>5}  {'dwell':>5}  {'est':>7}  {'delta':>7}")
best_delta = 999
best = None
for a10 in range(3, 15):
    for d10 in range(0, 80, 2):
        a_l = a10 / 10.0
        dw = d10 / 10.0
        est = estimate_fixed(a_l, 2.5, 0.5, dw)
        delta = abs(est - LITCHI_TARGET)
        if delta < best_delta:
            best_delta = delta
            best = (a_l, dw, est)
        if delta < 0.2:
            print(f"  {a_l:.1f}   {dw:.1f}s   {est:.2f}   {est-LITCHI_TARGET:+.2f}")

print(f"\nBest match: a_linear={best[0]:.1f}  dwell={best[1]:.1f}s  "
      f"→  {best[2]:.2f} min  |delta|={best_delta:.2f}")

# Also try sweeping A_CENTRIPETAL
print("\nSWEEP A_CENTRIPETAL (a_linear=1.0, dwell=0.8):")
for ac10 in range(5, 35, 5):
    ac = ac10 / 10.0
    est = estimate_fixed(1.0, ac, 0.5, 0.8)
    delta = est - LITCHI_TARGET
    mark = " <--" if abs(delta) < 0.3 else ""
    print(f"  a_cent={ac:.1f}  →  {est:.2f} min  ({delta:+.2f}){mark}")

# Try: a_linear × a_centripetal × dwell
print("\n3D SWEEP (a_linear × a_cent × dwell):")
best3 = None
best3_delta = 999
for a10 in range(3, 12):
    for ac10 in range(5, 35, 5):
        for d10 in range(0, 80, 5):
            a_l = a10 / 10.0
            ac = ac10 / 10.0
            dw = d10 / 10.0
            est = estimate_fixed(a_l, ac, 0.5, dw)
            delta = abs(est - LITCHI_TARGET)
            if delta < best3_delta:
                best3_delta = delta
                best3 = (a_l, ac, dw, est)

if best3:
    print(f"Best: a_linear={best3[0]:.1f}  a_cent={best3[1]:.1f}  "
          f"dwell={best3[2]:.1f}s  →  {best3[3]:.2f} min  |delta|={best3_delta:.2f}")
