# Flight Viewer Cesium Integration Plan

## Objectives
- Replace the transient Google Maps WebGL overlay with a stable Cesium-based renderer that streams Google Photorealistic 3D Tiles.
- Preserve CSV/KMZ ingestion, stats, and tooltip behavior while elevating the visualization to true 3D terrain.
- Keep the workflow deployable on Cloudflare Pages without custom build scripts.

## Workstreams
1. **Build & Runtime Plumbing**
   - Add `cesium` + `copy-webpack-plugin`, define `CESIUM_BASE_URL`, and override `@zip.js/zip.js` to a compatible release via `overrides`.
   - Ensure Cesium assets land in `public/cesium/` at build time and document the new env requirements.
2. **Renderer Implementation**
   - Instantiate a client-side Cesium `Viewer`, disable default imagery/sky, and load Google 3D tiles with the existing API key.
   - Render flight paths as polylines, waypoints as points with hover feedback, frustum lines for heading/pitch, and optional POI markers with labels.
3. **Interaction & Hover**
   - Use `ScreenSpaceEventHandler` for `MOUSE_MOVE` picking, enlarging waypoints on hover and syncing with the React tooltip.
   - Fit the camera to loaded missions and respect the selected lens when computing forward frustum vectors.
4. **Docs & Tooling Updates**
   - Refresh `docs/FLIGHT_VIEWER_3D_TERRAIN.md` with Cesium specifics and branch validation steps.
   - Remove the unused Google Maps overlay dependencies and note the new tileset requirement for future contributors.
5. **Validation Loop**
   - Run `npm run build`, push branch, bump `web/trigger-dev-build.txt`, and monitor Pages/CDK workflows.
   - Validate in a GPU-enabled browser (or recorded session) and capture results in `logs/agent-loop.log`.

## Risks & Mitigations
- **GPU / WebGL availability**: fallback messaging warns when contexts fail; plan for Playwright MCP runs that use hardware-backed browsers.
- **Tile quota**: Photorealistic tiles count against Google Maps Platform usage. Track load frequency and cache preview sessions.
- **Bundle weight**: Cesium is large; ensure tree-shaking and requestRender mode keep runtime cost tolerable.
