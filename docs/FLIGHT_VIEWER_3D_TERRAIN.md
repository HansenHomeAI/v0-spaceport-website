# Flight Viewer 3D Terrain Visualization

## Overview

The Flight Viewer now includes Google Earth-like 3D terrain visualization, displaying flight trajectories over real-world terrain with satellite imagery. This enables accurate collision avoidance analysis by showing the exact spatial relationship between flight paths and ground features.

## Features

- **Real-time Elevation Data**: Fetches terrain elevation from Google Maps Elevation API in a 50x50 grid
- **Satellite Imagery Overlay**: Textures the terrain mesh with Google Static Maps satellite imagery
- **Accurate Coordinate Mapping**: Converts GPS coordinates to local 3D space with proper scaling
- **Sky-blue Background**: Replaces void when terrain loads for realistic visualization
- **Automatic Center Calculation**: Centers terrain on the average of all flight waypoints

## Implementation Details

### Terrain Mesh Generation

1. **Grid Resolution**: 50x50 elevation samples (2,601 points)
2. **Coverage Area**: 4× the flight path bounding radius
3. **Coordinate Conversion**: 
   - Latitude: ~111km per degree
   - Longitude: Adjusted for latitude (111km × cos(lat))
4. **Elevation Fetching**: Parallel API requests to Google Maps Elevation API
5. **Geometry**: BufferGeometry with computed vertex normals for realistic lighting
6. **Texture**: 640x640 satellite imagery at zoom level 17

### API Configuration

**Environment Variable Required:**
```bash
NEXT_PUBLIC_GOOGLE_MAPS_API_KEY=your-api-key-here
```

**Required API Permissions:**
- Maps Elevation API (for terrain height data)
- Maps Static API (for satellite imagery texture)

## Usage

1. **Load Flight Data**: Upload CSV or KMZ flight files
2. **Automatic Terrain Loading**: Terrain loads automatically once flights are processed
3. **View 3D Scene**: Flight paths render over real-world 3D terrain

## Testing Instructions

### Preview URL
https://agent-38146275-flight-viewer.v0-spaceport-website-preview2.pages.dev/flight-viewer

### Test Data
Use the included `Edgewood-1.csv` test file:
- Location: 38.27°N, 78.17°W (Virginia)
- 54 waypoints
- Altitude range: 215-800 ft

### Expected Behavior

1. **Initial State**: 
   - Empty scene with placeholder text
   - Black background
   - Grid plane visible

2. **After Loading Flight**:
   - Sky blue background (#87CEEB)
   - Terrain mesh with satellite imagery
   - Flight path rendered above terrain
   - Camera frustums at each waypoint

3. **Console Logs**:
   ```
   [FlightViewer] Center coordinates: { lat: 38.xxx, lon: -78.xxx }
   [Google3DTerrain] Loading terrain data for: { centerLat: 38.xxx, centerLon: -78.xxx, radius: xxx }
   [Google3DTerrain] Fetched 2601 elevation points
   [Google3DTerrain] Satellite texture loaded
   [Google3DTerrain] Terrain mesh created successfully
   ```

4. **Controls**:
   - Orbit: Left mouse drag
   - Pan: Right mouse drag
   - Zoom: Mouse wheel
   - Hover waypoints: Shows heading, gimbal, altitude, speed

## Performance Characteristics

### API Requests
- **Elevation Data**: 2,601 requests (50×50 grid + 1 center)
- **Request Pattern**: Parallel fetch with Promise.all()
- **Rate Limiting**: Google Maps API standard limits apply
- **Caching**: Browser-level HTTP caching

### Memory Usage
- **Vertices**: 2,601 points × 3 coordinates × 4 bytes = ~31KB
- **Indices**: 5,000 triangles × 3 indices × 4 bytes = ~60KB
- **Texture**: 640×640 JPEG satellite image = ~100-200KB
- **Total**: ~200-300KB per terrain mesh

### Render Performance
- **Draw Calls**: 1 mesh + flight paths + camera frustums
- **Triangles**: 5,000 terrain triangles
- **Target**: 60 FPS on modern hardware

## Coordinate System

### Global (GPS)
- Latitude/Longitude in decimal degrees
- Altitude in feet above sea level

### Local (Three.js Scene)
- Origin: Center of flight path
- X-axis: East (meters)
- Y-axis: Up (meters, converted from feet)
- Z-axis: South (meters, negated from north)

### Conversion
```typescript
const EARTH_RADIUS_METERS = 6_378_137;
const FEET_TO_METERS = 0.3048;

// Lat/lon to meters
const x = (lon - centerLon) × cos(centerLat) × EARTH_RADIUS_METERS;
const z = -(lat - centerLat) × EARTH_RADIUS_METERS;
const y = altitudeFt × FEET_TO_METERS;
```

## Troubleshooting

### Terrain Not Loading
- Check console for `[Google3DTerrain]` logs
- Verify `NEXT_PUBLIC_GOOGLE_MAPS_API_KEY` is set
- Check Google Cloud Console for API quota
- Verify Maps Elevation API and Maps Static API are enabled

### Terrain Appears Flat
- Check if elevation API returned zero values
- Verify flight location has elevation data coverage
- Check console for API errors

### Satellite Texture Missing
- Check network tab for staticmap API request
- Verify Maps Static API is enabled
- Check API key restrictions

### Flight Path Not Aligned with Terrain
- Verify coordinate conversion math
- Check console for center coordinates
- Ensure GPS coordinates are valid

## Future Enhancements

- **Progressive Loading**: Load terrain tiles incrementally for larger areas
- **LOD System**: Multiple terrain detail levels based on camera distance
- **Building Data**: Add 3D building models from Google 3D Tiles API
- **Terrain Caching**: Cache elevation data in IndexedDB
- **Higher Resolution**: Support for denser elevation grids
- **Collision Detection**: Ray-cast from flight path to terrain for clearance analysis

## API Cost Analysis

### Per Terrain Load
- **Elevation API**: 2,601 requests × $0.005 per 1,000 = ~$0.013
- **Static Maps API**: 1 request × $0.002 = $0.002
- **Total per load**: ~$0.015

### Monthly Estimates (assuming 1,000 terrain loads/month)
- **Cost**: ~$15/month
- **Google Maps Platform free tier**: $200/month credit
- **Conclusion**: Well within free tier limits

## References

- [Google Maps Elevation API](https://developers.google.com/maps/documentation/elevation)
- [Google Maps Static API](https://developers.google.com/maps/documentation/maps-static)
- [Three.js BufferGeometry](https://threejs.org/docs/#api/en/core/BufferGeometry)
- [React Three Fiber](https://docs.pmnd.rs/react-three-fiber)

