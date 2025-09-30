# Litchi CSV to DJI Fly KMZ Conversion Plan

This document captures the assumptions, field mappings, and behavioral goals for the new converter that bridges Litchi waypoint CSV missions to DJI Fly Waypoint (KMZ/WPML) missions.

## References

- Litchi waypoint CSV schema and enumerations as documented by the community project [`JoeKae/litchi_wp`](https://github.com/JoeKae/litchi_wp) (see `src/litchi_wp/enums.py`).
- Empirical DJI Fly KMZ sample (`Edgewood-1.kmz`) supplied with this repository.

## Input Columns & Normalisation

| Litchi column            | Type   | Notes |
|-------------------------|--------|-------|
| `latitude` / `longitude`| float  | Decimal degrees (WGS84). Required. |
| `altitude(ft)`          | float  | Feet; convert to metres for DJI Fly. |
| `heading(deg)`          | float  | Optional; absolute yaw (0-360). |
| `curvesize(ft)`         | float  | Litchi curvature radius. Convert to metres for DJI turn damping. |
| `rotationdir`           | int    | 0 = CW, 1 = CCW. Currently advisory only; surfaced for future yaw interpolation logic. |
| `gimbalmode`            | enum   | `0` Disabled, `1` Focus POI, `2` Interpolate (per `litchi_wp`). |
| `gimbalpitchangle`      | float  | Degrees; used when gimbalmode == Interpolate. |
| `altitudemode`          | enum   | `0` MSL/relative-to-start, `1` AGL. We emit DJI `relativeToStartPoint` and warn when `1`. |
| `speed(m/s)`            | float  | Optional per-waypoint speed. Fallback to global transitional speed when blank. |
| `poi_latitude` / `poi_longitude` | float | Optional. If set, we emit DJI `waypointPoiPoint`. |
| `poi_altitude(ft)`      | float  | Optional, converted to metres. |
| `photo_timeinterval`    | float  | Seconds. >0 translates to DJI `multipleTiming` trigger between current and next leg. |
| `photo_distinterval`    | float  | Metres. Not supported yet (DJI Fly lacks direct analogue); we warn and skip. |

Additional legacy columns (`actiontype*`, etc.) are ignored for now but parsed defensively.

## DJI Waypoint Emission Rules

- **Altitude**: Converted to metres; folder `executeHeightMode` set to `relativeToStartPoint`. When any waypoint reports `altitudemode = 1 (AGL)`, the CLI must require `--assume-agl` or abort with an explanatory warning (DEM-backed conversion is out of scope).
- **Indices**: Preserve order 0..N-1. The converter must never drop or duplicate the final waypoint (regression in prior script).
- **Turn behaviour**:
  - Waypoint 0 uses `toPointAndStopWithContinuityCurvature` to mimic Litchi's stationary start.
  - Subsequent waypoints choose `toPointAndPassWithContinuityCurvature` when `curvesize(ft) > 0`, otherwise `toPointAndStopWithContinuityCurvature`.
  - `waypointTurnDampingDist` equals `curvesize` converted to metres (clamped ≥0).
  - DJI exports keep `useStraightLine = 0` even for stop-and-turn legs; we match that behaviour for consistency.
- **Heading & POI**:
  - If a POI is supplied, embed `waypointPoiPoint` (lat,lon,alt in metres) and set `waypointHeadingPathMode` to `followBadArc` (mirrors DJI export).
  - When `--set-heading-from-csv` is passed, also set `waypointHeadingAngle` and `_Enable = 1`; otherwise leave at zero so POI/path logic drives yaw.
  - Optional `--insert-yaw-actions` converts headings into explicit `rotateYaw` `reachPoint` action groups for drones that require it (default off; relies on DJI 1.0.2 allow-list).
- **Gimbal pitch**:
  - If `gimbalmode == INTERPOLATE` and pitch is present, add a `gimbalRotate` `reachPoint` action at waypoint 0.
  - For legs `i -> i+1`, emit `gimbalEvenlyRotate` `betweenAdjacentPoints` with the target pitch of waypoint `i+1`.
  - `gimbalmode` values `DISABLED` and `FOCUS_POI` skip pitch actions (future work may map POI focus to DJI payload focus).
- **Photo interval**:
  - When `photo_timeinterval > 0`, add a `multipleTiming` action group with `sequence` mode covering waypoints `[i, i+1]` (skipped for the terminal waypoint that lacks a following leg).
  - Distance-based intervals raise a warning (unsupported) and are omitted to avoid invalid WPML.
- **Speed**:
  - `waypointSpeed` uses the per-row value if present; otherwise falls back to the mission's global transitional speed.
  - Folder metadata includes `autoFlightSpeed` (global transitional speed), while `distance` / `duration` remain 0 until we have precise modelling.
- **Action groups**:
  - Nested inside each `<Placemark>` (prior script incorrectly placed them under `<Document>`).
  - `actionGroupId` increments globally to keep DJI Fly happy.
  - Only DJI Fly-safe functions are emitted: `gimbalRotate`, `gimbalEvenlyRotate`, `takePhoto`, `rotateYaw` (optional), with parameters matching observed exports.
- **Template**:
  - `template.kml` mirrors the root missionConfig metadata and stores author/timestamps for traceability.

## Validation & Testing Strategy

1. **Edgewood baseline**: Convert `Edgewood-1.csv` and assert:
   - waypoint count matches CSV rows (53 in the sample),
   - indices are contiguous,
   - terminal waypoint matches the CSV coordinates/altitude,
   - no action group references an index outside `[0, N-1]`.
2. **Structure checks**: Parse the generated WPML to ensure all required DJI nodes exist (`missionConfig`, `templateId`, per-waypoint turn params, action groups inside placemarks).
3. **Gimbal interpolation**: Verify gimbal evenly-rotate actions reference the correct segment and pitch.
4. **Photo interval**: Confirm multiple-timing action groups line up with segments and are skipped for the final waypoint.
5. **CLI regression tests**: Exercise `--set-heading-from-csv`, `--insert-yaw-actions`, and handling of missing speeds / unsupported distance intervals.

Additional fixtures can be added later for POI-free missions, manual yaw missions, and gimbal-disabled tracks.

## Open Items / Follow-ups

- True AGL-to-ATO conversion would require DEM integration (e.g., SRTM). Out of scope for the initial release.
- Distance-interval photography mapping needs validation against DJI's `distanceInterval` trigger.
- Multi-POI missions may require explicit DJI `<wpml:pointOfInterest>` definitions if we move beyond per-waypoint coordinates.
- DJI drone enum/sub-enum should become configurable once we know the fleet composition; defaults target the Mini 4 / Air 3 class (`68/0`).
- Consider emitting `distance` and `duration` folder metadata once we have trustworthy path physics.
