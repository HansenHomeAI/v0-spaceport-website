#!/usr/bin/env python3
"""
Validate flight time estimation accuracy.
Ensures the estimator matches an independent waypoint-based simulation
and that the optimizer never exceeds battery time.
"""
import sys, os, math, types

requests_stub = types.ModuleType('requests')
requests_stub.get = lambda *a, **k: None
sys.modules['requests'] = requests_stub

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'infrastructure', 'spaceport_cdk', 'lambda', 'drone_path'))
from lambda_function import SpiralDesigner

designer = SpiralDesigner()

FLIGHT_SPEED_MPS = designer.FLIGHT_SPEED_MPS
FT2M = designer.FT2M
A_CENTRIPETAL = designer.A_CENTRIPETAL
A_LINEAR = designer.A_LINEAR
V_MIN = designer.V_MIN_TURN

failures = []

def independent_simulation(params):
    """Independent flight time calc (mirrors estimator logic but written separately)."""
    wps = designer.build_slice(0, params)
    n = len(wps)
    if n < 2:
        return designer.TAKEOFF_LANDING_OVERHEAD_MINUTES

    dist_ft = sum(
        math.hypot(wps[i]['x'] - wps[i-1]['x'], wps[i]['y'] - wps[i-1]['y'])
        for i in range(1, n)
    )
    cruise_s = dist_ft * FT2M / FLIGHT_SPEED_MPS

    penalty_s = 0.0
    for i in range(1, n - 1):
        v1x, v1y = wps[i]['x'] - wps[i-1]['x'], wps[i]['y'] - wps[i-1]['y']
        v2x, v2y = wps[i+1]['x'] - wps[i]['x'], wps[i+1]['y'] - wps[i]['y']
        m1, m2 = math.hypot(v1x, v1y), math.hypot(v2x, v2y)
        if m1 < 1e-9 or m2 < 1e-9:
            continue
        cos_a = max(-1.0, min(1.0, (v1x*v2x + v1y*v2y) / (m1*m2)))
        theta = math.acos(cos_a)
        if theta < math.radians(5):
            continue
        curve_m = wps[i].get('curve', 40) * FT2M
        v_turn = max(V_MIN, min(FLIGHT_SPEED_MPS * math.cos(theta/2),
                                 math.sqrt(A_CENTRIPETAL * curve_m) if curve_m > 0 else 0))
        dv = FLIGHT_SPEED_MPS - v_turn
        if dv >= 0.05:
            penalty_s += 2.0 * dv / A_LINEAR

    return (cruise_s + penalty_s) / 60.0 + designer.TAKEOFF_LANDING_OVERHEAD_MINUTES


def check(label, params, target_battery=None):
    est = designer.estimate_flight_time_minutes(params, 41.0, -111.0)
    sim = independent_simulation(params)
    diff = abs(est - sim)

    ok = diff < 0.01
    battery_ok = True
    if target_battery is not None:
        battery_ok = est <= target_battery
        ok = ok and battery_ok

    status = "PASS" if ok else "FAIL"
    line = f"  [{status}] {label:55s}  est={est:6.2f}  sim={sim:6.2f}  diff={diff:+.3f}"
    if target_battery is not None:
        margin = target_battery - est
        line += f"  target={target_battery}  margin={margin:+.2f}"
        if not battery_ok:
            line += " *** OVER BATTERY ***"
    print(line)
    if not ok:
        failures.append(label)


print("=" * 100)
print("  Flight Time Estimation Validation Suite")
print("=" * 100)

print("\n--- Fixed parameter tests ---")
for slices in [1, 2, 3, 6]:
    for N in [3, 5, 7, 9, 12]:
        for rHold in [300, 1000, 3000, 8000]:
            if rHold <= 200:
                continue
            p = {'slices': slices, 'N': N, 'r0': 200, 'rHold': rHold}
            check(f"slices={slices} N={N} rHold={rHold}", p)

print("\n--- Optimizer battery-limit tests ---")
for battery in [8, 10, 12, 15, 18, 20, 25, 30, 35, 40, 45]:
    for slices in [1, 2, 3, 6]:
        opt = designer.optimize_spiral_for_battery(battery, slices, 41.0, -111.0)
        p = {'slices': opt['slices'], 'N': opt['N'], 'r0': opt.get('r0', 200), 'rHold': opt['rHold']}
        check(f"opt battery={battery} slices={slices} → N={opt['N']} rH={opt['rHold']:.0f}",
              p, target_battery=battery)

print("\n" + "=" * 100)
if failures:
    print(f"  FAILED {len(failures)} test(s):")
    for f in failures:
        print(f"    - {f}")
    sys.exit(1)
else:
    print("  ALL TESTS PASSED")
    sys.exit(0)
