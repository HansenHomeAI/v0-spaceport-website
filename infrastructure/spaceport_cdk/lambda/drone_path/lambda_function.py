import math
import json
import csv
import io
import os
import requests
import time
from typing import List, Dict, Tuple, Optional, Union


class TerrainElevationUnavailableError(RuntimeError):
    """Raised when terrain-following requires live elevation data but Google is unavailable."""


class SpiralDesigner:
    """
    Bounded Spiral Designer - Advanced Drone Flight Pattern Generator
    
    OVERVIEW:
    =========
    This system generates exponential spiral flight patterns optimized for:
    1. Battery duration constraints (auto-optimization)
    2. Neural network training data collection (differentiated altitudes) 
    3. Real estate 3D modeling (comprehensive coverage)
    
    CORE MATHEMATICAL FOUNDATION:
    ============================
    
    Exponential Spiral Equation:
    r(t) = r₀ * exp(α * t)
    
    Where:
    - r(t) = radius at parameter t
    - r₀ = starting radius (typically 50-150ft)
    - α = expansion coefficient = ln(r_hold/r₀)/(N*Δφ) * 0.86
    - t = parameter from 0 to N*Δφ 
    - N = number of bounces (direction changes)
    - Δφ = angular step per bounce = 2π/slices
    
    NEURAL NETWORK TRAINING OPTIMIZATION:
    ===================================== 
    
    Differentiated Altitude Logic:
    - OUTBOUND: 0.20 feet per foot of distance (balanced climb rate for optimal coverage)
    - INBOUND: 0.1 feet per foot ascent (continued climb for comprehensive altitude diversity)
    - RESULT: Progressive altitude increase throughout flight for varied training data
    
    Reduced Expansion Rate:
    - Alpha coefficient reduced by 14% (× 0.86) for denser coverage
    - Creates smaller steps between bounces for better photo overlap
    - Improves neural network training data quality
    
    THREE-PHASE FLIGHT PATTERN:
    ==========================
    1. OUTWARD SPIRAL: r₀ → r_max using exponential expansion
    2. HOLD PATTERN: Circular flight at maximum radius 
    3. INWARD SPIRAL: r_max → r₀ using exponential contraction
    
    BATTERY OPTIMIZATION ALGORITHM:
    ==============================
    Uses intelligent balanced scaling + binary search:
    1. Scale bounce count with battery duration (10min→5 bounces, 20min→8 bounces)
    2. Binary search on radius with fixed bounce count
            3. 98% battery utilization safety margin
    4. O(log n) computational complexity
    
    ELEVATION INTEGRATION:
    =====================
    - Google Maps Elevation API with 15-foot proximity caching
    - Terrain-following altitudes (AGL - Above Ground Level)
    - Real-time elevation data for accurate mission planning
    """
    
    # Physical Constants and Conversion Factors
    MAX_ERR = 0.2           # Maximum error tolerance for calculations
    EARTH_R = 6378137       # Earth radius in meters (WGS84)
    FT2M = 0.3048          # Feet to meters conversion factor
    MPS_TO_MPH = 2.236936  # Meters/sec to miles/hour conversion factor
    FLIGHT_SPEED_MPS = 8.85  # 19.8 mph (matches Litchi CSV speed)
    FLIGHT_SPEED_MPH = FLIGHT_SPEED_MPS * MPS_TO_MPH
    SPEED_FT_PER_SEC = FLIGHT_SPEED_MPS * 3.28084
    TAKEOFF_LANDING_OVERHEAD_MINUTES = 2.5  # Startup/landing + maneuver buffer
    MAX_TOTAL_WAYPOINTS = 99                # DJI/Litchi practical waypoint ceiling
    RESERVED_SAFETY_WAYPOINTS = 12          # Keep headroom for terrain safety insertions
    SPIN_MAX_HEADING_DELTA_DEG = 179.0
    MAX_ANGULAR_RATE_DEG_PER_SEC = 100.0
    DEFAULT_PHOTO_INTERVAL_SECONDS = 3.0
    SPIN_PHOTO_INTERVAL_SECONDS = 2.0
    GIMBAL_MIN_PITCH_DEG = -35
    GIMBAL_MAX_PITCH_DEG = -15
    
    def __init__(self):
        """
        Initialize the SpiralDesigner with caching and API configuration.
        
        CACHING STRATEGY:
        - waypoint_cache: Stores computed waypoints to avoid recalculation
        - elevation_cache: 15-foot proximity sharing to minimize API calls
        
        API KEY MANAGEMENT:
        - Development key provided for testing
        - Production should use environment variable GOOGLE_MAPS_API_KEY
        """
        self.waypoint_cache = []
        self.elevation_cache = {}  # Cache for elevation data with coordinate keys
        self.require_live_elevation = False
        
        # DEVELOPMENT API KEY - Replace with environment variable for production
        # This key is rate-limited and for development/testing only
        dev_api_key = "AIzaSyDkdnE1weVG38PSUO5CWFneFjH16SPYZHU"
        
        # Treat a blank env var the same as missing so preview/staging never silently
        # switches from the intended production key to an unusable empty string.
        configured_api_key = os.environ.get("GOOGLE_MAPS_API_KEY")
        self.api_key = configured_api_key or dev_api_key
        
        # Log which API key is being used (mask for security)
        key_source = "PRODUCTION" if configured_api_key else "DEV (RATE LIMITED)"
        masked_key = self.api_key[:10] + "..." + self.api_key[-4:] if self.api_key else "None"
        print(f"🔑 Using {key_source} API key: {masked_key}")

    def _handle_elevation_failure(self, message: str, default_elevation: float) -> float:
        if self.require_live_elevation:
            raise TerrainElevationUnavailableError(message)
        return default_elevation
    
    def haversine_distance(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """
        Calculate great-circle distance between two GPS coordinates using Haversine formula.
        
        HAVERSINE FORMULA:
        a = sin²(Δφ/2) + cos φ1 ⋅ cos φ2 ⋅ sin²(Δλ/2)  
        c = 2 ⋅ atan2( √a, √(1−a) )
        d = R ⋅ c
        
        Where:
        φ = latitude, λ = longitude, R = earth's radius (6,371km)
        
        USAGE: Flight time estimation, elevation caching optimization
        
        Args:
            lat1, lon1: First coordinate pair (degrees)
            lat2, lon2: Second coordinate pair (degrees)

        Returns:
            Distance in meters
        """
        R = 6371000.0  # Earth radius in meters
        dLat = math.radians(lat2 - lat1)
        dLon = math.radians(lon2 - lon1)
        a = (math.sin(dLat/2)**2 +
             math.cos(math.radians(lat1)) *
             math.cos(math.radians(lat2)) *
             math.sin(dLon/2)**2)
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
        return R * c
    
    def get_elevation_feet(self, lat: float, lon: float) -> float:
        """
        Fetch terrain elevation for a single coordinate using Google Maps Elevation API.
        
        CACHING STRATEGY:
        - Cache key: "lat.6decimal,lon.6decimal" for 6-decimal precision (~0.1m accuracy)
        - Reduces API calls for nearby waypoints
        - Essential for cost control in production
        
        ERROR HANDLING:
        - Network failures: Return reasonable default (1000ft)
        - API errors: Log error and return default
        - Invalid coordinates: Return default
        
        ELEVATION API RESPONSE FORMAT:
        {
            "results": [{"elevation": 1378.2, "location": {...}}],
            "status": "OK"
        }
        
        Args:
            lat: Latitude in decimal degrees
            lon: Longitude in decimal degrees

        Returns:
            Elevation in feet above sea level
        """
        # Check cache first to minimize API calls
        cache_key = f"{lat:.6f},{lon:.6f}"
        if cache_key in self.elevation_cache:
            return self.elevation_cache[cache_key]
        
        if not self.api_key:
            # Graceful degradation when no API key available
            print("Warning: No Google Maps API key available, using default elevation")
            return self._handle_elevation_failure(
                "Terrain following is unavailable because GOOGLE_MAPS_API_KEY is not configured.",
                4500.0,
            )
        
        try:
            # Google Maps Elevation API endpoint
            url = f"https://maps.googleapis.com/maps/api/elevation/json?locations={lat},{lon}&key={self.api_key}"
            response = requests.get(url, timeout=10)

            if response.status_code != 200:
                return self._handle_elevation_failure(
                    f"Terrain following is unavailable because the Google Elevation API returned HTTP {response.status_code}.",
                    1000.0,
                )

            data = response.json()
            if data["status"] != "OK" or not data["results"]:
                status = data.get("status", "Unknown error")
                detail = data.get("error_message")
                print(f"Google Elevation API error: {status}")
                if detail:
                    print(f"Google Elevation API detail: {detail}")
                message = f"Terrain following is unavailable because Google Elevation returned {status}"
                if detail:
                    message = f"{message}: {detail}"
                return self._handle_elevation_failure(message, 1000.0)
            
            # Convert meters to feet (Google returns meters)
            elevation_meters = data["results"][0]["elevation"]
            elevation_feet = elevation_meters * 3.28084
            
            # Cache the result for future use
            self.elevation_cache[cache_key] = elevation_feet
            print(f"Elevation fetched: {lat:.5f},{lon:.5f} = {elevation_feet:.1f} ft")
            return elevation_feet
            
        except Exception as e:
            print(f"Elevation API error for {lat},{lon}: {str(e)}")
            # Return reasonable default elevation on any error
            return self._handle_elevation_failure(
                f"Terrain following is unavailable because the Google Elevation request failed: {str(e)}",
                1000.0,
            )
    
    def get_elevations_feet_optimized(self, locations: List[Tuple[float, float]]) -> List[float]:
        """
        Optimized batch elevation fetching with 15-foot proximity sharing.
        
        OPTIMIZATION ALGORITHM:
        1. For each new waypoint, check if any previous waypoint is within 15 feet
        2. If found, reuse that elevation data (saves API calls)
        3. If not found, fetch new elevation and add to processed list
        4. Continue for all waypoints
        
        COST SAVINGS:
        - Typical spiral: 50+ waypoints
        - Without optimization: 50+ API calls ($0.005 each = $0.25+)
        - With optimization: ~15 API calls ($0.075)
        - 70% cost reduction while maintaining accuracy
        
        ACCURACY JUSTIFICATION:
        - 15 feet horizontal distance
        - Typical terrain slope: <5% grade
        - Maximum elevation error: 15ft × 0.05 = 0.75ft
        - Acceptable for drone flight planning (±1ft tolerance)
        
        Args:
            locations: List of (lat, lon) tuples
            
        Returns:
            List of elevations in feet, same order as input
        """
        if not locations:
            return []
        
        elevations = []
        processed_locations = []  # Track (lat, lon, elevation) for proximity checking
        
        for i, (lat, lon) in enumerate(locations):
            # Check if we can reuse elevation from a nearby processed location
            reused_elevation = None
            
            for j, (prev_lat, prev_lon, prev_elev) in enumerate(processed_locations):
                distance_ft = self.haversine_distance(lat, lon, prev_lat, prev_lon) * 3.28084
                if distance_ft <= 15.0:  # Within 15 feet
                    reused_elevation = prev_elev
                    break
            
            if reused_elevation is not None:
                # Reuse nearby elevation (saves API call)
                elevations.append(reused_elevation)
                processed_locations.append((lat, lon, reused_elevation))
            else:
                # Need to fetch new elevation
                elevation = self.get_elevation_feet(lat, lon)
                elevations.append(elevation)
                processed_locations.append((lat, lon, elevation))
        
        return elevations
    
    def distance(self, a: Dict, b: Dict) -> float:
        """Calculate 2D Euclidean distance between two points in feet."""
        return math.sqrt((a['x'] - b['x'])**2 + (a['y'] - b['y'])**2)
    
    def rotate_point(self, point: Dict, angle: float) -> Dict:
        """
        Rotate a 2D point by given angle using rotation matrix.
        
        ROTATION MATRIX:
        [x'] = [cos θ  -sin θ] [x]
        [y']   [sin θ   cos θ] [y]
        
        Used for: Orienting spiral slices around the center point
        """
        return {
            'x': point['x'] * math.cos(angle) - point['y'] * math.sin(angle),
            'y': point['x'] * math.sin(angle) + point['y'] * math.cos(angle)
        }

    def _segment_distance_feet(self, start: Dict, end: Dict) -> float:
        """Compute ground distance in feet between two waypoint records."""
        return self.haversine_distance(
            start['latitude'],
            start['longitude'],
            end['latitude'],
            end['longitude'],
        ) * 3.28084

    def _required_spin_splits(self, distances_ft: List[float], max_gap_ft: float) -> List[int]:
        """Calculate splits needed per segment to keep all segments under max_gap_ft."""
        if max_gap_ft <= 0:
            return [0] * len(distances_ft)

        splits: List[int] = []
        for distance in distances_ft:
            if distance <= 0:
                splits.append(0)
            else:
                splits.append(max(0, int(math.ceil(distance / max_gap_ft)) - 1))
        return splits

    def _allocate_spin_splits(self, distances_ft: List[float], spin_budget: int) -> List[int]:
        """
        Allocate spin insertions to minimize the longest segment (minimax).

        Uses binary search to find the smallest feasible max segment length and then
        spends any remaining budget on currently-longest segments.
        """
        if spin_budget <= 0 or not distances_ft:
            return [0] * len(distances_ft)

        max_distance = max(distances_ft)
        if max_distance <= 0:
            return [0] * len(distances_ft)

        # Theoretical best lower bound if all extra points were perfectly distributed.
        low = max_distance / (spin_budget + 1)
        high = max_distance

        for _ in range(40):
            mid = (low + high) / 2.0
            required = sum(self._required_spin_splits(distances_ft, mid))
            if required > spin_budget:
                low = mid
            else:
                high = mid

        splits = self._required_spin_splits(distances_ft, high)
        total_used = sum(splits)

        # Safety fallback for floating-point edge cases.
        if total_used > spin_budget:
            for idx in sorted(range(len(splits)), key=lambda i: distances_ft[i]):
                while splits[idx] > 0 and total_used > spin_budget:
                    splits[idx] -= 1
                    total_used -= 1

        # Use remaining budget to further reduce the largest resulting segment.
        remaining = spin_budget - total_used
        while remaining > 0:
            best_idx = -1
            best_segment = -1.0
            for i, distance in enumerate(distances_ft):
                if distance <= 0:
                    continue
                # After n splits, segment is split into n+1 pieces.
                segment_size = distance / (splits[i] + 1)
                if segment_size > best_segment:
                    best_segment = segment_size
                    best_idx = i

            if best_idx < 0:
                break

            splits[best_idx] += 1
            remaining -= 1

        return splits

    def _insert_spin_waypoints(self, waypoint_records: List[Dict]) -> List[Dict]:
        """
        Insert transit spin waypoints (never hover-in-place) to reduce large gaps
        while staying <= 99 total points.
        """
        if len(waypoint_records) < 2:
            return waypoint_records

        spin_budget = self.MAX_TOTAL_WAYPOINTS - len(waypoint_records)
        if spin_budget <= 0:
            return waypoint_records

        distances_ft = [
            self._segment_distance_feet(waypoint_records[i], waypoint_records[i + 1])
            for i in range(len(waypoint_records) - 1)
        ]
        splits = self._allocate_spin_splits(distances_ft, spin_budget)

        with_spin: List[Dict] = []
        for i in range(len(waypoint_records) - 1):
            start = waypoint_records[i]
            end = waypoint_records[i + 1]
            with_spin.append(start)

            segment_splits = splits[i]
            for split_idx in range(1, segment_splits + 1):
                fraction = split_idx / (segment_splits + 1)
                spin_point = {
                    'latitude': start['latitude'] + fraction * (end['latitude'] - start['latitude']),
                    'longitude': start['longitude'] + fraction * (end['longitude'] - start['longitude']),
                    'altitude': round(start['altitude'] + fraction * (end['altitude'] - start['altitude']), 2),
                    'curve_size_meters': round(
                        start['curve_size_meters'] + fraction * (end['curve_size_meters'] - start['curve_size_meters']),
                        2,
                    ),
                    'x': start['x'] + fraction * (end['x'] - start['x']),
                    'y': start['y'] + fraction * (end['y'] - start['y']),
                    'phase': 'spin',
                    'is_spin': True,
                }
                with_spin.append(spin_point)

        with_spin.append(waypoint_records[-1])
        return with_spin[:self.MAX_TOTAL_WAYPOINTS]

    def _build_gimbal_pitch_series(self, total_waypoints: int) -> List[int]:
        """
        Build a deterministic shuffled even distribution across gimbal range.
        """
        if total_waypoints <= 0:
            return []
        if total_waypoints == 1:
            return [self.GIMBAL_MIN_PITCH_DEG]

        span = self.GIMBAL_MAX_PITCH_DEG - self.GIMBAL_MIN_PITCH_DEG
        evenly_spaced = [
            self.GIMBAL_MIN_PITCH_DEG + (span * i / (total_waypoints - 1))
            for i in range(total_waypoints)
        ]

        # Deterministic Fisher-Yates shuffle with an LCG seed.
        indices = list(range(total_waypoints))
        seed = total_waypoints * 7919 + 104729
        for i in range(total_waypoints - 1, 0, -1):
            seed = (1103515245 * seed + 12345) & 0x7fffffff
            j = seed % (i + 1)
            indices[i], indices[j] = indices[j], indices[i]

        return [int(round(evenly_spaced[idx])) for idx in indices]

    def _enforce_waypoint_record_limit(self, waypoint_records: List[Dict]) -> List[Dict]:
        """
        Keep waypoint records within the Litchi 99-point cap by even downsampling.
        """
        total = len(waypoint_records)
        limit = self.MAX_TOTAL_WAYPOINTS
        if total <= limit:
            return waypoint_records

        # Preserve endpoints and distribute remaining samples uniformly.
        keep_indices = {0, total - 1}
        interior_to_pick = limit - 2
        if interior_to_pick > 0:
            step = (total - 1) / (limit - 1)
            for i in range(1, limit - 1):
                keep_indices.add(int(round(i * step)))

        ordered_indices = sorted(idx for idx in keep_indices if 0 <= idx < total)
        if len(ordered_indices) > limit:
            ordered_indices = ordered_indices[:limit]

        return [waypoint_records[idx] for idx in ordered_indices]

    def _compute_path_headings(self, waypoint_records: List[Dict]) -> List[int]:
        """Compute standard forward-facing headings from local X/Y geometry."""
        headings: List[int] = []
        for i, wp in enumerate(waypoint_records):
            if i < len(waypoint_records) - 1:
                next_wp = waypoint_records[i + 1]
                dx = next_wp['x'] - wp['x']
                dy = next_wp['y'] - wp['y']
                if abs(dx) < 1e-9 and abs(dy) < 1e-9:
                    heading = headings[-1] if headings else 0
                else:
                    heading = round(((math.atan2(dx, dy) * 180 / math.pi) + 360) % 360)
            else:
                heading = headings[-1] if headings else 0
            headings.append(heading)
        return headings

    def _compute_spin_headings(self, waypoint_records: List[Dict]) -> List[int]:
        """
        Compute constant clockwise spin headings constrained by:
        - Litchi shortest-path delta ceiling (179 deg)
        - Motion-blur angular velocity ceiling (100 deg/s)
        """
        if not waypoint_records:
            return []
        if len(waypoint_records) == 1:
            return [0]

        segment_distances_ft = [
            self._segment_distance_feet(waypoint_records[i], waypoint_records[i + 1])
            for i in range(len(waypoint_records) - 1)
        ]
        longest_segment_ft = max(segment_distances_ft) if segment_distances_ft else 0.0
        if longest_segment_ft <= 0:
            return [0] * len(waypoint_records)

        longest_segment_seconds = longest_segment_ft / max(self.SPEED_FT_PER_SEC, 1e-6)
        blur_limited_delta = self.MAX_ANGULAR_RATE_DEG_PER_SEC * longest_segment_seconds
        max_delta = min(self.SPIN_MAX_HEADING_DELTA_DEG, blur_limited_delta)
        spin_rate_deg_per_ft = max_delta / longest_segment_ft

        headings = [0]
        cumulative_distance_ft = 0.0
        for distance_ft in segment_distances_ft:
            cumulative_distance_ft += distance_ft
            heading = round((cumulative_distance_ft * spin_rate_deg_per_ft) % 360)
            headings.append(heading)

        return headings

    def _build_waypoint_records(
        self,
        spiral_path: List[Dict],
        center: Dict,
        ground_elevations: List[float],
        takeoff_elevation_feet: float,
        min_height: float,
        max_height: Optional[float],
        enhanced_waypoints_data: Optional[List[Dict]] = None,
    ) -> List[Dict]:
        """
        Build per-waypoint records (lat/lon/alt/curve/x/y) before heading/gimbal assignment.
        """
        first_waypoint_distance = 0
        max_outbound_altitude = 0
        max_outbound_distance = 0
        records: List[Dict] = []

        for i, wp in enumerate(spiral_path):
            is_safety_waypoint = bool(
                enhanced_waypoints_data
                and i < len(enhanced_waypoints_data)
                and enhanced_waypoints_data[i].get('is_safety', False)
            )

            phase = wp.get('phase', 'unknown')

            if is_safety_waypoint:
                safety_data = enhanced_waypoints_data[i]
                latitude = round(safety_data['coords']['lat'] * 100000) / 100000
                longitude = round(safety_data['coords']['lon'] * 100000) / 100000
                altitude_agl = safety_data['safety_altitude'] - takeoff_elevation_feet
                if altitude_agl < min_height:
                    altitude_agl = min_height
                altitude = round(altitude_agl * 100) / 100
            else:
                coords = self.xy_to_lat_lon(wp['x'], wp['y'], center['lat'], center['lon'])
                latitude = round(coords['lat'] * 100000) / 100000
                longitude = round(coords['lon'] * 100000) / 100000

                ground_elevation = ground_elevations[i]
                local_ground_offset = ground_elevation - takeoff_elevation_feet
                if local_ground_offset < 0:
                    local_ground_offset = 0

                dist_from_center = math.sqrt(wp['x']**2 + wp['y']**2)

                if i == 0:
                    first_waypoint_distance = dist_from_center
                    desired_agl = min_height
                    max_outbound_altitude = min_height
                    max_outbound_distance = dist_from_center
                elif 'outbound' in phase or 'hold' in phase:
                    additional_distance = dist_from_center - first_waypoint_distance
                    if additional_distance < 0:
                        additional_distance = 0
                    agl_increment = additional_distance * 0.20
                    desired_agl = min_height + agl_increment

                    if desired_agl > max_outbound_altitude:
                        max_outbound_altitude = desired_agl
                        max_outbound_distance = dist_from_center
                elif 'inbound' in phase:
                    distance_from_max = max_outbound_distance - dist_from_center
                    if distance_from_max < 0:
                        distance_from_max = 0
                    altitude_increase = distance_from_max * 0.1
                    desired_agl = max_outbound_altitude + altitude_increase

                    if desired_agl < min_height:
                        desired_agl = min_height
                else:
                    additional_distance = dist_from_center - first_waypoint_distance
                    if additional_distance < 0:
                        additional_distance = 0
                    agl_increment = additional_distance * 0.20
                    desired_agl = min_height + agl_increment

                final_altitude = local_ground_offset + desired_agl

                if max_height is not None:
                    adjusted_max_height = max_height - takeoff_elevation_feet
                    current_agl = final_altitude - ground_elevation
                    if current_agl > adjusted_max_height:
                        final_altitude = ground_elevation + adjusted_max_height

                altitude = round(final_altitude * 100) / 100

            curve_size_meters = round((wp['curve'] * self.FT2M) * 100) / 100

            records.append({
                'latitude': latitude,
                'longitude': longitude,
                'altitude': altitude,
                'curve_size_meters': curve_size_meters,
                'x': wp['x'],
                'y': wp['y'],
                'phase': phase,
                'is_spin': False,
            })

        return records
    
    def normalize_expansion_request(
        self,
        min_expansion_dist: Optional[float] = None,
        max_expansion_dist: Optional[float] = None,
    ) -> Dict:
        """Normalize optional expansion inputs into a single request shape."""
        if min_expansion_dist is not None and min_expansion_dist <= 0:
            raise ValueError("minExpansionDist must be greater than 0")
        if max_expansion_dist is not None and max_expansion_dist <= 0:
            raise ValueError("maxExpansionDist must be greater than 0")

        if min_expansion_dist is None and max_expansion_dist is None:
            return {
                'mode': 'default',
                'requested_min': None,
                'requested_max': None,
                'has_custom_spacing': False,
            }

        if min_expansion_dist is None:
            min_expansion_dist = max_expansion_dist
        if max_expansion_dist is None:
            max_expansion_dist = min_expansion_dist

        return {
            'mode': 'custom',
            'requested_min': float(min_expansion_dist),
            'requested_max': float(max_expansion_dist),
            'has_custom_spacing': True,
        }

    def build_requested_custom_intervals(
        self,
        N: int,
        requested_min: Optional[float],
        requested_max: Optional[float],
    ) -> List[float]:
        """Build the per-bounce expansion distances for a custom spacing request."""
        if requested_min is None and requested_max is None:
            return []

        min_dist = requested_min if requested_min is not None else requested_max
        max_dist = requested_max if requested_max is not None else min_dist
        if min_dist is None or max_dist is None:
            return []

        if N <= 1:
            return [float(min_dist)]

        return [
            float(min_dist + (max_dist - min_dist) * k / max(N - 1, 1))
            for k in range(N)
        ]

    @staticmethod
    def scale_custom_intervals(intervals: List[float], scale: float) -> List[float]:
        """Scale a custom spacing profile while preserving its shape."""
        return [float(interval * scale) for interval in intervals]

    @staticmethod
    def custom_outer_radius(r0: float, intervals: List[float]) -> float:
        """Return the maximum radius reached by a custom interval profile."""
        return float(r0 + sum(intervals))

    def calculate_actual_outer_radius(self, params: Dict) -> float:
        """Measure the maximum waypoint radius from the resolved path geometry."""
        wps = self.build_slice(0, params)
        if not wps:
            return float(params.get('r0', 0.0))
        return max(math.sqrt(wp['x'] * wp['x'] + wp['y'] * wp['y']) for wp in wps)

    def make_spiral(
        self,
        dphi: float,
        N: int,
        r0: float,
        r_hold: float,
        steps: int = 1200,
        custom_expansion_profile: Optional[List[float]] = None,
        min_expansion_dist: float = None,
        max_expansion_dist: float = None,
    ) -> List[Dict]:
        """
        Generate the core spiral pattern.
        
        Two modes:
        1. DEFAULT (exponential): r(t) = r₀ * exp(α*t) with progressive alpha
        2. CUSTOM DISTANCES: bounce-to-bounce distance progresses linearly
           from min_expansion_dist to max_expansion_dist (both in feet).
        
        Args:
            dphi: Angular step size per bounce (radians)
            N: Number of bounces (direction changes)
            r0: Starting radius (feet)
            r_hold: Target hold radius (feet) - used for alpha in default mode
            steps: Number of discrete points to generate
            min_expansion_dist: Minimum radial distance between bounces (feet), optional
            max_expansion_dist: Maximum radial distance between bounces (feet), optional
        """
        interval_profile = list(custom_expansion_profile) if custom_expansion_profile is not None else None
        if interval_profile is None:
            expansion_request = self.normalize_expansion_request(min_expansion_dist, max_expansion_dist)
            if expansion_request['has_custom_spacing']:
                interval_profile = self.build_requested_custom_intervals(
                    N,
                    expansion_request['requested_min'],
                    expansion_request['requested_max'],
                )
        else:
            expansion_request = {
                'mode': 'custom',
                'requested_min': interval_profile[0] if interval_profile else None,
                'requested_max': interval_profile[-1] if interval_profile else None,
                'has_custom_spacing': bool(interval_profile),
            }

        use_custom_distances = interval_profile is not None and len(interval_profile) > 0
        
        t_out = N * dphi
        t_hold = dphi
        t_total = 2 * t_out + t_hold
        
        if use_custom_distances:
            if len(interval_profile) != N:
                raise ValueError(f"Custom expansion profile length {len(interval_profile)} must match N={N}")

            bounce_radii = [float(r0)]
            for dist in interval_profile:
                bounce_radii.append(bounce_radii[-1] + dist)
            custom_max_radius = bounce_radii[-1]
            min_d = interval_profile[0]
            max_d = interval_profile[-1]
            print(f"🎯 Custom expansion: min={min_d}ft, max={max_d}ft, "
                  f"N={N}, final_radius={custom_max_radius:.1f}ft, "
                  f"bounce_radii={[round(r, 1) for r in bounce_radii]}")
        else:
            base_alpha = math.log(r_hold / r0) / (N * dphi)
            radius_ratio = r_hold / r0
            
            if radius_ratio > 20:
                early_density_factor = 1.02
                late_density_factor = 0.80
            elif radius_ratio > 10:
                early_density_factor = 1.05
                late_density_factor = 0.85
            else:
                early_density_factor = 1.0
                late_density_factor = 0.90
            
            alpha_early = base_alpha * early_density_factor
            alpha_late = base_alpha * late_density_factor
            t_transition = t_out * 0.4
            r_transition = r0 * math.exp(alpha_early * t_transition)
            actual_max_radius = r_transition * math.exp(alpha_late * (t_out - t_transition))
        
        spiral_points = []
        
        for i in range(steps):
            th = i * t_total / (steps - 1)
            
            if use_custom_distances:
                if th <= t_out:
                    bounce_progress = th / dphi
                    bounce_idx = min(int(bounce_progress), N - 1)
                    frac = bounce_progress - bounce_idx
                    r = bounce_radii[bounce_idx] + frac * (bounce_radii[bounce_idx + 1] - bounce_radii[bounce_idx])
                elif th <= t_out + t_hold:
                    r = custom_max_radius
                else:
                    inbound_t = th - (t_out + t_hold)
                    inbound_progress = inbound_t / dphi
                    bounce_idx = min(int(inbound_progress), N - 1)
                    frac = inbound_progress - bounce_idx
                    from_r = bounce_radii[N - bounce_idx]
                    to_r = bounce_radii[max(N - bounce_idx - 1, 0)]
                    r = from_r + frac * (to_r - from_r)
            else:
                if th <= t_out:
                    if th <= t_transition:
                        r = r0 * math.exp(alpha_early * th)
                    else:
                        r = r_transition * math.exp(alpha_late * (th - t_transition))
                elif th <= t_out + t_hold:
                    r = actual_max_radius
                else:
                    inbound_t = th - (t_out + t_hold)
                    r = actual_max_radius * math.exp(-alpha_late * inbound_t)
            
            phase = ((th / dphi) % 2 + 2) % 2
            phi = phase * dphi if phase <= 1 else (2 - phase) * dphi
            
            spiral_points.append({
                'x': r * math.cos(phi),
                'y': r * math.sin(phi)
            })
        
        return spiral_points
    
    def build_slice(self, slice_idx: int, params: Dict) -> List[Dict]:
        """
        Build waypoints for a single spiral slice with dynamic curve radius optimization.
        
        SLICE ORIENTATION:
        Each slice is rotated by (slice_idx * 2π/num_slices) + π/2
        The π/2 offset ensures first slice points north for intuitive navigation.
        
        WAYPOINT SAMPLING STRATEGY:
        Instead of recalculating spiral math, we sample directly from the high-precision
        spiral points (1200 points). This ensures perfect alignment between visualization
        and actual flight paths.
        
        DYNAMIC CURVE RADIUS SYSTEM:
        ============================
        
        MIDPOINTS (Ultra-smooth flight):
        - Base: 50ft
        - Scale: distance × 1.2  
        - Max: 1500ft
        - Purpose: Massive curves for buttery-smooth transitions
        
        NON-MIDPOINTS (Precise directional control):
        - Base: 40ft (doubled from original 20ft for smoother flight)
        - Scale: distance × 0.05
        - Max: 160ft (doubled from original 80ft)
        - Purpose: Larger curves for smoother directional changes while maintaining precision
        
        WAYPOINT PHASES:
        ===============
        - outbound_start: First waypoint at center
        - outbound_mid_N: Smooth transition points  
        - outbound_bounce_N: Direction change points
        - hold_mid: Middle of hold pattern
        - hold_end: End of hold pattern  
        - inbound_mid_N: Inbound transition points
        - inbound_bounce_N: Inbound direction changes
        
        Args:
            slice_idx: Index of the slice (0 to num_slices-1)
            params: Parameters dict with slices, N, r0, rHold
            
        Returns:
            List of waypoint dictionaries with x, y, curve, phase, t, id
        """
        dphi = 2 * math.pi / params['slices']
        offset = math.pi / 2 + slice_idx * dphi  # Orientation offset for this slice
        
        # Generate high-precision spiral points (1200 points for accuracy)
        spiral_pts = self.make_spiral(
            dphi, params['N'], params['r0'], params['rHold'],
            custom_expansion_profile=params.get('customExpansionProfile'),
            min_expansion_dist=params.get('minExpansionDist'),
            max_expansion_dist=params.get('maxExpansionDist'),
        )
        t_out = params['N'] * dphi
        t_hold = dphi
        t_total = 2 * t_out + t_hold
        
        waypoints = []
        
        # Slice-aware waypoint density (ported from ShapeLab)
        is_single_slice = params['slices'] == 1
        is_double_slice = params['slices'] == 2
        
        # Define midpoint fractions based on slice count
        if is_single_slice:
            shared_mid_fractions = [1/6, 2/6, 3/6, 4/6, 5/6]  # 5 midpoints per segment
        elif is_double_slice:
            shared_mid_fractions = [1/3, 2/3]  # 2 midpoints per segment
        else:
            shared_mid_fractions = [0.5]  # 1 midpoint per segment (standard)
        
        # Use reversed order for outbound (approaching bounce), normal order for inbound
        outbound_mid_fractions = list(reversed(shared_mid_fractions))
        inbound_mid_fractions = shared_mid_fractions
        hold_mid_fractions = shared_mid_fractions
        
        # Helper to generate progress labels for single/double slice flights
        def label_from_fraction(value: float) -> int:
            """Convert fraction to percentage label (e.g., 0.5 -> 50, 1/6 -> 17)"""
            return round((value + 1e-9) * 100)  # epsilon prevents floating point issues
        
        def find_spiral_point(target_t: float, is_midpoint: bool = False, phase: str = 'unknown') -> Dict:
            """
            Sample spiral point at given parameter t with dynamic curve radius calculation.
            
            SAMPLING ALGORITHM:
            1. Convert parameter t to array index
            2. Clamp index to valid range
            3. Extract point from pre-computed spiral
            4. Rotate to match slice orientation  
            5. Calculate dynamic curve radius based on distance and waypoint type
            
            Args:
                target_t: Parameter value (0 to t_total)
                is_midpoint: Whether this is a transition point (gets larger curves)
                phase: Waypoint phase identifier for altitude calculation
                
            Returns:
                Waypoint dictionary with all required fields
            """
            # Convert parameter t to spiral array index
            target_index = round(target_t * (len(spiral_pts) - 1) / t_total)
            clamped_index = max(0, min(len(spiral_pts) - 1, target_index))
            pt = spiral_pts[clamped_index]
            
            # Rotate point to match slice orientation
            rot_x = pt['x'] * math.cos(offset) - pt['y'] * math.sin(offset)
            rot_y = pt['x'] * math.sin(offset) + pt['y'] * math.cos(offset)
            
            # Dynamic curve radius calculation based on distance from center
            distance_from_center = math.sqrt(rot_x**2 + rot_y**2)
            
            if is_midpoint:
                # MIDPOINT CURVES: Ultra-smooth for seamless transitions
                base_curve = 50
                scale_factor = 1.2
                max_curve = 1500
                curve_radius = min(max_curve, base_curve + (distance_from_center * scale_factor))
            else:
                # NON-MIDPOINT CURVES: Doubled for smoother directional control  
                base_curve = 40  # Doubled from 20 for smoother flight
                scale_factor = 0.05
                max_curve = 160  # Doubled from 80 for smoother flight
                curve_radius = min(max_curve, base_curve + (distance_from_center * scale_factor))
            
            curve_radius = round(curve_radius * 10) / 10  # Round to 1 decimal place
            
            return {
                'x': rot_x,
                'y': rot_y,
                'curve': curve_radius,
                'phase': phase,  # ← Essential for differentiated altitude calculation
                't': target_t,
                'id': f"{phase}_{target_t:.3f}"
            }
        
        # PHASE 1: OUTWARD SPIRAL - Exponential expansion with direction changes
        waypoints.append(find_spiral_point(0, False, 'outbound_start'))
        
        for bounce in range(1, params['N'] + 1):
            # Add midpoints before each bounce (slice-aware density)
            for fraction in outbound_mid_fractions:
                t_mid = (bounce - fraction) * dphi
                progress_label = label_from_fraction(1 - fraction)
                
                # Add progress labels for single/double slice flights for better tracking
                if is_single_slice or is_double_slice:
                    phase = f'outbound_mid_{bounce}_q{progress_label}'
                else:
                    phase = f'outbound_mid_{bounce}'
                
                waypoints.append(find_spiral_point(t_mid, True, phase))
            
            # Add bounce point (direction change)
            t_bounce = bounce * dphi
            waypoints.append(find_spiral_point(t_bounce, False, f'outbound_bounce_{bounce}'))
        
        # PHASE 2: HOLD PATTERN - Circular flight at maximum radius
        t_end_hold = t_out + t_hold
        custom_hold_phases = is_single_slice or is_double_slice
        
        # Add hold midpoints (slice-aware density)
        for fraction in hold_mid_fractions:
            t_hold_point = t_out + fraction * t_hold
            
            # Add progress labels for single/double slice flights
            if custom_hold_phases:
                phase = f'hold_mid_q{label_from_fraction(fraction)}'
            else:
                phase = 'hold_mid'
            
            waypoints.append(find_spiral_point(t_hold_point, True, phase))
        
        waypoints.append(find_spiral_point(t_end_hold, False, 'hold_end'))
        
        # PHASE 3: INBOUND SPIRAL - Exponential contraction with direction changes
        
        # Add first inbound midpoints (slice-aware density)
        for fraction in inbound_mid_fractions:
            t_first_inbound_mid = t_end_hold + fraction * dphi
            
            # Add progress labels for single/double slice flights
            if is_single_slice or is_double_slice:
                phase = f'inbound_mid_0_q{label_from_fraction(fraction)}'
            else:
                phase = 'inbound_mid_0'
            
            waypoints.append(find_spiral_point(t_first_inbound_mid, True, phase))
        
        for bounce in range(1, params['N'] + 1):
            # Add bounce point (direction change)
            t_bounce = t_end_hold + bounce * dphi
            waypoints.append(find_spiral_point(t_bounce, False, f'inbound_bounce_{bounce}'))
            
            # Add midpoints after bounce (except after final bounce)
            if bounce < params['N']:
                for fraction in inbound_mid_fractions:
                    t_mid = t_end_hold + (bounce + fraction) * dphi
                    
                    # Add progress labels for single/double slice flights
                    if is_single_slice or is_double_slice:
                        phase = f'inbound_mid_{bounce}_q{label_from_fraction(fraction)}'
                    else:
                        phase = f'inbound_mid_{bounce}'
                    
                    waypoints.append(find_spiral_point(t_mid, True, phase))
        
        return waypoints
    
    def compute_waypoints(self, params: Dict) -> List[List[Dict]]:
        """
        Compute waypoints for all slices and cache results.
        
        MULTI-SLICE STRATEGY:
        Each battery flies one slice (360°/num_slices angular section).
        This enables parallel missions with multiple drones or sequential flights.
        
        Args:
            params: Parameters dict with slices, N, r0, rHold
            
        Returns:
            List of waypoint lists, one per slice
        """
        self.waypoint_cache = []
        for i in range(params['slices']):
            self.waypoint_cache.append(self.build_slice(i, params))
        return self.waypoint_cache

    @staticmethod
    def normalize_angle_deg(angle_deg: float) -> float:
        """Normalize an angle to the [0, 360) range."""
        normalized = angle_deg % 360.0
        return normalized if normalized >= 0 else normalized + 360.0

    def parse_boundary(self, raw_boundary: Optional[Dict], fallback_center: Optional[Dict] = None) -> Optional[Dict]:
        """Validate and normalize a boundary ellipse payload."""
        if not isinstance(raw_boundary, dict):
            return None

        enabled = bool(raw_boundary.get('enabled', True))
        center = self.parse_center({
            'lat': raw_boundary.get('centerLat'),
            'lng': raw_boundary.get('centerLng'),
        }) or fallback_center
        if not enabled or not center:
            return None

        try:
            major_radius = max(150.0, float(raw_boundary.get('majorRadiusFt', 150.0)))
            minor_radius = max(150.0, float(raw_boundary.get('minorRadiusFt', 150.0)))
        except (TypeError, ValueError):
            return None

        major_radius = max(major_radius, minor_radius)
        minor_radius = min(major_radius, minor_radius)

        rotation_deg = 0.0
        try:
            rotation_deg = self.normalize_angle_deg(float(raw_boundary.get('rotationDeg', 0.0)))
        except (TypeError, ValueError):
            rotation_deg = 0.0

        return {
            'version': 1,
            'enabled': True,
            'centerLat': float(center['lat']),
            'centerLng': float(center['lon']),
            'majorRadiusFt': major_radius,
            'minorRadiusFt': minor_radius,
            'rotationDeg': rotation_deg,
        }

    def parse_boundary_plan(self, raw_plan: Optional[Dict], num_batteries: int) -> Optional[Dict]:
        """Normalize a persisted boundary plan payload."""
        if not isinstance(raw_plan, dict):
            return None

        batteries = []
        for item in raw_plan.get('batteries', []):
            if not isinstance(item, dict):
                continue
            try:
                battery_index = int(item.get('batteryIndex'))
                start_angle_deg = float(item.get('startAngleDeg', 0.0))
                sweep_angle_deg = max(0.0, float(item.get('sweepAngleDeg', 0.0)))
                bounce_count = max(1, int(item.get('bounceCount', 1)))
                estimated_time = max(0.0, float(item.get('estimatedTimeMinutes', 0.0)))
                waypoint_count = max(0, int(item.get('waypointCount', 0)))
                coverage_share = max(0.0, float(item.get('coverageShare', 0.0)))
            except (TypeError, ValueError):
                continue

            batteries.append({
                'batteryIndex': battery_index,
                'startAngleDeg': self.normalize_angle_deg(start_angle_deg),
                'sweepAngleDeg': sweep_angle_deg,
                'bounceCount': bounce_count,
                'estimatedTimeMinutes': estimated_time,
                'waypointCount': waypoint_count,
                'coverageShare': coverage_share,
                'fitStatus': item.get('fitStatus', raw_plan.get('fitStatus', 'full')),
            })

        if not batteries:
            return None

        batteries.sort(key=lambda entry: entry['batteryIndex'])
        coverage_ratio = raw_plan.get('coverageRatio')
        try:
            coverage_ratio_value = min(1.0, max(0.0, float(coverage_ratio)))
        except (TypeError, ValueError):
            coverage_ratio_value = min(1.0, sum(entry['sweepAngleDeg'] for entry in batteries) / 360.0)

        limiting_index = raw_plan.get('limitingBatteryIndex')
        try:
            limiting_value = int(limiting_index) if limiting_index is not None else None
        except (TypeError, ValueError):
            limiting_value = None

        return {
            'version': 1,
            'fitStatus': raw_plan.get('fitStatus', 'full'),
            'coverageRatio': coverage_ratio_value,
            'limitingBatteryIndex': limiting_value,
            'batteries': batteries[:num_batteries],
        }

    def boundary_plan_entry(self, boundary_plan: Dict, battery_index: int) -> Optional[Dict]:
        """Return the 1-based battery entry from a boundary plan."""
        for item in boundary_plan.get('batteries', []):
            if int(item.get('batteryIndex', 0)) == battery_index:
                return item
        return None

    def build_boundary_slice(
        self,
        battery_index: int,
        total_batteries: int,
        boundary: Dict,
        start_angle_deg: float,
        sweep_angle_deg: float,
        bounce_count: int,
        params: Dict,
    ) -> List[Dict]:
        """
        Build waypoints for a boundary-fit ellipse slice with a custom angular sweep.
        """
        if sweep_angle_deg <= 0:
            return []

        dphi = math.radians(max(0.25, sweep_angle_deg))
        offset = math.radians(boundary['rotationDeg'])
        sector_start = math.radians(start_angle_deg)
        major_radius = max(150.0, float(boundary['majorRadiusFt']))
        minor_radius = max(150.0, min(float(boundary['minorRadiusFt']), major_radius))
        scale_radius = max(major_radius, minor_radius, 1.0)

        base_r0 = float(params.get('r0', 200.0))
        normalized_r0 = min(0.92, max(0.05, base_r0 / scale_radius))

        min_expansion = params.get('minExpansionDist')
        max_expansion = params.get('maxExpansionDist')
        normalized_min_expansion = (float(min_expansion) / scale_radius) if min_expansion is not None else None
        normalized_max_expansion = (float(max_expansion) / scale_radius) if max_expansion is not None else None

        spiral_pts = self.make_spiral(
            dphi,
            bounce_count,
            normalized_r0,
            1.0,
            min_expansion_dist=normalized_min_expansion,
            max_expansion_dist=normalized_max_expansion,
        )
        t_out = bounce_count * dphi
        t_hold = dphi
        t_total = 2 * t_out + t_hold

        is_single_slice = total_batteries == 1
        is_double_slice = total_batteries == 2
        if is_single_slice:
            shared_mid_fractions = [1 / 6, 2 / 6, 3 / 6, 4 / 6, 5 / 6]
        elif is_double_slice:
            shared_mid_fractions = [1 / 3, 2 / 3]
        else:
            shared_mid_fractions = [0.5]

        outbound_mid_fractions = list(reversed(shared_mid_fractions))
        inbound_mid_fractions = shared_mid_fractions
        hold_mid_fractions = shared_mid_fractions

        def label_from_fraction(value: float) -> int:
            return round((value + 1e-9) * 100)

        def find_boundary_point(target_t: float, is_midpoint: bool = False, phase: str = 'unknown') -> Dict:
            target_index = round(target_t * (len(spiral_pts) - 1) / t_total)
            clamped_index = max(0, min(len(spiral_pts) - 1, target_index))
            pt = spiral_pts[clamped_index]

            rho = min(1.0, max(0.0, math.sqrt((pt['x'] ** 2) + (pt['y'] ** 2))))
            phi = sector_start + math.atan2(pt['y'], pt['x'])
            ellipse_x = major_radius * rho * math.cos(phi)
            ellipse_y = minor_radius * rho * math.sin(phi)
            rot_x = ellipse_x * math.cos(offset) - ellipse_y * math.sin(offset)
            rot_y = ellipse_x * math.sin(offset) + ellipse_y * math.cos(offset)
            distance_from_center = math.sqrt(rot_x**2 + rot_y**2)

            if is_midpoint:
                base_curve = 50
                scale_factor = 1.2
                max_curve = 1500
                curve_radius = min(max_curve, base_curve + (distance_from_center * scale_factor))
            else:
                base_curve = 40
                scale_factor = 0.05
                max_curve = 160
                curve_radius = min(max_curve, base_curve + (distance_from_center * scale_factor))

            return {
                'x': rot_x,
                'y': rot_y,
                'curve': round(curve_radius * 10) / 10,
                'phase': phase,
                't': target_t,
                'id': f"boundary_{battery_index}_{phase}_{target_t:.3f}",
            }

        waypoints = [find_boundary_point(0, False, 'outbound_start')]

        for bounce in range(1, bounce_count + 1):
            for fraction in outbound_mid_fractions:
                t_mid = (bounce - fraction) * dphi
                progress_label = label_from_fraction(1 - fraction)
                phase = (
                    f'outbound_mid_{bounce}_q{progress_label}'
                    if (is_single_slice or is_double_slice)
                    else f'outbound_mid_{bounce}'
                )
                waypoints.append(find_boundary_point(t_mid, True, phase))

            t_bounce = bounce * dphi
            waypoints.append(find_boundary_point(t_bounce, False, f'outbound_bounce_{bounce}'))

        t_end_hold = t_out + t_hold
        for fraction in hold_mid_fractions:
            t_hold_point = t_out + fraction * t_hold
            phase = (
                f'hold_mid_q{label_from_fraction(fraction)}'
                if (is_single_slice or is_double_slice)
                else 'hold_mid'
            )
            waypoints.append(find_boundary_point(t_hold_point, True, phase))

        waypoints.append(find_boundary_point(t_end_hold, False, 'hold_end'))

        for fraction in inbound_mid_fractions:
            t_first_inbound_mid = t_end_hold + fraction * dphi
            phase = (
                f'inbound_mid_0_q{label_from_fraction(fraction)}'
                if (is_single_slice or is_double_slice)
                else 'inbound_mid_0'
            )
            waypoints.append(find_boundary_point(t_first_inbound_mid, True, phase))

        for bounce in range(1, bounce_count + 1):
            t_bounce = t_end_hold + bounce * dphi
            waypoints.append(find_boundary_point(t_bounce, False, f'inbound_bounce_{bounce}'))

            if bounce < bounce_count:
                for fraction in inbound_mid_fractions:
                    t_mid = t_end_hold + (bounce + fraction) * dphi
                    phase = (
                        f'inbound_mid_{bounce}_q{label_from_fraction(fraction)}'
                        if (is_single_slice or is_double_slice)
                        else f'inbound_mid_{bounce}'
                    )
                    waypoints.append(find_boundary_point(t_mid, True, phase))

        return waypoints

    def generate_boundary_preview_paths(self, params: Dict, boundary: Dict, boundary_plan: Dict) -> List[Dict]:
        """Convert a boundary plan into preview line coordinates for the client."""
        preview_paths = []
        for entry in boundary_plan.get('batteries', []):
            waypoints = self.build_boundary_slice(
                entry['batteryIndex'],
                params['slices'],
                boundary,
                entry['startAngleDeg'],
                entry['sweepAngleDeg'],
                entry['bounceCount'],
                params,
            )

            coordinates = []
            for waypoint in waypoints:
                lat_lon = self.xy_to_lat_lon(
                    waypoint['x'],
                    waypoint['y'],
                    boundary['centerLat'],
                    boundary['centerLng'],
                )
                coordinates.append([lat_lon['lon'], lat_lon['lat']])

            preview_paths.append({
                'batteryIndex': entry['batteryIndex'],
                'coordinates': coordinates,
            })

        return preview_paths

    def default_target_bounces(self, target_battery_minutes: float) -> int:
        """Return the base bounce count target for a battery duration."""
        if target_battery_minutes <= 12:
            return 7
        if target_battery_minutes <= 18:
            return 8
        if target_battery_minutes <= 25:
            return 9
        if target_battery_minutes <= 35:
            return 10
        if target_battery_minutes <= 45:
            return 12
        return 15

    def plan_boundary_mission(self, target_battery_minutes: float, num_batteries: int, boundary: Dict, params: Dict) -> Dict:
        """Allocate unequal ellipse sectors across batteries while respecting battery limits."""
        safe_time_limit = target_battery_minutes * 0.98
        baseline = self.optimize_spiral_for_battery(
            target_battery_minutes,
            num_batteries,
            boundary['centerLat'],
            boundary['centerLng'],
        )
        max_bounces = max(1, int(min(
            baseline.get('N', self.default_target_bounces(target_battery_minutes)),
            self.max_bounces_for_waypoint_budget(num_batteries),
        )))

        sector_params = {
            'slices': num_batteries,
            'r0': float(baseline.get('r0', 200.0)),
        }
        if params.get('minExpansionDist') is not None:
            sector_params['minExpansionDist'] = float(params['minExpansionDist'])
        if params.get('maxExpansionDist') is not None:
            sector_params['maxExpansionDist'] = float(params['maxExpansionDist'])

        current_angle = 0.0
        batteries = []

        for battery_idx in range(1, num_batteries + 1):
            remaining_angle = max(0.0, 360.0 - current_angle)
            remaining_batteries = num_batteries - battery_idx + 1
            reserved_angle = 0.25 * max(0, remaining_batteries - 1)
            max_candidate_angle = remaining_angle if battery_idx == num_batteries else max(0.25, remaining_angle - reserved_angle)

            best_entry = None
            low = 0.25
            high = max_candidate_angle

            def evaluate_sweep(sweep_angle_deg: float) -> Optional[Dict]:
                for bounce_count in range(max_bounces, 0, -1):
                    waypoints = self.build_boundary_slice(
                        battery_idx,
                        num_batteries,
                        boundary,
                        current_angle,
                        sweep_angle_deg,
                        bounce_count,
                        sector_params,
                    )
                    if not waypoints:
                        continue

                    estimated_time = self.estimate_generated_slice_time_minutes(waypoints)
                    if estimated_time <= safe_time_limit:
                        return {
                            'batteryIndex': battery_idx,
                            'startAngleDeg': round(current_angle, 3),
                            'sweepAngleDeg': round(sweep_angle_deg, 3),
                            'bounceCount': bounce_count,
                            'estimatedTimeMinutes': round(estimated_time, 2),
                            'waypointCount': len(waypoints),
                            'coverageShare': round(sweep_angle_deg / 360.0, 6),
                            'fitStatus': 'full',
                        }

                return None

            if high >= low:
                initial_candidate = evaluate_sweep(high)
                if initial_candidate:
                    best_entry = initial_candidate
                else:
                    for _ in range(18):
                        if high - low < 0.5:
                            break
                        mid = (low + high) / 2.0
                        candidate = evaluate_sweep(mid)
                        if candidate:
                            best_entry = candidate
                            low = mid
                        else:
                            high = mid

                    if not best_entry:
                        best_entry = evaluate_sweep(low)

            if not best_entry:
                break

            batteries.append(best_entry)
            current_angle += best_entry['sweepAngleDeg']

        coverage_ratio = min(1.0, current_angle / 360.0)
        fit_status = 'full' if coverage_ratio >= 0.999 else 'best_effort'
        limiting_battery_index = None
        if batteries:
            limiting_battery_index = max(
                batteries,
                key=lambda entry: entry.get('estimatedTimeMinutes', 0.0),
            )['batteryIndex']

        for entry in batteries:
            entry['fitStatus'] = fit_status

        if fit_status == 'best_effort':
            print(json.dumps({
                'event': 'boundary_best_effort',
                'coverageRatio': round(coverage_ratio, 4),
                'limitingBatteryIndex': limiting_battery_index,
                'batteries': batteries,
            }))
        else:
            print(json.dumps({
                'event': 'boundary_full_fit',
                'coverageRatio': round(coverage_ratio, 4),
                'limitingBatteryIndex': limiting_battery_index,
                'batteries': batteries,
            }))

        return {
            'version': 1,
            'fitStatus': fit_status,
            'coverageRatio': round(coverage_ratio, 4),
            'limitingBatteryIndex': limiting_battery_index,
            'batteries': batteries,
        }
    
    def parse_center(self, txt: Union[str, Dict]) -> Optional[Dict]:
        """
        Parse center coordinates from various human-readable formats or dict.
        
        SUPPORTED FORMATS:
        - {"lat": 41.73218, "lng": -111.83979} (dict)
        - "41.73218° N, 111.83979° W" (degree notation)
        - "41.73218, -111.83979" (decimal degrees)
        - "41.73218° N, 111.83979° W" (mixed formats)
        
        REGEX PATTERNS:
        - Degree format: (\\d+\\.?\\d*)\\s*°?\\s*([NS])\\s*,\\s*(\\d+\\.?\\d*)\\s*°?\\s*([EW])
        - Decimal format: ([-+]?\\d+\\.?\\d*)\\s*,\\s*([-+]?\\d+\\.?\\d*)
        
        Args:
            txt: Coordinate string in various formats or a dictionary with lat/lng
            
        Returns:
            Dict with 'lat' and 'lon' keys, or None if parsing fails
        """
        if isinstance(txt, dict):
            # Try to extract from common dict formats (lat/lng or lat/lon)
            if 'lat' in txt and ('lng' in txt or 'lon' in txt):
                lon_key = 'lng' if 'lng' in txt else 'lon'
                try:
                    return {'lat': float(txt['lat']), 'lon': float(txt[lon_key])}
                except (ValueError, TypeError):
                    return None
            return None

        import re
        
        if not isinstance(txt, str):
            txt = str(txt)
            
        txt = txt.strip()
        
        # Handle formats like "41.73218° N, 111.83979° W"
        degree_match = re.search(r'(\d+\.?\d*)\s*°?\s*([NS])\s*,\s*(\d+\.?\d*)\s*°?\s*([EW])', txt, re.IGNORECASE)
        if degree_match:
            lat = float(degree_match.group(1))
            lon = float(degree_match.group(3))
            
            # Apply hemisphere signs
            if degree_match.group(2).upper() == 'S':
                lat = -lat
            if degree_match.group(4).upper() == 'W':
                lon = -lon
            
            return {'lat': lat, 'lon': lon}
        
        # Handle simple decimal format like "41.73218, -111.83979"
        decimal_match = re.search(r'([-+]?\d+\.?\d*)\s*,\s*([-+]?\d+\.?\d*)', txt)
        if decimal_match:
            return {
                'lat': float(decimal_match.group(1)),
                'lon': float(decimal_match.group(2))
            }
        
        return None
    
    def xy_to_lat_lon(self, x_ft: float, y_ft: float, lat0: float, lon0: float) -> Dict:
        """
        Convert local XY coordinates (feet) to GPS coordinates using flat Earth approximation.
        
        FLAT EARTH APPROXIMATION:
        Valid for small areas (<100km). Assumes:
        - Earth is locally flat
        - 1 degree latitude ≈ 111,320 meters everywhere
        - 1 degree longitude ≈ 111,320 × cos(latitude) meters
        
        CONVERSION FORMULAS:
        Δlat = y_meters / EARTH_RADIUS_METERS
        Δlon = x_meters / (EARTH_RADIUS_METERS × cos(lat0))
        
        Args:
            x_ft, y_ft: Local coordinates in feet (relative to center)
            lat0, lon0: Center coordinates in decimal degrees
            
        Returns:
            Dict with 'lat' and 'lon' keys in decimal degrees
        """
        x_m = x_ft * self.FT2M
        y_m = y_ft * self.FT2M
        
        d_lat = y_m / self.EARTH_R
        d_lon = x_m / (self.EARTH_R * math.cos(lat0 * math.pi / 180))
        
        return {
            'lat': lat0 + d_lat * 180 / math.pi,
            'lon': lon0 + d_lon * 180 / math.pi
        }

    def lat_lon_to_xy(self, lat: float, lon: float, lat0: float, lon0: float) -> Dict:
        """
        Convert GPS coordinates to local XY coordinates (feet) using flat Earth approximation.
        
        INVERSE OF xy_to_lat_lon METHOD:
        This is the reverse conversion needed for placing safety waypoints correctly.
        
        Args:
            lat, lon: GPS coordinates in decimal degrees
            lat0, lon0: Center coordinates in decimal degrees
            
        Returns:
            Dict with 'x' and 'y' keys in feet relative to center
        """
        d_lat = (lat - lat0) * math.pi / 180
        d_lon = (lon - lon0) * math.pi / 180
        
        y_m = d_lat * self.EARTH_R
        x_m = d_lon * self.EARTH_R * math.cos(lat0 * math.pi / 180)
        
        return {
            'x': x_m / self.FT2M,
            'y': y_m / self.FT2M
        }
    
    def generate_spiral_data(self, params: Dict, debug_mode: bool = False, debug_angle: float = 0) -> Dict:
        """
        Generate spiral visualization data for frontend display (optional endpoint).
        
        This endpoint is used by the original interface for graph visualization.
        Your production frontend may not need this if you're not showing visualizations.
        
        Args:
            params: Spiral parameters
            debug_mode: Whether to show single slice
            debug_angle: Angle for debug slice (degrees)
            
        Returns:
            Dict with 'traces' key containing Plotly-compatible data
        """
        dphi = 2 * math.pi / params['slices']
        raw_spiral = self.make_spiral(dphi, params['N'], params['r0'], params['rHold'])
        
        traces = []
        hue0, hue1 = 220, 300
        offset = math.pi / 2
        
        if debug_mode:
            # Debug mode: single slice visualization
            debug_angle_rad = debug_angle * math.pi / 180
            angle = math.pi / 2 + debug_angle_rad
            c, s = math.cos(angle), math.sin(angle)
            
            # Spiral trace
            spiral_x = [pt['x'] * c - pt['y'] * s for pt in raw_spiral]
            spiral_y = [pt['x'] * s + pt['y'] * c for pt in raw_spiral]
            
            traces.append({
                'x': spiral_x,
                'y': spiral_y,
                'mode': 'lines',
                'line': {'color': '#0a84ff', 'width': 3},
                'name': 'Debug Slice'
            })
            
            # Radius line
            traces.append({
                'x': [0, params['rHold'] * math.cos(angle)],
                'y': [0, params['rHold'] * math.sin(angle)],
                'mode': 'lines',
                'line': {'color': '#ff9500', 'width': 2, 'dash': 'dot'},
                'name': 'Radius'
            })
        else:
            # Full pattern mode: all slices
            for k in range(params['slices']):
                angle = offset + k * dphi
                c, s = math.cos(angle), math.sin(angle)
                
                # Spiral trace
                spiral_x = [pt['x'] * c - pt['y'] * s for pt in raw_spiral]
                spiral_y = [pt['x'] * s + pt['y'] * c for pt in raw_spiral]
                
                hue = hue0 + (hue1 - hue0) * (k / (params['slices'] - 1) if params['slices'] > 1 else 0)
                
                traces.append({
                    'x': spiral_x,
                    'y': spiral_y,
                    'mode': 'lines',
                    'line': {'color': f'hsl({hue} 80% 55%)', 'width': 2}
                })
                
                # Radius line
                traces.append({
                    'x': [0, params['rHold'] * math.cos(angle)],
                    'y': [0, params['rHold'] * math.sin(angle)],
                    'mode': 'lines',
                    'line': {'color': '#ff9500', 'width': 2, 'dash': 'dot'}
                })
        
        return {'traces': traces}

    def generate_csv(
        self,
        params: Dict,
        center_str: str,
        min_height: float = 100.0,
        max_height: float = None,
        debug_mode: bool = False,
        debug_angle: float = 0,
        form_to_terrain: bool = True,
        spin_mode: bool = False,
    ) -> str:
        """
        Generate complete Litchi CSV mission file with elevation-aware altitudes and neural network optimizations.
        
        LITCHI CSV FORMAT (16 columns):
        ===============================
        1. latitude: GPS latitude in decimal degrees
        2. longitude: GPS longitude in decimal degrees  
        3. altitude(ft): Flight altitude in feet
        4. heading(deg): Forward direction in degrees (0-360)
        5. curvesize(ft): Turn radius in feet for smooth flight
        6. rotationdir: Rotation direction (0=none, 1=CW, -1=CCW)
        7. gimbalmode: Camera gimbal mode (2=focus POI)
        8. gimbalpitchangle: Camera tilt angle (-90 to +30 degrees)
        9. altitudemode: Altitude reference (0=AGL, 1=MSL)
        10. speed(m/s): Flight speed in meters per second
        11. poi_latitude: Point of Interest latitude (center of spiral)
        12. poi_longitude: Point of Interest longitude (center of spiral)
        13. poi_altitude(ft): POI altitude in feet
        14. poi_altitudemode: POI altitude mode (0=AGL, 1=MSL)
        15. photo_timeinterval: Time between photos (seconds, 0=disabled)
        16. photo_distinterval: Distance between photos (meters, 0=disabled)
        
        NEURAL NETWORK TRAINING ALTITUDE ALGORITHM:
        ==========================================
        
        DIFFERENTIATED ALTITUDE LOGIC:
        1. OUTBOUND waypoints: 0.20ft per foot climb rate (balanced coverage)
        2. INBOUND waypoints: 0.1ft per foot ascent rate (continued altitude gain)
        3. HOLD waypoints: Use outbound logic for consistency
        
        FIRST WAYPOINT SPECIAL CASE:
        - Always starts at min_height regardless of distance from center
        - Establishes baseline for all other calculations
        - Prevents artificially low starting altitudes
        
        ELEVATION INTEGRATION:
        - Terrain-following using Google Maps elevation data
        - 15-foot proximity sharing for cost optimization
        - AGL (Above Ground Level) altitude calculation
        
        Args:
            params: Spiral parameters dict {slices, N, r0, rHold}
            center_str: Center coordinates as string
            min_height: Minimum flight altitude AGL (feet)
            max_height: Maximum flight altitude AGL (feet, optional)
            debug_mode: Generate single slice only
            debug_angle: Specific angle for debug slice (degrees)
            spin_mode: Enable continuous spin-optimized waypoint densification
            
        Returns:
            Complete CSV file content as string
        """
        center = self.parse_center(center_str)
        if not center:
            raise ValueError("Invalid center coordinates")
        
        if form_to_terrain:
            # Get takeoff elevation for reference
            takeoff_elevation_feet = self.get_elevation_feet(center['lat'], center['lon'])
        else:
            print("🛫 Terrain following disabled - generating flat mission altitudes")
            takeoff_elevation_feet = 0.0
        
        # Generate waypoints using the same algorithm as the designer
        spiral_path = []
        
        if debug_mode:
            # Debug mode: single slice with exact angle control
            debug_angle_rad = debug_angle * math.pi / 180
            slice_index = round(debug_angle_rad / (2 * math.pi / params['slices'])) % params['slices']
            waypoints = self.compute_waypoints(params)
            
            if waypoints:
                spiral_path = waypoints[slice_index] if slice_index < len(waypoints) else waypoints[0]
                
                # Rotate to exact debug angle for precise testing
                actual_slice_angle = slice_index * (2 * math.pi / params['slices'])
                rotation_diff = debug_angle_rad - actual_slice_angle
                
                rotated_path = []
                for wp in spiral_path:
                    rotated_x = wp['x'] * math.cos(rotation_diff) - wp['y'] * math.sin(rotation_diff)
                    rotated_y = wp['x'] * math.sin(rotation_diff) + wp['y'] * math.cos(rotation_diff)
                    
                    rotated_wp = wp.copy()
                    rotated_wp['x'] = rotated_x
                    rotated_wp['y'] = rotated_y
                    rotated_path.append(rotated_wp)
                
                spiral_path = rotated_path
        else:
            # Full pattern mode: combine all slices for complete mission
            waypoints = self.compute_waypoints(params)
            spiral_path = []
            for slice_waypoints in waypoints:
                spiral_path.extend(slice_waypoints)
        
        # Ensure minimum curve radius for flight safety
        for wp in spiral_path:
            wp['curve'] = max(wp['curve'], 30)  # 30ft minimum for doubled curve settings
        
        # Convert waypoints to lat/lon and get optimized elevations
        locations = []
        waypoints_with_coords = []
        for wp in spiral_path:
            coords = self.xy_to_lat_lon(wp['x'], wp['y'], center['lat'], center['lon'])
            locations.append((coords['lat'], coords['lon']))
            waypoints_with_coords.append({
                'lat': coords['lat'],
                'lon': coords['lon'],
                'x': wp['x'],
                'y': wp['y'],
                'phase': wp.get('phase', 'unknown')
            })
        
        if form_to_terrain:
            # Get elevations with 15-foot proximity optimization
            ground_elevations = self.get_elevations_feet_optimized(locations)

            # Add elevations to waypoints_with_coords for adaptive sampling
            for i, elevation in enumerate(ground_elevations):
                waypoints_with_coords[i]['elevation'] = elevation

            # ADAPTIVE TERRAIN SAMPLING - Detect and add safety waypoints (All slices)
            print(f"🛡️  Starting adaptive terrain sampling for complete mission safety")
            safety_waypoints = self.adaptive_terrain_sampling(waypoints_with_coords)
        else:
            ground_elevations = [0.0] * len(locations)
            safety_waypoints = []
        
        if safety_waypoints:
            print(f"🔧 Integrating {len(safety_waypoints)} safety waypoints into complete mission flight path")
            # Convert safety waypoints to the format expected by CSV generation
            enhanced_waypoints_data = []
            
            for i, wp in enumerate(spiral_path):
                # Add original waypoint
                enhanced_waypoints_data.append({
                    'waypoint': wp,
                    'coords': waypoints_with_coords[i],
                    'ground_elevation': ground_elevations[i],
                    'is_safety': False
                })
                
                # Add any safety waypoints that belong after this original waypoint
                segment_safety_waypoints = [swp for swp in safety_waypoints if swp['segment_idx'] == i]
                for safety_wp in segment_safety_waypoints:
                    # Convert safety waypoint GPS coordinates back to local X,Y coordinates  
                    safety_local_coords = self.lat_lon_to_xy(
                        safety_wp['lat'], safety_wp['lon'], center['lat'], center['lon']
                    )
                    
                    # Create properly positioned safety waypoint
                    safety_pseudo_wp = {
                        'x': safety_local_coords['x'], 
                        'y': safety_local_coords['y'], 
                        'curve': 40, 
                        'phase': f"safety_{safety_wp['type']}"
                    }
                    enhanced_waypoints_data.append({
                        'waypoint': safety_pseudo_wp,
                        'coords': {'lat': safety_wp['lat'], 'lon': safety_wp['lon']},
                        'ground_elevation': safety_wp['elevation'],
                        'safety_altitude': safety_wp['altitude'],
                        'safety_reason': safety_wp['reason'],
                        'is_safety': True
                    })
            
            # Update the processing arrays to include safety waypoints
            spiral_path = [item['waypoint'] for item in enhanced_waypoints_data]
            locations = [(item['coords']['lat'], item['coords']['lon']) for item in enhanced_waypoints_data]
            ground_elevations = [item['ground_elevation'] for item in enhanced_waypoints_data]
            
            # Store enhanced waypoints data for later use
            self._enhanced_waypoints_data = enhanced_waypoints_data
            
            print(f"✅ Enhanced complete mission: {len(spiral_path)} total waypoints ({len(safety_waypoints)} safety additions)")
        else:
            print(f"✅ No terrain anomalies detected for complete mission - original flight path is safe")
            self._enhanced_waypoints_data = None
        
        # Generate CSV content with Litchi header
        header = "latitude,longitude,altitude(ft),heading(deg),curvesize(ft),rotationdir,gimbalmode,gimbalpitchangle,altitudemode,speed(m/s),poi_latitude,poi_longitude,poi_altitude(ft),poi_altitudemode,photo_timeinterval,photo_distinterval"
        rows = [header]
        
        enhanced_waypoints_data = getattr(self, '_enhanced_waypoints_data', None)
        waypoint_records = self._build_waypoint_records(
            spiral_path=spiral_path,
            center=center,
            ground_elevations=ground_elevations,
            takeoff_elevation_feet=takeoff_elevation_feet,
            min_height=min_height,
            max_height=max_height,
            enhanced_waypoints_data=enhanced_waypoints_data,
        )
        waypoint_records = self._enforce_waypoint_record_limit(waypoint_records)

        if spin_mode:
            waypoint_records = self._insert_spin_waypoints(waypoint_records)

        headings = (
            self._compute_spin_headings(waypoint_records)
            if spin_mode
            else self._compute_path_headings(waypoint_records)
        )
        gimbal_pitches = self._build_gimbal_pitch_series(len(waypoint_records))
        active_photo_interval = (
            self.SPIN_PHOTO_INTERVAL_SECONDS
            if spin_mode
            else self.DEFAULT_PHOTO_INTERVAL_SECONDS
        )

        for i, record in enumerate(waypoint_records):
            photo_interval = 0 if i == len(waypoint_records) - 1 else active_photo_interval
            # Spin mode: no POI (0) so Litchi uses per-waypoint headings; non-spin: POI at center
            poi_lat = 0 if spin_mode else center['lat']
            poi_lon = 0 if spin_mode else center['lon']
            row = [
                record['latitude'],
                record['longitude'],
                record['altitude'],
                headings[i],
                record['curve_size_meters'],
                0,                     # Rotation direction (clockwise in Litchi convention)
                2,
                gimbal_pitches[i],
                0,
                self.FLIGHT_SPEED_MPS,
                poi_lat,
                poi_lon,
                -35,
                0,
                photo_interval,
                0,
            ]
            rows.append(','.join(map(str, row)))
        
        return '\n'.join(rows)

    def generate_battery_csv(
        self,
        params: Dict,
        center_str: str,
        battery_index: int,
        min_height: float = 100.0,
        max_height: float = None,
        boundary: Optional[Dict] = None,
        boundary_plan: Optional[Dict] = None,
        form_to_terrain: bool = True,
        spin_mode: bool = False,
    ) -> str:
        """
        Generate Litchi CSV for a specific battery/slice with neural network altitude optimization.
        
        SINGLE-BATTERY MISSION STRATEGY:
        ===============================
        Each battery flies one complete slice (360°/num_batteries angular section).
        This enables:
        1. Parallel missions with multiple drones
        2. Sequential flights with battery swaps
        3. Risk distribution across separate flights
        4. Independent mission planning per battery
        
        IDENTICAL ALGORITHM:
        Uses the exact same altitude calculation as generate_csv() but for single slice.
        Ensures consistency between individual and combined missions.
        
        Args:
            params: Spiral parameters dict {slices, N, r0, rHold}
            center_str: Center coordinates as string
            battery_index: Battery number (0-based index)
            min_height: Minimum flight altitude AGL (feet)
            max_height: Maximum flight altitude AGL (feet, optional)
            
        Returns:
            CSV file content for specified battery as string
            
        Raises:
            ValueError: If battery_index is out of range
        """
        center = self.parse_center(center_str)
        if not center:
            raise ValueError("Invalid center coordinates")
            
        if boundary and boundary_plan:
            plan_entry = self.boundary_plan_entry(boundary_plan, battery_index + 1)
            if not plan_entry:
                raise ValueError(f"Battery index must be between 0 and {len(boundary_plan.get('batteries', [])) - 1}")
        else:
            # Validate battery index range
            if battery_index < 0 or battery_index >= params['slices']:
                raise ValueError(f"Battery index must be between 0 and {params['slices'] - 1}")
        
        # Clear caches to prevent memory accumulation across battery downloads
        self.elevation_cache = {}
        self.waypoint_cache = []
        
        if form_to_terrain:
            # Get takeoff elevation for reference
            takeoff_elevation_feet = self.get_elevation_feet(center['lat'], center['lon'])
        else:
            print("🛫 Terrain following disabled - generating flat battery mission altitudes")
            takeoff_elevation_feet = 0.0
        
        if boundary and boundary_plan:
            spiral_path = self.build_boundary_slice(
                battery_index + 1,
                params['slices'],
                boundary,
                plan_entry['startAngleDeg'],
                plan_entry['sweepAngleDeg'],
                plan_entry['bounceCount'],
                params,
            )
            if not spiral_path:
                raise ValueError(f"Battery {battery_index + 1} does not cover any boundary area")
        else:
            # Generate waypoints for all slices, then extract the specific battery slice
            all_waypoints = self.compute_waypoints(params)
            spiral_path = all_waypoints[battery_index]
        
        # Ensure minimum curve radius for flight safety
        for wp in spiral_path:
            wp['curve'] = max(wp['curve'], 30)  # 30ft minimum for doubled curve settings
        
        # Convert waypoints to lat/lon and get optimized elevations
        locations = []
        waypoints_with_coords = []
        for wp in spiral_path:
            coords = self.xy_to_lat_lon(wp['x'], wp['y'], center['lat'], center['lon'])
            locations.append((coords['lat'], coords['lon']))
            waypoints_with_coords.append({
                'lat': coords['lat'],
                'lon': coords['lon'],
                'x': wp['x'],
                'y': wp['y'],
                'phase': wp.get('phase', 'unknown')
            })
        
        if form_to_terrain:
            # Get elevations with 15-foot proximity optimization
            ground_elevations = self.get_elevations_feet_optimized(locations)

            # Add elevations to waypoints_with_coords for adaptive sampling
            for i, elevation in enumerate(ground_elevations):
                waypoints_with_coords[i]['elevation'] = elevation

            # ADAPTIVE TERRAIN SAMPLING - Detect and add safety waypoints
            print(f"🛡️  Starting adaptive terrain sampling for mission safety")
            safety_waypoints = self.adaptive_terrain_sampling(waypoints_with_coords)
        else:
            ground_elevations = [0.0] * len(locations)
            safety_waypoints = []
        
        if safety_waypoints:
            print(f"🔧 Integrating {len(safety_waypoints)} safety waypoints into flight path")
            # Convert safety waypoints to the format expected by CSV generation
            enhanced_waypoints_data = []
            
            for i, wp in enumerate(spiral_path):
                # Add original waypoint
                enhanced_waypoints_data.append({
                    'waypoint': wp,
                    'coords': waypoints_with_coords[i],
                    'ground_elevation': ground_elevations[i],
                    'is_safety': False
                })
                
                # Add any safety waypoints that belong after this original waypoint
                segment_safety_waypoints = [swp for swp in safety_waypoints if swp['segment_idx'] == i]
                for safety_wp in segment_safety_waypoints:
                    # Convert safety waypoint GPS coordinates back to local X,Y coordinates  
                    safety_local_coords = self.lat_lon_to_xy(
                        safety_wp['lat'], safety_wp['lon'], center['lat'], center['lon']
                    )
                    
                    # Create properly positioned safety waypoint
                    safety_pseudo_wp = {
                        'x': safety_local_coords['x'], 
                        'y': safety_local_coords['y'], 
                        'curve': 40, 
                        'phase': f"safety_{safety_wp['type']}"
                    }
                    enhanced_waypoints_data.append({
                        'waypoint': safety_pseudo_wp,
                        'coords': {'lat': safety_wp['lat'], 'lon': safety_wp['lon']},
                        'ground_elevation': safety_wp['elevation'],
                        'safety_altitude': safety_wp['altitude'],
                        'safety_reason': safety_wp['reason'],
                        'is_safety': True
                    })
            
            # Update the processing arrays to include safety waypoints
            spiral_path = [item['waypoint'] for item in enhanced_waypoints_data]
            locations = [(item['coords']['lat'], item['coords']['lon']) for item in enhanced_waypoints_data]
            ground_elevations = [item['ground_elevation'] for item in enhanced_waypoints_data]
            
            # Store enhanced waypoints data for later use
            self._enhanced_waypoints_data = enhanced_waypoints_data
            
            print(f"✅ Enhanced mission: {len(spiral_path)} total waypoints ({len(safety_waypoints)} safety additions)")
        else:
            print(f"✅ No terrain anomalies detected - original flight path is safe")
            self._enhanced_waypoints_data = None
        
        # Generate CSV content with Litchi header
        header = "latitude,longitude,altitude(ft),heading(deg),curvesize(ft),rotationdir,gimbalmode,gimbalpitchangle,altitudemode,speed(m/s),poi_latitude,poi_longitude,poi_altitude(ft),poi_altitudemode,photo_timeinterval,photo_distinterval"
        rows = [header]
        
        enhanced_waypoints_data = getattr(self, '_enhanced_waypoints_data', None)
        waypoint_records = self._build_waypoint_records(
            spiral_path=spiral_path,
            center=center,
            ground_elevations=ground_elevations,
            takeoff_elevation_feet=takeoff_elevation_feet,
            min_height=min_height,
            max_height=max_height,
            enhanced_waypoints_data=enhanced_waypoints_data,
        )
        waypoint_records = self._enforce_waypoint_record_limit(waypoint_records)

        if spin_mode:
            waypoint_records = self._insert_spin_waypoints(waypoint_records)

        headings = (
            self._compute_spin_headings(waypoint_records)
            if spin_mode
            else self._compute_path_headings(waypoint_records)
        )
        gimbal_pitches = self._build_gimbal_pitch_series(len(waypoint_records))
        active_photo_interval = (
            self.SPIN_PHOTO_INTERVAL_SECONDS
            if spin_mode
            else self.DEFAULT_PHOTO_INTERVAL_SECONDS
        )

        for i, record in enumerate(waypoint_records):
            photo_interval = 0 if i == len(waypoint_records) - 1 else active_photo_interval
            # Spin mode: no POI (0) so Litchi uses per-waypoint headings; non-spin: POI at center
            poi_lat = 0 if spin_mode else center['lat']
            poi_lon = 0 if spin_mode else center['lon']
            row = [
                record['latitude'],
                record['longitude'],
                record['altitude'],
                headings[i],
                record['curve_size_meters'],
                0,
                2,
                gimbal_pitches[i],
                0,
                self.FLIGHT_SPEED_MPS,
                poi_lat,
                poi_lon,
                -35,
                0,
                photo_interval,
                0,
            ]
            rows.append(','.join(map(str, row)))
        
        return '\n'.join(rows)

    # Calibrated physics constants for DJI / Litchi waypoint missions.
    # Values validated against Litchi Mission Hub's displayed flight time
    # for Curved Turns mode.  DJI flight controllers in waypoint mode
    # use very conservative acceleration (≈0.4 m/s²) for smooth, safe
    # flight — roughly 5-10× lower than the drone's theoretical max.
    # Calibrated against Litchi's reported 23 min for a known 20-min
    # battery, 3-slice, N=9, rHold=1523 flight.
    A_CENTRIPETAL = 2.5   # m/s² – lateral (cornering) acceleration limit
    A_LINEAR = 0.4        # m/s² – linear accel / decel in waypoint mode
    V_MIN_TURN = 0.5      # m/s – minimum speed through tightest turns
    WP_DWELL_S = 1.0      # seconds per interior waypoint for GPS lock,
                           # Bezier curve setup, and position confirmation

    def _waypoint_turn_speed(self, wps: List[Dict], idx: int) -> float:
        """Speed the drone can sustain at waypoint *idx* given
        the deflection angle and curve radius."""
        if idx <= 0 or idx >= len(wps) - 1:
            return self.FLIGHT_SPEED_MPS
        v1x = wps[idx]['x'] - wps[idx - 1]['x']
        v1y = wps[idx]['y'] - wps[idx - 1]['y']
        v2x = wps[idx + 1]['x'] - wps[idx]['x']
        v2y = wps[idx + 1]['y'] - wps[idx]['y']
        mag1 = math.sqrt(v1x * v1x + v1y * v1y)
        mag2 = math.sqrt(v2x * v2x + v2y * v2y)
        if mag1 < 1e-9 or mag2 < 1e-9:
            return self.FLIGHT_SPEED_MPS
        cos_a = max(-1.0, min(1.0, (v1x * v2x + v1y * v2y) / (mag1 * mag2)))
        theta = math.acos(cos_a)
        if theta < math.radians(5):
            return self.FLIGHT_SPEED_MPS
        curve_m = wps[idx].get('curve', 40) * self.FT2M
        v_cent = math.sqrt(self.A_CENTRIPETAL * curve_m) if curve_m > 0 else 0.0
        v_dir = self.FLIGHT_SPEED_MPS * math.cos(theta / 2)
        return max(self.V_MIN_TURN, min(v_cent, v_dir))

    @staticmethod
    def _segment_time(d_m: float, v0: float, v1: float,
                      v_max: float, a: float) -> float:
        """Time to traverse *d_m* metres with entry speed *v0*, exit speed
        *v1*, cruise cap *v_max*, and acceleration limit *a*.
        Uses a trapezoidal (or triangular) speed profile."""
        if d_m < 0.01:
            return 0.0
        d_up = max(0.0, (v_max * v_max - v0 * v0) / (2.0 * a))
        d_down = max(0.0, (v_max * v_max - v1 * v1) / (2.0 * a))
        if d_up + d_down <= d_m:
            t_up = (v_max - v0) / a if v_max > v0 else 0.0
            t_cruise = (d_m - d_up - d_down) / v_max
            t_down = (v_max - v1) / a if v_max > v1 else 0.0
            return t_up + t_cruise + t_down
        # Triangular — drone never reaches cruise on this segment
        v_peak_sq = (2.0 * a * d_m + v0 * v0 + v1 * v1) / 2.0
        v_peak = min(v_max, math.sqrt(max(0.01, v_peak_sq)))
        return max(0.0, (v_peak - v0) / a) + max(0.0, (v_peak - v1) / a)

    def estimate_generated_slice_time_minutes(self, waypoints: List[Dict]) -> float:
        """
        Estimate mission time directly from generated waypoints.
        """
        n = len(waypoints)
        if n < 2:
            return self.TAKEOFF_LANDING_OVERHEAD_MINUTES

        V = self.FLIGHT_SPEED_MPS
        a = self.A_LINEAR
        wp_speeds = [self._waypoint_turn_speed(waypoints, i) for i in range(n)]

        flight_s = 0.0
        for i in range(n - 1):
            dx = waypoints[i + 1]['x'] - waypoints[i]['x']
            dy = waypoints[i + 1]['y'] - waypoints[i]['y']
            d_m = math.sqrt(dx * dx + dy * dy) * self.FT2M
            flight_s += self._segment_time(d_m, wp_speeds[i], wp_speeds[i + 1], V, a)

        n_interior = max(0, n - 2)
        dwell_s = n_interior * self.WP_DWELL_S
        return (flight_s + dwell_s) / 60.0 + self.TAKEOFF_LANDING_OVERHEAD_MINUTES

    def estimate_flight_time_minutes(self, params: Dict, center_lat: float, center_lon: float) -> float:
        """
        Segment-by-segment speed-profile flight time estimation.

        For each pair of consecutive waypoints the method integrates a
        trapezoidal (or triangular) speed profile that respects:

          • The constrained turn-speed at each endpoint (deflection angle
            + curve radius → centripetal & directional limits).
          • A realistic linear acceleration limit (A_LINEAR = 1.0 m/s²)
            matching DJI waypoint-mode behaviour.
          • A small per-waypoint dwell for GPS position confirmation and
            Bezier curve setup.

        On short inner segments the drone physically cannot reach cruise
        speed before it must slow for the next turn.  This "speed ceiling"
        effect adds significant time that simpler penalty models miss.

        Args:
            params: Spiral parameters dict {slices, N, r0, rHold, ...}
            center_lat: (unused – kept for API compatibility)
            center_lon: (unused – kept for API compatibility)

        Returns:
            Estimated flight time in minutes for one battery / slice.
        """
        waypoints = self.build_slice(0, params)
        return self.estimate_generated_slice_time_minutes(waypoints)

    def midpoint_density_for_slices(self, slices: int) -> int:
        """Return extra midpoint count per segment for the given slice count."""
        if slices == 1:
            return 5
        if slices == 2:
            return 2
        return 1

    def estimate_slice_waypoint_count(self, slices: int, bounces: int) -> int:
        """
        Estimate waypoint count for one battery slice from build_slice() structure.

        Formula:
          total = 2 + 2*m*N + 2*N + m
        where:
          m = midpoints per segment
          N = bounce count
        """
        m = self.midpoint_density_for_slices(slices)
        return 2 + (2 * m * bounces) + (2 * bounces) + m

    def max_bounces_for_waypoint_budget(self, slices: int) -> int:
        """
        Compute the largest bounce count that keeps base waypoints under budget,
        leaving room for safety waypoints.
        """
        m = self.midpoint_density_for_slices(slices)
        max_base_waypoints = max(1, self.MAX_TOTAL_WAYPOINTS - self.RESERVED_SAFETY_WAYPOINTS)
        denominator = (2 * m) + 2
        # total = 2 + 2*m*N + 2*N + m <= max_base_waypoints
        return max(3, int((max_base_waypoints - (2 + m)) // denominator))

    def seed_bounces_for_battery(
        self,
        target_battery_minutes: float,
        min_bounces: int = 3,
        max_bounces: int = 15,
    ) -> int:
        """Return the heuristic bounce seed before the solver searches alternatives."""
        if target_battery_minutes <= 12:
            target_bounces = 7
        elif target_battery_minutes <= 18:
            target_bounces = 8
        elif target_battery_minutes <= 25:
            target_bounces = 9
        elif target_battery_minutes <= 35:
            target_bounces = 10
        elif target_battery_minutes <= 45:
            target_bounces = 12
        else:
            target_bounces = 15
        return max(min_bounces, min(max_bounces, target_bounces))

    def optimize_spiral_for_battery(
        self,
        target_battery_minutes: float,
        num_batteries: int,
        center_lat: float,
        center_lon: float,
        min_expansion_dist: Optional[float] = None,
        max_expansion_dist: Optional[float] = None,
    ) -> Dict:
        """
        Battery-first spiral optimization with late bounce selection.
        
        The time estimator always evaluates the exact final geometry that will be
        used for CSV generation.  Custom expansion constraints are solved inside
        the optimization pass instead of being applied as a later override.
        
        Args:
            target_battery_minutes: Target flight duration in minutes
            num_batteries: Number of battery slices to generate
            center_lat: Center latitude for flight time calculations
            center_lon: Center longitude for flight time calculations
            min_expansion_dist: Optional requested minimum bounce spacing in feet
            max_expansion_dist: Optional requested maximum bounce spacing in feet
            
        Returns:
            Dict with optimized parameters and performance metrics:
            {
                'slices': int,
                'N': int,
                'r0': float,
                'rHold': float,
                'estimated_time_minutes': float,
                'battery_utilization': float
            }
        """
        min_rHold, max_rHold = 200.0, 50000.0
        min_N, max_N = 3, 15
        preferred_r0 = 200.0
        fallback_r0 = 100.0
        start_radius_candidates = [preferred_r0, fallback_r0]
        rhold_tolerance_ft = 25.0
        scale_tolerance = 0.001
        max_iterations = 30
        target_limit = target_battery_minutes * 0.98

        expansion_request = self.normalize_expansion_request(min_expansion_dist, max_expansion_dist)
        requested_bounce_seed = self.seed_bounces_for_battery(target_battery_minutes, min_N, max_N)
        waypoint_budget_bounce_cap = min(max_N, self.max_bounces_for_waypoint_budget(num_batteries))
        candidate_bounces = list(range(min_N, waypoint_budget_bounce_cap + 1))
        if not candidate_bounces:
            raise ValueError("No valid bounce counts available for this slice configuration")

        print(
            f"Optimizing for {target_battery_minutes}min battery: seed={requested_bounce_seed}, "
            f"search={candidate_bounces[0]}-{candidate_bounces[-1]} bounces, "
            f"expansion_mode={expansion_request['mode']}"
        )

        def build_custom_params(start_radius: float, bounces: int, intervals: List[float]) -> Dict:
            actual_min = intervals[0] if intervals else None
            actual_max = intervals[-1] if intervals else None
            return {
                'slices': num_batteries,
                'N': bounces,
                'r0': start_radius,
                'rHold': self.custom_outer_radius(start_radius, intervals),
                'customExpansionProfile': list(intervals),
                'minExpansionDist': actual_min,
                'maxExpansionDist': actual_max,
            }

        def evaluate_default_candidate(start_radius: float, bounces: int) -> Optional[Dict]:
            base_params = {
                'slices': num_batteries,
                'N': bounces,
                'r0': start_radius,
            }
            effective_min_rHold = max(min_rHold, start_radius + 10.0)
            test_params = base_params.copy()
            test_params['rHold'] = effective_min_rHold

            try:
                min_time = self.estimate_flight_time_minutes(test_params, center_lat, center_lon)
            except Exception as exc:
                print(f"Error estimating minimum default candidate for N={bounces}: {exc}")
                return None

            if min_time > target_limit:
                return None

            best_params = test_params.copy()
            best_time = min_time
            low, high = effective_min_rHold, max_rHold
            iterations = 0

            while high - low > rhold_tolerance_ft and iterations < max_iterations:
                iterations += 1
                mid_rHold = (low + high) / 2.0
                probe_params = base_params.copy()
                probe_params['rHold'] = mid_rHold
                try:
                    estimated_time = self.estimate_flight_time_minutes(probe_params, center_lat, center_lon)
                except Exception as exc:
                    print(f"Error estimating default candidate for N={bounces}, rHold={mid_rHold}: {exc}")
                    high = mid_rHold
                    continue

                if estimated_time <= target_limit:
                    best_params = probe_params.copy()
                    best_time = estimated_time
                    low = mid_rHold
                else:
                    high = mid_rHold

            return {
                'params': best_params,
                'estimated_time': best_time,
                'slack': target_limit - best_time,
                'scale': 1.0,
                'expansion_mode': 'default',
                'actual_min': None,
                'actual_max': None,
                'actual_outer_radius': self.calculate_actual_outer_radius(best_params),
            }

        def evaluate_custom_candidate(start_radius: float, bounces: int, intervals: List[float], scale: float) -> Optional[Dict]:
            params = build_custom_params(start_radius, bounces, intervals)
            try:
                estimated_time = self.estimate_flight_time_minutes(params, center_lat, center_lon)
            except Exception as exc:
                print(f"Error estimating custom candidate for N={bounces}, scale={scale:.4f}: {exc}")
                return None

            return {
                'params': params,
                'estimated_time': estimated_time,
                'slack': target_limit - estimated_time,
                'scale': scale,
                'expansion_mode': 'custom',
                'actual_min': intervals[0] if intervals else None,
                'actual_max': intervals[-1] if intervals else None,
                'actual_outer_radius': params['rHold'],
            }

        best_candidate = None

        if not expansion_request['has_custom_spacing']:
            for start_radius in start_radius_candidates:
                candidates = []
                for bounces in candidate_bounces:
                    candidate = evaluate_default_candidate(start_radius, bounces)
                    if candidate is not None:
                        candidates.append(candidate)

                if candidates:
                    best_candidate = min(
                        candidates,
                        key=lambda candidate: (candidate['slack'], -candidate['params']['N']),
                    )
                    break

            if best_candidate is None:
                raise ValueError("Battery minutes are too low for a safe default mission")
        else:
            for start_radius in start_radius_candidates:
                requested_profiles = {
                    bounces: self.build_requested_custom_intervals(
                        bounces,
                        expansion_request['requested_min'],
                        expansion_request['requested_max'],
                    )
                    for bounces in candidate_bounces
                }

                full_spacing_candidates = []
                for bounces, requested_profile in requested_profiles.items():
                    candidate = evaluate_custom_candidate(start_radius, bounces, requested_profile, 1.0)
                    if candidate is not None and candidate['estimated_time'] <= target_limit:
                        full_spacing_candidates.append(candidate)

                if full_spacing_candidates:
                    best_candidate = min(
                        full_spacing_candidates,
                        key=lambda candidate: (candidate['slack'], -candidate['params']['N']),
                    )
                    break

                scaled_candidates = []
                for bounces, requested_profile in requested_profiles.items():
                    zero_candidate = evaluate_custom_candidate(
                        start_radius,
                        bounces,
                        self.scale_custom_intervals(requested_profile, 0.0),
                        0.0,
                    )
                    if zero_candidate is None or zero_candidate['estimated_time'] > target_limit:
                        continue

                    best_for_bounces = zero_candidate
                    low, high = 0.0, 1.0
                    iterations = 0
                    while high - low > scale_tolerance and iterations < max_iterations:
                        iterations += 1
                        mid_scale = (low + high) / 2.0
                        scaled_profile = self.scale_custom_intervals(requested_profile, mid_scale)
                        candidate = evaluate_custom_candidate(start_radius, bounces, scaled_profile, mid_scale)
                        if candidate is not None and candidate['estimated_time'] <= target_limit:
                            best_for_bounces = candidate
                            low = mid_scale
                        else:
                            high = mid_scale

                    scaled_candidates.append(best_for_bounces)

                if scaled_candidates:
                    best_candidate = min(
                        scaled_candidates,
                        key=lambda candidate: (-candidate['scale'], candidate['slack'], -candidate['params']['N']),
                    )
                    break

            if best_candidate is None:
                raise ValueError("Battery minutes are too low for a safe mission with the requested spacing")

        best_params = best_candidate['params'].copy()
        estimated_time = best_candidate['estimated_time']
        final_n = int(best_params['N'])
        actual_min = best_candidate['actual_min']
        actual_max = best_candidate['actual_max']
        actual_outer_radius = best_candidate['actual_outer_radius']

        adjusted_bounce_count = final_n != requested_bounce_seed
        adjusted_expansion = False
        if expansion_request['has_custom_spacing']:
            adjusted_expansion = (
                actual_min is not None
                and actual_max is not None
                and (
                    abs(actual_min - expansion_request['requested_min']) > 1e-6
                    or abs(actual_max - expansion_request['requested_max']) > 1e-6
                )
            )

        best_params.pop('customExpansionProfile', None)
        best_params['estimated_time_minutes'] = round(estimated_time, 2)
        best_params['battery_utilization'] = round((estimated_time / target_battery_minutes) * 100, 1)
        best_params['expansionMode'] = best_candidate['expansion_mode']
        best_params['actualMinExpansionDist'] = round(actual_min, 2) if actual_min is not None else None
        best_params['actualMaxExpansionDist'] = round(actual_max, 2) if actual_max is not None else None
        best_params['actualOuterRadius'] = round(actual_outer_radius, 2)
        best_params['requestedBounceSeed'] = requested_bounce_seed
        best_params['adjustedBounceCount'] = adjusted_bounce_count
        best_params['adjustedExpansion'] = adjusted_expansion
        best_params['minExpansionDist'] = best_params['actualMinExpansionDist']
        best_params['maxExpansionDist'] = best_params['actualMaxExpansionDist']

        print(
            f"Final optimization: {best_params['N']} bounces, {best_params['rHold']:.0f}ft radius, "
            f"{estimated_time:.1f}min ({best_params['battery_utilization']}%), "
            f"mode={best_params['expansionMode']}"
        )

        return best_params

    # ADAPTIVE TERRAIN SAMPLING SYSTEM
    # ================================
    # Prevents drone crashes by detecting terrain anomalies between waypoints
    # Optimized for large properties (100+ acres) with cost-effective sampling
    
    # Configuration parameters optimized for smart API usage
    SAFE_DISTANCE_FT = 300          # 300ft max distance without sampling (user specified)
    INITIAL_SAMPLE_INTERVAL = 250   # Sample every 250ft for finer baseline sampling
    ANOMALY_THRESHOLD = 25          # 25ft deviation triggers investigation (balanced detection)
    CRITICAL_THRESHOLD = 70         # 70ft deviation = immediate waypoint (major hazards)
    MODERATE_THRESHOLD = 40         # 40ft deviation = verification (moderate hazards)
    DENSE_SAMPLE_INTERVAL = 35      # Dense sampling every 35ft around anomalies (high precision)
    RIDGE_DETECTION_RADIUS = 150    # Sample within 150ft radius around detected anomalies
    MAX_SAFETY_WAYPOINTS_PER_SEGMENT = 1  # One safety waypoint per segment eliminates ordering issues
    SAFETY_BUFFER_FT = 100          # 100ft safety clearance above detected terrain
    MAX_API_CALLS_PER_REQUEST = 25  # Conservative limit for 30s timeout
    
    def generate_intermediate_points(self, start_lat: float, start_lon: float, end_lat: float, end_lon: float, interval_ft: float) -> List[Dict]:
        """
        Generate intermediate GPS points along a great circle path at specified intervals.
        
        ALGORITHM:
        1. Calculate total distance between start and end points
        2. Determine number of sample points based on interval
        3. Use spherical interpolation for accurate GPS positions
        4. Return list of intermediate points with lat/lon
        
        Args:
            start_lat, start_lon: Starting GPS coordinates
            end_lat, end_lon: Ending GPS coordinates  
            interval_ft: Distance between sample points in feet
            
        Returns:
            List of intermediate points with 'lat', 'lon', 'distance_from_start'
        """
        total_distance_m = self.haversine_distance(start_lat, start_lon, end_lat, end_lon)
        total_distance_ft = total_distance_m * 3.28084
        
        if total_distance_ft <= interval_ft:
            return []  # No intermediate points needed
        
        num_points = int(total_distance_ft / interval_ft)
        intermediate_points = []
        
        for i in range(1, num_points):  # Skip start (i=0) and end (i=num_points)
            fraction = i / num_points
            
            # Spherical linear interpolation for accurate GPS positions
            lat = start_lat + fraction * (end_lat - start_lat)
            lon = start_lon + fraction * (end_lon - start_lon)
            distance_from_start = fraction * total_distance_ft
            
            intermediate_points.append({
                'lat': lat,
                'lon': lon,
                'distance_from_start': distance_from_start
            })
        
        return intermediate_points
    
    def linear_interpolate_elevation(self, start_lat: float, start_lon: float, start_elev: float,
                                   end_lat: float, end_lon: float, end_elev: float,
                                   point_lat: float, point_lon: float) -> float:
        """
        Calculate expected elevation at a point using linear interpolation between two known points.
        
        INTERPOLATION ALGORITHM:
        1. Calculate distance from start to point
        2. Calculate total distance from start to end
        3. Find fraction of total distance
        4. Linearly interpolate elevation based on fraction
        
        Args:
            start_lat, start_lon, start_elev: Starting point and elevation
            end_lat, end_lon, end_elev: Ending point and elevation
            point_lat, point_lon: Point to interpolate elevation for
            
        Returns:
            Expected elevation in feet at the interpolated point
        """
        total_distance = self.haversine_distance(start_lat, start_lon, end_lat, end_lon)
        point_distance = self.haversine_distance(start_lat, start_lon, point_lat, point_lon)
        
        if total_distance == 0:
            return start_elev
        
        fraction = point_distance / total_distance
        expected_elevation = start_elev + fraction * (end_elev - start_elev)
        
        return expected_elevation
    
    def adaptive_terrain_sampling(self, waypoints_with_coords: List[Dict]) -> List[Dict]:
        """
        Adaptive terrain anomaly detection system for drone safety.
        
        SAFETY ALGORITHM:
        1. Analyze segments between consecutive waypoints
        2. Skip short segments (< SAFE_DISTANCE_FT)
        3. Sample terrain at regular intervals on long segments
        4. Compare actual vs expected elevation (linear interpolation)
        5. Detect anomalies above threshold
        6. Add safety waypoints for significant terrain features
        7. Respect waypoint budget (99 total limit)
        
        COST OPTIMIZATION:
        - Strategic sampling intervals based on segment length
        - Proximity caching for nearby elevation requests
        - Batch processing of elevation queries
        - Early termination if waypoint budget exhausted
        
        Args:
            waypoints_with_coords: List of waypoints with lat/lon/elevation data
            
        Returns:
            List of safety waypoints to insert into flight path
        """
        safety_waypoints = []
        total_api_calls = 0
        max_api_calls = self.MAX_API_CALLS_PER_REQUEST
        segments_processed = 0
        
        print(f"🔍 Starting smart terrain sampling for {len(waypoints_with_coords)} waypoints")
        print(f"   • Safe distance threshold: {self.SAFE_DISTANCE_FT}ft")
        print(f"   • API call budget: {max_api_calls} calls")
        
        for i in range(len(waypoints_with_coords) - 1):
            # Check waypoint budget
            if len(safety_waypoints) >= 20:  # Reserve waypoints for other uses
                print(f"⚠️  Waypoint budget limit reached, stopping terrain sampling")
                break
            
            # Check API call budget
            if total_api_calls >= max_api_calls:
                print(f"⚠️  API call budget limit reached, stopping terrain sampling")
                break
            
            current_wp = waypoints_with_coords[i]
            next_wp = waypoints_with_coords[i + 1]
            
            # Calculate segment distance
            segment_distance_ft = self.haversine_distance(
                current_wp['lat'], current_wp['lon'],
                next_wp['lat'], next_wp['lon']
            ) * 3.28084
            
            # Skip short segments - they're inherently safe (key optimization)
            if segment_distance_ft <= self.SAFE_DISTANCE_FT:
                print(f"   ✓ Segment {i+1}: {segment_distance_ft:.0f}ft - SAFE (< {self.SAFE_DISTANCE_FT}ft)")
                continue
            
            print(f"📏 Analyzing segment {i+1}: {segment_distance_ft:.0f}ft")
            
            # Generate sample points along the segment
            sample_points = self.generate_intermediate_points(
                current_wp['lat'], current_wp['lon'],
                next_wp['lat'], next_wp['lon'],
                self.INITIAL_SAMPLE_INTERVAL
            )
            
            if not sample_points:
                continue
            
            # Batch sample elevations for efficiency
            sample_locations = [(p['lat'], p['lon']) for p in sample_points]
            sample_elevations = self.get_elevations_feet_optimized(sample_locations)
            total_api_calls += len(sample_elevations)
            
            # Analyze each sample point for anomalies
            segment_anomalies = []
            
            for j, (sample_point, actual_elevation) in enumerate(zip(sample_points, sample_elevations)):
                expected_elevation = self.linear_interpolate_elevation(
                    current_wp['lat'], current_wp['lon'], current_wp['elevation'],
                    next_wp['lat'], next_wp['lon'], next_wp['elevation'],
                    sample_point['lat'], sample_point['lon']
                )
                
                deviation = actual_elevation - expected_elevation
                abs_deviation = abs(deviation)
                
                if abs_deviation > self.ANOMALY_THRESHOLD:
                    segment_anomalies.append({
                        'point': sample_point,
                        'actual_elevation': actual_elevation,
                        'expected_elevation': expected_elevation,
                        'deviation': deviation,
                        'abs_deviation': abs_deviation,
                        'risk_level': 'critical' if abs_deviation > self.CRITICAL_THRESHOLD else 'moderate'
                    })
                    
                    print(f"⚠️  Anomaly detected: {deviation:+.1f}ft deviation at {sample_point['distance_from_start']:.0f}ft")
            
            # Process anomalies and create safety waypoints
            segment_safety_waypoints = self.process_segment_anomalies(
                segment_anomalies, current_wp, next_wp, i
            )
            
            # Limit safety waypoints per segment
            if len(segment_safety_waypoints) > self.MAX_SAFETY_WAYPOINTS_PER_SEGMENT:
                # Keep only the most critical anomalies
                segment_safety_waypoints.sort(key=lambda x: x['abs_deviation'], reverse=True)
                segment_safety_waypoints = segment_safety_waypoints[:self.MAX_SAFETY_WAYPOINTS_PER_SEGMENT]
                print(f"🔄 Limited to {self.MAX_SAFETY_WAYPOINTS_PER_SEGMENT} safety waypoints for segment {i+1}")
            
            safety_waypoints.extend(segment_safety_waypoints)
        
        segments_analyzed = sum(1 for i in range(len(waypoints_with_coords) - 1) 
                               if self.haversine_distance(waypoints_with_coords[i]['lat'], waypoints_with_coords[i]['lon'],
                                                         waypoints_with_coords[i+1]['lat'], waypoints_with_coords[i+1]['lon']) * 3.28084 > self.SAFE_DISTANCE_FT)
        
        print(f"✅ Smart terrain sampling complete:")
        print(f"   • {len(safety_waypoints)} safety waypoints created")
        print(f"   • {total_api_calls}/{max_api_calls} API calls used ({total_api_calls/max_api_calls*100:.1f}%)")
        print(f"   • {segments_analyzed} segments analyzed (>{self.SAFE_DISTANCE_FT}ft)")
        print(f"   • {len(waypoints_with_coords)-1-segments_analyzed} segments skipped (<{self.SAFE_DISTANCE_FT}ft)")
        
        return safety_waypoints
    
    def process_segment_anomalies(self, anomalies: List[Dict], current_wp: Dict, next_wp: Dict, segment_idx: int) -> List[Dict]:
        """
        Process detected anomalies and create appropriate safety waypoints.
        
        SAFETY LOGIC:
        - Critical anomalies (>60ft): Immediate safety waypoint
        - Moderate anomalies (35-60ft): Dense sampling for verification
        - Positive deviations (hills): Fly over with safety buffer
        - Negative deviations (valleys): Maintain minimum altitude
        
        Args:
            anomalies: List of detected terrain anomalies
            current_wp: Current waypoint for context
            next_wp: Next waypoint for context
            segment_idx: Segment index for logging
            
        Returns:
            List of safety waypoints for this segment
        """
        safety_waypoints = []
        
        for anomaly in anomalies:
            point = anomaly['point']
            actual_elevation = anomaly['actual_elevation']
            deviation = anomaly['deviation']
            risk_level = anomaly['risk_level']
            
            if risk_level == 'critical':
                # Critical anomaly - immediate safety waypoint
                if deviation > 0:
                    # Positive deviation (hill/obstacle) - enhanced ridge mapping
                    print(f"🚨 Critical anomaly detected: +{deviation:.1f}ft - performing enhanced ridge sampling")
                    
                    # Perform enhanced dense sampling around the anomaly
                    enhanced_samples = self.enhanced_ridge_sampling(
                        anomaly, current_wp['lat'], current_wp['lon'], 
                        next_wp['lat'], next_wp['lon']
                    )
                    
                    if enhanced_samples:
                        # Choose sample with the GREATEST POSITIVE DEVIATION (ridge-lip) instead of simply highest elevation.
                        best_sample = None
                        best_dev = -float('inf')
                        for es in enhanced_samples:
                            expected_elev = self.linear_interpolate_elevation(
                                current_wp['lat'], current_wp['lon'], current_wp['elevation'],
                                next_wp['lat'], next_wp['lon'], next_wp['elevation'],
                                es['lat'], es['lon']
                            )
                            sample_dev = es['elevation'] - expected_elev
                            if sample_dev > best_dev:
                                best_dev = sample_dev
                                best_sample = es

                        if best_sample is None:
                            # Fallback to highest elevation sample
                            best_sample = max(enhanced_samples, key=lambda x: x['elevation'])
                            best_dev = best_sample['elevation'] - expected_elev

                        safety_altitude = best_sample['elevation'] + self.SAFETY_BUFFER_FT

                        safety_waypoints.append({
                            'lat': best_sample['lat'],
                            'lon': best_sample['lon'],
                            'altitude': safety_altitude,
                            'elevation': best_sample['elevation'],
                            'reason': f"Enhanced ridge mapping: +{best_dev:.1f}ft deviation",
                            'abs_deviation': anomaly['abs_deviation'],
                            'segment_idx': segment_idx,
                            'type': 'critical_safety_enhanced',
                            'distance_from_start': self.calculate_distance_along_segment(
                                current_wp['lat'], current_wp['lon'], 
                                next_wp['lat'], next_wp['lon'], 
                                best_sample['lat'], best_sample['lon']
                            )
                        })
                        print(f"✅ Enhanced safety waypoint placed at ridge-lip (+{best_dev:.1f}ft dev)")
                else:
                    # Negative deviation (valley) - ignored per new policy (no descent)
                    print(f"ℹ️  Skipping valley deviation {deviation:.1f}ft (no safety waypoint needed)")
            
            elif risk_level == 'moderate' and deviation > 0:
                # Moderate positive deviation - verify with dense sampling
                dense_points = self.verify_moderate_anomaly(point, actual_elevation)
                
                if dense_points:
                    max_elevation = max(p['elevation'] for p in dense_points)
                    safety_altitude = max_elevation + (self.SAFETY_BUFFER_FT * 0.7)  # Slightly less buffer for verified moderate
                    
                    safety_waypoints.append({
                        'lat': point['lat'],
                        'lon': point['lon'],
                        'altitude': safety_altitude,
                        'elevation': max_elevation,
                        'reason': f"Verified terrain feature: +{deviation:.1f}ft",
                        'abs_deviation': anomaly['abs_deviation'],
                        'segment_idx': segment_idx,
                        'type': 'moderate_safety',
                        'distance_from_start': self.calculate_distance_along_segment(
                            current_wp['lat'], current_wp['lon'], 
                            next_wp['lat'], next_wp['lon'], 
                            point['lat'], point['lon']
                        )
                    })
                    
                    print(f"⚠️  Moderate safety waypoint: Verified terrain feature +{deviation:.1f}ft")
        
        return safety_waypoints
    
    def verify_moderate_anomaly(self, center_point: Dict, center_elevation: float) -> List[Dict]:
        """
        Verify moderate anomalies with dense sampling around the detected point.
        
        VERIFICATION ALGORITHM:
        1. Create sampling points in a cross pattern around the anomaly
        2. Sample elevation at each verification point
        3. If multiple points confirm the anomaly, it's real terrain
        4. If isolated, it might be noise - ignore it
        
        Args:
            center_point: GPS coordinates of the detected anomaly
            center_elevation: Elevation at the anomaly point
            
        Returns:
            List of verification points if anomaly is confirmed, empty list otherwise
        """
        # Create verification points in a cross pattern (N, S, E, W)
        offset_degrees = self.DENSE_SAMPLE_INTERVAL / 364000  # Approximate conversion
        
        verification_points = [
            {'lat': center_point['lat'] + offset_degrees, 'lon': center_point['lon']},     # North
            {'lat': center_point['lat'] - offset_degrees, 'lon': center_point['lon']},     # South
            {'lat': center_point['lat'], 'lon': center_point['lon'] + offset_degrees},     # East
            {'lat': center_point['lat'], 'lon': center_point['lon'] - offset_degrees},     # West
        ]
        
        # Sample elevations at verification points
        verification_locations = [(p['lat'], p['lon']) for p in verification_points]
        verification_elevations = self.get_elevations_feet_optimized(verification_locations)
        
        # Add elevations to points
        for point, elevation in zip(verification_points, verification_elevations):
            point['elevation'] = elevation
        
        # Check if anomaly is confirmed by surrounding terrain
        confirmed_points = []
        for point in verification_points:
            if abs(point['elevation'] - center_elevation) <= 15:  # Within 15ft of center
                confirmed_points.append(point)
        
        # Require at least 2 confirmation points to verify the anomaly
        if len(confirmed_points) >= 2:
            return confirmed_points + [{'lat': center_point['lat'], 'lon': center_point['lon'], 'elevation': center_elevation}]
        else:
            return []  # Anomaly not confirmed - likely noise

    def insert_safety_waypoints(self, original_waypoints: List[Dict], safety_waypoints: List[Dict]) -> List[Dict]:
        """
        Insert safety waypoints into the original flight path while maintaining proper sequencing.
        
        INSERTION ALGORITHM:
        1. Group safety waypoints by segment
        2. Sort by distance along each segment
        3. Insert safety waypoints after their corresponding original waypoint
        4. Maintain proper heading and curve calculations
        5. Ensure total waypoint count stays under 99
        
        Args:
            original_waypoints: Original spiral waypoints
            safety_waypoints: Safety waypoints to insert
            
        Returns:
            Combined waypoint list with safety waypoints inserted
        """
        if not safety_waypoints:
            return original_waypoints
        
        # Group safety waypoints by segment
        safety_by_segment = {}
        for safety_wp in safety_waypoints:
            segment_idx = safety_wp['segment_idx']
            if segment_idx not in safety_by_segment:
                safety_by_segment[segment_idx] = []
            safety_by_segment[segment_idx].append(safety_wp)
        
        # Sort safety waypoints within each segment by distance from start
        for segment_idx in safety_by_segment:
            safety_by_segment[segment_idx].sort(key=lambda x: x.get('distance_from_start', 0))
        
        # Insert safety waypoints into the flight path
        enhanced_waypoints = []
        
        for i, waypoint in enumerate(original_waypoints):
            enhanced_waypoints.append(waypoint)
            
            # Insert safety waypoints after this original waypoint
            if i in safety_by_segment:
                for safety_wp in safety_by_segment[i]:
                    # Create properly formatted waypoint
                    enhanced_waypoint = {
                        'latitude': safety_wp['lat'],
                        'longitude': safety_wp['lon'],
                        'altitude': safety_wp['altitude'],
                        'elevation': safety_wp['elevation'],
                        'heading': waypoint.get('heading', 0),  # Use same heading as original
                        'curve': max(waypoint.get('curve', 40), 40),  # Ensure safe curve radius
                        'phase': f"safety_{safety_wp['type']}",
                        'reason': safety_wp['reason'],
                        'type': 'safety_waypoint'
                    }
                    enhanced_waypoints.append(enhanced_waypoint)
                    
                    print(f"✅ Inserted safety waypoint: {safety_wp['reason']}")
        
        # Check waypoint limit
        if len(enhanced_waypoints) > 95:  # Leave buffer for 99 limit
            print(f"⚠️  Enhanced path has {len(enhanced_waypoints)} waypoints, trimming to respect 99 limit")
            # Keep original waypoints and only the most critical safety waypoints
            critical_safety = [wp for wp in enhanced_waypoints if wp.get('type') == 'safety_waypoint' and 'critical' in wp.get('phase', '')]
            if len(original_waypoints) + len(critical_safety) <= 95:
                enhanced_waypoints = original_waypoints + critical_safety
            else:
                enhanced_waypoints = original_waypoints  # Fall back to original path
                print(f"⚠️  Too many waypoints, using original path without safety enhancements")
        
        print(f"📊 Final waypoint count: {len(enhanced_waypoints)} (original: {len(original_waypoints)}, safety: {len(enhanced_waypoints) - len(original_waypoints)})")
        return enhanced_waypoints

    def enhanced_ridge_sampling(self, anomaly: Dict, segment_start_lat: float, segment_start_lon: float, 
                               segment_end_lat: float, segment_end_lon: float) -> List[Dict]:
        """
        Perform enhanced dense sampling around a detected anomaly to better map ridgelines.
        
        SMART SAMPLING STRATEGY:
        1. Create dense sample grid around the anomaly point
        2. Sample along the segment direction for ridge continuity
        3. Sample perpendicular to segment for ridge width mapping  
        4. Use 35ft intervals for high-precision terrain mapping
        5. Limit total samples to stay within API budget
        
        This helps accurately place safety waypoints by understanding the full
        extent and shape of terrain features like ridgelines.
        
        Args:
            anomaly: Detected anomaly with point coordinates and deviation
            segment_start_lat, segment_start_lon: Start of the segment being analyzed
            segment_end_lat, segment_end_lon: End of the segment being analyzed
            
        Returns:
            List of enhanced sample points with elevations around the anomaly
        """
        anomaly_lat = anomaly['point']['lat']
        anomaly_lon = anomaly['point']['lon']
        
        # Calculate segment direction vector for oriented sampling
        segment_bearing = math.atan2(
            segment_end_lat - segment_start_lat,
            segment_end_lon - segment_start_lon
        )
        
        # Convert radius to GPS degrees (approximate)
        radius_degrees = self.RIDGE_DETECTION_RADIUS / 364000  # ~364,000 ft per degree
        interval_degrees = self.DENSE_SAMPLE_INTERVAL / 364000
        
        enhanced_samples = []
        
        # ALONG-SEGMENT SAMPLING: Map ridge continuity along flight path
        for offset_ft in [-100, -70, -35, 0, 35, 70, 100]:  # 7 samples along segment
            offset_degrees = offset_ft / 364000
            sample_lat = anomaly_lat + offset_degrees * math.cos(segment_bearing)
            sample_lon = anomaly_lon + offset_degrees * math.sin(segment_bearing)
            enhanced_samples.append({'lat': sample_lat, 'lon': sample_lon, 'type': 'along_segment'})
        
        # CROSS-SEGMENT SAMPLING: Map ridge width perpendicular to flight path
        perp_bearing = segment_bearing + math.pi / 2  # 90 degrees perpendicular
        for offset_ft in [-70, -35, 35, 70]:  # 4 samples across segment
            offset_degrees = offset_ft / 364000
            sample_lat = anomaly_lat + offset_degrees * math.cos(perp_bearing)
            sample_lon = anomaly_lon + offset_degrees * math.sin(perp_bearing)
            enhanced_samples.append({'lat': sample_lat, 'lon': sample_lon, 'type': 'cross_segment'})
        
        # Limit total samples to stay within API budget (max 11 samples per anomaly)
        if len(enhanced_samples) > 11:
            enhanced_samples = enhanced_samples[:11]
        
        # Batch sample elevations for efficiency
        sample_locations = [(s['lat'], s['lon']) for s in enhanced_samples]
        sample_elevations = self.get_elevations_feet_optimized(sample_locations)
        
        # Combine coordinates with elevations
        enhanced_samples_with_elevation = []
        for sample, elevation in zip(enhanced_samples, sample_elevations):
            enhanced_samples_with_elevation.append({
                'lat': sample['lat'],
                'lon': sample['lon'],
                'elevation': elevation,
                'sample_type': sample['type']
            })
        
        print(f"🔍 Enhanced ridge sampling: {len(enhanced_samples_with_elevation)} dense samples around anomaly")
        return enhanced_samples_with_elevation

    def calculate_distance_along_segment(self, start_lat: float, start_lon: float, end_lat: float, end_lon: float, point_lat: float, point_lon: float) -> float:
        """
        Calculate the distance along a segment from start to the projection of a point onto the segment.
        
        This uses vector projection to find where along the segment line the safety waypoint
        should be positioned for proper ordering.
        
        Args:
            start_lat, start_lon: Segment start coordinates
            end_lat, end_lon: Segment end coordinates  
            point_lat, point_lon: Safety waypoint coordinates
            
        Returns:
            Distance in feet from segment start to the projected position
        """
        # Convert to local XY coordinates for easier vector math
        # Use segment start as origin
        start_xy = {'x': 0, 'y': 0}
        end_xy = self.lat_lon_to_xy(end_lat, end_lon, start_lat, start_lon)
        point_xy = self.lat_lon_to_xy(point_lat, point_lon, start_lat, start_lon)
        
        # Vector from start to end (segment vector)
        segment_vec = {'x': end_xy['x'], 'y': end_xy['y']}
        segment_length_sq = segment_vec['x']**2 + segment_vec['y']**2
        
        if segment_length_sq == 0:
            # Start and end are the same point
            return 0.0
        
        # Vector from start to point
        start_to_point = {'x': point_xy['x'], 'y': point_xy['y']}
        
        # Project start_to_point onto segment_vec
        # t = (start_to_point · segment_vec) / |segment_vec|²
        dot_product = start_to_point['x'] * segment_vec['x'] + start_to_point['y'] * segment_vec['y']
        t = dot_product / segment_length_sq
        
        # Clamp t to [0, 1] to stay within segment bounds
        t = max(0.0, min(1.0, t))
        
        # Calculate distance along segment
        segment_length = math.sqrt(segment_length_sq)
        distance_along_segment = t * segment_length
        
        return distance_along_segment

# Lambda handler function
def lambda_handler(event, context):
    """
    AWS Lambda handler for enhanced drone path generation API.
    
    Supports multiple endpoints:
    - /api/optimize-spiral: Optimize flight parameters for battery constraints
    - /api/optimize-boundary: Optimize an ellipse-fit mission under battery constraints
    - /api/elevation: Get elevation data for coordinates
    - /api/csv: Generate master CSV with all waypoints
    - /api/csv/battery/{id}: Generate CSV for specific battery
    - /DronePathREST: Legacy endpoint for existing functionality
    """
    
    # CORS headers for all responses
    cors_headers = {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Headers': 'Content-Type',
        'Access-Control-Allow-Methods': 'POST, OPTIONS'
    }
    
    try:
        # Handle preflight OPTIONS requests
        if event.get('httpMethod') == 'OPTIONS':
            return {
                'statusCode': 200,
                'headers': cors_headers,
                'body': ''
            }
        
        # Parse request body
        if 'body' in event and event['body']:
            body = json.loads(event['body']) if isinstance(event['body'], str) else event['body']
        else:
            body = {}
        
        # Initialize spiral designer
        designer = SpiralDesigner()
        
        # Get the resource path to determine which endpoint was called
        resource_path = event.get('resource', '')
        path_parameters = event.get('pathParameters', {}) or {}
        
        # Route to appropriate handler based on resource path
        if resource_path == '/api/optimize-spiral':
            return handle_optimize_spiral(designer, body, cors_headers)
        elif resource_path == '/api/optimize-boundary':
            return handle_optimize_boundary(designer, body, cors_headers)
        elif resource_path == '/api/elevation':
            return handle_elevation(designer, body, cors_headers)
        elif resource_path == '/api/csv':
            return handle_csv_download(designer, body, cors_headers)
        elif resource_path == '/api/csv/battery/{id}':
            battery_id = path_parameters.get('id')
            return handle_battery_csv_download(designer, body, battery_id, cors_headers)
        elif resource_path == '/DronePathREST':
            # Legacy endpoint - maintain backward compatibility
            return handle_legacy_drone_path(designer, body, cors_headers)
        else:
            return {
                'statusCode': 404,
                'headers': cors_headers,
                'body': json.dumps({'error': f'Endpoint not found: {resource_path}'})
            }
            
    except Exception as e:
        print(f"Lambda handler error: {str(e)}")
        return {
            'statusCode': 500,
            'headers': cors_headers,
            'body': json.dumps({'error': f'Internal server error: {str(e)}'})
        }

def _parse_optional_float(value, default=None):
    """Parse an optional numeric field, treating blank strings as missing."""
    if value is None:
        return default
    if isinstance(value, (int, float)):
        return float(value)
    value_str = str(value).strip()
    if value_str == "":
        return default
    return float(value_str)

def _parse_expansion_inputs(body: Dict) -> Tuple[Optional[float], Optional[float]]:
    """
    Resolve expansion inputs from either raw request values or optimizer-produced
    actual values.  Actual values take precedence when present.
    """
    actual_min = _parse_optional_float(body.get('actualMinExpansionDist'), None)
    actual_max = _parse_optional_float(body.get('actualMaxExpansionDist'), None)

    if actual_min is not None or actual_max is not None:
        if actual_min is None:
            actual_min = actual_max
        if actual_max is None:
            actual_max = actual_min
        return actual_min, actual_max

    return (
        _parse_optional_float(body.get('minExpansionDist'), None),
        _parse_optional_float(body.get('maxExpansionDist'), None),
    )

def _build_adjustment_messages(
    optimized_params: Dict,
    requested_expansion: Dict,
) -> List[str]:
    """Summarize how the optimizer changed the requested inputs."""
    adjustments = []
    requested_seed = int(optimized_params.get('requestedBounceSeed', optimized_params.get('N', 0)))
    final_bounces = int(optimized_params.get('N', requested_seed))
    adjusted_bounces = bool(optimized_params.get('adjustedBounceCount'))
    adjusted_expansion = bool(optimized_params.get('adjustedExpansion'))

    if adjusted_bounces:
        if final_bounces < requested_seed:
            if requested_expansion['has_custom_spacing'] and adjusted_expansion:
                adjustments.append(
                    f"Reduced bounces from {requested_seed} to {final_bounces} before tightening spacing to fit battery target"
                )
            elif requested_expansion['has_custom_spacing']:
                adjustments.append(
                    f"Reduced bounces from {requested_seed} to {final_bounces} to preserve requested spacing within battery target"
                )
            else:
                adjustments.append(
                    f"Reduced bounces from {requested_seed} to {final_bounces} to fit battery target"
                )
        else:
            adjustments.append(
                f"Increased bounces from {requested_seed} to {final_bounces} to improve battery usage"
            )

    if adjusted_expansion and requested_expansion['has_custom_spacing']:
        actual_min = optimized_params.get('actualMinExpansionDist')
        actual_max = optimized_params.get('actualMaxExpansionDist')
        requested_min = requested_expansion.get('requested_min')
        requested_max = requested_expansion.get('requested_max')
        scale_candidates = []

        if requested_min not in (None, 0) and actual_min is not None:
            scale_candidates.append(actual_min / requested_min)
        if requested_max not in (None, 0) and actual_max is not None:
            scale_candidates.append(actual_max / requested_max)

        shrink_pct = 1
        if scale_candidates:
            shrink_pct = max(1, round((1.0 - min(scale_candidates)) * 100))

        adjustments.append(f"Tightened requested spacing by {shrink_pct}% to fit battery target")

    return adjustments

def handle_optimize_spiral(designer, body, cors_headers):
    """Handle /api/optimize-spiral endpoint"""
    try:
        if body.get('boundary') is not None:
            return handle_optimize_boundary(designer, body, cors_headers)

        battery_minutes = float(body.get('batteryMinutes', 20))
        batteries = int(body.get('batteries', 3))
        center = body.get('center', '')
        min_exp, max_exp = _parse_expansion_inputs(body)
        
        # Validate battery minutes to prevent division by zero
        if battery_minutes <= 0:
            return {
                'statusCode': 400,
                'headers': cors_headers,
                'body': json.dumps({'error': 'Battery minutes must be greater than 0'})
            }
        
        if not center:
            return {
                'statusCode': 400,
                'headers': cors_headers,
                'body': json.dumps({'error': 'Center coordinates are required'})
            }
        
        # Parse center coordinates
        center_coords = designer.parse_center(center)
        if not center_coords:
            return {
                'statusCode': 400,
                'headers': cors_headers,
                'body': json.dumps({'error': 'Invalid center coordinates format'})
            }
        
        # Optimize spiral parameters
        optimized_params = designer.optimize_spiral_for_battery(
            battery_minutes,
            batteries,
            center_coords['lat'],
            center_coords['lon'],
            min_expansion_dist=min_exp,
            max_expansion_dist=max_exp,
        )
        requested_expansion = designer.normalize_expansion_request(min_exp, max_exp)
        adjustments = _build_adjustment_messages(optimized_params, requested_expansion)
        
        return {
            'statusCode': 200,
            'headers': cors_headers,
            'body': json.dumps({
                'optimized_params': optimized_params,
                'optimization_info': {
                    'algorithm': 'Battery-First Late Bounce Optimization',
                    'pattern_type': (
                        'Custom Expansion Spiral Optimization'
                        if requested_expansion['has_custom_spacing']
                        else 'Exponential Spiral Optimization'
                    ),
                    'bounce_scaling_reason': (
                        f"Battery duration {battery_minutes}min → seed {optimized_params['requestedBounceSeed']} "
                        f"bounces, resolved to {optimized_params['N']}"
                    ),
                    'safety_margin': '98% battery utilization maximum',
                    'requested_constraints': {
                        'batteryMinutes': battery_minutes,
                        'batteries': batteries,
                        'minExpansionDist': min_exp,
                        'maxExpansionDist': max_exp,
                    },
                    'final_constraints': {
                        'N': optimized_params['N'],
                        'r0': optimized_params['r0'],
                        'rHold': optimized_params['rHold'],
                        'actualMinExpansionDist': optimized_params['actualMinExpansionDist'],
                        'actualMaxExpansionDist': optimized_params['actualMaxExpansionDist'],
                        'estimated_time_minutes': optimized_params['estimated_time_minutes'],
                        'battery_utilization': optimized_params['battery_utilization'],
                    },
                    'adjustments': adjustments,
                }
            })
        }
        
    except ValueError as e:
        return {
            'statusCode': 400,
            'headers': cors_headers,
            'body': json.dumps({'error': f'Optimization failed: {str(e)}'})
        }
    except Exception as e:
        return {
            'statusCode': 500,
            'headers': cors_headers,
            'body': json.dumps({'error': f'Optimization failed: {str(e)}'})
        }

def handle_optimize_boundary(designer, body, cors_headers):
    """Handle /api/optimize-boundary endpoint."""
    try:
        battery_minutes = float(body.get('batteryMinutes', 20))
        batteries = int(body.get('batteries', 3))
        center = body.get('center', '')
        center_coords = designer.parse_center(center)
        boundary = designer.parse_boundary(body.get('boundary'), center_coords)

        if battery_minutes <= 0:
            return {
                'statusCode': 400,
                'headers': cors_headers,
                'body': json.dumps({'error': 'Battery minutes must be greater than 0'})
            }

        if batteries <= 0 or batteries > 12:
            return {
                'statusCode': 400,
                'headers': cors_headers,
                'body': json.dumps({'error': 'Battery count must be between 1 and 12'})
            }

        if not boundary:
            return {
                'statusCode': 400,
                'headers': cors_headers,
                'body': json.dumps({'error': 'A valid boundary is required'})
            }

        params = {
            'slices': batteries,
            'r0': 200.0,
        }
        min_exp = body.get('minExpansionDist')
        max_exp = body.get('maxExpansionDist')
        if min_exp is not None and str(min_exp).strip() != '':
            params['minExpansionDist'] = float(min_exp)
        if max_exp is not None and str(max_exp).strip() != '':
            params['maxExpansionDist'] = float(max_exp)

        boundary_plan = designer.plan_boundary_mission(battery_minutes, batteries, boundary, params)
        preview_paths = designer.generate_boundary_preview_paths(params, boundary, boundary_plan)

        toast_message = None
        if boundary_plan['fitStatus'] != 'full':
            toast_message = (
                'Increase battery quantity or duration to better capture this area. '
                'The current mission is the largest battery-safe fit inside the boundary.'
            )

        print(json.dumps({
            'event': 'optimize_boundary',
            'boundary': boundary,
            'batteryMinutes': battery_minutes,
            'batteries': batteries,
            'fitStatus': boundary_plan['fitStatus'],
            'coverageRatio': boundary_plan['coverageRatio'],
            'limitingBatteryIndex': boundary_plan['limitingBatteryIndex'],
        }))

        return {
            'statusCode': 200,
            'headers': cors_headers,
            'body': json.dumps({
                'boundary': boundary,
                'boundaryPlan': boundary_plan,
                'previewPaths': preview_paths,
                'toastMessage': toast_message,
            })
        }
    except Exception as e:
        return {
            'statusCode': 500,
            'headers': cors_headers,
            'body': json.dumps({'error': f'Boundary optimization failed: {str(e)}'})
        }

def handle_elevation(designer, body, cors_headers):
    """Handle /api/elevation endpoint"""
    try:
        designer.require_live_elevation = True
        center = body.get('center', '')
        
        if not center:
            return {
                'statusCode': 400,
                'headers': cors_headers,
                'body': json.dumps({'error': 'Center coordinates are required'})
            }
        
        # Parse center coordinates
        center_coords = designer.parse_center(center)
        if not center_coords:
            return {
                'statusCode': 400,
                'headers': cors_headers,
                'body': json.dumps({'error': 'Invalid center coordinates format'})
            }
        
        # Get elevation data
        elevation_feet = designer.get_elevation_feet(center_coords['lat'], center_coords['lon'])
        elevation_meters = elevation_feet * 0.3048
        
        return {
            'statusCode': 200,
            'headers': cors_headers,
            'body': json.dumps({
                'elevation_feet': round(elevation_feet, 1),
                'elevation_meters': round(elevation_meters, 1),
                'coordinates': center_coords
            })
        }

    except TerrainElevationUnavailableError as e:
        return {
            'statusCode': 503,
            'headers': cors_headers,
            'body': json.dumps({'error': str(e)})
        }
    except Exception as e:
        return {
            'statusCode': 500,
            'headers': cors_headers,
            'body': json.dumps({'error': f'Elevation lookup failed: {str(e)}'})
        }

def _parse_bool(value, default=True):
    """Parse API boolean fields without treating the string 'false' as truthy."""
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"true", "1", "yes", "on"}:
            return True
        if normalized in {"false", "0", "no", "off"}:
            return False
    return bool(value)

def _parse_bool_field(value, default: bool = False) -> bool:
    """Parse API boolean values from bool/int/string payloads."""
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value != 0

    normalized = str(value).strip().lower()
    if normalized in {'true', '1', 'yes', 'y', 'on'}:
        return True
    if normalized in {'false', '0', 'no', 'n', 'off'}:
        return False
    return default

def handle_csv_download(designer, body, cors_headers):
    """Handle /api/csv endpoint"""
    try:
        # Extract parameters from body
        slices = body.get('slices', 3)
        N = body.get('N', 8)
        r0 = body.get('r0', 150)
        rHold = body.get('rHold', 1595)
        center = body.get('center', '')
        # Robustly parse minHeight / maxHeight so blank strings don't cause errors
        def _parse_height(value, default=None):
            """Convert height field to float, returning default if blank or invalid."""
            if value is None:
                return default
            if isinstance(value, (int, float)):
                return float(value)
            # Handle empty string or whitespace
            value_str = str(value).strip()
            if value_str == "":
                return default
            try:
                return float(value_str)
            except (ValueError, TypeError):
                return default

        # Default minimum altitude is 120 ft AGL when user leaves field blank
        min_height = _parse_height(body.get('minHeight'), 120.0)
        # maxHeight is optional – if blank/invalid we treat as unlimited (None)
        max_height = _parse_height(body.get('maxHeight'), None)
        form_to_terrain = _parse_bool(body.get('formToTerrain'), True)
        designer.require_live_elevation = form_to_terrain
        spin_mode = _parse_bool_field(body.get('spinMode'), False)
        
        if not center:
            return {
                'statusCode': 400,
                'headers': cors_headers,
                'body': json.dumps({'error': 'Center coordinates are required'})
            }
        
        # Build parameters for CSV generation
        params = {
            'slices': slices,
            'N': N,
            'r0': r0,
            'rHold': rHold
        }
        
        min_exp, max_exp = _parse_expansion_inputs(body)
        if min_exp is not None:
            params['minExpansionDist'] = min_exp
        if max_exp is not None:
            params['maxExpansionDist'] = max_exp
        
        # Generate CSV content
        csv_content = designer.generate_csv(
            params,
            center,
            min_height,
            max_height,
            form_to_terrain=form_to_terrain,
            spin_mode=spin_mode,
            form_to_terrain=form_to_terrain,
        )
        
        # Return CSV as text/csv
        return {
            'statusCode': 200,
            'headers': {
                **cors_headers,
                'Content-Type': 'text/csv',
                'Content-Disposition': 'attachment; filename="flight-plan.csv"'
            },
            'body': csv_content
        }

    except TerrainElevationUnavailableError as e:
        return {
            'statusCode': 503,
            'headers': cors_headers,
            'body': json.dumps({'error': str(e)})
        }
    except Exception as e:
        return {
            'statusCode': 500,
            'headers': cors_headers,
            'body': json.dumps({'error': f'CSV generation failed: {str(e)}'})
        }

def handle_battery_csv_download(designer, body, battery_id, cors_headers):
    """Handle /api/csv/battery/{id} endpoint"""
    try:
        if not battery_id:
            return {
                'statusCode': 400,
                'headers': cors_headers,
                'body': json.dumps({'error': 'Battery ID is required'})
            }
        
        try:
            battery_index = int(battery_id) - 1  # Convert to 0-based index
        except ValueError:
            return {
                'statusCode': 400,
                'headers': cors_headers,
                'body': json.dumps({'error': 'Invalid battery ID'})
            }
        
        boundary = designer.parse_boundary(body.get('boundary'))
        boundary_plan = designer.parse_boundary_plan(body.get('boundaryPlan'), int(body.get('slices', 3)))

        # Extract parameters from body with type conversion
        slices = int(body.get('slices', len(boundary_plan.get('batteries', [])) if boundary_plan else 3))
        N = int(body.get('N', 8))
        r0 = float(body.get('r0', 150))
        rHold = float(body.get('rHold', 1595))
        center = body.get('center', '')
        # Robustly parse minHeight / maxHeight so blank strings don't cause errors
        def _parse_height(value, default=None):
            """Convert height field to float, returning default if blank or invalid."""
            if value is None:
                return default
            if isinstance(value, (int, float)):
                return float(value)
            # Handle empty string or whitespace
            value_str = str(value).strip()
            if value_str == "":
                return default
            try:
                return float(value_str)
            except (ValueError, TypeError):
                return default

        # Default minimum altitude is 120 ft AGL when user leaves field blank
        min_height = _parse_height(body.get('minHeight'), 120.0)
        # maxHeight is optional – if blank/invalid we treat as unlimited (None)
        max_height = _parse_height(body.get('maxHeight'), None)
        form_to_terrain = _parse_bool(body.get('formToTerrain'), True)
        designer.require_live_elevation = form_to_terrain
        spin_mode = _parse_bool_field(body.get('spinMode'), False)
        
        if not center:
            return {
                'statusCode': 400,
                'headers': cors_headers,
                'body': json.dumps({'error': 'Center coordinates are required'})
            }
        
        if battery_index < 0 or battery_index >= slices:
            return {
                'statusCode': 400,
                'headers': cors_headers,
                'body': json.dumps({'error': f'Battery ID must be between 1 and {slices}'})
            }
        
        # Build parameters for CSV generation
        params = {
            'slices': slices,
            'N': N,
            'r0': r0,
            'rHold': rHold
        }
        
        min_exp, max_exp = _parse_expansion_inputs(body)
        if min_exp is not None:
            params['minExpansionDist'] = min_exp
        if max_exp is not None:
            params['maxExpansionDist'] = max_exp
        
        # Generate battery-specific CSV content
        csv_content = designer.generate_battery_csv(
            params,
            center,
            battery_index,
            min_height,
            max_height,
            boundary=boundary,
            boundary_plan=boundary_plan,
            form_to_terrain=form_to_terrain,
            spin_mode=spin_mode,
            boundary=boundary,
            boundary_plan=boundary_plan,
            form_to_terrain=form_to_terrain,
        )
        # Debug: verify spin_mode and POI in response headers (and CloudWatch)
        print(f"[battery-csv] spin_mode={spin_mode}, battery_id={battery_id}")
        poi_in_csv = '0,0' if spin_mode else 'center'

        return {
            'statusCode': 200,
            'headers': {
                **cors_headers,
                'Content-Type': 'text/csv',
                'Content-Disposition': f'attachment; filename="battery-{battery_id}.csv"',
                'Access-Control-Expose-Headers': 'X-Spin-Mode-Applied, X-POI-Used',
                'X-Spin-Mode-Applied': 'true' if spin_mode else 'false',
                'X-POI-Used': poi_in_csv,
            },
            'body': csv_content
        }

    except TerrainElevationUnavailableError as e:
        return {
            'statusCode': 503,
            'headers': cors_headers,
            'body': json.dumps({'error': str(e)})
        }
    except Exception as e:
        return {
            'statusCode': 500,
            'headers': cors_headers,
            'body': json.dumps({'error': f'Battery CSV generation failed: {str(e)}'})
        }

def handle_legacy_drone_path(designer, body, cors_headers):
    """Handle legacy /DronePathREST endpoint for backward compatibility"""
    try:
        # This maintains compatibility with existing functionality
        # Add your existing drone path logic here if needed
        return {
            'statusCode': 200,
            'headers': cors_headers,
            'body': json.dumps({'message': 'Legacy endpoint - implement existing functionality here'})
        }
        
    except Exception as e:
        return {
            'statusCode': 500,
            'headers': cors_headers,
            'body': json.dumps({'error': f'Legacy endpoint error: {str(e)}'})
        }

# Example usage and testing
if __name__ == "__main__":
    designer = SpiralDesigner()
    
    # Test parameters
    test_params = {
        'slices': 6,
        'N': 6,
        'r0': 1,
        'rHold': 50
    }
    
    # Test waypoint generation
    waypoints = designer.compute_waypoints(test_params)
    print(f"Generated {len(waypoints)} slices with waypoints")
    
    # Test CSV generation
    try:
        csv_content = designer.generate_csv(
            test_params, 
            "41.73218, -111.83979",
            debug_mode=False
        )
        print(f"Generated CSV with {len(csv_content.split(chr(10))) - 1} waypoints")
    except Exception as e:
        print(f"CSV generation error: {e}") 
