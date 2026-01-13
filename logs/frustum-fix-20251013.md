# Camera Frustum Fix - 2025-10-13

## Problem
Flight lab viewer showed all camera frustums with identical heading and pitch, despite waypoints having dynamic gimbal requirements. Occasional spurious roll axis changes.

## Root Causes
1. **Line 335**: Hardcoded `gimbalPitch = -90` constant
2. **Lines 352-364**: Heading calculated from consecutive waypoints instead of toward center
3. **Lines 415-417**: Arrow rotation bug (`rotation.x` set twice)
4. No explicit rotation order → gimbal lock causing roll artifacts

## Solution
```typescript
// For photogrammetry spiral: camera aims at center (0,0,0)
const horizontalDist = Math.hypot(wp.x, wp.y);
let heading = 0;
if (horizontalDist > 0.1) {
  heading = Math.atan2(-wp.x, -wp.y);  // angle toward center
}

// Calculate gimbal pitch: angle to look down at center
let gimbalPitch = -90; // default nadir
if (horizontalDist > 0.1) {
  const pitchAngle = Math.atan2(wp.z, horizontalDist);
  gimbalPitch = -(90 - (pitchAngle * 180 / Math.PI));
}

// YXZ rotation order prevents roll
frustum.rotation.order = 'YXZ';
frustum.rotation.y = heading;
frustum.rotation.x = (gimbalPitch * Math.PI) / 180;
frustum.rotation.z = 0; // explicitly no roll
```

## Verification
Console output from live preview:
```
WP 0: heading=-180.0°, pitch=-51.3°, dist=150ft, alt=120ft
WP 1: heading=119.9°, pitch=-53.9°, dist=179ft, alt=131ft
WP 2: heading=60.1°, pitch=-56.1°, dist=214ft, alt=144ft
WP 3: heading=120.2°, pitch=-58.1°, dist=255ft, alt=159ft
WP 4: heading=179.8°, pitch=-59.8°, dist=305ft, alt=177ft
```

✓ Heading varies per waypoint
✓ Pitch progressively steeper as drone climbs
✓ No spurious roll

## Commit
84e53d6 - fix: accurate camera frustum heading and pitch for photogrammetry spiral

## Preview URL
https://agent-84729351-path-optimiza.v0-spaceport-website-preview2.pages.dev/shape-lab

