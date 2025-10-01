/**
 * Flight Path Converter: CSV (Litchi) → KMZ (DJI WPML)
 * Spec-compliant converter following DJI's WPML 1.0.2 format
 */

import JSZip from "jszip";
import { XMLBuilder } from "fast-xml-parser";

const FEET_TO_METERS = 0.3048;

interface LitchiWaypoint {
  latitude: number;
  longitude: number;
  altitude_ft: number;
  heading_deg: number;
  curvesize_ft: number;
  rotationdir: number;
  gimbalmode: number;
  gimbalpitchangle: number;
  altitudemode: number;
  speed_ms: number;
  poi_latitude: number | null;
  poi_longitude: number | null;
  poi_altitude_ft: number | null;
  poi_altitudemode: number;
  photo_timeinterval: number;
  photo_distinterval: number;
}

interface ConversionOptions {
  signalLostAction: "continue" | "executeLostAction";
  missionSpeed: number; // m/s
  droneType: "dji_fly" | "mavic3_enterprise" | "matrice_30";
  headingMode: "poi_or_interpolate" | "follow_wayline" | "manual";
  allowStraightLines: boolean;
}

const DRONE_ENUM_VALUES: Record<string, { value: number; subValue: number }> = {
  dji_fly: { value: 68, subValue: 0 },
  mavic3_enterprise: { value: 67, subValue: 0 },
  matrice_30: { value: 60, subValue: 1 },
};

export async function convertLitchiCSVToKMZ(
  csvContent: string,
  fileName: string,
  options: ConversionOptions
): Promise<Blob> {
  // Parse CSV
  const waypoints = parseLitchiCSV(csvContent);
  
  if (waypoints.length === 0) {
    throw new Error("No valid waypoints found in CSV");
  }

  // Generate WPML files
  const templateKML = generateTemplateKML(options);
  const waylinesWPML = generateWaylinesWPML(waypoints, options);

  // Create KMZ (ZIP with specific structure)
  const zip = new JSZip();
  const wpmz = zip.folder("wpmz");
  
  if (!wpmz) {
    throw new Error("Failed to create wpmz folder");
  }

  wpmz.file("template.kml", templateKML);
  wpmz.file("waylines.wpml", waylinesWPML);

  // Generate KMZ blob
  const kmzBlob = await zip.generateAsync({
    type: "blob",
    compression: "DEFLATE",
    compressionOptions: { level: 9 },
  });

  return kmzBlob;
}

function parseLitchiCSV(csvContent: string): LitchiWaypoint[] {
  const lines = csvContent.trim().split("\n");
  if (lines.length < 2) {
    throw new Error("CSV must contain header and at least one waypoint");
  }

  const header = lines[0].toLowerCase().split(",").map(h => h.trim());
  const waypoints: LitchiWaypoint[] = [];

  for (let i = 1; i < lines.length; i++) {
    const values = lines[i].split(",").map(v => v.trim());
    if (values.length < header.length) continue;

    const wp: any = {};
    header.forEach((col, idx) => {
      const value = values[idx];
      
      // Map CSV columns to standardized names
      const normalizedCol = col
        .replace(/\(.*?\)/g, "") // Remove units
        .replace(/[^a-z0-9_]/g, "_")
        .replace(/_+/g, "_")
        .replace(/^_|_$/g, "");

      const numValue = parseFloat(value);
      wp[normalizedCol] = isNaN(numValue) ? null : numValue;
    });

    waypoints.push({
      latitude: wp.latitude || 0,
      longitude: wp.longitude || 0,
      altitude_ft: wp.altitude || 0,
      heading_deg: wp.heading || 0,
      curvesize_ft: wp.curvesize || 0,
      rotationdir: wp.rotationdir || 0,
      gimbalmode: wp.gimbalmode || 2,
      gimbalpitchangle: wp.gimbalpitchangle || -90,
      altitudemode: wp.altitudemode || 0,
      speed_ms: wp.speed || 5,
      poi_latitude: wp.poi_latitude || null,
      poi_longitude: wp.poi_longitude || null,
      poi_altitude_ft: wp.poi_altitude || null,
      poi_altitudemode: wp.poi_altitudemode || 0,
      photo_timeinterval: wp.photo_timeinterval || 0,
      photo_distinterval: wp.photo_distinterval || 0,
    });
  }

  return waypoints;
}

function generateTemplateKML(options: ConversionOptions): string {
  const droneInfo = DRONE_ENUM_VALUES[options.droneType] || DRONE_ENUM_VALUES.dji_fly;
  const timestamp = Math.floor(Date.now() / 1000);

  const templateData = {
    "?xml": {
      "@_version": "1.0",
      "@_encoding": "UTF-8",
    },
    kml: {
      "@_xmlns": "http://www.opengis.net/kml/2.2",
      "@_xmlns:wpml": "http://www.dji.com/wpmz/1.0.2",
      Document: {
        "wpml:author": "SpaceportFlightConverter",
        "wpml:createTime": timestamp,
        "wpml:updateTime": timestamp,
        "wpml:missionConfig": {
          "wpml:flyToWaylineMode": "safely",
          "wpml:finishAction": "goHome",
          "wpml:exitOnRCLost": options.signalLostAction === "continue" ? "goToContinue" : "executeLostAction",
          "wpml:executeRCLostAction": "goBack",
          "wpml:globalTransitionalSpeed": options.missionSpeed,
          "wpml:droneInfo": {
            "wpml:droneEnumValue": droneInfo.value,
            "wpml:droneSubEnumValue": droneInfo.subValue,
          },
        },
      },
    },
  };

  const builder = new XMLBuilder({
    ignoreAttributes: false,
    format: true,
    indentBy: "  ",
    suppressEmptyNode: true,
  });

  return builder.build(templateData);
}

function generateWaylinesWPML(waypoints: LitchiWaypoint[], options: ConversionOptions): string {
  const droneInfo = DRONE_ENUM_VALUES[options.droneType] || DRONE_ENUM_VALUES.dji_fly;

  // Build Placemarks
  const placemarks = waypoints.map((wp, index) => {
    const executeHeight = wp.altitude_ft * FEET_TO_METERS;
    const poiPoint = wp.poi_latitude && wp.poi_longitude
      ? `${wp.poi_latitude},${wp.poi_longitude},${(wp.poi_altitude_ft || 0) * FEET_TO_METERS}`
      : null;

    const actionGroups: any[] = [];
    let actionGroupId = index * 3;

    // Initial gimbal position action
    if (index === 0) {
      actionGroups.push({
        "wpml:actionGroupId": actionGroupId++,
        "wpml:actionGroupStartIndex": index,
        "wpml:actionGroupEndIndex": index,
        "wpml:actionGroupMode": "parallel",
        "wpml:actionTrigger": {
          "wpml:actionTriggerType": "reachPoint",
        },
        "wpml:action": {
          "wpml:actionId": 0,
          "wpml:actionActuatorFunc": "gimbalRotate",
          "wpml:actionActuatorFuncParam": {
            "wpml:gimbalHeadingYawBase": "aircraft",
            "wpml:gimbalRotateMode": "absoluteAngle",
            "wpml:gimbalPitchRotateEnable": 1,
            "wpml:gimbalPitchRotateAngle": wp.gimbalpitchangle,
            "wpml:gimbalRollRotateEnable": 0,
            "wpml:gimbalRollRotateAngle": 0,
            "wpml:gimbalYawRotateEnable": 0,
            "wpml:gimbalYawRotateAngle": 0,
            "wpml:gimbalRotateTimeEnable": 0,
            "wpml:gimbalRotateTime": 0,
            "wpml:payloadPositionIndex": 0,
          },
        },
      });
    }

    // Gimbal transition to next waypoint
    if (index < waypoints.length - 1) {
      const nextWp = waypoints[index + 1];
      actionGroups.push({
        "wpml:actionGroupId": actionGroupId++,
        "wpml:actionGroupStartIndex": index,
        "wpml:actionGroupEndIndex": index + 1,
        "wpml:actionGroupMode": "parallel",
        "wpml:actionTrigger": {
          "wpml:actionTriggerType": "betweenAdjacentPoints",
        },
        "wpml:action": {
          "wpml:actionId": 0,
          "wpml:actionActuatorFunc": "gimbalEvenlyRotate",
          "wpml:actionActuatorFuncParam": {
            "wpml:gimbalPitchRotateAngle": nextWp.gimbalpitchangle,
            "wpml:payloadPositionIndex": 0,
          },
        },
      });
    }

    // Photo capture action
    if (wp.photo_timeinterval > 0) {
      actionGroups.push({
        "wpml:actionGroupId": actionGroupId++,
        "wpml:actionGroupStartIndex": index,
        "wpml:actionGroupEndIndex": index + 1,
        "wpml:actionGroupMode": "sequence",
        "wpml:actionTrigger": {
          "wpml:actionTriggerType": "multipleTiming",
          "wpml:actionTriggerParam": wp.photo_timeinterval,
        },
        "wpml:action": {
          "wpml:actionId": 0,
          "wpml:actionActuatorFunc": "takePhoto",
          "wpml:actionActuatorFuncParam": {
            "wpml:payloadPositionIndex": 0,
            "wpml:useGlobalPayloadLensIndex": 0,
          },
        },
      });
    }

    // Heading mode logic
    let headingMode = "manually";
    let headingAngle = wp.heading_deg;
    let headingPathMode = "followBadArc";
    let headingAngleEnable = 0;

    if (options.headingMode === "follow_wayline") {
      headingMode = "followWayline";
      headingAngleEnable = 0;
    } else if (options.headingMode === "manual") {
      headingMode = "manually";
      headingAngleEnable = 0;
    } else if (poiPoint) {
      headingMode = "towardPOI";
      headingAngleEnable = 0;
    } else {
      headingMode = "manually";
      headingAngleEnable = 0;
    }

    // Waypoint turn mode
    const isLastWaypoint = index === waypoints.length - 1;
    const turnMode = isLastWaypoint
      ? "toPointAndStopWithContinuityCurvature"
      : "toPointAndPassWithContinuityCurvature";

    const placemark: any = {
      Point: {
        coordinates: `${wp.longitude},${wp.latitude}`,
      },
      "wpml:index": index,
      "wpml:executeHeight": executeHeight,
      "wpml:waypointSpeed": wp.speed_ms,
      "wpml:waypointHeadingParam": {
        "wpml:waypointHeadingMode": headingMode,
        "wpml:waypointHeadingAngle": headingAngle,
        ...(poiPoint && { "wpml:waypointPoiPoint": poiPoint }),
        "wpml:waypointHeadingAngleEnable": headingAngleEnable,
        "wpml:waypointHeadingPathMode": headingPathMode,
      },
      "wpml:waypointTurnParam": {
        "wpml:waypointTurnMode": turnMode,
        "wpml:waypointTurnDampingDist": 0,
      },
      "wpml:useStraightLine": options.allowStraightLines ? 1 : 0,
    };

    if (actionGroups.length > 0) {
      placemark["wpml:actionGroup"] = actionGroups;
    }

    return placemark;
  });

  const waylinesData = {
    "?xml": {
      "@_version": "1.0",
      "@_encoding": "UTF-8",
    },
    kml: {
      "@_xmlns": "http://www.opengis.net/kml/2.2",
      "@_xmlns:wpml": "http://www.dji.com/wpmz/1.0.2",
      Document: {
        "wpml:missionConfig": {
          "wpml:flyToWaylineMode": "safely",
          "wpml:finishAction": "goHome",
          "wpml:exitOnRCLost": options.signalLostAction === "continue" ? "goToContinue" : "executeLostAction",
          "wpml:executeRCLostAction": "goBack",
          "wpml:globalTransitionalSpeed": options.missionSpeed,
          "wpml:droneInfo": {
            "wpml:droneEnumValue": droneInfo.value,
            "wpml:droneSubEnumValue": droneInfo.subValue,
          },
        },
        Folder: {
          "wpml:templateId": 0,
          "wpml:executeHeightMode": "relativeToStartPoint",
          "wpml:waylineId": 0,
          "wpml:distance": 0,
          "wpml:duration": 0,
          "wpml:autoFlightSpeed": options.missionSpeed,
          Placemark: placemarks,
        },
      },
    },
  };

  const builder = new XMLBuilder({
    ignoreAttributes: false,
    format: true,
    indentBy: "  ",
    suppressEmptyNode: true,
    arrayNodeName: "Placemark",
  });

  return builder.build(waylinesData);
}

export function downloadBlob(blob: Blob, filename: string): void {
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
}

