# Flight Viewer Cesium 3D Terrain

## Overview

The flight viewer now renders missions inside a Cesium globe that streams Google Photorealistic 3D Tiles. Cesium handles terrain meshing, camera navigation, and level-of-detail loading, while we overlay missions as native Cesium entities (polylines, points, and labels). Hovering a waypoint highlights the entity and keeps the UI tooltip in sync with the scene.

## Key Changes

- **Cesium Viewer** replaces the Google Maps WebGL overlay. A headless `Viewer` instance is mounted in the flight viewer panel and pointed at the Google 3D Tiles endpoint.
- **Asset bundling**: `npm run build/dev/start` now run `scripts/copy-cesium-assets.cjs`, copying `node_modules/cesium/Build/Cesium` into `public/cesium` so assets like `approximateTerrainHeights.json`, Draco decoders, and imagery load without 404s.
- **Entity-based overlays**: each flight creates Cesium polylines for the path, `PointGraphics` for waypoints, frustum direction lines, and an optional POI marker with a label.
- **Hover state**: `ScreenSpaceEventHandler` drives picking. When the cursor intersects a waypoint entity we enlarge its point and propagate the hover event back to React for tooltip updates.
- **Camera fitting**: after ingesting flights we compute a bounding sphere and call `viewer.camera.flyToBoundingSphere` so the mission is framed even when altitudes vary dramatically.
- **Asset packing**: `copy-webpack-plugin` ships `node_modules/cesium/Build/Cesium` into `public/cesium/`, and `CESIUM_BASE_URL` is defined at build time so runtime asset requests resolve correctly.

## Configuration

Environment variables:

```bash
NEXT_PUBLIC_GOOGLE_MAPS_API_KEY=your-google-key
```

The key must have access to the **Map Tiles API** (Photorealistic 3D Tiles). No Map ID is required now that Cesium hosts the rendering. The Cloudflare Pages workflow already exposes the key via both legacy (`GOOGLE_MAPS_API_KEY`) and `NEXT_PUBLIC_` slots.

## Implementation Notes

- We disable Cesium's default imagery/sky so the photorealistic tiles provide the full visual background.
- `CESIUM_BASE_URL` respects any configured `basePath`, so preview deployments continue to resolve `/agent-*/cesium/...` correctly.
- Google tiles are requested directly with `https://tile.googleapis.com/v1/3dtiles/root.json?key=...`.
- Waypoint hover size changes use `ConstantProperty` updates so they render immediately without rebuilding the entity.
- POIs render as 10px points with a "POI" label offset above the feature for readability.
- All distances are computed in meters using Haversine math to keep the stats panel accurate even for multi-kilometre flights.

## Usage Checklist

1. Run `npm run build` to ensure the Cesium bundling passes locally.
2. Start the dev server or load the Cloudflare preview for your branch.
3. Upload CSV or KMZ flight plans; the viewer should recenter, stream terrain, and render the mission in 3D.
4. Hover waypoints to confirm the marker grows and the sidebar tooltip updates with heading/pitch/altitude details.

## Troubleshooting

| Symptom | What to check |
| --- | --- |
| **"Google Maps API key missing" placeholder** | Ensure `NEXT_PUBLIC_GOOGLE_MAPS_API_KEY` is defined in the Pages deployment environment. |
| **Tileset fails to load** | Verify the key has Map Tiles API access and the billing project is enabled. The console logs the exact error from Cesium. |
| **Blank globe / no buildings** | The Photorealistic dataset sometimes blocks WebGL contexts without GPU support. Confirm the browser exposes WebGL2 (use `chrome://gpu`) or test in a GPU-enabled Playwright run. |
| **Hover never triggers** | Picking requires `requestRenderMode` updates. Make sure entities exist (`viewer.entities.values.length`) and the handler still owns the canvas. Resetting the page usually restores state. |

## Validation

- `npm run build` (typecheck + lint) succeeds.
- Manual run in a GPU-enabled browser shows 3D tiles and highlighted waypoints.
- Playwright MCP baseline can still upload `Edgewood-1.csv` without code changes (front-end only).
- Logs for validation runs are appended to `logs/agent-loop.log` as part of the dev loop.
