# Flight Viewer Google Maps 3D Overlay

## Overview

The Flight Viewer now renders flight plans on top of the live Google Maps 3D globe. We load the Maps JavaScript WebGL renderer, attach a `ThreeJSOverlayView`, and stream photorealistic terrain directly from Google so the drone path aligns with real-world topography and buildings.

## Key Changes

- **WebGL Overlay**: Google maintains the terrain mesh/imagery; we no longer fetch Elevation & Static Map tiles manually.
- **Three.js Sync**: A shared scene in `ThreeJSOverlayView` drives our flight path tube, waypoint frustums, and POI markers so they track the basemap camera.
- **Raycast Hovering**: Cursor movement is forwarded through `overlay.raycast` to power the waypoint tooltip and highlight logic.
- **Camera Alignment**: The overlay ties its anchor to the active flight centroid so coordinates convert straight from lat/lon/altitude to meters.

## Configuration

Add the following public environment variables (preview + production):

```bash
NEXT_PUBLIC_GOOGLE_MAPS_API_KEY=xyz
NEXT_PUBLIC_GOOGLE_MAPS_MAP_ID=abcdefghijklmno
```

Secrets are injected at build and runtime via `.github/workflows/deploy-cloudflare-pages.yml` (`GOOGLE_MAPS_API_KEY` / `GOOGLE_MAPS_MAP_ID`).

Required Google Maps Platform APIs:
- Maps JavaScript API
- Map Tiles API (Photorealistic 3D Tiles)
- Optional: Places/Geocoding if other features rely on them (existing list already enabled).

## Implementation Notes

- Map bootstraps with `@googlemaps/js-api-loader` and a branch-specific `mapId` so preview builds can point at dedicated styles if needed. The Map ID must have **Photorealistic 3D Tiles** enabled; otherwise Google delivers raster tiles and the overlay is disabled.
- `ThreeJSOverlayView` is created with `anchor = {lat, lng, altitude: 0}` and `upAxis = "Z"`, keeping Three.js coordinates in meters (X east, Y north, Z up).
- Flight path geometry is derived from `overlay.latLngAltitudeToVector3` so every waypoint/POI is co-located with Google’s globe mesh.
- Waypoint camera frustums are stand-alone `THREE.Group`s with dashed FOV lines that toggle on hover.
- Hover detection stores a lookup of interactive objects; pointer movement updates a normalized vector passed to `overlay.raycast`.
- Map bounds fit all loaded flights and then reset tilt/heading (67° tilt, heading 0°) to provide the Google Earth perspective.
- The map container is a dedicated absolutely positioned div with a fixed 520px minimum height—matching Google’s examples—to guarantee the canvas is visible before the WebGL overlay initializes.

## Usage

1. Open `/flight-viewer` on the branch preview.
2. Upload one or more CSV/KMZ files (e.g. `Edgewood-1.csv` in repo root).
3. The map recenters, 3D terrain streams automatically, and the path renders with camera frustums stacked above the ground.
4. Hover over a frustum to highlight it and surface waypoint metadata in the sidebar tooltip.

## Troubleshooting

- **Blank Map**: Confirm `NEXT_PUBLIC_GOOGLE_MAPS_API_KEY` is present in the runtime environment (`console.log` at mount surfaces status). Missing keys render a placeholder warning.
- **2D View Only**: Ensure the referenced `mapId` has Photorealistic 3D Tiles enabled and the browser exposes WebGL2. If `map.getRenderingType()` reports `RASTER`, the UI shows a warning and falls back to 2D polylines/markers.
- **No Hover Feedback**: Check the browser console for `raycast` errors; they typically mean the overlay scene failed to rebuild after ingesting flights.
- **Flight Misalignment**: Validate waypoint altitudes are in feet; the converter now multiplies by 0.3048 before passing to Google.

## Validation Checklist

- `npm run build` (lint + typecheck) passes locally.
- Load preview deployment, import `Edgewood-1.csv`, verify the path tracks over real terrain.
- Hovering a waypoint lights up the dashed FOV lines and updates the stats panel.
- Playwright MCP regression can continue hitting the preview URL (no API contract changes).
