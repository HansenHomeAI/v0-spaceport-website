import json
import os
import boto3
import uuid
from datetime import datetime
import math
import requests

# Initialize DynamoDB resource
dynamodb = boto3.resource('dynamodb')
table_name = os.environ.get('DYNAMODB_TABLE_NAME')
table = dynamodb.Table(table_name)

API_KEY = os.environ.get("GOOGLE_MAPS_API_KEY", "")  # set in Lambda environment

def handler(event, context):
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
        # Parse the incoming request body
        body = json.loads(event['body']) if isinstance(event['body'], str) else event['body']
        
        # Generate a unique ID for this request
        request_id = str(uuid.uuid4())
        
        # Store the request in DynamoDB
        table.put_item(
            Item={
                'id': request_id,
                'timestamp': datetime.utcnow().isoformat(),
                'request_data': body,
                'status': 'processed'
            }
        )
        
        # ---------------------------------------------------------------------
        # EXTRACT COMMON FIELDS
        # ---------------------------------------------------------------------
        title = body.get("title", "untitled")
        coordinates = body.get("coordinates", "")
        takeoff_coordinates = body.get("takeoffCoordinates", "")
        mode = body.get("mode", "standard")

        slider_fraction = float(body.get("sliderFraction", 0))
        min_height = body.get("minHeight", "")
        max_height = body.get("maxHeight", "")
        battery_capacity = body.get("batteryCapacity", "")

        num_loops = body.get("numLoops", "")
        initial_radius = body.get("initialRadius", "")
        radius_increment = body.get("radiusIncrement", "")
        exponential_radius = bool(body.get("exponentialRadius", False))
        agl_increment = body.get("aglIncrement", "")
        exponential_agl = bool(body.get("exponentialAGL", False))
        initial_agl = body.get("initialAGL", "")
        start_point_altitude = body.get("startPointAltitude", "")
        poi_altitude = body.get("poiAltitude", "")
        use_gimbal_tilt_mode = bool(body.get("useGimbalTiltMode", False))
        poi_rows = body.get("poiRows", [])

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
            min_height_ranch = parse_float(body.get("minHeightRanch", ""), 100)
            max_height_ranch = parse_float(body.get("maxHeightRanch", ""), None)
            battery_capacity_ranch = parse_float(body.get("batteryCapacityRanch", ""), 20.0)
            num_batteries_ranch = parse_int(body.get("numBatteriesRanch", ""), 4)
            initial_radius_ranch = parse_float(body.get("initialRadiusRanch", ""), 350.0)

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
        return {
            "statusCode": 200,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*",  # Replace '*' with your frontend domain
            },
            "body": json.dumps({
                "title": title,
                "elevationMsg": elev_msg,
                "masterWaypoints": master_waypoints,
                "segments": segments,
                "totalFlightTimeMinutes": float(f"{total_ranch_time if mode=='ranch' else totalFlightTimeMinutes:.2f}"),
                "logs": logs
            })
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