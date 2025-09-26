# 3D Flight Path Viewer

The Flight Path Viewer is a development-only Next.js page (`/dev/flight-viewer`) that renders Litchi-compatible CSV exports as a georeferenced polyline inside Google Maps' Photorealistic 3D tiles. It is intended for rapid design loops when tuning the Spaceport flight path generator.

## Prerequisites

1. **Google Maps JavaScript API key** with Photorealistic 3D Tiles enabled.
   - Set `NEXT_PUBLIC_GOOGLE_MAPS_API_KEY` in your environment/secrets.
2. **Google Maps Map ID** configured for Photorealistic 3D (Vector, Tilt, Photorealistic imagery enabled).
   - Set `NEXT_PUBLIC_GOOGLE_MAPS_MAP_ID` to that ID so the preview matches the operating area scale.
3. Install frontend dependencies in `web/` and run the dev server:
   ```bash
   cd web
   npm install
   npm run dev
   ```
4. Navigate to `http://localhost:3000/dev/flight-viewer` and drop a CSV that matches the generator's column layout.

## Features

- Parses every column in the generator CSV (heading, curve radius, gimbal configuration, POI metadata).
- Computes derived telemetry: horizontal/3D distance, slope grade, altitude range, and curvature limits.
- WebGL overlay renders the flight line at true altitude with per-vertex colouring for **slope** (green → red) or **curve radius**.
- Displays the POI focus point using altitude-aware advanced markers.
- Warns about questionable values (missing coordinates, turn radii tighter than the safety floor).
- Provides a compact table of the first 16 waypoints alongside aggregate metrics.

## Usage Notes

- Rendering stays client-side; CSV files are never uploaded to any service.
- Photorealistic tiles demand Chrome/Edge 113+ or Safari TP with WebGL2 enabled. The map falls back gracefully if they are unavailable.
- If `NEXT_PUBLIC_GOOGLE_MAPS_MAP_ID` is omitted, the page still works, but the basemap may not match the real-world elevation model. Always configure an explicit Map ID before validating production missions.
- Use the colour-mode toggle to inspect steep climbs vs. tight radius turns. Both metrics pull directly from the generator output, so adjustments will be immediately visible after re-uploading a CSV.

## Troubleshooting

- **Blank map / authorization errors**: confirm the API key is permitted to use Photorealistic 3D tiles and the Maps JavaScript API.
- **Jagged or missing line**: ensure the CSV includes valid latitude/longitude/altitude values for every row; the parser skips invalid rows and records each skip as a warning.
- **Unexpected curvature colour**: the algorithm clamps radii to 5–80 metres; adjust the thresholds inside `web/components/FlightPath3DMap.tsx` if your missions exceed that range.

For UX issues or new metrics you would like to visualise, open an iteration on the `dev/flight-viewer` page or extend `web/lib/flightPath.ts` with the additional analytics.
