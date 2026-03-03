#!/usr/bin/env python3
"""
Detailed per-waypoint analysis showing the missing Bezier arc time.
The drone follows Bezier curves at every waypoint — the actual path is
longer than the polyline, and the arcs are traversed at reduced speed.
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
a_lin = designer.A_LINEAR
a_cent = designer.A_CENTRIPETAL


def turn_angle(wps, idx):
    if idx <= 0 or idx >= len(wps) - 1:
        return 0.0
    v1x = wps[idx]['x'] - wps[idx-1]['x']
    v1y = wps[idx]['y'] - wps[idx-1]['y']
    v2x = wps[idx+1]['x'] - wps[idx]['x']
    v2y = wps[idx+1]['y'] - wps[idx]['y']
    m1, m2 = math.hypot(v1x, v1y), math.hypot(v2x, v2y)
    if m1 < 1e-9 or m2 < 1e-9:
        return 0.0
    cos_a = max(-1.0, min(1.0, (v1x*v2x + v1y*v2y) / (m1*m2)))
    return math.acos(cos_a)


# Generate the exact same flight the user tested: 20min, 3 slices
opt = designer.optimize_spiral_for_battery(20, 3, 41.0, -111.0)
params = {'slices': opt['slices'], 'N': opt['N'], 'r0': opt.get('r0', 200), 'rHold': opt['rHold']}
wps = designer.build_slice(0, params)
n = len(wps)

print(f"Flight: 20min battery, 3 slices")
print(f"Params: N={params['N']}  rHold={params['rHold']}")
print(f"Waypoints: {n}")
print()

# Per-waypoint data
total_arc_time = 0.0
total_arc_extra_dist = 0.0
total_straight_credit = 0.0

print(f"{'WP':>3} {'θ°':>6} {'C_ft':>6} {'C_m':>6} {'V_turn':>7} {'V_cent':>7} "
      f"{'Arc_m':>7} {'ArcTime':>8} {'StraightCredit':>14} {'Net_s':>7}")
print("-" * 90)

for i in range(1, n - 1):
    theta = turn_angle(wps, i)
    C_ft = wps[i].get('curve', 40)
    C_m = C_ft * FT2M
    theta_deg = math.degrees(theta)

    # Current V_turn (cos(θ/2) + centripetal)
    v_dir = V * math.cos(theta / 2)
    v_cent = math.sqrt(a_cent * C_m) if C_m > 0 else V
    v_turn = max(designer.V_MIN_TURN, min(v_dir, v_cent))

    # Bezier arc length ≈ C * θ (circular-arc approx)
    arc_m = C_m * theta if theta > math.radians(5) else 0.0

    # The polyline already counts 2*C_m through this waypoint
    # Arc replaces this with a longer path at slower speed
    arc_time = arc_m / max(0.1, v_turn) if arc_m > 0 else 0.0
    straight_credit = 2 * C_m / V if arc_m > 0 else 0.0
    net = arc_time - straight_credit

    if theta > math.radians(5):
        total_arc_time += arc_time
        total_arc_extra_dist += max(0, arc_m - 2 * C_m)
        total_straight_credit += straight_credit
        print(f"{i:3d} {theta_deg:6.1f} {C_ft:6.0f} {C_m:6.1f} {v_turn:7.2f} {v_cent:7.2f} "
              f"{arc_m:7.1f} {arc_time:8.2f} {straight_credit:14.2f} {net:7.2f}")

print("-" * 90)
print(f"TOTAL ARC TIME:        {total_arc_time:8.1f}s = {total_arc_time/60:.2f} min")
print(f"TOTAL STRAIGHT CREDIT: {total_straight_credit:8.1f}s = {total_straight_credit/60:.2f} min")
print(f"NET ARC CORRECTION:    {(total_arc_time - total_straight_credit):8.1f}s = "
      f"{(total_arc_time - total_straight_credit)/60:.2f} min")
print(f"EXTRA ARC DISTANCE:    {total_arc_extra_dist:8.0f}m")

# Full time breakdown
est = designer.estimate_flight_time_minutes(params, 41.0, -111.0)
cruise_m = sum(math.hypot(wps[i+1]['x']-wps[i]['x'], wps[i+1]['y']-wps[i]['y'])*FT2M for i in range(n-1))
cruise_time = cruise_m / V / 60
print(f"\nCruise-only:           {cruise_time:.2f} min")
print(f"Segment model est:     {est:.2f} min")
print(f"Model overhead:        {est - cruise_time:.2f} min  (decel + dwell + fixed)")
print(f"Arc correction:        {(total_arc_time - total_straight_credit)/60:.2f} min")
print(f"CORRECTED estimate:    {est + (total_arc_time - total_straight_credit)/60:.2f} min")
print(f"Litchi actual:         23.00 min")
print(f"Delta:                 {est + (total_arc_time - total_straight_credit)/60 - 23:.2f} min")

# Also try with V_turn = sqrt(A_CENT * C * cos(θ/2)) model
print("\n" + "="*70)
print("ALTERNATIVE: V_turn from effective curvature R_eff = C * cos(θ/2)")
print("="*70)
alt_arc_total = 0.0
alt_credit_total = 0.0
for i in range(1, n - 1):
    theta = turn_angle(wps, i)
    if theta < math.radians(5):
        continue
    C_m = wps[i].get('curve', 40) * FT2M
    R_eff = C_m * math.cos(theta / 2)
    v_turn_alt = min(V, max(0.5, math.sqrt(a_cent * max(0.01, R_eff))))
    arc_m = C_m * theta
    arc_time = arc_m / v_turn_alt
    straight_credit = 2 * C_m / V
    alt_arc_total += arc_time
    alt_credit_total += straight_credit

alt_correction = (alt_arc_total - alt_credit_total) / 60
print(f"Alt arc correction:    {alt_correction:.2f} min")
print(f"CORRECTED estimate:    {est + alt_correction:.2f} min")
print(f"Litchi actual:         23.00 min")
print(f"Delta:                 {est + alt_correction - 23:.2f} min")
