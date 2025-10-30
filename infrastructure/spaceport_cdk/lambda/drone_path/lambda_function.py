from __future__ import annotations

import math
import json
import csv
import io
import os
import requests
import time
import heapq
from dataclasses import dataclass, field
from typing import Any, List, Dict, Tuple, Optional

FT_PER_METER = 3.28084
M_PER_FT = 0.3048

try:
    from .elevation_provider import ElevationProvider, LatLon
except ImportError:  # pragma: no cover - fallback for local execution
    from elevation_provider import ElevationProvider, LatLon

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
        self._last_sampling_metrics: Dict[str, Any] = {}
        self._last_sampling_hazards: List[Hazard] = []

        # DEVELOPMENT API KEY - Replace with environment variable for production
        # This key is rate-limited and for development/testing only
        dev_api_key = "AIzaSyDkdnE1weVG38PSUO5CWFneFjH16SPYZHU"
        
        # Priority: Environment variable > Development key
        self.api_key = os.environ.get("GOOGLE_MAPS_API_KEY", dev_api_key)
        
        # Log which API key is being used (mask for security)
        key_source = "PRODUCTION" if "GOOGLE_MAPS_API_KEY" in os.environ else "DEV (RATE LIMITED)"
        masked_key = self.api_key[:10] + "..." + self.api_key[-4:] if self.api_key else "None"
        print(f"🔑 Using {key_source} API key: {masked_key}")
    
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
            return 4500.0  # Default elevation in feet
        
        try:
            # Google Maps Elevation API endpoint
            url = f"https://maps.googleapis.com/maps/api/elevation/json?locations={lat},{lon}&key={self.api_key}"
            response = requests.get(url, timeout=10)
            
            if response.status_code != 200:
                raise ValueError(f"Elevation HTTP error {response.status_code}")
            
            data = response.json()
            if data["status"] != "OK" or not data["results"]:
                print(f"Google Elevation API error: {data.get('status', 'Unknown error')}")
                return 1000.0  # Default to 1000ft if API fails
            
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
            return 1000.0
    
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
    
    def make_spiral(self, dphi: float, N: int, r0: float, r_hold: float, steps: int = 1200) -> List[Dict]:
        """
        Generate the core exponential spiral pattern with neural network optimizations.
        
        MATHEMATICAL FOUNDATION:
        =======================
        
        Exponential Spiral: r(t) = r₀ * exp(α * t)
        
        Original Alpha: α = ln(r_hold/r₀)/(N*Δφ)
        OPTIMIZED Alpha: α = ln(r_hold/r₀)/(N*Δφ) * 0.86  ← 14% reduction for denser coverage
        
        WHY 14% REDUCTION?
        - Creates smaller radial steps between bounces
        - Increases waypoint density by ~14% per spiral area  
        - Better photo overlap for neural network training
        - Smoother flight transitions
        
        THREE-PHASE ALGORITHM:
        =====================
        
        Phase 1 - OUTWARD SPIRAL (0 ≤ t ≤ t_out):
        r(t) = r₀ * exp(α * t)
        
        Phase 2 - HOLD PATTERN (t_out < t ≤ t_out + t_hold):
        r(t) = actual_max_radius  ← Uses ACTUAL radius reached, not original r_hold
        
        Phase 3 - INWARD SPIRAL (t > t_out + t_hold):
        r(t) = actual_max_radius * exp(-α * (t - t_out - t_hold))
        
        CRITICAL FIX IMPLEMENTED:
        The hold pattern now uses actual_max_radius instead of r_hold parameter.
        This eliminates the large gap that was occurring between outbound_bounce_6 and hold_mid.
        
        PHASE CALCULATION:
        Phase oscillates between 0 and 2Δφ to create the characteristic spiral bounce pattern.
        
        Args:
            dphi: Angular step size per bounce (radians)
            N: Number of bounces (direction changes)
            r0: Starting radius (feet)
            r_hold: Target hold radius (feet) - used only for alpha calculation
            steps: Number of discrete points to generate (1200 = high precision)
            
        Returns:
            List of {x, y} points in feet relative to center
        """
        # PROGRESSIVE ALPHA SYSTEM: Steeper early bounces, normal later bounces
        # Solution: Use higher alpha for early expansion, then reduce for later bounces
        
        # Calculate base parameters
        base_alpha = math.log(r_hold / r0) / (N * dphi)
        radius_ratio = r_hold / r0
        
        # PROGRESSIVE EXPANSION: Different alpha for different parts of spiral
        # Early bounces (first 40%): More aggressive expansion
        # Later bounces (last 60%): Normal expansion for good coverage
        
        if radius_ratio > 20:   # Medium-large spirals need progressive approach
            early_density_factor = 1.02   # 2% MORE expansion for early bounces (fine-tuned for 4000ft)
            late_density_factor = 0.80    # 20% reduction for later bounces (good coverage)
            print(f"🎯 Progressive expansion: early_boost=+2%, late_reduction=20%, ratio={radius_ratio:.1f}")
        elif radius_ratio > 10:   # Medium spirals
            early_density_factor = 1.05   # 5% more expansion for early bounces
            late_density_factor = 0.85    # 15% reduction for later bounces
            print(f"🎯 Progressive expansion: early_boost=+5%, late_reduction=15%, ratio={radius_ratio:.1f}")
        else:  # Small spirals
            early_density_factor = 1.0    # Normal expansion
            late_density_factor = 0.90    # 10% reduction
            print(f"🎯 Progressive expansion: early_boost=0%, late_reduction=10%, ratio={radius_ratio:.1f}")
        
        # We'll use these factors dynamically in the spiral generation below
        alpha_early = base_alpha * early_density_factor
        alpha_late = base_alpha * late_density_factor
        
        # Time parameters
        t_out = N * dphi          # Time to complete outward spiral
        t_hold = dphi             # Time for hold pattern (one angular step)
        t_total = 2 * t_out + t_hold  # Total spiral time
        
        # PROGRESSIVE ALPHA TRANSITION POINT
        t_transition = t_out * 0.4  # First 40% uses early alpha, rest uses late alpha
        
        # Calculate ACTUAL radius with progressive alpha
        # Early phase: r0 * exp(alpha_early * t) for t <= t_transition  
        # Late phase: r_transition * exp(alpha_late * (t - t_transition)) for t > t_transition
        r_transition = r0 * math.exp(alpha_early * t_transition)
        actual_max_radius = r_transition * math.exp(alpha_late * (t_out - t_transition))
        
        spiral_points = []
        
        for i in range(steps):
            # Convert step index to parameter t
            th = i * t_total / (steps - 1)
            
            # Calculate radius based on current phase with PROGRESSIVE ALPHA
            if th <= t_out:
                # PHASE 1: Outward spiral - PROGRESSIVE expansion
                if th <= t_transition:
                    # Early bounces: Steeper expansion (alpha_early)
                    r = r0 * math.exp(alpha_early * th)
                else:
                    # Later bounces: Normal expansion (alpha_late) from transition point
                    r = r_transition * math.exp(alpha_late * (th - t_transition))
            elif th <= t_out + t_hold:
                # PHASE 2: Hold pattern - constant radius at ACTUAL maximum reached
                r = actual_max_radius  # ← FIXED: Use actual radius reached, not original r_hold
            else:
                # PHASE 3: Inbound spiral - exponential contraction from actual maximum
                inbound_t = th - (t_out + t_hold)
                r = actual_max_radius * math.exp(-alpha_late * inbound_t)  # Use late alpha for inbound
            
            # Calculate phase for bounce pattern
            # Phase oscillates between 0 and 2*dphi to create directional changes
            phase = ((th / dphi) % 2 + 2) % 2
            phi = phase * dphi if phase <= 1 else (2 - phase) * dphi
            
            # Convert polar coordinates (r, phi) to Cartesian (x, y)
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
        spiral_pts = self.make_spiral(dphi, params['N'], params['r0'], params['rHold'])
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
    
    def parse_center(self, txt: str) -> Optional[Dict]:
        """
        Parse center coordinates from various human-readable formats.
        
        SUPPORTED FORMATS:
        - "41.73218° N, 111.83979° W" (degree notation)
        - "41.73218, -111.83979" (decimal degrees)
        - "41.73218° N, 111.83979° W" (mixed formats)
        
        REGEX PATTERNS:
        - Degree format: (\d+\.?\d*)\s*°?\s*([NS])\s*,\s*(\d+\.?\d*)\s*°?\s*([EW])
        - Decimal format: ([-+]?\d+\.?\d*)\s*,\s*([-+]?\d+\.?\d*)
        
        Args:
            txt: Coordinate string in various formats
            
        Returns:
            Dict with 'lat' and 'lon' keys, or None if parsing fails
        """
        import re
        
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

    def generate_csv(self, params: Dict, center_str: str, min_height: float = 100.0, max_height: float = None, debug_mode: bool = False, debug_angle: float = 0) -> str:
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
            
        Returns:
            Complete CSV file content as string
        """
        center = self.parse_center(center_str)
        if not center:
            raise ValueError("Invalid center coordinates")
        
        # Get takeoff elevation for reference
        takeoff_elevation_feet = self.get_elevation_feet(center['lat'], center['lon'])
        
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
        
        # Get elevations with 15-foot proximity optimization
        ground_elevations = self.get_elevations_feet_optimized(locations)
        
        # Add elevations to waypoints_with_coords for adaptive sampling
        for i, elevation in enumerate(ground_elevations):
            waypoints_with_coords[i]['elevation'] = elevation
        
        # ADAPTIVE TERRAIN SAMPLING - Detect and add safety waypoints (All slices)
        print(f"🛡️  Starting adaptive terrain sampling for complete mission safety")
        safety_waypoints = self.adaptive_terrain_sampling(
            waypoints_with_coords,
            min_agl_ft=min_height,
            max_agl_ft=max_height,
        )
        
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
        
        # Track altitude calculation state for neural network optimization
        first_waypoint_distance = 0
        max_outbound_altitude = 0
        max_outbound_distance = 0
        
        enhanced_waypoints_data = getattr(self, '_enhanced_waypoints_data', None)
        
        for i, wp in enumerate(spiral_path):
            # Check if this is a safety waypoint
            is_safety_waypoint = (enhanced_waypoints_data and 
                                  i < len(enhanced_waypoints_data) and 
                                  enhanced_waypoints_data[i].get('is_safety', False))
            
            if is_safety_waypoint:
                # Safety waypoint - use pre-calculated coordinates and altitude
                safety_data = enhanced_waypoints_data[i]
                latitude = round(safety_data['coords']['lat'] * 100000) / 100000
                longitude = round(safety_data['coords']['lon'] * 100000) / 100000
                # Safety waypoint altitude is stored as absolute MSL. Convert to the
                # same reference frame used by regular waypoints (feet above take-off).
                altitude_agl = safety_data['safety_altitude'] - takeoff_elevation_feet
                if altitude_agl < min_height:
                    altitude_agl = min_height  # Never below minimum flight height
                altitude = round(altitude_agl * 100) / 100
                
                print(f"🚨 Safety waypoint {i+1}: {safety_data['safety_reason']} at {altitude:.1f}ft")
            else:
                # Regular waypoint - normal processing
                coords = self.xy_to_lat_lon(wp['x'], wp['y'], center['lat'], center['lon'])
                latitude = round(coords['lat'] * 100000) / 100000  # 5 decimal places (~1m accuracy)
                longitude = round(coords['lon'] * 100000) / 100000
                
                # Calculate elevation-aware altitude with terrain following
                ground_elevation = ground_elevations[i]
                local_ground_offset = ground_elevation - takeoff_elevation_feet
                if local_ground_offset < 0:
                    local_ground_offset = 0  # Never fly below takeoff elevation
                
                # NEURAL NETWORK ALTITUDE CALCULATION ALGORITHM
                # =============================================
                dist_from_center = math.sqrt(wp['x']**2 + wp['y']**2)
                phase = wp.get('phase', 'unknown')
                
                if i == 0:
                    # FIRST WAYPOINT: Always starts at min_height
                    first_waypoint_distance = dist_from_center
                    desired_agl = min_height
                    max_outbound_altitude = min_height
                    max_outbound_distance = dist_from_center
                elif 'outbound' in phase or 'hold' in phase:
                    # OUTBOUND & HOLD: Balanced climb with 0.20ft per foot climb rate
                    additional_distance = dist_from_center - first_waypoint_distance
                    if additional_distance < 0:
                        additional_distance = 0
                    agl_increment = additional_distance * 0.20  # ShapeLab optimized rate
                    desired_agl = min_height + agl_increment
                    
                    # Track maximum for inbound ascent calculations
                    if desired_agl > max_outbound_altitude:
                        max_outbound_altitude = desired_agl
                        max_outbound_distance = dist_from_center
                elif 'inbound' in phase:
                    # INBOUND: Continued climb with 0.1ft per foot ascent rate
                    distance_from_max = max_outbound_distance - dist_from_center
                    if distance_from_max < 0:
                        distance_from_max = 0
                    altitude_increase = distance_from_max * 0.1  # Gentle continued ascent
                    desired_agl = max_outbound_altitude + altitude_increase
                    
                    # Safety floor: never below min_height
                    if desired_agl < min_height:
                        desired_agl = min_height
                else:
                    # Fallback for unknown phases (should not occur in normal operation)
                    additional_distance = dist_from_center - first_waypoint_distance
                    if additional_distance < 0:
                        additional_distance = 0
                    agl_increment = additional_distance * 0.20
                    desired_agl = min_height + agl_increment
                
                # Calculate final MSL altitude (terrain following)
                final_altitude = local_ground_offset + desired_agl
                
                # Apply maximum height constraint if specified
                if max_height is not None:
                    adjusted_max_height = max_height - takeoff_elevation_feet
                    current_agl = final_altitude - ground_elevation
                    if current_agl > adjusted_max_height:
                        final_altitude = ground_elevation + adjusted_max_height
                
                altitude = round(final_altitude * 100) / 100  # Round to cm precision
            
            # Calculate forward-looking heading using atan2
            heading = 0
            if i < len(spiral_path) - 1:
                next_wp = spiral_path[i + 1]
                dx = next_wp['x'] - wp['x']
                dy = next_wp['y'] - wp['y']
                heading = round(((math.atan2(dx, dy) * 180 / math.pi) + 360) % 360)
            
            # Convert curve radius from feet to meters (Litchi requirement)
            curve_size_meters = round((wp['curve'] * self.FT2M) * 100) / 100
            
            # Calculate sinusoidal gimbal pitch for varied photo angles
            progress = i / (len(spiral_path) - 1) if len(spiral_path) > 1 else 0
            gimbal_pitch = round(-35 + 14 * math.sin(progress * math.pi))  # -35° to -21° range
            
            # Calculate photo interval timing
            # Start photos at first waypoint, continue throughout flight, stop at last waypoint
            if i == 0:
                photo_interval = 3.0  # Start taking photos at 3-second intervals
            elif i == len(spiral_path) - 1:
                photo_interval = 0    # Stop taking photos at the last waypoint
            else:
                photo_interval = 3.0  # Continue 3-second intervals throughout flight
            
            # Create CSV row with all 16 Litchi columns
            row = [
                latitude,                   # GPS latitude
                longitude,                  # GPS longitude  
                altitude,                   # Flight altitude (MSL feet)
                heading,                    # Forward direction (degrees)
                curve_size_meters,          # Turn radius (meters)
                0,                          # Rotation direction (none)
                2,                          # Gimbal mode (focus POI)
                gimbal_pitch,               # Camera tilt angle 
                0,                          # Altitude mode (AGL)
                8.85,                       # Speed (19.8 mph = 8.85 m/s)
                center['lat'],              # POI latitude (spiral center)
                center['lon'],              # POI longitude (spiral center)
                -35,                        # POI altitude (-35ft AGL)
                0,                          # POI altitude mode (AGL)
                photo_interval,             # Photo interval (3s start/middle, 0s stop)
                0                           # Photo distance interval (disabled)
            ]
            
            rows.append(','.join(map(str, row)))
        
        return '\n'.join(rows)

    def generate_battery_csv(self, params: Dict, center_str: str, battery_index: int, min_height: float = 100.0, max_height: float = None) -> str:
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
            
        # Validate battery index range
        if battery_index < 0 or battery_index >= params['slices']:
            raise ValueError(f"Battery index must be between 0 and {params['slices'] - 1}")
        
        # Clear caches to prevent memory accumulation across battery downloads
        self.elevation_cache = {}
        self.waypoint_cache = []
        
        # Get takeoff elevation for reference
        takeoff_elevation_feet = self.get_elevation_feet(center['lat'], center['lon'])
        
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
        
        # Get elevations with 15-foot proximity optimization
        ground_elevations = self.get_elevations_feet_optimized(locations)
        
        # Add elevations to waypoints_with_coords for adaptive sampling
        for i, elevation in enumerate(ground_elevations):
            waypoints_with_coords[i]['elevation'] = elevation
        
        # ADAPTIVE TERRAIN SAMPLING - Detect and add safety waypoints
        print(f"🛡️  Starting adaptive terrain sampling for mission safety")
        safety_waypoints = self.adaptive_terrain_sampling(
            waypoints_with_coords,
            min_agl_ft=min_height,
            max_agl_ft=max_height,
        )
        
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
        
        # Track altitude calculation state (IDENTICAL to generate_csv logic)
        first_waypoint_distance = 0
        max_outbound_altitude = 0
        max_outbound_distance = 0
        
        # Process waypoints with identical algorithm to ensure consistency
        for i, wp in enumerate(spiral_path):
            # Convert to GPS coordinates with high precision
            coords = self.xy_to_lat_lon(wp['x'], wp['y'], center['lat'], center['lon'])
            latitude = round(coords['lat'] * 100000) / 100000
            longitude = round(coords['lon'] * 100000) / 100000
            
            # Calculate elevation-aware altitude with terrain following
            ground_elevation = ground_elevations[i]
            local_ground_offset = ground_elevation - takeoff_elevation_feet
            if local_ground_offset < 0:
                local_ground_offset = 0
            
            # NEURAL NETWORK ALTITUDE CALCULATION (identical to generate_csv)
            dist_from_center = math.sqrt(wp['x']**2 + wp['y']**2)
            phase = wp.get('phase', 'unknown')
            
            if i == 0:
                # FIRST WAYPOINT: Always starts at min_height
                first_waypoint_distance = dist_from_center
                desired_agl = min_height
                max_outbound_altitude = min_height
                max_outbound_distance = dist_from_center
            elif 'outbound' in phase or 'hold' in phase:
                # OUTBOUND & HOLD: Balanced climb with 0.20ft per foot climb rate
                additional_distance = dist_from_center - first_waypoint_distance
                if additional_distance < 0:
                    additional_distance = 0
                agl_increment = additional_distance * 0.20  # ShapeLab optimized rate
                desired_agl = min_height + agl_increment
                
                # Track maximum for inbound ascent calculations
                if desired_agl > max_outbound_altitude:
                    max_outbound_altitude = desired_agl
                    max_outbound_distance = dist_from_center
            elif 'inbound' in phase:
                # INBOUND: Continued climb with 0.1ft per foot ascent rate
                distance_from_max = max_outbound_distance - dist_from_center
                if distance_from_max < 0:
                    distance_from_max = 0
                altitude_increase = distance_from_max * 0.1  # Gentle continued ascent
                desired_agl = max_outbound_altitude + altitude_increase
                
                # Safety floor: never below min_height
                if desired_agl < min_height:
                    desired_agl = min_height
            else:
                # Fallback for unknown phases
                additional_distance = dist_from_center - first_waypoint_distance
                if additional_distance < 0:
                    additional_distance = 0
                agl_increment = additional_distance * 0.20
                desired_agl = min_height + agl_increment
            
            # Calculate final MSL altitude (terrain following)
            final_altitude = local_ground_offset + desired_agl
            
            # Apply maximum height constraint if specified
            if max_height is not None:
                adjusted_max_height = max_height - takeoff_elevation_feet
                current_agl = final_altitude - ground_elevation
                if current_agl > adjusted_max_height:
                    final_altitude = ground_elevation + adjusted_max_height
            
            altitude = round(final_altitude * 100) / 100
            
            # Calculate forward-looking heading using atan2
            heading = 0
            if i < len(spiral_path) - 1:
                next_wp = spiral_path[i + 1]
                dx = next_wp['x'] - wp['x']
                dy = next_wp['y'] - wp['y']
                heading = round(((math.atan2(dx, dy) * 180 / math.pi) + 360) % 360)
            
            # Convert curve radius from feet to meters
            curve_size_meters = round((wp['curve'] * self.FT2M) * 100) / 100
            
            # Calculate sinusoidal gimbal pitch for varied photo angles
            progress = i / (len(spiral_path) - 1) if len(spiral_path) > 1 else 0
            gimbal_pitch = round(-35 + 14 * math.sin(progress * math.pi))
            
            # Calculate photo interval timing
            # Start photos at first waypoint, continue throughout flight, stop at last waypoint
            if i == 0:
                photo_interval = 3.0  # Start taking photos at 3-second intervals
            elif i == len(spiral_path) - 1:
                photo_interval = 0    # Stop taking photos at the last waypoint
            else:
                photo_interval = 3.0  # Continue 3-second intervals throughout flight
            
            # Create CSV row (identical format to generate_csv)
            row = [
                latitude,                   # GPS latitude
                longitude,                  # GPS longitude  
                altitude,                   # Flight altitude (MSL feet)
                heading,                    # Forward direction (degrees)
                curve_size_meters,          # Turn radius (meters)
                0,                          # Rotation direction (none)
                2,                          # Gimbal mode (focus POI)
                gimbal_pitch,               # Camera tilt angle 
                0,                          # Altitude mode (AGL)
                8.85,                       # Speed (19.8 mph = 8.85 m/s)
                center['lat'],              # POI latitude (spiral center)
                center['lon'],              # POI longitude (spiral center)
                -35,                        # POI altitude (-35ft AGL)
                0,                          # POI altitude mode (AGL)
                photo_interval,             # Photo interval (3s start/middle, 0s stop)
                0                           # Photo distance interval (disabled)
            ]
            
            rows.append(','.join(map(str, row)))
        
        return '\n'.join(rows)

    def estimate_flight_time_minutes(self, params: Dict, center_lat: float, center_lon: float) -> float:
        """
        ACCURATE flight time estimation based on actual spiral path length.
        
        APPROACH:
        - Calculate actual spiral path length using mathematical integration
        - Account for all phases: outbound spiral, hold pattern, inbound spiral
        - Use realistic drone speed (25 mph) and acceleration/deceleration
        - Add overhead for takeoff, landing, photos, hover time
        
        Args:
            params: Spiral parameters dict {slices, N, r0, rHold}
            center_lat: Center latitude for distance calculations  
            center_lon: Center longitude for distance calculations
            
        Returns:
            Estimated flight time in minutes
        """
        # Get spiral parameters
        N = params['N']  # Number of bounces
        r0 = params['r0']  # Starting radius
        r_hold = params['rHold']  # Target hold radius
        slices = params['slices']  # Number of slices
        
        # Calculate spiral parameters
        dphi = 2 * math.pi / slices  # Angular step per bounce
        base_alpha = math.log(r_hold / r0) / (N * dphi)
        
        # Progressive alpha factors (same as in make_spiral)
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
        
        # Time parameters
        t_out = N * dphi  # Time to complete outward spiral
        t_hold = dphi  # Time for hold pattern
        t_transition = t_out * 0.4  # Progressive alpha transition point
        
        # Calculate actual spiral path length using mathematical integration
        # For exponential spiral r(t) = r0 * exp(alpha * t), the arc length is:
        # L = ∫√(r² + (dr/dt)²) dt = ∫√(r² + (alpha * r)²) dt = ∫r * √(1 + alpha²) dt
        
        # Outbound spiral path length (with progressive alpha)
        # Early phase: r(t) = r0 * exp(alpha_early * t) for t <= t_transition
        # Late phase: r(t) = r_transition * exp(alpha_late * (t - t_transition)) for t > t_transition
        
        r_transition = r0 * math.exp(alpha_early * t_transition)
        
        # Early phase length
        early_length_factor = math.sqrt(1 + alpha_early**2)
        early_length = (r_transition - r0) / alpha_early * early_length_factor
        
        # Late phase length
        actual_max_radius = r_transition * math.exp(alpha_late * (t_out - t_transition))
        late_length_factor = math.sqrt(1 + alpha_late**2)
        late_length = (actual_max_radius - r_transition) / alpha_late * late_length_factor
        
        # Hold pattern length (circular arc)
        hold_length = actual_max_radius * t_hold
        
        # Inbound spiral length (using late alpha for consistency)
        inbound_length = (actual_max_radius - r0) / alpha_late * late_length_factor
        
        # Total spiral path length
        total_spiral_length_ft = early_length + late_length + hold_length + inbound_length
        
        # Convert to miles and calculate flight time
        total_distance_miles = total_spiral_length_ft / 5280
        flight_speed_mph = 25  # Realistic drone speed
        
        # Base flight time
        flight_time_hours = total_distance_miles / flight_speed_mph
        flight_time_minutes = flight_time_hours * 60
        
        # Add overhead for takeoff, landing, photos, hover time, acceleration/deceleration
        overhead_minutes = 1.5  # Reduced from 2.0 since we're more accurate now
        
        return flight_time_minutes + overhead_minutes

    def optimize_spiral_for_battery(self, target_battery_minutes: float, num_batteries: int, center_lat: float, center_lon: float) -> Dict:
        """
        Battery-optimized spiral generation using intelligent balanced scaling algorithm.
        
        OPTIMIZATION STRATEGY:
        =====================
        
        BALANCED SCALING APPROACH:
        1. Scale bounce count with battery duration first (quality optimization)
        2. Binary search on radius with fixed bounce count (coverage optimization)
        3. Bonus bounce addition if significant headroom available
        
        BOUNCE COUNT SCALING LOGIC:
        - 10-12 min → 5 bounces (minimal pattern for short flights)
        - 13-18 min → 6 bounces (balanced for medium flights)
        - 19-25 min → 8 bounces (optimal quality/coverage balance)
        - 26-35 min → 10 bounces (comprehensive coverage)
        - 36+ min → 12 bounces (maximum detail capture)
        
        BINARY SEARCH OPTIMIZATION:
        - O(log n) computational complexity vs O(n) brute force
        - 98% battery utilization safety margin
        - 10ft radius tolerance for practical purposes
        - Maximum 20 iterations for performance
        
        BONUS BOUNCE LOGIC:
        If battery utilization < 85%, attempt to add one more bounce
        for enhanced coverage without safety risk.
        
        ERROR HANDLING:
        - Graceful degradation for impossible constraints
        - Automatic bounce reduction if minimum spiral too large
        - Fallback to safe parameters on optimization failure
        
        Args:
            target_battery_minutes: Target flight duration in minutes
            num_batteries: Number of battery slices to generate
            center_lat: Center latitude for flight time calculations
            center_lon: Center longitude for flight time calculations
            
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
        # Define parameter constraints for safety and practicality
        min_r0, max_r0 = 50.0, 500.0       # Start radius range (feet)
        min_rHold, max_rHold = 200.0, 50000.0  # Hold radius range (feet) - RESTORED ORIGINAL
        min_N, max_N = 3, 15               # Bounce count range - RESTORED ORIGINAL
        
        # PROGRESSIVE BOUNCE SCALING: Longer flights = more bounces for better coverage
        if target_battery_minutes <= 12:
            target_bounces = 7   # Minimal for short flights
        elif target_battery_minutes <= 18:
            target_bounces = 8   # Good coverage for medium flights
        elif target_battery_minutes <= 25:
            target_bounces = 9   # Better coverage for longer flights
        elif target_battery_minutes <= 35:
            target_bounces = 10  # Comprehensive coverage
        elif target_battery_minutes <= 45:
            target_bounces = 12  # Maximum coverage
        else:
            target_bounces = 15  # Maximum for very long duration flights
        
        # Clamp to valid range for safety
        target_bounces = max(min_N, min(max_N, target_bounces))
        
        # Initialize base parameters with scaled bounce count
        base_params = {
            'slices': num_batteries,
            'N': target_bounces,
            'r0': 200.0  # Original start radius for proper expansion scaling
        }
        
        print(f"Optimizing for {target_battery_minutes}min battery: targeting {target_bounces} bounces")
        
        # Feasibility check: Test if minimum parameters can fit
        test_params = base_params.copy()
        test_params['rHold'] = min_rHold
        
        try:
            min_time = self.estimate_flight_time_minutes(test_params, center_lat, center_lon)
            if min_time > target_battery_minutes:
                # Minimum spiral too large - reduce bounces and retry
                reduced_bounces = max(min_N, target_bounces - 2)
                print(f"Minimum spiral too large, reducing bounces from {target_bounces} to {reduced_bounces}")
                base_params['N'] = reduced_bounces
                target_bounces = reduced_bounces
                
                test_params = base_params.copy()
                test_params['rHold'] = min_rHold
                min_time = self.estimate_flight_time_minutes(test_params, center_lat, center_lon)
                
                if min_time > target_battery_minutes:
                    # Still too large - return absolute minimum configuration
                    return {
                        'slices': num_batteries,
                        'N': min_N,
                        'r0': 100.0,
                        'rHold': min_rHold,
                        'estimated_time_minutes': min_time,
                        'battery_utilization': round((min_time / target_battery_minutes) * 100, 1)
                    }
        except Exception as e:
            print(f"Error testing minimum parameters: {e}")
        
        # BINARY SEARCH: Optimize hold radius with fixed bounce count
        best_params = None
        best_time = 0.0
        
        low, high = min_rHold, max_rHold
        tolerance = 25.0        # 25ft tolerance for large-scale optimization
        max_iterations = 30     # Increased iterations for large radius ranges
        iterations = 0
        
        while high - low > tolerance and iterations < max_iterations:
            iterations += 1
            mid_rHold = (low + high) / 2
            
            # Test current radius with FIXED bounce count
            test_params = base_params.copy()
            test_params['rHold'] = mid_rHold
            
            try:
                estimated_time = self.estimate_flight_time_minutes(test_params, center_lat, center_lon)
                
                # Apply 2% safety margin (98% utilization maximum) - RESTORED ORIGINAL
                if estimated_time <= target_battery_minutes * 0.98:
                    # Configuration fits safely - try larger radius
                    best_params = test_params.copy()
                    best_time = estimated_time
                    low = mid_rHold
                else:
                    # Too large - try smaller radius
                    high = mid_rHold
                    
            except Exception as e:
                print(f"Error estimating time for rHold={mid_rHold}: {e}")
                high = mid_rHold  # Assume failure means too large
        
        # BONUS BOUNCE: Attempt to add one more bounce if significant headroom
        if best_params and best_time < target_battery_minutes * 0.85 and target_bounces < max_N:
            test_params = best_params.copy()
            test_params['N'] = target_bounces + 1
            
            try:
                estimated_time = self.estimate_flight_time_minutes(test_params, center_lat, center_lon)
                if estimated_time <= target_battery_minutes * 0.98:
                    print(f"Adding bonus bounce: {target_bounces} → {target_bounces + 1}")
                    best_params = test_params.copy()
                    best_time = estimated_time
            except:
                pass  # Keep original if bonus bounce fails
        
        # Final safety check: Ensure we have valid parameters
        if not best_params:
            best_params = {
                'slices': num_batteries,
                'N': target_bounces,
                'r0': 150.0,
                'rHold': min_rHold
            }
            try:
                best_time = self.estimate_flight_time_minutes(best_params, center_lat, center_lon)
            except:
                best_time = target_battery_minutes * 1.2  # Conservative estimate
        
        # Add performance metrics to results
        best_params['estimated_time_minutes'] = round(best_time, 2)
        best_params['battery_utilization'] = round((best_time / target_battery_minutes) * 100, 1)
        
        print(f"Final optimization: {best_params['N']} bounces, {best_params['rHold']:.0f}ft radius, {best_time:.1f}min ({best_params['battery_utilization']}%)")
        
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
    
    def adaptive_terrain_sampling(self, waypoints_with_coords: List[Dict], *, min_agl_ft: Optional[float] = None, max_agl_ft: Optional[float] = None, point_budget: Optional[int] = None) -> List[Dict]:
        """Proxy to the v2 terrain sampler for backwards compatibility."""
        provider = DesignerElevationProvider(self)
        cfg = build_sampler_config_from_env()
        constraints = AglConstraints(min_agl_ft=min_agl_ft, max_agl_ft=max_agl_ft)
        budget = point_budget or int(os.getenv('TERRAIN_SAMPLER_POINT_BUDGET', '90'))
        result = two_pass_adaptive_sampling(waypoints_with_coords, provider, cfg, constraints, budget)
        self._last_sampling_metrics = result.metrics
        self._last_sampling_hazards = result.hazards
        return result.safety_waypoints

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

        spacing_ft = _env_float('MIN_SAFETY_WAYPOINT_SPACING', 50.0)
        deduped: List[Dict[str, Any]] = []
        for candidate in sorted(safety_waypoints, key=lambda x: x.get('distance_from_start', 0.0)):
            too_close = any(
                self.haversine_distance(candidate['lat'], candidate['lon'], existing['lat'], existing['lon']) * FT_PER_METER < spacing_ft
                for existing in deduped
            )
            if too_close:
                continue
            if 'agl_target_ft' in candidate:
                candidate['altitude'] = candidate['elevation'] + candidate['agl_target_ft']
            deduped.append(candidate)

        safety_waypoints = deduped

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

def handle_optimize_spiral(designer, body, cors_headers):
    """Handle /api/optimize-spiral endpoint"""
    try:
        battery_minutes = float(body.get('batteryMinutes', 20))
        batteries = int(body.get('batteries', 3))
        center = body.get('center', '')
        
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
            battery_minutes, batteries, center_coords['lat'], center_coords['lon']
        )
        
        return {
            'statusCode': 200,
            'headers': cors_headers,
            'body': json.dumps({
                'optimized_params': optimized_params,
                'optimization_info': {
                    'algorithm': 'Intelligent Balanced Scaling with Binary Search',
                    'pattern_type': 'Exponential Spiral with Neural Network Optimization',
                    'bounce_scaling_reason': f"Battery duration {battery_minutes}min → {optimized_params['N']} bounces",
                    'safety_margin': '98% battery utilization maximum'
                }
            })
        }
        
    except Exception as e:
        return {
            'statusCode': 500,
            'headers': cors_headers,
            'body': json.dumps({'error': f'Optimization failed: {str(e)}'})
        }

def handle_elevation(designer, body, cors_headers):
    """Handle /api/elevation endpoint"""
    try:
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
        
    except Exception as e:
        return {
            'statusCode': 500,
            'headers': cors_headers,
            'body': json.dumps({'error': f'Elevation lookup failed: {str(e)}'})
        }

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
        
        # Generate CSV content
        csv_content = designer.generate_csv(params, center, min_height, max_height)
        
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
        
        # Extract parameters from body with type conversion
        slices = int(body.get('slices', 3))
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
        
        # Generate battery-specific CSV content
        csv_content = designer.generate_battery_csv(params, center, battery_index, min_height, max_height)
        
        # Return CSV as text/csv
        return {
            'statusCode': 200,
            'headers': {
                **cors_headers,
                'Content-Type': 'text/csv',
                'Content-Disposition': f'attachment; filename="battery-{battery_id}.csv"'
            },
            'body': csv_content
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


@dataclass
class SamplerConfig:
    discovery_interval_ft: float
    dense_interval_ft: float
    medium_interval_ft: float
    sparse_interval_ft: float
    grad_medium_ft_per_100: float
    grad_high_ft_per_100: float
    grad_critical_ft_per_100: float
    discovery_fraction: float
    refinement_fraction: float
    min_safety_spacing_ft: float
    safety_buffer_ft: float


@dataclass
class AglConstraints:
    min_agl_ft: Optional[float] = None
    max_agl_ft: Optional[float] = None


@dataclass
class SampledPoint:
    lat: float
    lon: float
    distance_ft: float
    elevation_ft: float
    phase: Optional[str] = None
    source: str = "discovery"
    gradient_ft_per_100: float = 0.0
    curvature_ft_per_100: float = 0.0
    segment_index: int = 0


@dataclass(order=True)
class SegmentRisk:
    priority: float
    segment_index: int
    start_distance_ft: float
    end_distance_ft: float
    max_gradient: float
    max_curvature: float


@dataclass
class Hazard:
    lat: float
    lon: float
    distance_ft: float
    ground_ft: float
    severity: float
    gradient_ft_per_100: float
    curvature_ft_per_100: float
    segment_index: int
    description: str


@dataclass
class TerrainSamplingResult:
    discovery_points: List[SampledPoint] = field(default_factory=list)
    refinement_points: List[SampledPoint] = field(default_factory=list)
    hazards: List[Hazard] = field(default_factory=list)
    safety_waypoints: List[Dict[str, Any]] = field(default_factory=list)
    metrics: Dict[str, Any] = field(default_factory=dict)


def _env_float(name: str, default: float) -> float:
    value = os.getenv(name)
    if value is None:
        return default
    try:
        return float(value)
    except ValueError:
        return default


def _env_int(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None:
        return default
    try:
        return int(value)
    except ValueError:
        return default


def build_sampler_config_from_env() -> SamplerConfig:
    discovery_interval = _env_float('SPARSE_DISCOVERY_INTERVAL', 360.0)
    dense_interval = _env_float('DENSE', 30.0)
    medium_interval = _env_float('MEDIUM', 100.0)
    sparse_interval = _env_float('SPARSE', 260.0)
    grad_medium = _env_float('GRADIENT_MEDIUM', 10.0)
    grad_high = _env_float('GRADIENT_HIGH', 20.0)
    grad_critical = _env_float('GRADIENT_CRITICAL', 40.0)
    discovery_fraction = _env_float('TERRAIN_DISCOVERY_FRACTION', 0.25)
    discovery_fraction = max(0.05, min(discovery_fraction, 0.9))
    refinement_fraction = max(0.0, min(1.0, 1.0 - discovery_fraction))
    min_spacing = _env_float('MIN_SAFETY_WAYPOINT_SPACING', 50.0)
    safety_buffer = _env_float('TERRAIN_SAFETY_BUFFER_FT', 100.0)
    return SamplerConfig(
        discovery_interval_ft=discovery_interval,
        dense_interval_ft=dense_interval,
        medium_interval_ft=medium_interval,
        sparse_interval_ft=sparse_interval,
        grad_medium_ft_per_100=grad_medium,
        grad_high_ft_per_100=grad_high,
        grad_critical_ft_per_100=grad_critical,
        discovery_fraction=discovery_fraction,
        refinement_fraction=refinement_fraction,
        min_safety_spacing_ft=min_spacing,
        safety_buffer_ft=safety_buffer,
    )


def haversine_ft(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    radius_m = 6371000.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2) ** 2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return radius_m * c * FT_PER_METER


def compute_path_distances(path_ll: List[Dict[str, Any]]) -> List[float]:
    if not path_ll:
        return [0.0]
    distances = [0.0]
    for idx in range(1, len(path_ll)):
        prev = path_ll[idx - 1]
        curr = path_ll[idx]
        seg = haversine_ft(prev['lat'], prev['lon'], curr['lat'], curr['lon'])
        distances.append(distances[-1] + seg)
    return distances


def interpolate_along_path(path_ll: List[Dict[str, Any]], distances: List[float], target_distance: float) -> Tuple[float, float, int, float]:
    if not path_ll:
        raise ValueError('Path cannot be empty')
    if target_distance <= 0:
        return path_ll[0]['lat'], path_ll[0]['lon'], 0, 0.0
    if target_distance >= distances[-1]:
        return path_ll[-1]['lat'], path_ll[-1]['lon'], len(path_ll) - 2, 1.0
    for idx in range(1, len(distances)):
        if target_distance <= distances[idx]:
            start_distance = distances[idx - 1]
            seg_length = max(distances[idx] - start_distance, 1e-6)
            fraction = (target_distance - start_distance) / seg_length
            start = path_ll[idx - 1]
            end = path_ll[idx]
            lat = start['lat'] + fraction * (end['lat'] - start['lat'])
            lon = start['lon'] + fraction * (end['lon'] - start['lon'])
            return lat, lon, idx - 1, fraction
    last = path_ll[-1]
    return last['lat'], last['lon'], len(path_ll) - 2, 1.0


def _batched(points: List[LatLon], size: int) -> List[List[LatLon]]:
    return [points[i:i + size] for i in range(0, len(points), size)]


def _smooth_series(values: List[float], window: int = 5) -> List[float]:
    if len(values) < 3:
        return values[:]
    if window % 2 == 0:
        window += 1
    window = max(3, window)
    radius = window // 2
    smoothed: List[float] = []
    for idx in range(len(values)):
        start = max(0, idx - radius)
        end = min(len(values), idx + radius + 1)
        window_vals = values[start:end]
        median_val = sorted(window_vals)[len(window_vals) // 2]
        mean_val = sum(window_vals) / len(window_vals)
        smoothed.append((median_val + mean_val) / 2.0)
    return smoothed


def sparse_discovery_scan(path_ll: List[Dict[str, Any]], provider: ElevationProvider, cfg: SamplerConfig, budget_points: int) -> Tuple[List[SampledPoint], int]:
    if len(path_ll) < 2 or budget_points <= 0:
        return [], 0
    distances = compute_path_distances(path_ll)
    total_length = distances[-1]
    if total_length <= 0:
        return [], 0
    interval = max(cfg.discovery_interval_ft, total_length / max(budget_points - 1, 1))
    targets = [0.0]
    current = interval
    while current < total_length and len(targets) < budget_points - 1:
        targets.append(current)
        current += interval
    if targets[-1] != total_length:
        targets.append(total_length)
    latlons: List[LatLon] = []
    samples: List[SampledPoint] = []
    for target in targets:
        lat, lon, segment_index, _ = interpolate_along_path(path_ll, distances, target)
        phase = path_ll[segment_index].get('phase') if 0 <= segment_index < len(path_ll) else None
        samples.append(SampledPoint(lat=lat, lon=lon, distance_ft=target, elevation_ft=0.0, phase=phase, source='discovery', segment_index=segment_index))
        latlons.append((lat, lon))
    batch_size = max(1, provider.max_batch_size())
    points_used = 0
    sample_idx = 0
    for chunk in _batched(latlons, batch_size):
        elevations_m = provider.sample(chunk)
        points_used += len(elevations_m)
        for elevation_m in elevations_m:
            samples[sample_idx].elevation_ft = elevation_m * FT_PER_METER
            sample_idx += 1
    return samples, points_used


def calculate_elevation_gradient(amls_ft: List[float], distances_ft: List[float], window_ft: float) -> List[float]:
    gradients: List[float] = []
    window_ft = max(window_ft, 1.0)
    for idx in range(len(amls_ft)):
        left = idx
        while left > 0 and distances_ft[idx] - distances_ft[left] < window_ft:
            left -= 1
        right = idx
        while right < len(amls_ft) - 1 and distances_ft[right] - distances_ft[idx] < window_ft:
            right += 1
        if left == idx or right == idx:
            gradients.append(0.0)
            continue
        rise = amls_ft[right] - amls_ft[left]
        run = max(distances_ft[right] - distances_ft[left], 1.0)
        gradients.append((rise / run) * 100.0)
    return gradients


def calculate_terrain_curvature(amls_ft: List[float], distances_ft: List[float], window_ft: float) -> List[float]:
    gradients = calculate_elevation_gradient(amls_ft, distances_ft, max(window_ft / 2.0, 1.0))
    curvatures: List[float] = []
    for idx in range(len(gradients)):
        if idx == 0 or idx == len(gradients) - 1:
            curvatures.append(0.0)
            continue
        delta_distance = max(distances_ft[idx + 1] - distances_ft[idx - 1], 1.0)
        curvature = (gradients[idx + 1] - gradients[idx - 1]) / delta_distance * 100.0
        curvatures.append(curvature)
    return curvatures


def rank_segments_by_risk(samples: List[SampledPoint]) -> List[SegmentRisk]:
    queue: List[SegmentRisk] = []
    for idx in range(len(samples) - 1):
        grad = max(abs(samples[idx].gradient_ft_per_100), abs(samples[idx + 1].gradient_ft_per_100))
        curv = max(abs(samples[idx].curvature_ft_per_100), abs(samples[idx + 1].curvature_ft_per_100))
        segment_length = samples[idx + 1].distance_ft - samples[idx].distance_ft
        if segment_length <= 0:
            continue
        severity = grad * 0.7 + curv * 0.3
        if severity <= 0:
            continue
        heapq.heappush(queue, SegmentRisk(
            priority=-severity,
            segment_index=idx,
            start_distance_ft=samples[idx].distance_ft,
            end_distance_ft=samples[idx + 1].distance_ft,
            max_gradient=grad,
            max_curvature=curv,
        ))
    return queue


def choose_interval(max_gradient: float, cfg: SamplerConfig) -> float:
    if max_gradient >= cfg.grad_critical_ft_per_100:
        return cfg.dense_interval_ft
    if max_gradient >= cfg.grad_high_ft_per_100:
        return cfg.medium_interval_ft
    if max_gradient >= cfg.grad_medium_ft_per_100:
        return cfg.sparse_interval_ft
    return cfg.discovery_interval_ft * 1.5


def detect_peak_elevation(segment: SegmentRisk, path_ll: List[Dict[str, Any]], distances: List[float], provider: ElevationProvider, budget_left: int) -> Tuple[Optional[SampledPoint], int]:
    if budget_left <= 0:
        return None, 0
    left = segment.start_distance_ft
    right = segment.end_distance_ft
    best_sample: Optional[SampledPoint] = None
    points_used = 0
    iterations = min(4, max(1, budget_left // 2))
    for _ in range(iterations):
        if budget_left - points_used < 2:
            break
        l_mid = left + (right - left) / 3.0
        r_mid = right - (right - left) / 3.0
        coords = [interpolate_along_path(path_ll, distances, l_mid), interpolate_along_path(path_ll, distances, r_mid)]
        latlons = [(coords[0][0], coords[0][1]), (coords[1][0], coords[1][1])]
        elevations_m = provider.sample(latlons)
        points_used += len(elevations_m)
        samples = []
        for (lat, lon, segment_index, _), elevation_m in zip(coords, elevations_m):
            phase = path_ll[segment_index].get('phase') if 0 <= segment_index < len(path_ll) else None
            samples.append(SampledPoint(
                lat=lat,
                lon=lon,
                distance_ft=l_mid if len(samples) == 0 else r_mid,
                elevation_ft=elevation_m * FT_PER_METER,
                phase=phase,
                source='refinement',
                gradient_ft_per_100=segment.max_gradient,
                curvature_ft_per_100=segment.max_curvature,
                segment_index=segment.segment_index,
            ))
        if not samples:
            break
        left_sample, right_sample = samples
        if best_sample is None or left_sample.elevation_ft > best_sample.elevation_ft:
            best_sample = left_sample
        if right_sample.elevation_ft > (best_sample.elevation_ft if best_sample else -float('inf')):
            best_sample = right_sample
        if left_sample.elevation_ft > right_sample.elevation_ft:
            right = r_mid
        else:
            left = l_mid
    return best_sample, points_used


def adaptive_refinement_sampling(
    segment_queue: List[SegmentRisk],
    path_ll: List[Dict[str, Any]],
    distances: List[float],
    provider: ElevationProvider,
    cfg: SamplerConfig,
    budget_points: int,
) -> Tuple[List[SampledPoint], List[Hazard], int, Dict[str, Any]]:
    refined_samples: List[SampledPoint] = []
    hazards: List[Hazard] = []
    points_used = 0
    segments_considered = 0
    while segment_queue and points_used < budget_points:
        segment = heapq.heappop(segment_queue)
        severity = -segment.priority
        segment_length = max(segment.end_distance_ft - segment.start_distance_ft, 1.0)
        segments_considered += 1
        budget_left = budget_points - points_used
        if segment.max_gradient >= cfg.grad_critical_ft_per_100:
            peak_sample, used = detect_peak_elevation(segment, path_ll, distances, provider, budget_left)
            points_used += used
            if peak_sample:
                refined_samples.append(peak_sample)
                hazards.append(Hazard(
                    lat=peak_sample.lat,
                    lon=peak_sample.lon,
                    distance_ft=peak_sample.distance_ft,
                    ground_ft=peak_sample.elevation_ft,
                    severity=severity,
                    gradient_ft_per_100=segment.max_gradient,
                    curvature_ft_per_100=segment.max_curvature,
                    segment_index=segment.segment_index,
                    description='Critical gradient peak located via ternary search',
                ))
            continue
        interval = choose_interval(segment.max_gradient, cfg)
        targets: List[float] = []
        current = segment.start_distance_ft + interval
        while current < segment.end_distance_ft and len(targets) < budget_left:
            targets.append(current)
            current += interval
        if not targets:
            # Ensure at least one midpoint sample when budget allows
            midpoint = segment.start_distance_ft + segment_length / 2.0
            if budget_left > 0:
                targets.append(midpoint)
        if not targets:
            continue
        latlons: List[LatLon] = []
        samples: List[SampledPoint] = []
        for target in targets[:budget_left]:
            lat, lon, segment_index, _ = interpolate_along_path(path_ll, distances, target)
            phase = path_ll[segment_index].get('phase') if 0 <= segment_index < len(path_ll) else None
            samples.append(SampledPoint(
                lat=lat,
                lon=lon,
                distance_ft=target,
                elevation_ft=0.0,
                phase=phase,
                source='refinement',
                gradient_ft_per_100=segment.max_gradient,
                curvature_ft_per_100=segment.max_curvature,
                segment_index=segment_index,
            ))
            latlons.append((lat, lon))
        batch_size = max(1, provider.max_batch_size())
        sample_idx = 0
        for chunk in _batched(latlons, batch_size):
            elevations_m = provider.sample(chunk)
            points_used += len(elevations_m)
            for elevation_m in elevations_m:
                samples[sample_idx].elevation_ft = elevation_m * FT_PER_METER
                sample_idx += 1
            if points_used >= budget_points:
                break
        refined_samples.extend(samples[:sample_idx])
        if samples:
            hazard_source = max(samples[:sample_idx], key=lambda s: s.elevation_ft, default=None)
            if hazard_source:
                hazards.append(Hazard(
                    lat=hazard_source.lat,
                    lon=hazard_source.lon,
                    distance_ft=hazard_source.distance_ft,
                    ground_ft=hazard_source.elevation_ft,
                    severity=severity,
                    gradient_ft_per_100=segment.max_gradient,
                    curvature_ft_per_100=segment.max_curvature,
                    segment_index=segment.segment_index,
                    description='High-risk terrain refinement sample',
                ))
    metrics = {
        'segments_considered': segments_considered,
    }
    return refined_samples, hazards, points_used, metrics


def _hazards_from_discovery(samples: List[SampledPoint], cfg: SamplerConfig) -> List[Hazard]:
    hazards: List[Hazard] = []
    for sample in samples:
        severity = max(0.0, abs(sample.gradient_ft_per_100) - cfg.grad_medium_ft_per_100)
        if severity <= 0 and abs(sample.curvature_ft_per_100) <= cfg.grad_medium_ft_per_100:
            continue
        hazards.append(Hazard(
            lat=sample.lat,
            lon=sample.lon,
            distance_ft=sample.distance_ft,
            ground_ft=sample.elevation_ft,
            severity=max(severity, abs(sample.curvature_ft_per_100)),
            gradient_ft_per_100=sample.gradient_ft_per_100,
            curvature_ft_per_100=sample.curvature_ft_per_100,
            segment_index=sample.segment_index,
            description='Discovery gradient alert',
        ))
    return hazards


def generate_terrain_feature_waypoints(hazards: List[Hazard], agl: AglConstraints, cfg: SamplerConfig) -> List[Dict[str, Any]]:
    if not hazards:
        return []
    min_agl = agl.min_agl_ft if agl.min_agl_ft is not None else 120.0
    safety_waypoints: List[Dict[str, Any]] = []
    accepted: List[Hazard] = []
    sorted_hazards = sorted(hazards, key=lambda h: h.severity, reverse=True)
    for hazard in sorted_hazards:
        too_close = any(
            haversine_ft(hazard.lat, hazard.lon, existing.lat, existing.lon) < cfg.min_safety_spacing_ft
            for existing in accepted
        )
        if too_close:
            continue
        target_agl = max(min_agl, cfg.safety_buffer_ft)
        altitude = hazard.ground_ft + target_agl
        if agl.max_agl_ft is not None:
            altitude = min(altitude, hazard.ground_ft + agl.max_agl_ft)
            target_agl = altitude - hazard.ground_ft
        safety_waypoints.append({
            'lat': hazard.lat,
            'lon': hazard.lon,
            'altitude': altitude,
            'elevation': hazard.ground_ft,
            'reason': hazard.description,
            'segment_idx': hazard.segment_index,
            'type': 'terrain_safety',
            'distance_from_start': hazard.distance_ft,
            'severity': hazard.severity,
            'agl_target_ft': target_agl,
        })
        accepted.append(hazard)
    return safety_waypoints


def two_pass_adaptive_sampling(
    path_ll: List[Dict[str, Any]],
    provider: ElevationProvider,
    cfg: SamplerConfig,
    agl: AglConstraints,
    point_budget: int,
) -> TerrainSamplingResult:
    if len(path_ll) < 2 or point_budget <= 0:
        return TerrainSamplingResult()
    discovery_budget = max(2, int(point_budget * cfg.discovery_fraction))
    discovery_samples, discovery_used = sparse_discovery_scan(path_ll, provider, cfg, discovery_budget)
    if not discovery_samples:
        return TerrainSamplingResult()
    distances = [sample.distance_ft for sample in discovery_samples]
    elevations = [sample.elevation_ft for sample in discovery_samples]
    smooth_window = max(3, int(cfg.discovery_interval_ft // 50) | 1)
    smoothed = _smooth_series(elevations, smooth_window)
    gradients = calculate_elevation_gradient(smoothed, distances, max(cfg.discovery_interval_ft * 2.0, 100.0))
    curvatures = calculate_terrain_curvature(smoothed, distances, max(cfg.discovery_interval_ft * 3.0, 150.0))
    for sample, grad, curv in zip(discovery_samples, gradients, curvatures):
        sample.gradient_ft_per_100 = grad
        sample.curvature_ft_per_100 = curv
    segment_queue = rank_segments_by_risk(discovery_samples)
    refinement_budget = max(0, point_budget - discovery_used)
    distances_exact = compute_path_distances(path_ll)
    refinement_samples, refinement_hazards, refinement_used, refinement_metrics = adaptive_refinement_sampling(
        segment_queue,
        path_ll,
        distances_exact,
        provider,
        cfg,
        refinement_budget,
    )
    hazards = _hazards_from_discovery(discovery_samples, cfg) + refinement_hazards
    safety_waypoints = generate_terrain_feature_waypoints(hazards, agl, cfg)
    metrics = {
        'discovery_points_used': discovery_used,
        'refinement_points_used': refinement_used,
        'total_points_used': discovery_used + refinement_used,
        'hazards_detected': len(hazards),
        'safety_waypoints': len(safety_waypoints),
    }
    metrics.update(refinement_metrics)
    print(
        f"Terrain sampler v2 → discovery: {discovery_used} pts, refinement: {refinement_used} pts, hazards: {len(hazards)}, safety waypoints: {len(safety_waypoints)}"
    )
    return TerrainSamplingResult(
        discovery_points=discovery_samples,
        refinement_points=refinement_samples,
        hazards=hazards,
        safety_waypoints=safety_waypoints,
        metrics=metrics,
    )


class DesignerElevationProvider(ElevationProvider):
    def __init__(self, designer: 'SpiralDesigner') -> None:
        self.designer = designer

    def sample(self, points: List[LatLon]) -> List[float]:
        if not points:
            return []
        elevations_ft = self.designer.get_elevations_feet_optimized(points)
        return [elevation * M_PER_FT for elevation in elevations_ft]

    def max_batch_size(self) -> int:
        return getattr(self.designer, 'MAX_API_CALLS_PER_REQUEST', 25)


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
