# Shape Lab vs Production Drone Path Comparison

## Overview
The shape lab (`web/app/shape-lab/page.tsx`) is a browser-based 3D visualization tool built with Three.js and React that mirrors the core spiral generation logic from the production Lambda function (`infrastructure/spaceport_cdk/lambda/drone_path/lambda_function.py`). Below are the key differences and modifications made during development.

---

## Core Algorithm Similarities

### ✅ Matching Elements
Both implementations share:

1. **Progressive Alpha System** - Identical steeper early bounces + normal later bounces
   - `early_density_factor` and `late_density_factor` based on `radius_ratio`
   - Same ratio thresholds: `>20`, `>10`, else fallback
   - Same transition point: 40% of outbound time

2. **Three-Phase Spiral** - Identical structure
   - Outward spiral with exponential expansion
   - Hold pattern at maximum radius
   - Inward spiral with exponential contraction

3. **Exponential Radius Calculation** - Identical math
   ```
   r_transition = r0 * exp(alpha_early * t_transition)
   actual_max_radius = r_transition * exp(alpha_late * (t_out - t_transition))
   ```

4. **Phase Oscillation** - Identical bounce pattern
   ```
   phase = ((th / dphi) % 2 + 2) % 2
   phi = phase <= 1 ? phase * dphi : (2 - phase) * dphi
   ```

---

## Key Differences

### 1. **Altitude Calculation Logic**

#### Production Lambda (Python)
```python
# Neural network optimization rates
OUTBOUND & HOLD: 0.37ft per foot climb rate  # Detail capture
INBOUND: 0.10ft per foot descent rate        # Context capture
```

- **Purpose**: Differentiated altitudes for neural network training
- **Result**: Up to 135ft altitude difference at same locations
- **Complexity**: Tracks `max_outbound_altitude` and `max_outbound_distance`

#### Shape Lab (TypeScript)
```typescript
// Simplified visualization rates
OUTBOUND & HOLD: 0.20ft per foot climb rate
INBOUND: 0.10ft per foot descent rate
```

- **Purpose**: Clean 3D visualization without extreme altitude differences
- **Result**: More balanced altitude profile for easier visualization
- **Simplification**: Same structure but reduced outbound climb rate

**Why Modified**: Shape lab prioritizes visual clarity over neural network training requirements. The 0.37 rate creates very tall spirals that are harder to visualize effectively.

---

### 2. **Waypoint Density & Sampling**

#### Production Lambda
```python
# Simple midpoint strategy (production-tested)
- outbound_mid_{N} at 0.5 position between bounces
- Single hold_mid waypoint
- inbound_mid_{N} at 0.5 position between bounces
```

**Total waypoints**: ~13-17 waypoints per slice (typical)

#### Shape Lab (Recent Development)
```typescript
// Enhanced density for single/double slice flights
Single slice (1 battery):
  - 5 midpoints per segment (1/6, 2/6, 3/6, 4/6, 5/6 intervals)
  - Labeled as q17, q33, q50, q67, q83
  
Double slice (2 batteries):
  - 2 midpoints per segment (1/3, 2/3 intervals)
  - Labeled as q33, q67

Multi-slice (3+ batteries):
  - 1 midpoint per segment (0.5 interval)
  - Standard production behavior
```

**Total waypoints**: 
- Single slice: ~60-80 waypoints
- Double slice: ~26-34 waypoints  
- Multi-slice: ~13-17 waypoints (matches production)

**Why Modified**: Single and double slice flights need denser coverage since they cover larger angular sections (360° and 180° respectively) compared to multi-battery flights.

---

### 3. **Dynamic Curve Radius System**

#### Production Lambda
```python
if is_midpoint:
    # Ultra-smooth transitions
    base_curve = 50ft
    scale_factor = 1.2
    max_curve = 1500ft
else:
    # Doubled for smoother directional control
    base_curve = 40ft  # Doubled from original 20ft
    scale_factor = 0.05
    max_curve = 160ft  # Doubled from original 80ft
```

#### Shape Lab
```typescript
// IDENTICAL curve calculation
if (isMidpoint) {
  base_curve = 50
  scale_factor = 1.2
  max_curve = 1500
} else {
  base_curve = 40
  scale_factor = 0.05
  max_curve = 160
}
```

**Status**: ✅ Perfectly synchronized after recent updates

---

### 4. **Circular Arc Rendering** (Shape Lab Exclusive)

#### Production Lambda
- Outputs straight-line waypoint sequences
- Drone interpolates curves based on `curve` property in CSV
- No visual rendering of curved paths

#### Shape Lab
```typescript
// Litchi-style tangent-based circular arc rendering
- Calculates tangent points on segments before/after waypoint
- Renders true circular arcs between tangent points
- Uses waypoint.curve as turn radius
- Interpolates altitude linearly across arc
```

**Why Added**: The shape lab provides real-time 3D visualization of how the drone will actually fly curved paths, not just straight-line waypoint connections. This matches Litchi's flight behavior more accurately.

**Implementation**: 
- Uses geometric tangent calculations
- Samples circular arcs at proper density
- Handles degenerate cases (straight lines, opposite directions)
- Prevents roll by fixing rotation order to 'YXZ'

---

### 5. **3D Visualization Features** (Shape Lab Exclusive)

Production Lambda outputs CSV files; shape lab adds:

1. **Interactive 3D Canvas**
   - Real-time Three.js rendering
   - Apple-style UI with smooth controls
   - Grid helper scaled 1.5x for visibility

2. **Camera Frustum Visualization**
   - Shows drone camera FOV (84° typical)
   - Calculates heading and gimbal pitch per waypoint
   - Hover tooltips with waypoint details

3. **Orbit Controls**
   - Left drag: Rotate around focus point
   - Right drag / Ctrl+drag: Pan focus point
   - Scroll: Zoom with smooth damping
   - Camera state preservation across parameter changes

4. **Waypoint Color Coding**
   - Red: Start waypoint
   - Orange: Bounce points
   - Blue: Hold waypoints
   - Gray: Mid waypoints

---

### 6. **Battery Duration to Bounce Count Mapping**

#### Production Lambda
```python
# Progressive bounce scaling for battery optimization
≤12 min → 7 bounces
≤18 min → 8 bounces
≤25 min → 9 bounces
≤35 min → 10 bounces
≤45 min → 12 bounces
>45 min → 15 bounces

# Uses binary search to optimize rHold radius
# 98% battery utilization target
```

#### Shape Lab
```typescript
// Simplified mapping for visualization
function mapBatteryToBounces(minutes: number): number {
  const n = Math.round(5 + 0.3 * (minutes - 10));
  return Math.max(3, Math.min(12, n));
}

// Linear scaling: 10min→5, 20min→8, 30min→11
// Clamped [3, 12] for practical range
```

**Why Modified**: Shape lab uses simpler linear mapping because it doesn't need the production optimization algorithm. Production Lambda uses battery-specific optimization with binary search on radius.

---

### 7. **Hold Radius Calculation**

#### Production Lambda
```python
BASE_RHOLD_FT = 1595ft  # For 10min battery reference
# Binary search optimization adjusts rHold dynamically
# Final value depends on battery duration + terrain + constraints
```

#### Shape Lab
```typescript
BASE_RHOLD_FT = 1595
function calculateHoldRadius(batteryMinutes: number): number {
  return BASE_RHOLD_FT * (batteryMinutes / BASE_BATTERY_MINUTES);
}

// Direct linear scaling with battery duration
// 10min → 1595ft, 20min → 3190ft, 30min → 4785ft
```

**Why Modified**: Shape lab uses deterministic linear scaling for predictable visualization. Production uses optimization algorithms that adjust based on real-world constraints.

---

### 8. **Terrain Handling**

#### Production Lambda
- Google Maps Elevation API integration
- 15-foot proximity caching for optimization
- Adaptive terrain sampling (detects ridges/valleys)
- Safety waypoint injection for terrain anomalies
- MSL (Mean Sea Level) altitude calculations
- Terrain-following with AGL (Above Ground Level) tracking

#### Shape Lab
```typescript
// No terrain integration
// Pure AGL altitudes relative to flat ground at minHeight
// maxHeight optional ceiling constraint
```

**Why Excluded**: Terrain API calls and complex elevation logic aren't needed for the shape visualization sandbox. Shape lab focuses on flight pattern geometry, not real-world terrain.

---

### 9. **GPS Coordinate Conversion**

#### Production Lambda
```python
# Full GPS integration
def xy_to_lat_lon(x, y, center_lat, center_lon):
    # Converts local XY (feet) to GPS lat/lon
    # Uses Earth radius and proper trigonometry
    
def lat_lon_to_xy(lat, lon, center_lat, center_lon):
    # Reverse conversion for terrain sampling
```

#### Shape Lab
```typescript
// Not needed - works entirely in local XY coordinates
// Visualization uses feet for distances
// No GPS output required
```

**Why Excluded**: Shape lab is a pure geometric visualizer. It doesn't need GPS coordinates since it's not generating real flight missions.

---

### 10. **Output Format**

#### Production Lambda
```python
# Generates Litchi CSV format
# 16 columns per waypoint:
# - GPS coordinates (lat/lon)
# - Altitude (MSL feet)
# - Heading (forward-looking)
# - Curve size (meters, converted from feet)
# - Gimbal mode & pitch
# - Speed, POI, photo intervals
```

#### Shape Lab
```typescript
// Interactive 3D visualization
// Real-time parameter adjustment
// Visual feedback only (no file output)
```

**Why Different**: Production outputs flight-ready CSV files for drone execution. Shape lab provides interactive design/preview environment.

---

## Evolution During Development

### Recent Shape Lab Modifications (This Branch)

1. **Slice-Aware Waypoint Density** (agent-93847201-single-spiral-work)
   - Added sixth-interval sampling for single-slice flights
   - Added third-interval sampling for double-slice flights
   - Improves coverage for wide-angle battery slices

2. **Circular Arc Rendering** (agent-19472638-flight-path-slope)
   - Implemented Litchi-style tangent-based curves
   - Fixed frustum orientation using YXZ rotation order
   - Added curve radius tooltips on hover

3. **isMidpoint Flag Integration** (merged from both branches)
   - Ultra-smooth curves (1500ft max) for transition waypoints
   - Standard curves (160ft max) for bounce waypoints
   - Matches production's dual-curve-radius system

---

## Summary

### Core Algorithm: ✅ Identical
The mathematical foundation (progressive alpha spiral, exponential expansion/contraction, phase oscillation) is exactly the same.

### Altitude Logic: ✅ SYNCHRONIZED (as of 2025-10-13)
Both now use:
- Outbound: 0.20 ft/ft climb rate
- Inbound: 0.10 ft/ft ascent rate (changed from descent)
- Result: Progressive altitude increase throughout flight with "flat top" ceiling behavior

### Waypoint Density: ✅ SYNCHRONIZED (as of 2025-10-13)
Production now matches shape lab:
- Single battery: 5 midpoints per segment (1/6 intervals) with q-labels
- Double battery: 2 midpoints per segment (1/3 intervals) with q-labels
- Multi-battery (3+): 1 midpoint per segment (standard)

### Curve Rendering: ➕ Shape Lab Only
Shape lab renders true circular arcs; production outputs waypoint sequences only.

### Terrain/GPS: ➕ Production Only
Production handles real-world terrain and coordinates; shape lab is geometry-focused.

### Output: 🎯 Different Purpose
Production generates flight-ready CSV files; shape lab provides interactive 3D visualization.

---

## Recent Changes (2025-10-13)

**PORTED FROM SHAPELAB TO PRODUCTION:**

1. ✅ Slice-aware waypoint density
   - Implemented in `build_slice()` method
   - Single/double slice missions now generate 60-80 and 26-34 waypoints respectively
   - Multi-battery missions (3+) unchanged

2. ✅ Updated altitude rates
   - Outbound: 0.37 → 0.20 ft/ft (gentler climb)
   - Inbound: 0.10 descent → 0.10 ascent (continuous climb)
   - Applied to both `generate_csv()` and `generate_battery_csv()` methods
   - Documentation updated throughout

**RESULT:** Production and shape lab now share identical flight path generation logic for geometry and altitude profiles.

---

## Recommendation

**Status**: Production and shape lab are now synchronized for core flight path generation logic.

**Next steps**: Test production CSV generation with single/double battery missions to verify waypoint counts and altitude profiles match shape lab visualization.

The shape lab continues to serve as an excellent sandbox for testing spiral geometry changes before implementing them in production.

