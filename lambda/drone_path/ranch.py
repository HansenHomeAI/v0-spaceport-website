import math
from .helpers import (
    compute_destination_point,
    haversine_distance,
    calculate_bearing,
    enforce_max_distance_between_waypoints
)

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