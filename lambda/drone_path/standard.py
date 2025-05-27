import math
from .helpers import (
    compute_destination_point,
    haversine_distance,
    calculate_bearing,
    enforce_max_distance_between_waypoints,
    get_elevations_feet
)

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