import json
import os
import math
import sys

# Add the package directory to the Python path
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), "package"))

# Now we can import requests
import requests

API_KEY = os.environ.get("GOOGLE_MAPS_API_KEY", "")  # set in Lambda environment

def lambda_handler(event, context):
    """
    AWS Lambda entry point.
    Expects a JSON payload in event['body'] with the user input fields.
    Handles OPTIONS requests for CORS.
    """
    logs = []  # Initialize a list to hold log entries

    def log(title, msg):
        logs.append({"title": title, "msg": msg})

    log("Lambda Handler Start", "Received event. Attempting to parse event body.")
    log("Event Debug", f"Event keys: {list(event.keys())}")

    # Check if the request is an OPTIONS preflight request
    method = event.get('httpMethod', '').upper()
    log("HTTP Method Check", f"Method: {method}")
    if method == 'OPTIONS':
        log("CORS Preflight", "Responding to OPTIONS preflight request.")
        return {
            'statusCode': 200,
            'headers': {
                'Access-Control-Allow-Origin': '*',  # Replace '*' with your frontend domain in production
                'Access-Control-Allow-Headers': 'Content-Type, x-amz-date, authorization, x-api-key, x-amz-security-token',
                'Access-Control-Allow-Methods': 'OPTIONS,POST'  # Include all methods your API supports
            },
            'body': ''
        }

    try:
        # Existing POST logic starts here
        log("Body Presence Check", "Verifying 'body' is in event...")
        if "body" not in event:
            raise ValueError("No body in event.")
        log("Body Presence", "Body found in event.")

        # Ensure the body is parsed correctly into a dictionary
        if isinstance(event["body"], str):
            payload = json.loads(event["body"])
        else:
            payload = event["body"]
        log("Payload Decoded", f"Payload keys: {list(payload.keys())}")

        # ---------------------------------------------------------------------
        # EXTRACT COMMON FIELDS
        # ---------------------------------------------------------------------
        title = payload.get("title", "untitled")
        coordinates = payload.get("coordinates", "")
        takeoff_coordinates = payload.get("takeoffCoordinates", "")
        mode = payload.get("mode", "standard")

        slider_fraction = float(payload.get("sliderFraction", 0))
        min_height = payload.get("minHeight", "")
        max_height = payload.get("maxHeight", "")
        battery_capacity = payload.get("batteryCapacity", "")

        num_loops = payload.get("numLoops", "")
        initial_radius = payload.get("initialRadius", "")
        radius_increment = payload.get("radiusIncrement", "")
        exponential_radius = bool(payload.get("exponentialRadius", False))
        agl_increment = payload.get("aglIncrement", "")
        exponential_agl = bool(payload.get("exponentialAGL", False))
        initial_agl = payload.get("initialAGL", "")
        start_point_altitude = payload.get("startPointAltitude", "")
        poi_altitude = payload.get("poiAltitude", "")
        use_gimbal_tilt_mode = bool(payload.get("useGimbalTiltMode", False))
        poi_rows = payload.get("poiRows", [])

        log("Input Extraction", f"Title: {title}, Coordinates: {coordinates}, Mode: {mode}")
        log("Input Extraction Continued", f"TakeoffCoords: {takeoff_coordinates}, SliderFraction: {slider_fraction}, BatteryCap: {battery_capacity}")

        # ---------------------------------------------------------------------
        # PARSE MAIN PROPERTY COORDINATES & ELEVATION
        # ---------------------------------------------------------------------
        log("Coordinate Parsing", "About to parse main coordinates...")
        lat, lon = parse_coordinates(coordinates)
        log("Parsed Coordinates:", f"Latitude: {lat}, Longitude: {lon}")

        # Elevation for main property
        log("Elevation Fetch", f"Fetching elevation for lat={lat}, lon={lon}")
        elevation_feet = get_elevation_feet(lat, lon)
        elev_msg = f"Elevation at ({lat:.5f}, {lon:.5f}): {elevation_feet:.2f} ft"
        log("Elevation:", elev_msg)

        # ---------------------------------------------------------------------
        # TAKEOFF COORDINATES (OPTIONAL)
        # ---------------------------------------------------------------------
        takeoff_lat = lat
        takeoff_lon = lon
        takeoff_elev_feet = elevation_feet
        if takeoff_coordinates.strip() != "":
            log("Takeoff Parsing", "Takeoff coordinates present, parsing them...")
            t_lat, t_lon = parse_coordinates(takeoff_coordinates)
            t_elev_feet = get_elevation_feet(t_lat, t_lon)
            takeoff_lat = t_lat
            takeoff_lon = t_lon
            takeoff_elev_feet = t_elev_feet
            log("Takeoff:", f"Using separate coords: ({t_lat}, {t_lon}), Elev: {t_elev_feet} ft")
        else:
            log("Takeoff:", "No separate takeoff coords provided, using main coords for takeoff.")

        # ---------------------------------------------------------------------
        # CONVERT USER INPUTS TO NUMERIC WITH DEFAULTS
        # (COMMON TO STANDARD/ADVANCED)
        # ---------------------------------------------------------------------
        log("User Inputs to Numeric", "Parsing numeric/bool inputs (non-Ranch fields).")
        battery_capacity_val = parse_float(battery_capacity, 20.0)  # For Standard/Advanced

        # Decide if Standard or Advanced
        is_standard_mode = (mode == "standard")
        log("Mode Determination", f"is_standard_mode: {is_standard_mode}")

        if is_standard_mode:
            # --- STANDARD logic (unchanged) ---
            loops_float = 5 + (15 - 5)*slider_fraction
            n_loops = round(loops_float)
            init_radius = 150 + (500 - 150)*slider_fraction
            rad_increment = 1.2
            do_exponential_radius = True

            min_h = parse_float(min_height, 100)
            init_agl = min_h
            start_alt = min_h

            do_exponential_agl = False
            a_increment = 25

            max_h_val = parse_float(max_height, None)
            default_poi_alt = 0
            log("Standard Mode Values", f"Loops: {n_loops}, init_radius: {init_radius}, min_height: {min_h}")

        else:
            # --- ADVANCED logic (unchanged) ---
            n_loops = parse_int(num_loops, 3)
            init_radius = parse_float(initial_radius, 200)
            rad_increment = parse_float(radius_increment, 50)
            do_exponential_radius = exponential_radius

            a_increment = parse_float(agl_increment, 20)
            do_exponential_agl = exponential_agl

            init_agl = parse_float(initial_agl, 150)
            start_alt = parse_float(start_point_altitude, 70)
            default_poi_alt = parse_float(poi_altitude, 0)
            max_h_val = parse_float(max_height, None)

            log("Advanced Mode Values", f"n_loops: {n_loops}, init_radius: {init_radius}, rad_increment: {rad_increment}")
            log("Advanced Mode Values2", f"init_agl: {init_agl}, start_alt: {start_alt}, default_poi_alt: {default_poi_alt}")

        # Process POI rows for advanced or standard
        log("POI Processing", "Processing POI rows if advanced (or forcibly standard).")
        poi_list = []
        if not is_standard_mode:
            index = 1
            for row in poi_rows:
                log("POI Row", f"Row {index}: {row}")
                alt_val = parse_float(row.get("altitude", ""), None)
                loop_from = parse_int(row.get("loopFrom", ""), None)
                loop_to = parse_int(row.get("loopTo", ""), None)
                if alt_val is None or loop_from is None or loop_to is None:
                    raise ValueError(f"Invalid POI input for POI {index}.")
                poi_list.append({
                    "altitude": alt_val,
                    "loopFrom": loop_from,
                    "loopTo": loop_to
                })
                log("POI Row Parsed", f"Row {index} => altitude: {alt_val}, loopFrom: {loop_from}, loopTo: {loop_to}")
                index += 1
        else:
            log("POI Processing", "No POI rows used in standard mode.")

        # ---------------------------------------------------------------------
        # ============= RANCH MODE: SINGLE-BATCH ELEVATION ====================
        # ---------------------------------------------------------------------
        if mode == "ranch":
            log("Ranch Mode", "Parsing ranch-specific fields & generating Ranch flight paths.")
            # Ranch fields (defaults)
            min_height_ranch = parse_float(payload.get("minHeightRanch", ""), 100)
            max_height_ranch = parse_float(payload.get("maxHeightRanch", ""), None)
            battery_capacity_ranch = parse_float(payload.get("batteryCapacityRanch", ""), 20.0)
            num_batteries_ranch = parse_int(payload.get("numBatteriesRanch", ""), 4)
            initial_radius_ranch = parse_float(payload.get("initialRadiusRanch", ""), 350.0)

            # Generate ranch segments with single-batch elevation approach
            ranch_segments, total_ranch_time = generate_ranch_flight_segments(
                lat_center=lat,
                lon_center=lon,
                takeoffLat=takeoff_lat,
                takeoffLon=takeoff_lon,
                takeoffElevationFeet=takeoff_elev_feet,
                elevationFeet=elevation_feet,
                numBatteries=num_batteries_ranch,
                initialRadius=initial_radius_ranch,
                minHeight=min_height_ranch,
                maxHeightVal=max_height_ranch,
                batteryCapacity=battery_capacity_ranch,
                flightSpeedMph=19.8,    # same as standard/advanced
                verticalSpeedMps=5,     # same as standard/advanced
                forceGimbalTilt=use_gimbal_tilt_mode or is_standard_mode,
                log=log
            )

            master_waypoints = []
            segments = ranch_segments
            totalFlightTimeMinutes = total_ranch_time

        else:
            # -----------------------------------------------------------------
            # EXISTING STANDARD/ADVANCED LOGIC - UNCHANGED
            # -----------------------------------------------------------------
            log("Flight Path Generation", "Calling generate_master_flight_path for standard/advanced modes.")
            master_waypoints = generate_master_flight_path(
                lat_center=lat,
                lon_center=lon,
                elevFeet=elevation_feet,
                numLoops=n_loops,
                initialRadius=init_radius,
                radiusIncrement=rad_increment,
                initialAGL=init_agl,
                aglIncrement=a_increment,
                exponentialRadius=do_exponential_radius,
                poiList=poi_list,
                exponentialAGL=do_exponential_agl,
                defaultPoiAltitude=default_poi_alt,
                takeoffElevationFeet=takeoff_elev_feet,
                forceGimbalTilt=is_standard_mode or use_gimbal_tilt_mode,
                maxHeightVal=max_h_val,
                log=log
            )
            log("Flight Path Generation", f"Master waypoints generated: {len(master_waypoints)} total.")

            # Segment flight path by battery capacity
            log("Flight Path Segmentation", "Calling segment_flight_path for standard/advanced.")
            totalFlightTimeMinutes, segments = segment_flight_path(
                master_waypoints,
                lat_center=lat,
                lon_center=lon,
                elevationFeet=elevation_feet,
                batteryCapacity=battery_capacity_val,
                startPointAltitude=parse_float(start_point_altitude, 70),
                poiAltitude=0,
                takeoffLat=takeoff_lat,
                takeoffLon=takeoff_lon,
                takeoffElevationFeet=takeoff_elev_feet,
                log=log
            )
            log("Flight Path Segmentation", f"Finished segmentation. {len(segments)} segments generated.")

        # ---------------------------------------------------------------------
        # FINAL RESPONSE
        # ---------------------------------------------------------------------
        log("Lambda Completion", "Returning success response.")
        
        # Ensure totalFlightTimeMinutes is always properly defined
        if mode == "ranch":
            final_flight_time = total_ranch_time
        else:
            final_flight_time = totalFlightTimeMinutes
        
        log("Flight Time", f"Mode: {mode}, Final flight time: {final_flight_time:.2f} minutes")
            
        response_body = {
            "title": title,
            "elevationMsg": elev_msg,
            "masterWaypoints": master_waypoints,
            "segments": segments,
            "totalFlightTimeMinutes": float(f"{final_flight_time:.2f}"),
            "logs": logs
        }
        
        log("Response Structure", f"Keys in response: {list(response_body.keys())}")
        
        return {
            "statusCode": 200,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*",  # Replace '*' with your frontend domain
            },
            "body": json.dumps(response_body)
        }

    except Exception as e:
        log("Error Handler", f"An exception occurred: {str(e)}")
        return {
            "statusCode": 500,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*",  # Replace '*' with your frontend domain
                "Access-Control-Allow-Headers": "Content-Type, Authorization",
                "Access-Control-Allow-Methods": "OPTIONS,POST"
            },
            "body": json.dumps({
                "error": str(e),
                "logs": logs
            })
        }


# -------------------------------------------------------------------------
#                   RANCH-SPECIFIC SHAPE GENERATION
# -------------------------------------------------------------------------
def generate_ranch_flight_segments(lat_center,
                                   lon_center,
                                   takeoffLat,
                                   takeoffLon,
                                   takeoffElevationFeet,
                                   elevationFeet,
                                   numBatteries,
                                   initialRadius,
                                   minHeight,
                                   maxHeightVal,
                                   batteryCapacity,
                                   flightSpeedMph,
                                   verticalSpeedMps,
                                   forceGimbalTilt,
                                   log):
    """
    Single-batch approach:
      1) For each battery slice, build the bounces in memory, using only geometry/time
         (no Google Elevation calls) to see if the next bounce fits under batteryCapacity.
      2) Once we finalize how many bounces we can have, do ONE get_elevations_feet call
         for the entire slice, then build final waypoints.
    """
    slices = []
    totalFlightTimeSec = 0.0
    speedMps = flightSpeedMph * 0.44704
    hoverTime = 3
    accelTime = 2

    # tilt
    TILT_START = -29
    TILT_END = -21
    tilt_range = TILT_END - TILT_START

    # AGL increment
    AGL_INC = 25.0  # each bounce raises AGL by 25ft

    if numBatteries < 1:
        numBatteries = 1
    sliceAngle = 360.0 / numBatteries

    # We'll define a method to compute bounce-based time cost
    def time_for_segment(polarPoints):
        """
        Estimate total flight time (2D + vertical) + overhead + return home
        purely via geometry, ignoring actual ground elevation.
        """
        if not polarPoints:
            return 0.0

        # Start at home altitude = minHeight
        localSec = 0.0
        # ascend
        localSec += (minHeight * 0.3048) / verticalSpeedMps

        # we'll track a "previous" point in 2D
        prevLat = takeoffLat
        prevLon = takeoffLon
        prevAlt = minHeight
        for p in polarPoints:
            # distance
            distFt = p["radiusFt"]  # approximate distance from center
            # but we need the distance from prev to this waypoint. We'll do:
            # 1) convert prev -> center & current -> center => two vectors => approximate chord
            # or do a direct haversine with a small function.
            # We'll do an approximate bearing from the center for 'p', then haversine from prev.

            # 1) get lat/lon for p
            r_meters = p["radiusFt"] * 0.3048
            latlon = compute_destination_point(lat_center, lon_center, r_meters, p["angleDeg"])
            distM = haversine_distance(prevLat, prevLon, latlon["lat"], latlon["lon"])
            altDiffM = abs(p["desiredAGL"] - prevAlt) * 0.3048
            tHoriz = distM / speedMps
            tVert = altDiffM / verticalSpeedMps
            localSec += (tHoriz + tVert + hoverTime + accelTime)

            # update prev
            prevLat = latlon["lat"]
            prevLon = latlon["lon"]
            prevAlt = p["desiredAGL"]

        # return home
        distHomeM = haversine_distance(prevLat, prevLon, takeoffLat, takeoffLon)
        altHomeM = abs(prevAlt - minHeight) * 0.3048
        localSec += (distHomeM / speedMps) + (altHomeM / verticalSpeedMps) + (hoverTime + accelTime)
        # final descent
        localSec += (minHeight * 0.3048) / verticalSpeedMps
        return localSec

    for sliceIdx in range(numBatteries):
        angle_min = sliceIdx * sliceAngle
        angle_max = angle_min + sliceAngle
        direction = 1
        bounceIndex = 0
        currentAngle = angle_min
        currentRadiusFt = initialRadius
        RADIUS_PER_BOUNCE = 200.0  # user-defined

        # Build a "polarPoints" list for final usage
        polarPoints = []
        polarPoints.append({
            "angleDeg": currentAngle,
            "radiusFt": currentRadiusFt,
            "desiredAGL": minHeight,  # we'll override final for each bounce
            "tiltVal": TILT_START
        })

        while True:
            nextAngle = angle_max if direction == 1 else angle_min
            nextRadius = currentRadiusFt + RADIUS_PER_BOUNCE
            bounceAGL = minHeight + (AGL_INC * (bounceIndex + 1)) if bounceIndex >= 0 else minHeight
            bounceTilt = TILT_START if bounceIndex < 1 else (TILT_START + (tilt_range * bounceIndex / 100.0))  
            # we'll refine tilt after we know final bounceCount

            candidate = {
                "angleDeg": nextAngle,
                "radiusFt": nextRadius,
                "desiredAGL": bounceAGL,
                "tiltVal": bounceTilt
            }

            # test
            testList = polarPoints + [candidate]
            estSec = time_for_segment(testList)
            estMin = estSec / 60.0
            if estMin > batteryCapacity:
                log("Battery Limit Hit", f"slice={sliceIdx+1}, bounce={bounceIndex+1}, estMin={estMin:.2f} => stop.")
                break

            # accept
            bounceIndex += 1
            polarPoints.append(candidate)
            currentRadiusFt = nextRadius
            currentAngle = nextAngle
            direction *= -1

            if bounceIndex > 100:
                log("Max Bounce Cap", f"slice={sliceIdx+1} -> reached 100 bounces, stopping.")
                break

        # Now we do single pass of real elevation for all polarPoints
        # with final tilt interpolation
        # 1) final bounce count = bounceIndex
        # 2) tilt step if bounceCount>1, else 0
        if bounceIndex <= 1:
            tiltStep = 0.0
        else:
            tiltStep = tilt_range / (bounceIndex - 1) if bounceIndex > 1 else 0

        for i, p in enumerate(polarPoints):
            p["desiredAGL"] = minHeight + (AGL_INC * i)  # each bounce adds 25ft
            if forceGimbalTilt:
                p["tiltVal"] = TILT_START + (tiltStep * i)

        # Build final segment
        segWPs, segTimeSec = finalize_ranch_slice_single_batch(
            polarPoints,
            lat_center,
            lon_center,
            takeoffLat,
            takeoffLon,
            takeoffElevationFeet,
            minHeight,
            maxHeightVal,
            speedMps,
            verticalSpeedMps,
            forceGimbalTilt,
            log
        )
        slices.append(segWPs)
        totalFlightTimeSec += segTimeSec

    return slices, totalFlightTimeSec / 60.0

def finalize_ranch_slice_single_batch(polarPoints,
                                      lat_center,
                                      lon_center,
                                      takeoffLat,
                                      takeoffLon,
                                      takeoffElevationFeet,
                                      minHeight,
                                      maxHeightVal,
                                      speedMps,
                                      verticalSpeedMps,
                                      forceGimbalTilt,
                                      log):
    """
    Takes the final list of polarPoints (already decided how many bounces).
    We do exactly ONE get_elevations_feet call for all points, then build the segment.
    """
    if len(polarPoints) < 2:
        # trivial => up/down
        seg = []
        ascend = (minHeight * 0.3048) / verticalSpeedMps
        totalSec = ascend + ascend
        homeWp = build_ranch_waypoint(takeoffLat, takeoffLon, minHeight, lat_center, lon_center)
        seg.append(homeWp)
        seg.append(homeWp)
        return seg, totalSec

    # Convert to lat/lon
    latlons = []
    for p in polarPoints:
        distM = p["radiusFt"] * 0.3048
        coords = compute_destination_point(lat_center, lon_center, distM, p["angleDeg"])
        latlons.append(coords)

    # single fetch
    try:
        elevsFeet = get_elevations_feet([(c["lat"], c["lon"]) for c in latlons])
    except:
        elevsFeet = [takeoffElevationFeet]*len(latlons)

    segment = []
    startWp = build_ranch_waypoint(takeoffLat, takeoffLon, minHeight, lat_center, lon_center)
    segment.append(startWp)
    totalSec = 0.0
    # ascend
    totalSec += (minHeight * 0.3048) / verticalSpeedMps

    prevWp = startWp
    hoverTime = 3
    accelTime = 2

    # build each bounce
    for i, p in enumerate(polarPoints):
        coords = latlons[i]
        groundElev = elevsFeet[i]
        localOffset = groundElev - takeoffElevationFeet
        if localOffset < 0:
            localOffset = 0
        finalAlt = localOffset + p["desiredAGL"]
        # clamp
        if maxHeightVal is not None:
            adjustedMax = maxHeightVal - takeoffElevationFeet
            currentAGL = finalAlt - groundElev
            if currentAGL > adjustedMax:
                finalAlt = groundElev + adjustedMax

        # times
        distM = haversine_distance(prevWp["latitude"], prevWp["longitude"], coords["lat"], coords["lon"])
        altDiffM = abs(finalAlt - prevWp["altitude"]) * 0.3048
        segTime = distM / speedMps + altDiffM / verticalSpeedMps + hoverTime + accelTime
        totalSec += segTime

        nextWp = build_ranch_waypoint(coords["lat"], coords["lon"], finalAlt, lat_center, lon_center)
        if forceGimbalTilt:
            nextWp["gimbalpitchangle"] = f"{p['tiltVal']:.2f}"
        else:
            horizDistMeters = haversine_distance(coords["lat"], coords["lon"], lat_center, lon_center)
            vertDiffFt = finalAlt
            angleDeg = -math.degrees(math.atan2(vertDiffFt * 0.3048, horizDistMeters))
            nextWp["gimbalpitchangle"] = f"{angleDeg:.2f}"

        segment.append(nextWp)
        prevWp = nextWp

    # return home
    homeDistM = haversine_distance(prevWp["latitude"], prevWp["longitude"], takeoffLat, takeoffLon)
    altDiffHomeM = abs(prevWp["altitude"] - minHeight) * 0.3048
    homeTime = homeDistM / speedMps + altDiffHomeM / verticalSpeedMps + hoverTime + accelTime
    totalSec += homeTime

    homeWp = build_ranch_waypoint(takeoffLat, takeoffLon, minHeight, lat_center, lon_center)
    homeWp["heading"] = calculate_bearing(prevWp["latitude"], prevWp["longitude"], takeoffLat, takeoffLon)
    homeWp["curvesize"] = prevWp["curvesize"]
    segment.append(homeWp)

    # final descent
    totalSec += (minHeight * 0.3048) / verticalSpeedMps

    # enforce distance
    segment = enforce_max_distance_between_waypoints(segment, 6560)
    return segment, totalSec

def build_ranch_waypoint(lat, lon, alt, lat_center, lon_center):
    """
    Helper for consistent structure.
    """
    return {
        "latitude": lat,
        "longitude": lon,
        "altitude": alt,
        "heading": 0,
        "curvesize": "25.00",
        "rotationdir": 0,
        "gimbalmode": 2,
        "gimbalpitchangle": "0.00",
        "altitudemode": 0,
        # ~19.8 mph
        "speed": "8.82",
        "poi_latitude": lat_center,
        "poi_longitude": lon_center,
        "poi_altitude": 0,
        "poi_altitudemode": 0,
        "photo_timeinterval": 3.5,
        "photo_distinterval": 0
    }

# -------------------------------------------------------------------------
#         ALL OTHER FUNCTIONS (UNMODIFIED) BELOW HERE
# -------------------------------------------------------------------------

def parse_coordinates(coord_str):
    import re
    coord_str = coord_str.replace("\n", " ").strip()
    if not coord_str:
        raise ValueError("No coordinates provided.")

    dms_regex = re.compile(r'(\d+)[°\s](\d+)[\'\s](\d+(?:\.\d+)?)["]?\s*([NnSs]),?\s*(\d+)[°\s](\d+)[\'\s](\d+(?:\.\d+)?)["]?\s*([EeWw])')
    match_dms = dms_regex.search(coord_str)
    if match_dms:
        latDeg = float(match_dms.group(1))
        latMin = float(match_dms.group(2))
        latSec = float(match_dms.group(3))
        latDir = match_dms.group(4)
        lonDeg = float(match_dms.group(5))
        lonMin = float(match_dms.group(6))
        lonSec = float(match_dms.group(7))
        lonDir = match_dms.group(8)

        lat = latDeg + (latMin / 60) + (latSec / 3600)
        lon = lonDeg + (lonMin / 60) + (lonSec / 3600)

        if latDir.upper() == 'S':
            lat = -abs(lat)
        if lonDir.upper() == 'W':
            lon = -abs(lon)
        return (lat, lon)

    decimal_regex = re.compile(r'([+-]?\d+(\.\d+)?)[°\s]*([NnSs])?\s*,?\s*([+-]?\d+(\.\d+)?)[°\s]*([EeWw])?')
    match_dec = decimal_regex.search(coord_str)
    if match_dec:
        lat = float(match_dec.group(1))
        latDir = match_dec.group(3)
        lon = float(match_dec.group(4))
        lonDir = match_dec.group(6)

        if latDir and latDir.upper() == 'S':
            lat = -abs(lat)
        if lonDir and lonDir.upper() == 'W':
            lon = -abs(lon)
        return (lat, lon)

    raise ValueError("Invalid coordinate format.")

def get_elevation_feet(lat, lon):
    url = f"https://maps.googleapis.com/maps/api/elevation/json?locations={lat},{lon}&key={API_KEY}"
    resp = requests.get(url)
    if resp.status_code != 200:
        raise ValueError(f"Elevation HTTP error {resp.status_code}")
    js = resp.json()
    if js["status"] != "OK" or not js["results"]:
        raise ValueError(f"Elevation unavailable: {js['status']}")
    elevation_meters = js["results"][0]["elevation"]
    return elevation_meters * 3.28084

def get_elevations_feet(locations):
    results = []
    for (lat, lon) in locations:
        try:
            results.append(get_elevation_feet(lat, lon))
        except:
            results.append(None)
    if any(r is None for r in results):
        raise ValueError("Failed to fetch some elevations.")
    return results

def parse_float(s, default=None):
    try:
        return float(s)
    except:
        return default

def parse_int(s, default=None):
    try:
        return int(float(s))
    except:
        return default

def generate_master_flight_path(lat_center, lon_center, elevFeet, 
                                numLoops, initialRadius, radiusIncrement, 
                                initialAGL, aglIncrement, exponentialRadius, 
                                poiList, exponentialAGL, defaultPoiAltitude, 
                                takeoffElevationFeet, forceGimbalTilt, maxHeightVal, log):
    log("generate_master_flight_path", f"Entered function with numLoops={numLoops}, initialRadius={initialRadius}")
    waypoints = []
    locations = []
    numPointsPerRing = 4
    speedMps = 19.8 * 0.44704
    photo_timeinterval = 2.8
    photo_distinterval = 0
    altitudemode = 0
    gimbalmode = 2
    rotationdir = 0

    log("Gimbal Tilt Logic", f"AGL start: {initialAGL}, loops: {numLoops}")
    tiltStart = -32
    tiltEnd = -10
    totalTilt = tiltEnd - tiltStart
    tiltStep = totalTilt / (numLoops - 1) if numLoops > 1 else 0

    def getPoiOverrideForLoop(loopIndex):
        loopNum = loopIndex + 1
        for poi in poiList:
            if loopNum >= poi["loopFrom"] and loopNum <= poi["loopTo"]:
                return poi["altitude"]
        return None

    for loopIndex in range(numLoops):
        if exponentialRadius:
            radiusFeet = initialRadius * (radiusIncrement ** loopIndex)
        else:
            radiusFeet = initialRadius + loopIndex * radiusIncrement

        if exponentialAGL:
            desiredAGL = initialAGL * (aglIncrement ** loopIndex)
        else:
            desiredAGL = initialAGL + loopIndex * aglIncrement

        userOverride = getPoiOverrideForLoop(loopIndex)
        if forceGimbalTilt:
            loopTilt = userOverride if userOverride is not None else (tiltStart + tiltStep * loopIndex)
            poiAltitudeUsed = 0
        else:
            loopTilt = tiltStart + tiltStep * loopIndex
            poiAltitudeUsed = userOverride if userOverride is not None else defaultPoiAltitude

        radiusMeters = radiusFeet * 0.3048
        theta = 360.0 / numPointsPerRing

        chordFeet = 2 * radiusFeet * math.sin((theta / 2) * math.pi / 180)
        curvesizeFeet = chordFeet / 2
        if curvesizeFeet > 3280:
            curvesizeFeet = 3280

        log("Loop Build", f"loopIndex={loopIndex}, radiusFeet={radiusFeet}, desiredAGL={desiredAGL}, userOverride={userOverride}")
        for i in range(numPointsPerRing + 1):
            angle = (i % numPointsPerRing) * theta
            bearing = (angle) % 360
            wp = compute_destination_point(lat_center, lon_center, radiusMeters, bearing)
            heading = (bearing + 180) % 360

            locations.append((wp["lat"], wp["lon"]))
            waypoints.append({
                "latitude": wp["lat"],
                "longitude": wp["lon"],
                "heading": heading,
                "curvesize": f"{curvesizeFeet:.2f}",
                "rotationdir": rotationdir,
                "gimbalmode": gimbalmode,
                "gimbalpitchangle": 0,
                "altitudemode": altitudemode,
                "speed": f"{speedMps:.2f}",
                "poi_latitude": lat_center,
                "poi_longitude": lon_center,
                "poi_altitude": poiAltitudeUsed,
                "poi_altitudemode": 0,
                "photo_timeinterval": photo_timeinterval,
                "photo_distinterval": photo_distinterval,
                "desiredAGL": desiredAGL,
                "loopIndex": loopIndex,
                "altitude": 0,
                "tiltForThisLoop": loopTilt
            })

    log("Elevation Batch Fetch", f"About to fetch elevations for {len(locations)} waypoint-locations.")
    elevsFeet = get_elevations_feet(locations)
    log("Elevation Batch Fetch", "Finished fetching elevations.")

    for i, wp in enumerate(waypoints):
        groundElev = elevsFeet[i]
        localGroundOffset = groundElev - takeoffElevationFeet
        if localGroundOffset < 0:
            localGroundOffset = 0
        finalAltitude = localGroundOffset + wp["desiredAGL"]

        if maxHeightVal is not None:
            adjustedMaxHeight = maxHeightVal - takeoffElevationFeet
            currentAGL = finalAltitude - groundElev
            if currentAGL > adjustedMaxHeight:
                finalAltitude = groundElev + adjustedMaxHeight
                log("Capping Altitude", f"Waypoint {i}: ground at {groundElev} ft => finalAltitude clamped to {finalAltitude} ft")

        wp["altitude"] = finalAltitude

        if forceGimbalTilt:
            wp["gimbalpitchangle"] = f"{wp['tiltForThisLoop']:.2f}"
        else:
            horizDistMeters = haversine_distance(wp["latitude"], wp["longitude"],
                                                 wp["poi_latitude"], wp["poi_longitude"])
            vertDiffFt = wp["altitude"] - wp["poi_altitude"]
            vertDiffMeters = vertDiffFt * 0.3048
            angle = -math.degrees(math.atan2(vertDiffMeters, horizDistMeters))
            wp["gimbalpitchangle"] = f"{angle:.2f}"

    log("Distance Enforcement", f"Enforcing max distance on {len(waypoints)} waypoints.")
    wpts_limited = enforce_max_distance_between_waypoints(waypoints, 6560)
    log("Distance Enforcement", f"Returned {len(wpts_limited)} waypoints after enforcement.")
    return wpts_limited

def segment_flight_path(masterWaypoints, lat_center, lon_center, elevationFeet,
                        batteryCapacity, startPointAltitude, poiAltitude,
                        takeoffLat, takeoffLon, takeoffElevationFeet, log):
    """
    Unchanged existing function for segmenting Standard/Advanced flight paths
    by battery capacity.
    """
    log("segment_flight_path", f"Entered with {len(masterWaypoints)} masterWaypoints, batteryCapacity={batteryCapacity}")
    segments = []
    totalFlightTimeSeconds = 0
    idx = 0
    speedMps = 19.8 * 0.44704
    verticalSpeedMps = 5
    altitudemode = 0
    gimbalmode = 2
    rotationdir = 0
    hoverTime = 3
    accelTime = 2

    log("Segmenting Path:", f"Battery capacity ~{batteryCapacity} minutes")

    while idx < len(masterWaypoints):
        currentSeg = []
        currentSegTime = 0
        log("Segment Loop Start", f"Starting new segment from waypoint index {idx}")

        # Start waypoint is home with altitude = startPointAltitude
        startWp = {
            "latitude": takeoffLat,
            "longitude": takeoffLon,
            "altitude": startPointAltitude,
            "heading": 0,
            "curvesize": 0,
            "rotationdir": rotationdir,
            "gimbalmode": gimbalmode,
            "gimbalpitchangle": 0,
            "altitudemode": altitudemode,
            "speed": f"{speedMps:.2f}",
            "poi_latitude": lat_center,
            "poi_longitude": lon_center,
            "poi_altitude": poiAltitude,
            "poi_altitudemode": 0,
            "photo_timeinterval": 0,
            "photo_distinterval": 0
        }
        currentSeg.append(startWp)
        log("Home Waypoint", "Added startWp as first in segment.")

        ascendTime = (startPointAltitude * 0.3048) / verticalSpeedMps
        currentSegTime += ascendTime
        log("AscendTime", f"AscendTime so far = {ascendTime:.2f}s, total seg time = {currentSegTime:.2f}s")

        segStartIdx = idx if idx == 0 else idx - 1
        while segStartIdx < len(masterWaypoints):
            wp = masterWaypoints[segStartIdx]
            segTime = 0

            if len(currentSeg) > 1:
                prev = currentSeg[-1]
                dist = haversine_distance(prev["latitude"], prev["longitude"],
                                          wp["latitude"], wp["longitude"])
                timeHorz = dist / speedMps
                altChange = wp["altitude"] - prev["altitude"]
                timeVert = abs(altChange * 0.3048) / verticalSpeedMps
                segTime = timeHorz + timeVert
                log("SegTime - existing seg", f"Dist={dist:.2f}m, altChange={altChange:.2f}ft => segTime={segTime:.2f}s")
            else:
                dist = haversine_distance(startWp["latitude"], startWp["longitude"],
                                          wp["latitude"], wp["longitude"])
                timeHorz = dist / speedMps
                altDiff = wp["altitude"] - startPointAltitude
                timeVert = abs(altDiff * 0.3048) / verticalSpeedMps
                segTime = timeHorz + timeVert
                log("SegTime - first master WP", f"Dist={dist:.2f}m, altDiff={altDiff:.2f}ft => segTime={segTime:.2f}s")

            segTime += (hoverTime + accelTime)
            distToHome = haversine_distance(wp["latitude"], wp["longitude"],
                                            takeoffLat, takeoffLon)
            timeHome = distToHome / speedMps
            altHomeDiff = wp["altitude"] - startPointAltitude
            timeVertHome = abs(altHomeDiff * 0.3048) / verticalSpeedMps
            returnTime = timeHome + timeVertHome + accelTime
            descentTime = (startPointAltitude * 0.3048) / verticalSpeedMps

            projectedMin = (currentSegTime + segTime + returnTime + descentTime) / 60.0
            log("Battery Projection", f"projectedMin={projectedMin:.2f}, batteryCapacity={batteryCapacity}")

            if projectedMin > batteryCapacity:
                log("Battery Limit Hit", f"Cannot add WP at index {segStartIdx}, would exceed capacity.")
                break

            currentSeg.append(wp)
            currentSegTime += segTime
            log("WP Added to Segment", f"segStartIdx={segStartIdx}, currentSegTime={currentSegTime:.2f}s")
            segStartIdx += 1

        idx = segStartIdx
        log("Segment End", f"Segment used up to master waypoint index {idx-1}")

        # Return home
        lastWp = currentSeg[-1]
        homeDist = haversine_distance(lastWp["latitude"], lastWp["longitude"],
                                      takeoffLat, takeoffLon)
        timeHorzHome = homeDist / speedMps
        altDiffHome = lastWp["altitude"] - startPointAltitude
        timeVertHome = abs(altDiffHome * 0.3048) / verticalSpeedMps
        transitionTime = timeHorzHome + timeVertHome + accelTime
        currentSegTime += transitionTime
        log("Return Home Time", f"homeDist={homeDist:.2f}m, altDiffHome={altDiffHome:.2f}, transitionTime={transitionTime:.2f}s => totalSegTime={currentSegTime:.2f}s")

        if homeDist > 0 or altDiffHome != 0:
            homeWp = dict(startWp)
            homeWp["heading"] = calculate_bearing(lastWp["latitude"], lastWp["longitude"],
                                                  takeoffLat, takeoffLon)
            homeWp["curvesize"] = lastWp["curvesize"]
            currentSeg.append(homeWp)
            log("Return Home WP", "Appended final home WP for this segment.")

        descentFinal = (startPointAltitude * 0.3048) / verticalSpeedMps
        currentSegTime += descentFinal
        log("Descent Final", f"Final descent time: {descentFinal:.2f}s => totalSegTime={currentSegTime:.2f}s")

        currentSeg = enforce_max_distance_between_waypoints(currentSeg, 6560)
        log("Max Dist Enforcement", f"Segment now has {len(currentSeg)} WPs after enforcement.")

        totalFlightTimeSeconds += currentSegTime
        segments.append(currentSeg)
        log("Segment Appended", f"Completed segment with {len(currentSeg)} WPs. totalFlightTimeSeconds={totalFlightTimeSeconds:.2f}")

    totalFlightTimeMinutes = totalFlightTimeSeconds / 60.0
    log("Total Flight Time:", f"{totalFlightTimeMinutes:.2f} minutes")
    return (totalFlightTimeMinutes, segments)

def compute_destination_point(lat, lon, distanceMeters, bearingDegrees):
    R = 6378137.0
    bearingRad = math.radians(bearingDegrees)
    latRad = math.radians(lat)
    lonRad = math.radians(lon)

    newLatRad = math.asin(
        math.sin(latRad)*math.cos(distanceMeters/R) +
        math.cos(latRad)*math.sin(distanceMeters/R)*math.cos(bearingRad)
    )
    newLonRad = lonRad + math.atan2(
        math.sin(bearingRad)*math.sin(distanceMeters/R)*math.cos(latRad),
        math.cos(distanceMeters/R) - math.sin(latRad)*math.sin(newLatRad)
    )

    return {
        "lat": math.degrees(newLatRad),
        "lon": math.degrees(newLonRad)
    }

def haversine_distance(lat1, lon1, lat2, lon2):
    R = 6371000.0
    dLat = math.radians(lat2 - lat1)
    dLon = math.radians(lon2 - lon1)
    a = (math.sin(dLat/2)**2 +
         math.cos(math.radians(lat1)) *
         math.cos(math.radians(lat2)) *
         math.sin(dLon/2)**2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    return R * c

def calculate_bearing(lat1, lon1, lat2, lon2):
    dLon = math.radians(lon2 - lon1)
    lat1Rad = math.radians(lat1)
    lat2Rad = math.radians(lat2)
    y = math.sin(dLon) * math.cos(lat2Rad)
    x = math.cos(lat1Rad)*math.sin(lat2Rad) - math.sin(lat1Rad)*math.cos(lat2Rad)*math.cos(dLon)
    bearing = math.degrees(math.atan2(y, x))
    return (bearing + 360) % 360

def enforce_max_distance_between_waypoints(waypoints, maxFt):
    result = []
    maxMeters = maxFt*0.3048

    for i in range(len(waypoints) - 1):
        result.append(waypoints[i])
        dist = haversine_distance(
            waypoints[i]["latitude"], waypoints[i]["longitude"],
            waypoints[i+1]["latitude"], waypoints[i+1]["longitude"]
        )
        if dist > maxMeters:
            inserts = insert_midpoints(waypoints[i], waypoints[i+1], maxMeters)
            result.extend(inserts)
    result.append(waypoints[-1])
    return result

def insert_midpoints(wp1, wp2, maxMeters):
    mids = []
    dist = haversine_distance(wp1["latitude"], wp1["longitude"],
                              wp2["latitude"], wp2["longitude"])
    if dist <= maxMeters:
        return mids
    midpoint = compute_midpoint(
        wp1["latitude"], wp1["longitude"],
        wp2["latitude"], wp2["longitude"]
    )
    midWp = dict(wp1)
    midWp["latitude"] = midpoint["lat"]
    midWp["longitude"] = midpoint["lon"]
    midWp["altitude"] = (wp1["altitude"] + wp2["altitude"]) / 2.0
    midWp["heading"] = calculate_bearing(wp1["latitude"], wp1["longitude"],
                                         wp2["latitude"], wp2["longitude"])
    g1 = float(wp1["gimbalpitchangle"])
    g2 = float(wp2["gimbalpitchangle"])
    midWp["gimbalpitchangle"] = f"{(g1 + g2)/2:.2f}"
    mids.extend(insert_midpoints(wp1, midWp, maxMeters))
    mids.append(midWp)
    mids.extend(insert_midpoints(midWp, wp2, maxMeters))
    return mids

def compute_midpoint(lat1, lon1, lat2, lon2):
    lat1Rad = math.radians(lat1)
    lon1Rad = math.radians(lon1)
    lat2Rad = math.radians(lat2)
    lon2Rad = math.radians(lon2)
    dLon = lon2Rad - lon1Rad

    Bx = math.cos(lat2Rad) * math.cos(dLon)
    By = math.cos(lat2Rad) * math.sin(dLon)
    lat3 = math.atan2(
        math.sin(lat1Rad) + math.sin(lat2Rad),
        math.sqrt((math.cos(lat1Rad) + Bx)**2 + By**2)
    )
    lon3 = lon1Rad + math.atan2(By, math.cos(lat1Rad) + Bx)

    return {
        "lat": math.degrees(lat3),
        "lon": math.degrees(lon3)
    }
