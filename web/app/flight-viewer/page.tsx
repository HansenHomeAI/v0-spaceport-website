"use client";

import React, { ChangeEvent, useCallback, useMemo, useState, useEffect, useRef } from "react";
import Papa from "papaparse";
import JSZip from "jszip";
import { XMLParser } from "fast-xml-parser";
import { convertLitchiCSVToKMZ, downloadBlob } from "../../lib/flightConverter";
import { buildApiUrl } from "../api-config";
import "./styles.css";

type RawFlightRow = Record<string, unknown>;

interface PreparedRow {
  latitude: number;
  longitude: number;
  altitudeFt: number;
  headingDeg: number | null;
  curveSizeFt: number | null;
  rotationDir: number | null;
  gimbalMode: number | null;
  gimbalPitchAngle: number | null;
  altitudeMode: number | null;
  speedMs: number | null;
  poiLatitude: number | null;
  poiLongitude: number | null;
  poiAltitudeFt: number | null;
  poiAltitudeMode: number | null;
  photoTimeInterval: number | null;
  photoDistInterval: number | null;
}

interface ProcessedSample extends PreparedRow {
  index: number;
}

interface PoiData {
  latitude: number;
  longitude: number;
  altitudeFt: number;
  altitudeMode: number | null;
}

interface FlightData {

  id: string;
  name: string;
  color: string;
  samples: ProcessedSample[];
  poi: PoiData | null;
}


interface FlightPathSceneProps {
  flights: FlightData[];
  selectedLens: string;
  onWaypointHover: (flightId: string, waypointIndex: number | null) => void;
}

type CesiumModule = typeof import("cesium");

declare const CESIUM_BASE_URL: string | undefined;

declare global {
  interface Window {
    CESIUM_BASE_URL?: string;
  }
}

const EARTH_RADIUS_METERS = 6_378_137;
const FEET_TO_METERS = 0.3048;
const LOG_PREFIX = "[FlightViewer]";
const SAMPLE_LOG_INTERVAL_MS = 1_000;

type LogLevel = "log" | "info" | "warn" | "error" | "debug";

function log(level: LogLevel, ...args: unknown[]): void {
  const fn = (console[level] as (...logArgs: unknown[]) => void) ?? console.log;
  fn(LOG_PREFIX, ...args);
}

function summarizeKey(key: string | undefined): string {
  if (!key) {
    return "<absent>";
  }
  const trimmed = key.trim();
  if (!trimmed) {
    return "<empty-string>";
  }
  if (trimmed.length <= 10) {
    return `${trimmed} (len=${trimmed.length})`;
  }
  return `${trimmed.slice(0, 6)}…${trimmed.slice(-4)} (len=${trimmed.length})`;
}

function attachPixelSampler(
  viewer: import("cesium").Viewer,
  Cesium: CesiumModule,
): () => void {
  const scene = viewer.scene;
  const canvas = scene.canvas;
  const approxScene = scene as unknown as { context?: { gl?: WebGLRenderingContext | null } };
  const gl = approxScene.context?.gl ??
    (canvas.getContext('webgl2') as WebGLRenderingContext | null) ??
    (canvas.getContext('webgl') as WebGLRenderingContext | null);

  if (!gl) {
    log("warn", "[PixelSampler] WebGL context unavailable; skipping pixel sampling");
    return () => {};
  }

  const pixelBuffer = new Uint8Array(4);
  let lastLogTs = 0;
  let consecutiveLowLuma = 0;

  const handler = () => {
    const now = performance.now();
    if (now - lastLogTs < SAMPLE_LOG_INTERVAL_MS) {
      return;
    }
    lastLogTs = now;

    try {
      gl.readPixels(
        Math.max(0, Math.floor(canvas.width / 2)),
        Math.max(0, Math.floor(canvas.height / 2)),
        1,
        1,
        gl.RGBA,
        gl.UNSIGNED_BYTE,
        pixelBuffer,
      );
      const [r, g, b, a] = pixelBuffer;
      const brightness = Math.round((r + g + b) / 3);
      const detail = { r, g, b, a, brightness, canvas: { width: canvas.width, height: canvas.height } };
      if (brightness < 8) {
        consecutiveLowLuma += 1;
        log("warn", "[PixelSampler] center RGBA below visibility threshold", { ...detail, consecutiveLowLuma });
      } else {
        if (consecutiveLowLuma > 0) {
          log("info", "[PixelSampler] brightness recovered", { brightness, consecutiveLowLuma });
          consecutiveLowLuma = 0;
        }
        log("info", "[PixelSampler] center RGBA", detail);
      }
    } catch (error) {
      log("warn", "[PixelSampler] readPixels failed", error);
      scene.postRender.removeEventListener(handler);
    }
  };

  scene.postRender.addEventListener(handler);
  log("info", "[PixelSampler] attached postRender sampler");

  return () => {
    try {
      scene.postRender.removeEventListener(handler);
    } catch (error) {
      log("warn", "[PixelSampler] failed to remove sampler", error);
    }
    log("info", "[PixelSampler] detached");
  };
}

const FLIGHT_COLORS = [
  "#4f83ff",
  "#ff7a18",
  "#00d9ff",
  "#ff4d94",
  "#7aff7a",
  "#ffbb00",
  "#bb7aff",
  "#ff5757",
  "#00ffaa",
  "#ffcc66",
];

function degreesToRadians(value: number): number {
  return (value * Math.PI) / 180;
}

const DRONE_LENSES: Record<string, { name: string; fov: number; aspectRatio: number }> = {
  mavic3_wide: { name: "Mavic 3 Wide (24mm)", fov: 84, aspectRatio: 4 / 3 },
  mavic3_tele: { name: "Mavic 3 Tele (162mm)", fov: 15, aspectRatio: 4 / 3 },
  air3_wide: { name: "Air 3 Wide (24mm)", fov: 82, aspectRatio: 4 / 3 },
  mini4_wide: { name: "Mini 4 Pro (24mm)", fov: 82.1, aspectRatio: 4 / 3 },
  phantom4: { name: "Phantom 4 Pro (24mm)", fov: 73.7, aspectRatio: 3 / 2 },
};


function toNumber(value: unknown): number {
  if (typeof value === "number" && Number.isFinite(value)) {
    return value;
  }
  if (typeof value === "string" && value.trim().length > 0) {
    const parsed = Number(value);
    return Number.isFinite(parsed) ? parsed : Number.NaN;
  }
  return Number.NaN;
}

function toOptionalNumber(value: unknown): number | null {
  const parsed = toNumber(value);
  return Number.isFinite(parsed) ? parsed : null;
}

/**
 * Calculate bearing (heading) from point1 to point2 in degrees (0-360)
 * Uses the Haversine formula for accuracy over long distances
 */
function calculateBearing(lat1: number, lon1: number, lat2: number, lon2: number): number {
  const lat1Rad = (lat1 * Math.PI) / 180;
  const lat2Rad = (lat2 * Math.PI) / 180;
  const dLon = ((lon2 - lon1) * Math.PI) / 180;

  const y = Math.sin(dLon) * Math.cos(lat2Rad);
  const x = Math.cos(lat1Rad) * Math.sin(lat2Rad) -
            Math.sin(lat1Rad) * Math.cos(lat2Rad) * Math.cos(dLon);
  
  let bearing = Math.atan2(y, x);
  bearing = (bearing * 180) / Math.PI;
  bearing = (bearing + 360) % 360; // Normalize to 0-360
  
  return bearing;
}

function sanitizeRow(row: RawFlightRow): PreparedRow | null {
  const latitude = toNumber(row.latitude);
  const longitude = toNumber(row.longitude);
  const altitudeFt = toNumber(row["altitude(ft)"] ?? row.altitudeft ?? row.altitude);

  if (!Number.isFinite(latitude) || !Number.isFinite(longitude) || !Number.isFinite(altitudeFt)) {
    return null;
  }

  return {
    latitude,
    longitude,
    altitudeFt,
    headingDeg: toOptionalNumber(row["heading(deg)"] ?? row.headingdeg ?? row.heading),
    curveSizeFt: toOptionalNumber(row["curvesize(ft)"] ?? row.curvesizeft),
    rotationDir: toOptionalNumber(row.rotationdir),
    gimbalMode: toOptionalNumber(row.gimbalmode),
    gimbalPitchAngle: toOptionalNumber(row.gimbalpitchangle ?? row["gimbal_pitch(deg)"]),
    altitudeMode: toOptionalNumber(row.altitudemode),
    speedMs: toOptionalNumber(row["speed(m/s)"] ?? row.speedms ?? row.speed),
    poiLatitude: toOptionalNumber(row.poi_latitude ?? row.poi_latitude_deg),
    poiLongitude: toOptionalNumber(row.poi_longitude ?? row.poi_longitude_deg),
    poiAltitudeFt: toOptionalNumber(row["poi_altitude(ft)"] ?? row.poi_altitudeft),
    poiAltitudeMode: toOptionalNumber(row.poi_altitudemode),
    photoTimeInterval: toOptionalNumber(row.photo_timeinterval),
    photoDistInterval: toOptionalNumber(row.photo_distinterval),
  };
}

function buildSamples(samples: PreparedRow[]): { samples: ProcessedSample[]; poi: PoiData | null } {
  if (!samples.length) {
    return { samples: [], poi: null };
  }

  // First pass: create samples with indices
  const processedSamples: ProcessedSample[] = samples.map((sample, index) => ({
    ...sample,
    index,
  }));

  // Second pass: calculate heading angles from path when missing or zero
  for (let i = 0; i < processedSamples.length; i++) {
    const sample = processedSamples[i];
    
    // If heading is missing, null, or zero, calculate it from the flight path
    if (!sample.headingDeg || sample.headingDeg === 0) {
      let calculatedHeading: number | null = null;
      
      if (i < processedSamples.length - 1) {
        // For all points except the last, calculate bearing to next point
        const nextSample = processedSamples[i + 1];
        calculatedHeading = calculateBearing(
          sample.latitude,
          sample.longitude,
          nextSample.latitude,
          nextSample.longitude
        );
      } else if (i > 0) {
        // For the last point, use the bearing from the previous point
        const prevSample = processedSamples[i - 1];
        calculatedHeading = calculateBearing(
          prevSample.latitude,
          prevSample.longitude,
          sample.latitude,
          sample.longitude
        );
      }
      
      // Update the heading with calculated value
      if (calculatedHeading !== null) {
        sample.headingDeg = calculatedHeading;
      }
    }
  }

  const firstPoiSource = samples.find(entry =>
    Number.isFinite(entry.poiLatitude ?? Number.NaN) && Number.isFinite(entry.poiLongitude ?? Number.NaN),
  );

  let poi: PoiData | null = null;
  if (firstPoiSource && firstPoiSource.poiLatitude !== null && firstPoiSource.poiLongitude !== null) {
    const poiAltitudeFt = firstPoiSource.poiAltitudeFt ?? samples[0].altitudeFt;
    poi = {
      latitude: firstPoiSource.poiLatitude,
      longitude: firstPoiSource.poiLongitude,
      altitudeFt: poiAltitudeFt,
      altitudeMode: firstPoiSource.poiAltitudeMode,
    };
  }

  return { samples: processedSamples, poi };
}

async function parseKMZFile(file: File): Promise<PreparedRow[]> {
  const zip = await JSZip.loadAsync(file);
  const wpmlFile = zip.file("wpmz/waylines.wpml");
  if (!wpmlFile) {
    throw new Error("No waylines.wpml found in KMZ");
  }

  const xmlContent = await wpmlFile.async("string");
  const parser = new XMLParser({ ignoreAttributes: false });
  const parsed = parser.parse(xmlContent);

  const placemarks = parsed?.kml?.Document?.Folder?.Placemark;
  if (!placemarks) {
    throw new Error("No waypoints found in KMZ");
  }

  const waypointArray = Array.isArray(placemarks) ? placemarks : [placemarks];
  const rows: PreparedRow[] = [];

  for (const mark of waypointArray) {
    const coords = mark?.Point?.coordinates;
    const executeHeight = mark?.["wpml:executeHeight"];
    const speed = mark?.["wpml:waypointSpeed"];
    const heading = mark?.["wpml:waypointHeadingParam"]?.["wpml:waypointHeadingAngle"];
    const poiPoint = mark?.["wpml:waypointHeadingParam"]?.["wpml:waypointPoiPoint"];

    let gimbalPitch: number | null = null;
    const actionGroups = mark?.["wpml:actionGroup"];
    const groups = Array.isArray(actionGroups) ? actionGroups : actionGroups ? [actionGroups] : [];
    for (const group of groups) {
      const action = group?.["wpml:action"];
      const actions = Array.isArray(action) ? action : action ? [action] : [];
      for (const act of actions) {
        const func = act?.["wpml:actionActuatorFunc"];
        if (func === "gimbalRotate" || func === "gimbalEvenlyRotate") {
          const pitch = act?.["wpml:actionActuatorFuncParam"]?.["wpml:gimbalPitchRotateAngle"];
          if (pitch !== undefined && pitch !== null) {
            gimbalPitch = Number(pitch);
            break;
          }
        }
      }
      if (gimbalPitch !== null) {
        break;
      }
    }

    if (!coords || executeHeight === undefined || executeHeight === null) {
      continue;
    }

    const [lon, lat] = String(coords)
      .split(",")
      .map(value => Number(value));
    if (!Number.isFinite(lat) || !Number.isFinite(lon)) {
      continue;
    }

    const altitudeMeters = Number(executeHeight);
    const altitudeFt = altitudeMeters / FEET_TO_METERS;

    let poiLat: number | null = null;
    let poiLon: number | null = null;
    let poiAltFt: number | null = null;
    if (typeof poiPoint === "string") {
      const poiParts = poiPoint.split(",").map(Number);
      if (poiParts.length >= 3 && Number.isFinite(poiParts[0]) && Number.isFinite(poiParts[1])) {
        poiLat = poiParts[0];
        poiLon = poiParts[1];
        poiAltFt = poiParts[2] / FEET_TO_METERS;
      }
    }

    rows.push({
      latitude: lat,
      longitude: lon,
      altitudeFt,
      headingDeg: toOptionalNumber(heading),
      curveSizeFt: null,
      rotationDir: null,
      gimbalMode: null,
      gimbalPitchAngle: gimbalPitch,
      altitudeMode: null,
      speedMs: toOptionalNumber(speed),
      poiLatitude: poiLat,
      poiLongitude: poiLon,
      poiAltitudeFt: poiAltFt,
      poiAltitudeMode: null,
      photoTimeInterval: null,
      photoDistInterval: null,
    });
  }

  if (!rows.length) {
    throw new Error("KMZ file did not contain any waypoints");
  }

  return rows;
}

function computeStats(flight: FlightData | null) {
  if (!flight || flight.samples.length < 2) {
    return null;
  }

  const totalDistanceMeters = flight.samples.reduce((acc, sample, index) => {
    if (index === 0) {
      return 0;
    }
    const prev = flight.samples[index - 1];
    const horizontalDistance = haversineDistance(
      prev.latitude,
      prev.longitude,
      sample.latitude,
      sample.longitude,
    );
    const altitudeDiffMeters = (sample.altitudeFt - prev.altitudeFt) * FEET_TO_METERS;
    return acc + Math.sqrt(horizontalDistance ** 2 + altitudeDiffMeters ** 2);
  }, 0);

  const altitudeValues = flight.samples.map(sample => sample.altitudeFt);
  const maxAltitudeFt = Math.max(...altitudeValues);
  const minAltitudeFt = Math.min(...altitudeValues);

  const speedValues = flight.samples
    .map(sample => sample.speedMs)
    .filter((value): value is number => value !== null && Number.isFinite(value));

  const averageSpeedMs = speedValues.length
    ? speedValues.reduce((acc, value) => acc + value, 0) / speedValues.length
    : null;

  return {
    totalDistanceMeters,
    totalDistanceFeet: totalDistanceMeters / FEET_TO_METERS,
    maxAltitudeFt,
    minAltitudeFt,
    averageSpeedMs,
  };
}

function formatNumber(value: number, fractionDigits = 1): string {
  return new Intl.NumberFormat("en-US", { maximumFractionDigits: fractionDigits }).format(value);
}

function haversineDistance(lat1: number, lon1: number, lat2: number, lon2: number): number {
  const dLat = degreesToRadians(lat2 - lat1);
  const dLon = degreesToRadians(lon2 - lon1);
  const rLat1 = degreesToRadians(lat1);
  const rLat2 = degreesToRadians(lat2);
  const a =
    Math.sin(dLat / 2) ** 2 +
    Math.cos(rLat1) * Math.cos(rLat2) * Math.sin(dLon / 2) ** 2;
  const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
  return EARTH_RADIUS_METERS * c;
}

const tilesetUrl = (apiKey: string) => `https://tile.googleapis.com/v1/3dtiles/root.json?key=${apiKey}`;

function destinationLatLon(
  lat: number,
  lon: number,
  headingDeg: number,
  distanceMeters: number,
) {
  const angularDistance = distanceMeters / EARTH_RADIUS_METERS;
  const headingRad = degreesToRadians(headingDeg);
  const latRad = degreesToRadians(lat);
  const lonRad = degreesToRadians(lon);

  const sinLat = Math.sin(latRad);
  const cosLat = Math.cos(latRad);
  const sinAng = Math.sin(angularDistance);
  const cosAng = Math.cos(angularDistance);

  const destLat = Math.asin(
    sinLat * cosAng + cosLat * sinAng * Math.cos(headingRad),
  );
  const destLon =
    lonRad +
    Math.atan2(
      Math.sin(headingRad) * sinAng * cosLat,
      cosAng - sinLat * Math.sin(destLat),
    );

  return {
    lat: (destLat * 180) / Math.PI,
    lon: ((destLon * 180) / Math.PI + 540) % 360 - 180,
  };
}

function setPointPixelSize(
  Cesium: CesiumModule | null,
  entity: import("cesium").Entity | undefined,
  size: number,
) {
  if (!Cesium || !entity?.point) {
    return;
  }
  const property = entity.point.pixelSize as { setValue?: (value: number) => void } | undefined;
  if (property?.setValue) {
    property.setValue(size);
  } else {
    entity.point.pixelSize = new Cesium.ConstantProperty(size);
  }
}

function FlightPathScene({ flights, selectedLens, onWaypointHover }: FlightPathSceneProps): JSX.Element {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const viewerRef = useRef<import("cesium").Viewer | null>(null);
  const cesiumRef = useRef<CesiumModule | null>(null);
  const tilesetRef = useRef<import("cesium").Cesium3DTileset | null>(null);
  const flightEntitiesRef = useRef<import("cesium").Entity[]>([]);
  const handlerRef = useRef<import("cesium").ScreenSpaceEventHandler | null>(null);
  const hoverRef = useRef<{ flightId: string; index: number; key: string } | null>(null);
  const waypointEntityMapRef = useRef<Map<string, import("cesium").Entity>>(new Map());
  const resizeObserverRef = useRef<ResizeObserver | null>(null);
  const pixelSamplerCleanupRef = useRef<(() => void) | null>(null);
  const [initError, setInitError] = useState<string | null>(null);
  const [viewerReady, setViewerReady] = useState(false);

  const apiKey = process.env.NEXT_PUBLIC_GOOGLE_MAPS_API_KEY || "";
  const keySummary = useMemo(() => summarizeKey(apiKey), [apiKey]);

  useEffect(() => {
    log("info", "[Init] API key detected", { present: Boolean(apiKey), summary: keySummary });
  }, [apiKey, keySummary]);

  // Fetch terrain elevation for first waypoint via backend in prod/preview,
  // and via local Next API proxy in dev (avoids CORS in both cases)
  const fetchTerrainElevation = useCallback(async (lat: number, lon: number): Promise<number> => {
    try {
      // Use local proxy in dev to avoid CORS; otherwise use configured backend
      let elevationUrl: string;
      const isLocalHost = typeof window !== 'undefined' && (/^(localhost|127\.0\.0\.1)$/).test(window.location.hostname);
      if (isLocalHost) {
        elevationUrl = '/api/elevation-proxy';
      } else {
        elevationUrl = buildApiUrl.dronePath.elevation();
      }
      log("debug", "[Elevation] Fetching terrain elevation", { lat, lon, elevationUrl, isLocalHost });
      const response = await fetch(elevationUrl, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ center: `${lat}, ${lon}` }),
      });

      if (!response.ok) {
        log("error", "[Elevation] HTTP error", { status: response.status, statusText: response.statusText });
        return 0;
      }

      const data = await response.json();
      if (!data.elevation_meters) {
        log("error", "[Elevation] Missing response data", data);
        return 0;
      }

      const elevationMeters = data.elevation_meters;
      const elevationFeet = data.elevation_feet;
      log("info", "[Elevation] Terrain sample retrieved", {
        lat,
        lon,
        elevationMeters,
        elevationFeet,
      });
      return elevationMeters; // Return in meters for Cesium
    } catch (error) {
      log("error", "[Elevation] Fetch failed", error);
      return 0;
    }
  }, []);

  useEffect(() => {
    if (!apiKey) {
      log("error", "[Init] Missing Google Maps API key; photorealistic tiles cannot load");
      setInitError("missing-key");
      return;
    }
    if (!containerRef.current || viewerRef.current) {
      return;
    }

    let cancelled = false;

    (async () => {
      try {
        log("info", "[Init] Importing Cesium");
        const Cesium = await import("cesium");
        cesiumRef.current = Cesium;

        // Disable Cesium Ion
        Cesium.Ion.defaultAccessToken = "";

        // Set Cesium base URL
        if (typeof window !== "undefined") {
          window.CESIUM_BASE_URL = (window.CESIUM_BASE_URL ?? (typeof CESIUM_BASE_URL !== 'undefined' ? CESIUM_BASE_URL : "/cesium"));
        }

        log("info", "[Init] Creating viewer", {
          cesiumBaseUrl: window?.CESIUM_BASE_URL,
          containerReady: Boolean(containerRef.current),
        });

        const viewer = new Cesium.Viewer(containerRef.current, {
          imageryProvider: false as any,
          baseLayerPicker: false,
          geocoder: false,
          timeline: false,
          animation: false,
          navigationHelpButton: false,
          homeButton: false,
          infoBox: false,
          selectionIndicator: false,
          sceneModePicker: false,
          fullscreenButton: false,
          vrButton: false,
          navigationInstructionsInitiallyVisible: false,
          requestRenderMode: true,
          maximumRenderTimeChange: Infinity,
        } as any);
        
        // Hide Cesium credits
        if (viewer.cesiumWidget?.creditContainer) {
          const container = viewer.cesiumWidget.creditContainer as HTMLElement;
          if (container.style) {
            container.style.display = "none";
          }
        }

        pixelSamplerCleanupRef.current?.();
        pixelSamplerCleanupRef.current = attachPixelSampler(viewer, Cesium);

        log("info", "[Init] Viewer ready, configuring scene overrides");

        // Configure scene for photorealistic tiles only
        viewer.scene.globe.show = false;
        viewer.scene.skyAtmosphere.show = false;
        viewer.scene.skyBox.show = false;
        viewer.scene.backgroundColor = Cesium.Color.BLACK;
        viewer.scene.fog.enabled = false;
        viewer.imageryLayers.removeAll();
        
        // Enable depth testing for proper 3D rendering
        viewer.scene.globe.depthTestAgainstTerrain = false;
        
        viewerRef.current = viewer;
        
        // Force initial resize to fill container and set up resize observer
        if (containerRef.current) {
          viewer.resize();
          
          // Set up resize observer to handle container size changes
          resizeObserverRef.current = new ResizeObserver(() => {
            if (viewerRef.current) {
              viewerRef.current.resize();
            }
          });
          resizeObserverRef.current.observe(containerRef.current);
        }

        try {
          // Load Google Photorealistic 3D Tiles
          log("info", "[Tiles] Loading Google Photorealistic 3D Tiles", {
            tilesetUrl: tilesetUrl("<redacted>"),
            keySummary,
          });
          const tileset = await Cesium.Cesium3DTileset.fromUrl(
            `https://tile.googleapis.com/v1/3dtiles/root.json?key=${apiKey}`,
            {
              // Enable screen space error for better quality
              maximumScreenSpaceError: 16,
              // Don't show credits on screen (we'll handle attribution separately)
              showCreditsOnScreen: false,
              // Optimize loading
              skipLevelOfDetail: false,
              baseScreenSpaceError: 1024,
              skipScreenSpaceErrorFactor: 16,
              skipLevels: 1,
              immediatelyLoadDesiredLevelOfDetail: false,
              loadSiblings: false,
              cullWithChildrenBounds: true,
            }
          );
          
          if (cancelled) {
            tileset.destroy();
            return;
          }

          viewer.scene.primitives.add(tileset);
          tilesetRef.current = tileset;

          const tileLoadProgressEvent = (tileset as unknown as {
            tileLoadProgressEvent?: { addEventListener?: (cb: (pending: number) => void) => void };
          }).tileLoadProgressEvent;
          tileLoadProgressEvent?.addEventListener?.((pending: number) => {
            log("debug", "[Tiles] Load progress", { pending });
          });

          const readyPromise: Promise<unknown> | undefined = (tileset as any)?.readyPromise;
          readyPromise
            ?.then(() => {
              const tilesetAny = tileset as any;
              log("info", "[Tiles] readyPromise resolved", {
                boundingSphereRadius: tileset.boundingSphere?.radius,
                memoryUsageInBytes: tilesetAny?.totalMemoryUsageInBytes ?? tilesetAny?.memoryUsageInBytes ?? null,
              });
              viewer.scene.requestRender();
            })
            ?.catch((err: unknown) => {
              log("error", "[Tiles] readyPromise rejected", err);
            });

          // Wait for initial tiles to load
          tileset.initialTilesLoaded.addEventListener(() => {
            if (!cancelled && viewerRef.current) {
              viewerRef.current.scene.requestRender();
              setViewerReady(true);
              log("info", "[Tiles] Initial tiles loaded; viewer ready for rendering");
            }
          });

          // Handle tileset errors
          tileset.tileFailed.addEventListener((error: any) => {
            log("error", "[Tiles] Tile failed to load", error);
          });

        } catch (tilesetErr) {
          log("error", "[Tiles] Photorealistic tiles failed", tilesetErr);
          const message = tilesetErr instanceof Error ? tilesetErr.message : "";
          setInitError(message ? `tileset:${message}` : "tileset");
          // Still set viewer ready so we can show flight paths even without terrain
          setViewerReady(true);
          log("warn", "[Tiles] Using fallback rendering without photorealistic terrain", {
            errorMessage: tilesetErr instanceof Error ? tilesetErr.message : tilesetErr,
          });
        }

        // Set up mouse interaction for waypoint hover
        handlerRef.current = new Cesium.ScreenSpaceEventHandler(viewer.scene.canvas);
        handlerRef.current.setInputAction((movement: any) => {
          if (!viewerRef.current || !cesiumRef.current) {
            return;
          }
          const Cesium = cesiumRef.current;
          const picked = viewerRef.current.scene.pick(movement.endPosition);
          
          if (Cesium.defined(picked) && picked.id?.properties) {
            const props = picked.id.properties;
            const timestamp = Cesium.JulianDate.now();
            const flightId = props.flightId?.getValue?.(timestamp) ?? props.flightId;
            const index = props.index?.getValue?.(timestamp) ?? props.index;
            
            if (typeof flightId === "string" && typeof index === "number") {
              const key = `${flightId}:${index}`;
              if (!hoverRef.current || hoverRef.current.key !== key) {
                // Reset previous hover
                if (hoverRef.current) {
                  const previousEntity = waypointEntityMapRef.current.get(hoverRef.current.key);
                  setPointPixelSize(Cesium, previousEntity, 6);
                }
                // Set new hover
                const currentEntity = waypointEntityMapRef.current.get(key);
                setPointPixelSize(Cesium, currentEntity, 9);
                viewerRef.current?.scene.requestRender();
                onWaypointHover(flightId, index);
                hoverRef.current = { flightId, index, key };
              }
              return;
            }
          }

          // Clear hover if nothing picked
          if (hoverRef.current) {
            const previousEntity = waypointEntityMapRef.current.get(hoverRef.current.key);
            setPointPixelSize(Cesium, previousEntity, 6);
            onWaypointHover(hoverRef.current.flightId, null);
            hoverRef.current = null;
            viewerRef.current?.scene.requestRender();
          }
        }, Cesium.ScreenSpaceEventType.MOUSE_MOVE);
        
      } catch (err) {
        log("error", "[Init] Cesium initialization failed", err);
        setInitError("init");
      }
    })();

    return () => {
      cancelled = true;

      pixelSamplerCleanupRef.current?.();
      pixelSamplerCleanupRef.current = null;

      // Clear hover highlight BEFORE destroying Cesium objects
      if (hoverRef.current) {
        const previousEntity = waypointEntityMapRef.current.get(hoverRef.current.key);
        setPointPixelSize(cesiumRef.current, previousEntity, 6);
        onWaypointHover(hoverRef.current.flightId, null);
        hoverRef.current = null;
      }

      // Remove entities while viewer is still alive
      if (viewerRef.current) {
        try {
          flightEntitiesRef.current.forEach((entity) => {
            try {
              viewerRef.current?.entities.remove(entity);
            } catch (_) {
              // ignore if already removed
            }
          });
        } finally {
          flightEntitiesRef.current = [];
        }
      } else {
        flightEntitiesRef.current = [];
      }
      waypointEntityMapRef.current.clear();

      // Disconnect observers/handlers
      if (resizeObserverRef.current) {
        resizeObserverRef.current.disconnect();
        resizeObserverRef.current = null;
      }
      if (handlerRef.current && typeof (handlerRef.current as any).isDestroyed === 'function') {
        if (!(handlerRef.current as any).isDestroyed()) {
          handlerRef.current.destroy();
        }
      } else if (handlerRef.current) {
        // Some builds may not expose isDestroyed on handler
        try { handlerRef.current.destroy(); } catch (_) {}
      }
      handlerRef.current = null;

      // Remove/destroy tileset before destroying the viewer
      if (tilesetRef.current) {
        try {
          if (viewerRef.current && !(viewerRef.current as any).isDestroyed?.()) {
            try { viewerRef.current.scene.primitives.remove(tilesetRef.current); } catch (_) {}
          }
        } catch (_) {}
        try {
          if (typeof (tilesetRef.current as any).isDestroyed === 'function') {
            if (!(tilesetRef.current as any).isDestroyed()) {
              tilesetRef.current.destroy();
            }
          } else {
            (tilesetRef.current as any).destroy?.();
          }
        } catch (_) {}
      }
      tilesetRef.current = null;

      // Finally destroy the viewer (after clearing tweens/datasources)
      if (viewerRef.current) {
        try { (viewerRef.current as any).scene?.tweens?.removeAll?.(); } catch (_) {}
        try { (viewerRef.current as any).dataSources?.removeAll?.(); } catch (_) {}
        try { (viewerRef.current as any).entities?.removeAll?.(); } catch (_) {}
        try {
          if (typeof (viewerRef.current as any).isDestroyed === 'function') {
            if (!(viewerRef.current as any).isDestroyed()) {
              viewerRef.current.destroy();
            }
          } else {
            (viewerRef.current as any).destroy?.();
          }
        } catch (_) {}
      }
      viewerRef.current = null;

      setViewerReady(false);
    };
  }, [apiKey, onWaypointHover]);

  useEffect(() => {
    const initialViewer = viewerRef.current;
    const Cesium = cesiumRef.current;
    if (!initialViewer || !Cesium || !viewerReady) {
      return;
    }

    let disposed = false;

    flightEntitiesRef.current.forEach(entity => initialViewer.entities.remove(entity));
    flightEntitiesRef.current = [];
    if (hoverRef.current) {
      const previousEntity = waypointEntityMapRef.current.get(hoverRef.current.key);
      setPointPixelSize(Cesium, previousEntity, 6);
      onWaypointHover(hoverRef.current.flightId, null);
      hoverRef.current = null;
    }
    waypointEntityMapRef.current.clear();

    if (!flights.length) {
      const v = viewerRef.current as any;
      if (!disposed && v && !(v.isDestroyed?.())) {
        try { v.scene.requestRender(); } catch {}
      }
      return;
    }

    const lensSpec = DRONE_LENSES[selectedLens] ?? DRONE_LENSES.mavic3_wide;
    const forwardDistanceBase = Math.max(20, 40 - lensSpec.fov * 0.2);

    const positionsForFit: import("cesium").Cartesian3[] = [];

    log("info", "[Render] Preparing scene entities", {
      flights: flights.length,
      totalSamples: flights.reduce((acc, f) => acc + f.samples.length, 0),
      selectedLens,
      forwardDistanceBase,
    });

    // Use Google Elevation API to get terrain height at first waypoint only
    // Then apply that offset to all waypoints (they're already AGL-relative to each other)
    if (flights.length > 0 && flights[0].samples.length > 0) {
      const firstWaypoint = flights[0].samples[0];
      
      fetchTerrainElevation(firstWaypoint.latitude, firstWaypoint.longitude)
        .then((terrainElevationMeters) => {
          if (disposed) return;
          const viewer = viewerRef.current as any;
          if (!viewer || viewer.isDestroyed?.()) return;
          log("info", "[Render] Applying terrain offset", {
            terrainElevationMeters,
            terrainElevationFeet: terrainElevationMeters * 3.28084,
            flights: flights.length,
          });

          flights.forEach(flight => {
            const positions: import("cesium").Cartesian3[] = [];

            flight.samples.forEach((sample) => {
              const aglHeightMeters = sample.altitudeFt * FEET_TO_METERS; // Flight altitude AGL
              const absoluteHeightMSL = terrainElevationMeters + aglHeightMeters; // MSL = terrain + AGL

              const position = Cesium.Cartesian3.fromDegrees(
                sample.longitude,
                sample.latitude,
                absoluteHeightMSL
              );
              positions.push(position);
            });

            // Render using terrain-corrected positions
            if (positions.length >= 2) {
              const path = viewer.entities.add({
                polyline: {
                  positions,
                  width: 2.2,
                  material: Cesium.Color.fromCssColorString(flight.color).withAlpha(0.95),
                  arcType: Cesium.ArcType.GEODESIC,
                },
              });
              flightEntitiesRef.current.push(path);
            }

            positions.forEach((position, index) => {
              const waypointEntity = viewer.entities.add({
                position,
                point: {
                  pixelSize: 6,
                  color: Cesium.Color.fromCssColorString(flight.color),
                  outlineColor: Cesium.Color.fromCssColorString("#182036"),
                  outlineWidth: 1,
                },
                properties: {
                  flightId: flight.id,
                  index,
                },
              });
              flightEntitiesRef.current.push(waypointEntity);
              waypointEntityMapRef.current.set(`${flight.id}:${index}`, waypointEntity);

              const headingDeg = flight.samples[index].headingDeg ?? 0;
              const pitchDeg = flight.samples[index].gimbalPitchAngle ?? -45;
              const forwardDistance = forwardDistanceBase;
              const horizontalDistance = forwardDistance * Math.cos(degreesToRadians(pitchDeg));
              const verticalOffset = forwardDistance * Math.sin(degreesToRadians(pitchDeg));
              const destination = destinationLatLon(
                flight.samples[index].latitude,
                flight.samples[index].longitude,
                headingDeg,
                horizontalDistance,
              );

              // Use same terrain offset for frustum target
              const targetAbsoluteHeight = terrainElevationMeters + (flight.samples[index].altitudeFt * FEET_TO_METERS) + verticalOffset;

              const target = Cesium.Cartesian3.fromDegrees(
                destination.lon,
                destination.lat,
                targetAbsoluteHeight,
              );

              const frustumLine = viewer.entities.add({
                polyline: {
                  positions: [position, target],
                  width: 1.4,
                  material: Cesium.Color.fromCssColorString(flight.color).withAlpha(0.55),
                },
                properties: {
                  flightId: flight.id,
                  index,
                },
              });
              flightEntitiesRef.current.push(frustumLine);
            });

            if (flight.poi) {
              // Use same terrain offset for POI
              const poiAltitudeFt = flight.poi.altitudeFt ?? flight.samples[0]?.altitudeFt ?? 0;
              const poiAbsoluteHeight = terrainElevationMeters + (poiAltitudeFt * FEET_TO_METERS);

              const poiEntity = viewer.entities.add({
                position: Cesium.Cartesian3.fromDegrees(
                  flight.poi.longitude,
                  flight.poi.latitude,
                  poiAbsoluteHeight,
                ),
                point: {
                  pixelSize: 10,
                  color: Cesium.Color.fromCssColorString("#ffbb00"),
                  outlineColor: Cesium.Color.fromCssColorString("#0b0e24"),
                  outlineWidth: 2,
                },
                label: {
                  text: "POI",
                  font: "14px 'Inter', sans-serif",
                  fillColor: Cesium.Color.WHITE,
                  outlineColor: Cesium.Color.fromCssColorString("#1b1f3b"),
                  outlineWidth: 3,
                  pixelOffset: new Cesium.Cartesian2(0, -20),
                  disableDepthTestDistance: Number.POSITIVE_INFINITY,
                },
              });
              flightEntitiesRef.current.push(poiEntity);
            }

            positionsForFit.push(...positions);
          });

          if (positionsForFit.length) {
            const boundingSphere = Cesium.BoundingSphere.fromPoints(positionsForFit);
            const expandedRadius = boundingSphere.radius * 2.5;
            const expandedSphere = new Cesium.BoundingSphere(boundingSphere.center, expandedRadius);

            log("debug", "[Render] Flying camera to bounding sphere", {
              radius: boundingSphere.radius,
              expandedRadius,
            });

            const onMoveEnd = () => {
              log("info", "[Render] Camera moved to bounding sphere", {
                expandedRadius,
                cameraPosition: viewer.camera.position,
              });
              viewer.camera.moveEnd.removeEventListener(onMoveEnd);
            };
            viewer.camera.moveEnd.addEventListener(onMoveEnd);
            try {
              viewer.camera.flyToBoundingSphere(expandedSphere, {
                duration: 1.5,
                offset: new Cesium.HeadingPitchRange(
                  0,
                  Cesium.Math.toRadians(-45), // Look down at 45 degrees
                  expandedRadius
                ),
              });
            } catch (error) {
              log("warn", "[Render] Failed to move camera to bounding sphere", error);
              viewer.camera.moveEnd.removeEventListener(onMoveEnd);
            }
          }

          try { viewer.scene.requestRender(); } catch {}
      })
      .catch((error: Error) => {
        log("error", "[Render] Elevation lookup failed; rendering without terrain correction", error);
          if (disposed) return;
          const viewer = viewerRef.current as any;
          if (!viewer || viewer.isDestroyed?.()) return;
        // Fallback: render without terrain correction (AGL as MSL)
        flights.forEach(flight => {
          const positions = flight.samples.map(sample =>
            Cesium.Cartesian3.fromDegrees(sample.longitude, sample.latitude, sample.altitudeFt * FEET_TO_METERS)
          );

          if (positions.length >= 2) {
            const path = viewer.entities.add({
              polyline: {
                positions,
                width: 2.2,
                material: Cesium.Color.fromCssColorString(flight.color).withAlpha(0.95),
                arcType: Cesium.ArcType.GEODESIC,
              },
            });
            flightEntitiesRef.current.push(path);
          }

          positions.forEach((position, index) => {
            const waypointEntity = viewer.entities.add({
              position,
              point: {
                pixelSize: 6,
                color: Cesium.Color.fromCssColorString(flight.color),
                outlineColor: Cesium.Color.fromCssColorString("#182036"),
                outlineWidth: 1,
              },
              properties: {
                flightId: flight.id,
                index,
              },
            });
            flightEntitiesRef.current.push(waypointEntity);
            waypointEntityMapRef.current.set(`${flight.id}:${index}`, waypointEntity);
          });

          positionsForFit.push(...positions);
        });

        if (positionsForFit.length) {
          const boundingSphere = Cesium.BoundingSphere.fromPoints(positionsForFit);
          const expandedRadius = boundingSphere.radius * 2.5;
          const expandedSphere = new Cesium.BoundingSphere(boundingSphere.center, expandedRadius);

          log("debug", "[Render] Fallback camera flyTo bounding sphere", {
            radius: boundingSphere.radius,
            expandedRadius,
          });

          const onMoveEnd = () => {
            log("info", "[Render] Fallback camera move complete", {
              expandedRadius,
              cameraPosition: viewer.camera.position,
            });
            viewer.camera.moveEnd.removeEventListener(onMoveEnd);
          };
          viewer.camera.moveEnd.addEventListener(onMoveEnd);
          try {
            viewer.camera.flyToBoundingSphere(expandedSphere, {
              duration: 1.5,
              offset: new Cesium.HeadingPitchRange(
                0,
                Cesium.Math.toRadians(-45),
                expandedRadius
              ),
            });
          } catch (error) {
            log("warn", "[Render] Fallback camera movement failed", error);
            viewer.camera.moveEnd.removeEventListener(onMoveEnd);
          }
        }

        try { viewer.scene.requestRender(); } catch {}
      });
    }
    return () => { disposed = true; };
  }, [flights, selectedLens, viewerReady, fetchTerrainElevation]);

  if (!apiKey) {
    return (
      <div className="flight-viewer__map-placeholder">
        <p>Google Maps API key missing. Set NEXT_PUBLIC_GOOGLE_MAPS_API_KEY to enable photorealistic terrain.</p>
      </div>
    );
  }

  return (
    <div className="flight-viewer__map-container">
      <div ref={containerRef} className="flight-viewer__cesium-canvas" />
      {initError && (
        <div className="flight-viewer__map-warning">
          <strong>3D view unavailable.</strong>
          {" "}
          {initError === "missing-key"
            ? "Add a Google Maps API key to render photorealistic terrain."
            : initError.startsWith("tileset")
            ? `Photorealistic tiles failed to load (${initError.split(":").slice(1).join(":") || "check Map Tiles API access"}).`
            : "WebGL initialization failed."}
        </div>
      )}
    </div>
  );
}
export default function FlightViewerPage(): JSX.Element {
  const [flights, setFlights] = useState<FlightData[]>([]);
  const [status, setStatus] = useState<string | null>(null);
  const [isParsing, setIsParsing] = useState(false);
  // Camera/lens state
  const [selectedLens, setSelectedLens] = useState("mavic3_wide");
  const [hoveredWaypoint, setHoveredWaypoint] = useState<{ flightId: string; index: number } | null>(null);
  
  // Converter modal state
  const [showConverter, setShowConverter] = useState(false);
  const [converterFile, setConverterFile] = useState<File | null>(null);
  const [converting, setConverting] = useState(false);
  const [converterStatus, setConverterStatus] = useState<string | null>(null);
  const [converterOptions, setConverterOptions] = useState({
    signalLostAction: "executeLostAction" as "continue" | "executeLostAction",
    missionSpeed: 8.85,
    droneType: "dji_fly" as "dji_fly" | "mavic3_enterprise" | "matrice_30",
    headingMode: "poi_or_interpolate" as "poi_or_interpolate" | "follow_wayline" | "manual",
    allowStraightLines: false,
  });

  const onFilesSelected = useCallback(async (event: ChangeEvent<HTMLInputElement>) => {
    const fileList = event.target.files;
    if (!fileList || fileList.length === 0) {
      return;
    }

    setIsParsing(true);
    setStatus(null);

    const newFlights: FlightData[] = [];
    const errors: string[] = [];

    for (let i = 0; i < fileList.length; i += 1) {
      const file = fileList[i];
      const extension = file.name.toLowerCase().split(".").pop();

      try {
        let prepared: PreparedRow[] = [];

        if (extension === "kmz") {
          prepared = await parseKMZFile(file);
        } else if (extension === "csv") {
          await new Promise<void>((resolve, reject) => {
            Papa.parse<RawFlightRow>(file, {
              header: true,
              skipEmptyLines: true,
              dynamicTyping: true,
              complete: result => {
                if (result.errors.length) {
                  reject(new Error(`CSV parse error: ${result.errors[0].message}`));
                  return;
                }
                prepared = result.data
                  .map(sanitizeRow)
                  .filter((value): value is PreparedRow => value !== null);
                resolve();
              },
              error: err => reject(err),
            });
          });
        } else {
          errors.push(`${file.name}: Unsupported format (use .csv or .kmz)`);
          continue;
        }

        if (!prepared.length) {
          errors.push(`${file.name}: No valid waypoints found`);
          continue;
        }

        const { samples, poi } = buildSamples(prepared);

        const flightId = `${Date.now()}-${i}`;
        const colorIndex = (flights.length + newFlights.length) % FLIGHT_COLORS.length;

        newFlights.push({
          id: flightId,
          name: file.name,
          color: FLIGHT_COLORS[colorIndex],
          samples,
          poi,
        });
      } catch (err) {
        errors.push(`${file.name}: ${err instanceof Error ? err.message : "Unknown error"}`);
      }
    }

    setIsParsing(false);

    if (newFlights.length > 0) {
      setFlights(prev => [...prev, ...newFlights]);
      setStatus(null);
    }

    if (errors.length > 0 && newFlights.length === 0) {
      setStatus(errors.join("; "));
    }
  }, [flights.length]);

  const removeFlight = useCallback((id: string) => {
    setFlights(prev => prev.filter(f => f.id !== id));
  }, []);

  const clearAll = useCallback(() => {
    setFlights([]);
    setStatus(null);
  }, []);

  const handleWaypointHover = useCallback((flightId: string, waypointIndex: number | null) => {
    if (waypointIndex === null) {
      setHoveredWaypoint(null);
    } else {
      setHoveredWaypoint({ flightId, index: waypointIndex });
    }
  }, []);

  const hoveredData = useMemo(() => {
    if (!hoveredWaypoint) return null;
    const flight = flights.find(f => f.id === hoveredWaypoint.flightId);
    if (!flight) return null;
    const sample = flight.samples[hoveredWaypoint.index];
    if (!sample) return null;
    return { flight, sample };
  }, [hoveredWaypoint, flights]);

  const handleConvertFile = useCallback(async () => {
    if (!converterFile) return;
    
    setConverting(true);
    setConverterStatus(null);

    try {
      const csvContent = await converterFile.text();
      const kmzBlob = await convertLitchiCSVToKMZ(
        csvContent,
        converterFile.name,
        converterOptions
      );

      const outputName = converterFile.name.replace(/\.csv$/i, ".kmz");
      downloadBlob(kmzBlob, outputName);
      
      setConverterStatus(`Converted to ${outputName}`);
      setTimeout(() => {
        setShowConverter(false);
        setConverterFile(null);
        setConverterStatus(null);
      }, 2000);
    } catch (err) {
      setConverterStatus(`Error: ${err instanceof Error ? err.message : "Conversion failed"}`);
    } finally {
      setConverting(false);
    }
  }, [converterFile, converterOptions]);

  return (
    <main className="flight-viewer">
      <div className="flight-viewer__intro">
        <div>
          <h1>Flight Viewer</h1>
          <p>Upload CSV or KMZ files to compare paths, inspect curvature, and verify coordinates in 3D.</p>
        </div>
        <button 
          className="flight-viewer__converter-btn"
          onClick={() => setShowConverter(true)}
        >
          Convert CSV to KMZ
        </button>
      </div>

      <section className="flight-viewer__content">
        <aside className="flight-viewer__sidebar">
          <label className="flight-viewer__upload">
            <span className="flight-viewer__upload-title">Add flight files</span>
            <span className="flight-viewer__upload-hint">Support for CSV (Litchi/DJI) and KMZ (DJI WPML) formats. Select multiple files to overlay paths.</span>
            <input
              type="file"
              accept=".csv,text/csv,.kmz,application/vnd.google-earth.kmz"
              multiple
              onChange={onFilesSelected}
              disabled={isParsing}
            />
          </label>

          {isParsing && <p className="flight-viewer__status">Parsing files...</p>}
          {status && !isParsing && <p className="flight-viewer__status flight-viewer__status--error">{status}</p>}

          {flights.length > 0 && (
            <>
              <div className="flight-viewer__flight-list">
                <div className="flight-viewer__flight-list-header">
                  <h3>Loaded Flights ({flights.length})</h3>
                  <button onClick={clearAll} className="flight-viewer__clear-btn">Clear All</button>
                </div>
                {flights.map(flight => {
                  const stats = computeStats(flight);
                  return (
                    <div key={flight.id} className="flight-viewer__flight-item">
                      <div className="flight-viewer__flight-item-header">
                        <div className="flight-viewer__flight-color" style={{ backgroundColor: flight.color }} />
                        <span className="flight-viewer__flight-name">{flight.name}</span>
                        <button 
                          onClick={() => removeFlight(flight.id)} 
                          className="flight-viewer__remove-btn"
                          aria-label={`Remove ${flight.name}`}
                        >
                          x
                        </button>
                      </div>
                      <div className="flight-viewer__flight-stats">
                        <span>{flight.samples.length} pts</span>
                        {stats && (
                          <>
                            <span>-</span>
                            <span>{formatNumber(stats.totalDistanceMeters, 0)}m</span>
                            <span>-</span>
                            <span>{formatNumber(stats.minAltitudeFt, 0)}-{formatNumber(stats.maxAltitudeFt, 0)}ft</span>
                          </>
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>
            </>
          )}

          {flights.length === 0 && !isParsing && (
            <div className="flight-viewer__details flight-viewer__details--placeholder">
              <h2>How it works</h2>
              <ul>
                <li>Upload CSV (Litchi/DJI) or KMZ (DJI WPML) flight plans.</li>
                <li>All paths share a common reference point for accurate overlays.</li>
                <li>Metric and imperial units are automatically converted.</li>
                <li>Each flight gets a unique color for easy comparison.</li>
              </ul>
            </div>
          )}
        </aside>

        <div className="flight-viewer__visualizer" aria-live="polite">
          {flights.length > 0 && (
            <div className="flight-viewer__controls">
              <label className="flight-viewer__lens-select">
                <span>Camera Lens:</span>
                <select value={selectedLens} onChange={(e) => setSelectedLens(e.target.value)}>
                  {Object.entries(DRONE_LENSES).map(([key, lens]) => (
                    <option key={key} value={key}>
                      {lens.name}
                    </option>
                  ))}
                </select>
              </label>
            </div>
          )}
          
          {hoveredData && (
            <div className="flight-viewer__tooltip">
              <div className="flight-viewer__tooltip-header">
                <span className="flight-viewer__tooltip-marker" style={{ background: hoveredData.flight.color }} />
                <strong>{hoveredData.flight.name}</strong> - Waypoint {hoveredData.sample.index + 1}
              </div>
              <div className="flight-viewer__tooltip-body">
                <div className="flight-viewer__tooltip-row">
                  <span>Heading:</span>
                  <span>{hoveredData.sample.headingDeg?.toFixed(1) || "--"}deg</span>
                </div>
                <div className="flight-viewer__tooltip-row">
                  <span>Gimbal Pitch:</span>
                  <span>{hoveredData.sample.gimbalPitchAngle?.toFixed(1) || "--"}deg</span>
                </div>
                <div className="flight-viewer__tooltip-row">
                  <span>Altitude:</span>
                  <span>{hoveredData.sample.altitudeFt.toFixed(1)} ft</span>
                </div>
                <div className="flight-viewer__tooltip-row">
                  <span>Speed:</span>
                  <span>{hoveredData.sample.speedMs?.toFixed(1) || "--"} m/s</span>
                </div>
              </div>
            </div>
          )}
          
          {flights.length > 0 ? (
            <FlightPathScene
              flights={flights}
              selectedLens={selectedLens}
              onWaypointHover={handleWaypointHover}
            />
          ) : (
            <div className="flight-viewer__placeholder">
              <div className="flight-viewer__placeholder-inner">
                <p>Select flight files to render their 3D trajectories.</p>
              </div>
            </div>
          )}
        </div>
      </section>

      {showConverter && (
        <div className="flight-viewer__modal-overlay" onClick={() => setShowConverter(false)}>
          <div className="flight-viewer__modal" onClick={(e) => e.stopPropagation()}>
            <div className="flight-viewer__modal-header">
              <h2>CSV to KMZ Converter</h2>
              <button 
                className="flight-viewer__modal-close"
                onClick={() => setShowConverter(false)}
              >
                x
              </button>
            </div>

            <div className="flight-viewer__modal-body">
              <p className="flight-viewer__modal-description">
                Convert Litchi CSV waypoint missions to DJI Fly/Pilot 2 compatible KMZ files.
              </p>

              <label className="flight-viewer__converter-upload">
                <span>Select Litchi CSV file</span>
                <input
                  type="file"
                  accept=".csv,text/csv"
                  onChange={(e) => setConverterFile(e.target.files?.[0] || null)}
                />
              </label>

              {converterFile && (
                <div className="flight-viewer__converter-file">
                  {converterFile.name}
                </div>
              )}

              <div className="flight-viewer__converter-options">
                <label>
                  <span>Signal Lost Action</span>
                  <select
                    value={converterOptions.signalLostAction}
                    onChange={(e) => setConverterOptions(prev => ({
                      ...prev,
                      signalLostAction: e.target.value as "continue" | "executeLostAction"
                    }))}
                  >
                    <option value="executeLostAction">Execute Lost Action</option>
                    <option value="continue">Continue Mission</option>
                  </select>
                </label>

                <label>
                  <span>Mission Speed (m/s)</span>
                  <input
                    type="number"
                    min="1"
                    max="15"
                    step="0.1"
                    value={converterOptions.missionSpeed}
                    onChange={(e) => setConverterOptions(prev => ({
                      ...prev,
                      missionSpeed: parseFloat(e.target.value)
                    }))}
                  />
                </label>

                <label>
                  <span>Drone Type</span>
                  <select
                    value={converterOptions.droneType}
                    onChange={(e) => setConverterOptions(prev => ({
                      ...prev,
                      droneType: e.target.value as any
                    }))}
                  >
                    <option value="dji_fly">DJI Fly (Consumer)</option>
                    <option value="mavic3_enterprise">Mavic 3 Enterprise</option>
                    <option value="matrice_30">Matrice 30</option>
                  </select>
                </label>

                <label>
                  <span>Heading Mode</span>
                  <select
                    value={converterOptions.headingMode}
                    onChange={(e) => setConverterOptions(prev => ({
                      ...prev,
                      headingMode: e.target.value as any
                    }))}
                  >
                    <option value="poi_or_interpolate">Toward POI / Interpolate</option>
                    <option value="follow_wayline">Follow Wayline</option>
                    <option value="manual">Manual</option>
                  </select>
                </label>

                <label className="flight-viewer__converter-checkbox">
                  <input
                    type="checkbox"
                    checked={converterOptions.allowStraightLines}
                    onChange={(e) => setConverterOptions(prev => ({
                      ...prev,
                      allowStraightLines: e.target.checked
                    }))}
                  />
                  <span>Allow Straight Lines (may show incorrectly in DJI Fly)</span>
                </label>
              </div>

              {converterStatus && (
              <div className={`flight-viewer__converter-status ${converterStatus.startsWith("Converted") ? "success" : "error"}`}>
                  {converterStatus}
                </div>
              )}

              <div className="flight-viewer__modal-actions">
                <button
                  className="flight-viewer__modal-btn secondary"
                  onClick={() => setShowConverter(false)}
                  disabled={converting}
                >
                  Cancel
                </button>
                <button
                  className="flight-viewer__modal-btn primary"
                  onClick={handleConvertFile}
                  disabled={!converterFile || converting}
                >
                  {converting ? "Converting..." : "Convert & Download"}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

    </main>
  );
}
