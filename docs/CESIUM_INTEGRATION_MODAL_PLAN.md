# Cesium 3D Integration into New Project Modal

## Goal
Replace Mapbox map inside New Project modal with Cesium + Google Photorealistic 3D Tiles, keeping modal UI/flow unchanged.

## Branch
- Branch: `agent-20251030195656-integrate-3d-viewer-into-modal` (auto-generated when executing)

## Scope
- Swap map provider in `web/components/NewProjectModal.tsx` only
- Reuse proven scene logic from `web/app/flight-viewer/page.tsx`:
  - Viewer initialization
  - Google Photorealistic 3D Tiles loading
  - Double-click selection
  - Marker placement
  - Flight path rendering
  - Elevation offset handling
- Preserve all existing modal UX, controls, and upload/optimize flows
- Only the map rendering surface changes

## Key Requirements

### 1. Embed Cesium Canvas
- Replace Mapbox GL JS with Cesium `<div>` canvas inside existing `map-wrapper`
- Keep all sibling overlays intact (`expand-button`, blur layers, instructions)
- Lazy-import `cesium`, disable Ion, set `window.CESIUM_BASE_URL` (fallback `/cesium`)
- Initialize `Viewer` with:
  - `imageryProvider: false`
  - `baseLayerPicker: false`
  - All UI controls disabled (timeline, animation, etc.)
  - `requestRenderMode: true`
  - Black background, no globe/sky

### 2. Location Marker
- Use `web/public/assets/SpaceportIcons/TeardropPin.svg` as marker image
- Create Cesium `Entity` with `billboard` using the SVG
- Marker positioned at `selectedCoords` (lat, lng)
- Scale and alignment: tip touches ground

### 3. Interactions
- **Double-click in 3D**: Compute lat/lng from click → set `selectedCoords` → update marker → update address field
- **Coordinate input** (`lat,lng`): Parse → set `selectedCoords` → update marker → `camera.flyTo`
- **Geocoding**: Keep existing Mapbox geocoding HTTP call → on result, set `selectedCoords` → update marker → fly camera
- All interactions preserve existing autosave behavior

### 4. Flight Rendering
- When battery CSV(s) generated or user uploads CSV/KMZ:
  - Parse using same logic from `flight-viewer/page.tsx`
  - Render colored polylines per flight + small point entities for waypoints
  - **No hover behavior** in modal (unlike flight viewer page)
- Apply elevation MSL offset:
  - Use `/app/api/elevation-proxy` for first waypoint
  - Add terrain elevation to all waypoint heights (MSL = terrain + AGL)
  - Safe fallback to AGL-only if proxy fails
- Auto-fit camera to loaded paths on initial render
- Preserve user camera afterwards (unless modal already refits)

### 5. Error Handling
- Missing `NEXT_PUBLIC_GOOGLE_MAPS_API_KEY`: Show clear inline message in map area, keep modal usable
- Photorealistic tiles fail: Show non-blocking warning overlay, keep marker/paths visible
- Respect `CESIUM_BASE_URL` (assets in `public/cesium`)

## Implementation Steps

1. **Remove Mapbox GL JS**
   - Remove Mapbox imports and initialization
   - Remove `MAPBOX_TOKEN` usage
   - Keep geocoding HTTP API calls (no UI dependency)

2. **Add Cesium Integration**
   - Import Cesium dynamically
   - Initialize viewer in `useEffect` when modal opens
   - Load Google Photorealistic 3D Tiles using same pattern from flight-viewer

3. **Marker System**
   - Create marker entity ref
   - Update marker position when `selectedCoords` changes
   - Handle double-click events to set coordinates

4. **Coordinate Input/Geocoding**
   - Wire existing coordinate parsing to marker/camera
   - Wire existing geocoding results to marker/camera
   - Keep address field updates

5. **Flight Path Rendering**
   - Extract flight parsing logic (reuse from flight-viewer)
   - Add useEffect to render flights when CSV/KMZ data available
   - Apply elevation offset using elevation proxy
   - Render polylines + waypoints without hover

6. **Testing**
   - Use local dev server (`npm run dev` in `web/`)
   - Establish baseline: open modal, verify current Mapbox behavior
   - Iterate visually: make change → test locally → compare
   - Use Playwright MCP for automated visual testing

## Files to Edit
- `web/components/NewProjectModal.tsx` (main implementation)

## Files to Reference (Do Not Edit)
- `web/app/flight-viewer/page.tsx` (reuse Cesium scene logic)
- `web/app/api/elevation-proxy/route.ts` (elevation API usage)

## Acceptance Criteria
- Modal opens and shows Cesium 3D scene in map area
- Double-click to place/select location works and persists through autosave
- Address entry with coordinates and geocoding both position 3D marker and camera
- Battery CSV downloads auto-render as colored polylines + waypoints
- Uploaded CSV/KMZ files render flight paths in 3D
- Elevation MSL offset applied (falls back safely if API unavailable)
- Lint passes (`npx next lint`)
- Local dev server runs without errors

## Deliverables
- Branch name: `agent-{timestamp}-integrate-3d-viewer-into-modal`
- List of edited files
- Brief test notes (manual steps performed and results)

## Notes
- No redesign of modal UI
- No infrastructure or secret changes
- No hover behavior in modal (keep it in flight-viewer page only)
- Use local dev server for fast iteration (not preview URL)





