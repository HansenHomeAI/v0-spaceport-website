import json
import os
import math
import requests

# Fetch the Google Maps API key from environment or parameter store
API_KEY = os.environ.get("GOOGLE_MAPS_API_KEY", "")  # Ensure this env var is set to your actual API key

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
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Headers': 'Content-Type, x-amz-date, authorization, x-api-key, x-amz-security-token',
                'Access-Control-Allow-Methods': 'OPTIONS,POST'
            },
            'body': ''
        }

    try:
        log("Body Presence Check", "Verifying 'body' is in event...")
        if "body" not in event:
            raise ValueError("No body in event.")
        log("Body Presence", "Body found in event.")

        # Parse request payload
        payload = event['body']
        if isinstance(payload, str):
            payload = json.loads(payload)
        log("Payload Decoded", f"Payload keys: {list(payload.keys())}")

        # Extract common fields
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

        # Helper parsers
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
            if js.get("status") != "OK" or not js.get("results"):
                raise ValueError(f"Elevation unavailable: {js.get('status')}")
            elevation_meters = js["results"][0]["elevation"]
            return elevation_meters * 3.28084

        def get_elevations_feet(locations):
            results = []
            for (lt, ln) in locations:
                try:
                    results.append(get_elevation_feet(lt, ln))
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

        # Parse main coordinates & elevation
        lat, lon = parse_coordinates(coordinates)
        log("Parsed Coordinates", f"({lat}, {lon})")
        elevation_feet = get_elevation_feet(lat, lon)
        elev_msg = f"Elevation at ({lat:.5f}, {lon:.5f}): {elevation_feet:.2f} ft"
        log("Elevation", elev_msg)

        # ... rest of your production logic unchanged ...
        # (Insert the rest of your existing functions here)

        # Placeholder final response for structure
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Headers': 'Content-Type, x-amz-date, authorization, x-api-key, x-amz-security-token',
                'Access-Control-Allow-Methods': 'OPTIONS,POST'
            },
            'body': json.dumps({ 'message': 'Production drone path logic executed', 'elevationMsg': elev_msg, 'logs': logs })
        }

    except Exception as e:
        log("Error Handler", f"Exception occurred: {str(e)}")
        return {
            'statusCode': 500,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Headers': 'Content-Type, x-amz-date, authorization, x-api-key, x-amz-security-token',
                'Access-Control-Allow-Methods': 'OPTIONS,POST'
            },
            'body': json.dumps({ 'error': str(e), 'logs': logs })
        } 