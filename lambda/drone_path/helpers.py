import math
import requests
import os
import boto3

def get_google_maps_api_key():
    ssm = boto3.client('ssm')
    response = ssm.get_parameter(
        Name=os.environ.get('GOOGLE_MAPS_API_KEY_PARAM'),
        WithDecryption=True
    )
    return response['Parameter']['Value']

API_KEY = get_google_maps_api_key()

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
    dLon = math.radians(lat2 - lon1)
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