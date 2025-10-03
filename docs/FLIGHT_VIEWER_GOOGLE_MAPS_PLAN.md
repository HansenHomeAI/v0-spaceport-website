# Flight Viewer Google Maps Upgrade Plan

## Objectives
- Swap the bespoke elevation mesh for Google's recommended WebGL overlay backed by Maps JavaScript and Photorealistic 3D Tiles.
- Preserve existing flight path rendering, waypoint hover telemetry, and POI markers while leveraging the live globe.
- Keep the data pipeline (CSV/KMZ ingestion, stats) intact so only the visualization layer changes.

## Tasks
1. **Configuration & Tooling**
   - Add `@googlemaps/js-api-loader` + `@types/google.maps` dependencies.
   - Introduce `NEXT_PUBLIC_GOOGLE_MAPS_MAP_ID` (preview + production) and surface it in the workflow + docs.
2. **Viewer Refactor**
   - Replace the `@react-three/fiber` `<Canvas>` scene with a `google.maps.Map` container configured for immersive 3D (tilt, heading, map ID).
   - Instantiate a `ThreeJSOverlayView` from `@googlemaps/three` to host Three.js content synchronized with the map camera.
3. **Geometry Port**
   - Rebuild flight path, frustum meshes, and POI markers using plain Three.js objects attached to the overlay scene.
   - Reuse the Catmull-Rom smoothing + lens metadata while converting lat/lon/alt via `overlay.latLngAltitudeToVector3`.
4. **Interaction Layer**
   - Wire pointer tracking through Google Maps events and use `overlay.raycast` for hover detection to keep the stats panel reactive.
   - Tune material updates (highlight, opacity) to mirror the legacy behavior.
5. **Validation**
   - Local `npm run build` + targeted sanity checks (load demo CSV, verify 3D globe + overlays in browser, capture console logs).
   - Update `docs/FLIGHT_VIEWER_3D_TERRAIN.md` (rename/augment) with new setup instructions and troubleshooting tips.
6. **Ops Hooks**
   - Bump `web/trigger-dev-build.txt` once ready, push branch, monitor Pages + CDK workflows, and document loop progress in `logs/agent-loop.log`.

## Risks & Mitigations
- **API quota**: WebGL overlay fetches Photorealistic 3D Tiles; monitor usage and throttle rerenders if necessary.
- **Hover latency**: Ensure `overlay.requestRedraw()` runs when pointer moves to keep raycasting responsive.
- **SSR safety**: Guard map initialization to run only when `window` is available.
