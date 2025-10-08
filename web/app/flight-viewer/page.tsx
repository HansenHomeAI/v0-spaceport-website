"use client";

import React, { ChangeEvent, useCallback, useMemo, useState, useEffect, useRef } from "react";
import Papa from "papaparse";
import JSZip from "jszip";
import { XMLParser } from "fast-xml-parser";
import { convertLitchiCSVToKMZ, downloadBlob } from "../../lib/flightConverter";
import { buildApiUrl } from "../api-config";

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

  const processedSamples: ProcessedSample[] = samples.map((sample, index) => ({
    ...sample,
    index,
  }));

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
  const [initError, setInitError] = useState<string | null>(null);
  const [viewerReady, setViewerReady] = useState(false);

  const apiKey = process.env.NEXT_PUBLIC_GOOGLE_MAPS_API_KEY || "";

  // Fetch terrain elevation for first waypoint via our backend (avoids CORS)
  const fetchTerrainElevation = useCallback(async (lat: number, lon: number): Promise<number> => {
    try {
      const elevationUrl = buildApiUrl.dronePath.elevation();
      const response = await fetch(elevationUrl, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ center: `${lat}, ${lon}` }),
      });
      
      if (!response.ok) {
        console.error('[FlightViewer] Elevation API HTTP error:', response.status);
        return 0;
      }
      
      const data = await response.json();
      if (!data.elevation_meters) {
        console.error('[FlightViewer] Elevation API missing data:', data);
        return 0;
      }
      
      const elevationMeters = data.elevation_meters;
      const elevationFeet = data.elevation_feet;
      console.log(`[FlightViewer] Terrain elevation at first waypoint: ${elevationFeet.toFixed(1)}ft (${elevationMeters.toFixed(1)}m)`);
      return elevationMeters; // Return in meters for Cesium
    } catch (error) {
      console.error('[FlightViewer] Elevation API error:', error);
      return 0;
    }
  }, []);

  useEffect(() => {
    if (!apiKey) {
      setInitError("missing-key");
      return;
    }
    if (!containerRef.current || viewerRef.current) {
      return;
    }

    let cancelled = false;

    (async () => {
      try {
        const Cesium = await import("cesium");
        cesiumRef.current = Cesium;
        
        // Disable Cesium Ion
        Cesium.Ion.defaultAccessToken = "";
        
        // Set Cesium base URL
        if (typeof window !== "undefined") {
          window.CESIUM_BASE_URL = (window.CESIUM_BASE_URL ?? (typeof CESIUM_BASE_URL !== 'undefined' ? CESIUM_BASE_URL : "/cesium"));
        }

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

          // Wait for initial tiles to load
          tileset.initialTilesLoaded.addEventListener(() => {
            if (!cancelled && viewerRef.current) {
              viewerRef.current.scene.requestRender();
              setViewerReady(true);
            }
          });

          // Handle tileset errors
          tileset.tileFailed.addEventListener((error: any) => {
            console.error("[FlightPathScene] Tile failed to load", error);
          });

        } catch (tilesetErr) {
          console.error("[FlightPathScene] Photorealistic tiles failed", tilesetErr);
          const message = tilesetErr instanceof Error ? tilesetErr.message : "";
          setInitError(message ? `tileset:${message}` : "tileset");
          // Still set viewer ready so we can show flight paths even without terrain
          setViewerReady(true);
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
        console.error("[FlightPathScene] Cesium initialization failed", err);
        setInitError("init");
      }
    })();

    return () => {
      cancelled = true;
      if (resizeObserverRef.current) {
        resizeObserverRef.current.disconnect();
        resizeObserverRef.current = null;
      }
      if (handlerRef.current) {
        handlerRef.current.destroy();
        handlerRef.current = null;
      }
      flightEntitiesRef.current.forEach(entity => viewerRef.current?.entities.remove(entity));
      flightEntitiesRef.current = [];
      if (tilesetRef.current) {
        tilesetRef.current.destroy();
        tilesetRef.current = null;
      }
      if (viewerRef.current) {
        viewerRef.current.destroy();
        viewerRef.current = null;
      }
      if (hoverRef.current) {
        const previousEntity = waypointEntityMapRef.current.get(hoverRef.current.key);
        setPointPixelSize(cesiumRef.current, previousEntity, 6);
        onWaypointHover(hoverRef.current.flightId, null);
        hoverRef.current = null;
      }
      waypointEntityMapRef.current.clear();
      setViewerReady(false);
    };
  }, [apiKey, onWaypointHover]);

  useEffect(() => {
    const viewer = viewerRef.current;
    const Cesium = cesiumRef.current;
    if (!viewer || !Cesium || !viewerReady) {
      return;
    }

    flightEntitiesRef.current.forEach(entity => viewer.entities.remove(entity));
    flightEntitiesRef.current = [];
    if (hoverRef.current) {
      const previousEntity = waypointEntityMapRef.current.get(hoverRef.current.key);
      setPointPixelSize(Cesium, previousEntity, 6);
      onWaypointHover(hoverRef.current.flightId, null);
      hoverRef.current = null;
    }
    waypointEntityMapRef.current.clear();

    if (!flights.length) {
      viewer.scene.requestRender();
      return;
    }

    const lensSpec = DRONE_LENSES[selectedLens] ?? DRONE_LENSES.mavic3_wide;
    const forwardDistanceBase = Math.max(20, 40 - lensSpec.fov * 0.2);

    const positionsForFit: import("cesium").Cartesian3[] = [];

    // Use Google Elevation API to get terrain height at first waypoint only
    // Then apply that offset to all waypoints (they're already AGL-relative to each other)
    if (flights.length > 0 && flights[0].samples.length > 0) {
      const firstWaypoint = flights[0].samples[0];
      
      fetchTerrainElevation(firstWaypoint.latitude, firstWaypoint.longitude)
        .then((terrainElevationMeters) => {
          console.log(`[FlightViewer] Applying terrain offset: ${(terrainElevationMeters * 3.28084).toFixed(1)}ft to all waypoints`);
          
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

          // Add buffer to the bounding sphere for better view
          const expandedRadius = boundingSphere.radius * 2.5;
          const expandedSphere = new Cesium.BoundingSphere(boundingSphere.center, expandedRadius);

          viewer.camera.flyToBoundingSphere(expandedSphere, {
            duration: 1.5,
            offset: new Cesium.HeadingPitchRange(
              0,
              Cesium.Math.toRadians(-45), // Look down at 45 degrees
              expandedRadius
            ),
          });
        }

        viewer.scene.requestRender();
      })
      .catch((error: Error) => {
        console.error('[FlightViewer] Google Elevation API failed, rendering without terrain correction:', error);
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

          viewer.camera.flyToBoundingSphere(expandedSphere, {
            duration: 1.5,
            offset: new Cesium.HeadingPitchRange(
              0,
              Cesium.Math.toRadians(-45),
              expandedRadius
            ),
          });
        }

        viewer.scene.requestRender();
      });
    }
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

      <style jsx>{`
        .flight-viewer {
          display: flex;
          flex-direction: column;
          gap: 2rem;
          padding: 4rem clamp(1.5rem, 4vw, 4rem);
          color: #f5f6fb;
          background: radial-gradient(circle at top, #0b0b1a, #030309 55%);
          min-height: calc(100vh - 160px);
        }

        .flight-viewer__intro {
          display: flex;
          align-items: center;
          gap: 2rem;
          flex-wrap: wrap;
        }

        .flight-viewer__intro > div {
          flex: 1;
        }

        .flight-viewer__intro h1 {
          margin: 0;
          font-size: clamp(2rem, 2.8vw, 3rem);
          font-weight: 600;
        }

        .flight-viewer__intro p {
          margin-top: 0.5rem;
          max-width: 40rem;
          line-height: 1.5;
          color: rgba(220, 224, 255, 0.75);
        }

        .flight-viewer__converter-btn {
          background: linear-gradient(135deg, #4f83ff 0%, #3d6dd9 100%);
          border: 1px solid rgba(79, 131, 255, 0.5);
          color: white;
          padding: 0.75rem 1.5rem;
          border-radius: 12px;
          font-size: 0.95rem;
          font-weight: 600;
          cursor: pointer;
          transition: all 0.2s ease;
          white-space: nowrap;
        }

        .flight-viewer__converter-btn:hover {
          transform: translateY(-2px);
          box-shadow: 0 8px 20px rgba(79, 131, 255, 0.3);
        }

        .flight-viewer__content {
          display: grid;
          grid-template-columns: minmax(260px, 320px) 1fr;
          gap: clamp(1.5rem, 4vw, 3rem);
          align-items: stretch;
        }

        .flight-viewer__sidebar {
          display: flex;
          flex-direction: column;
          gap: 1.5rem;
          backdrop-filter: blur(12px);
        }

        .flight-viewer__upload {
          border: 1px dashed rgba(99, 104, 149, 0.6);
          border-radius: 16px;
          padding: 1.5rem;
          display: flex;
          flex-direction: column;
          gap: 0.5rem;
          background: rgba(13, 16, 42, 0.35);
          position: relative;
          cursor: pointer;
          transition: border-color 0.2s ease, transform 0.2s ease;
        }

        .flight-viewer__upload:hover {
          border-color: #4f83ff;
          transform: translateY(-2px);
        }

        .flight-viewer__upload input {
          position: absolute;
          inset: 0;
          opacity: 0;
          cursor: pointer;
        }

        .flight-viewer__upload-title {
          font-weight: 600;
          letter-spacing: 0.02em;
        }

        .flight-viewer__upload-hint {
          font-size: 0.9rem;
          color: rgba(207, 211, 255, 0.7);
        }

        .flight-viewer__status {
          margin: 0;
          font-size: 0.9rem;
          color: rgba(207, 211, 255, 0.85);
        }

        .flight-viewer__status--error {
          color: #ff766a;
        }

        .flight-viewer__details {
          background: rgba(11, 14, 36, 0.55);
          padding: 1.25rem 1.5rem;
          border-radius: 16px;
          display: flex;
          flex-direction: column;
          gap: 1rem;
          border: 1px solid rgba(80, 82, 126, 0.3);
        }

        .flight-viewer__details h2 {
          margin: 0;
          font-size: 1.1rem;
          font-weight: 600;
        }

        .flight-viewer__details dl {
          display: grid;
          grid-template-columns: max-content 1fr;
          gap: 0.5rem 0.75rem;
          margin: 0;
        }

        .flight-viewer__details dt {
          font-size: 0.85rem;
          text-transform: uppercase;
          letter-spacing: 0.08em;
          color: rgba(174, 180, 228, 0.7);
        }

        .flight-viewer__details dd {
          margin: 0;
          font-size: 0.95rem;
          color: rgba(231, 234, 255, 0.92);
        }

        .flight-viewer__details span {
          display: inline-block;
          margin-left: 0.25rem;
          color: rgba(174, 180, 228, 0.7);
        }

        .flight-viewer__details--placeholder ul {
          margin: 0;
          padding-left: 1.1rem;
          display: flex;
          flex-direction: column;
          gap: 0.5rem;
          font-size: 0.95rem;
          color: rgba(210, 214, 250, 0.8);
        }

        .flight-viewer__flight-list {
          background: rgba(11, 14, 36, 0.55);
          padding: 1.25rem;
          border-radius: 16px;
          border: 1px solid rgba(80, 82, 126, 0.3);
          display: flex;
          flex-direction: column;
          gap: 0.75rem;
        }

        .flight-viewer__flight-list-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          padding-bottom: 0.5rem;
          border-bottom: 1px solid rgba(80, 82, 126, 0.25);
        }

        .flight-viewer__flight-list-header h3 {
          margin: 0;
          font-size: 1rem;
          font-weight: 600;
          color: rgba(231, 234, 255, 0.92);
        }

        .flight-viewer__clear-btn {
          background: rgba(255, 82, 82, 0.15);
          border: 1px solid rgba(255, 82, 82, 0.4);
          color: #ff5757;
          padding: 0.35rem 0.75rem;
          border-radius: 8px;
          font-size: 0.85rem;
          cursor: pointer;
          transition: all 0.2s ease;
        }

        .flight-viewer__clear-btn:hover {
          background: rgba(255, 82, 82, 0.25);
          border-color: #ff5757;
        }

        .flight-viewer__flight-item {
          background: rgba(16, 19, 48, 0.4);
          padding: 0.75rem;
          border-radius: 12px;
          border: 1px solid rgba(80, 82, 126, 0.2);
          display: flex;
          flex-direction: column;
          gap: 0.5rem;
        }

        .flight-viewer__flight-item-header {
          display: flex;
          align-items: center;
          gap: 0.75rem;
        }

        .flight-viewer__flight-color {
          width: 16px;
          height: 16px;
          border-radius: 4px;
          flex-shrink: 0;
        }

        .flight-viewer__flight-name {
          flex: 1;
          font-size: 0.9rem;
          font-weight: 500;
          color: rgba(231, 234, 255, 0.95);
          overflow: hidden;
          text-overflow: ellipsis;
          white-space: nowrap;
        }

        .flight-viewer__remove-btn {
          background: none;
          border: none;
          color: rgba(174, 180, 228, 0.6);
          font-size: 1.5rem;
          line-height: 1;
          padding: 0;
          width: 24px;
          height: 24px;
          cursor: pointer;
          transition: color 0.2s ease;
          display: flex;
          align-items: center;
          justify-content: center;
        }

        .flight-viewer__remove-btn:hover {
          color: #ff766a;
        }

        .flight-viewer__flight-stats {
          display: flex;
          gap: 0.5rem;
          font-size: 0.8rem;
          color: rgba(174, 180, 228, 0.75);
          padding-left: 1.5rem;
        }

        .flight-viewer__modal-overlay {
          position: fixed;
          inset: 0;
          background: rgba(3, 3, 9, 0.85);
          backdrop-filter: blur(8px);
          z-index: 1000;
          display: flex;
          align-items: center;
          justify-content: center;
          padding: 2rem;
          animation: fadeIn 0.2s ease;
        }

        @keyframes fadeIn {
          from { opacity: 0; }
          to { opacity: 1; }
        }

        .flight-viewer__modal {
          background: linear-gradient(160deg, rgba(15, 20, 50, 0.98), rgba(8, 10, 28, 0.98));
          border: 1px solid rgba(79, 131, 255, 0.25);
          border-radius: 20px;
          max-width: 600px;
          width: 100%;
          max-height: 90vh;
          overflow-y: auto;
          box-shadow: 0 20px 60px rgba(0, 0, 0, 0.5);
          animation: slideUp 0.3s ease;
        }

        @keyframes slideUp {
          from { transform: translateY(20px); opacity: 0; }
          to { transform: translateY(0); opacity: 1; }
        }

        .flight-viewer__modal-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          padding: 1.5rem 2rem;
          border-bottom: 1px solid rgba(80, 82, 126, 0.25);
        }

        .flight-viewer__modal-header h2 {
          margin: 0;
          font-size: 1.5rem;
          font-weight: 600;
          color: rgba(231, 234, 255, 0.95);
        }

        .flight-viewer__modal-close {
          background: none;
          border: none;
          color: rgba(174, 180, 228, 0.6);
          font-size: 2rem;
          line-height: 1;
          cursor: pointer;
          padding: 0;
          width: 32px;
          height: 32px;
          transition: color 0.2s ease;
        }

        .flight-viewer__modal-close:hover {
          color: #ff766a;
        }

        .flight-viewer__modal-body {
          padding: 2rem;
          display: flex;
          flex-direction: column;
          gap: 1.5rem;
        }

        .flight-viewer__modal-description {
          margin: 0;
          font-size: 0.95rem;
          color: rgba(210, 214, 250, 0.8);
          line-height: 1.5;
        }

        .flight-viewer__converter-upload {
          border: 2px dashed rgba(79, 131, 255, 0.4);
          border-radius: 12px;
          padding: 1.5rem;
          text-align: center;
          cursor: pointer;
          transition: all 0.2s ease;
          position: relative;
        }

        .flight-viewer__converter-upload:hover {
          border-color: #4f83ff;
          background: rgba(79, 131, 255, 0.05);
        }

        .flight-viewer__converter-upload span {
          display: block;
          font-size: 0.95rem;
          color: rgba(231, 234, 255, 0.9);
          margin-bottom: 0.5rem;
        }

        .flight-viewer__converter-upload input {
          position: absolute;
          inset: 0;
          opacity: 0;
          cursor: pointer;
        }

        .flight-viewer__converter-file {
          background: rgba(79, 131, 255, 0.1);
          border: 1px solid rgba(79, 131, 255, 0.3);
          padding: 0.75rem 1rem;
          border-radius: 8px;
          font-size: 0.9rem;
          color: rgba(231, 234, 255, 0.95);
          text-align: center;
        }

        .flight-viewer__converter-options {
          display: flex;
          flex-direction: column;
          gap: 1rem;
        }

        .flight-viewer__converter-options label {
          display: flex;
          flex-direction: column;
          gap: 0.5rem;
        }

        .flight-viewer__converter-options label > span {
          font-size: 0.85rem;
          font-weight: 500;
          color: rgba(210, 214, 250, 0.9);
          text-transform: uppercase;
          letter-spacing: 0.05em;
        }

        .flight-viewer__converter-options select,
        .flight-viewer__converter-options input[type="number"] {
          background: rgba(16, 19, 48, 0.6);
          border: 1px solid rgba(80, 82, 126, 0.4);
          color: rgba(231, 234, 255, 0.95);
          padding: 0.75rem 1rem;
          border-radius: 8px;
          font-size: 0.95rem;
          transition: border-color 0.2s ease;
        }

        .flight-viewer__converter-options select:focus,
        .flight-viewer__converter-options input[type="number"]:focus {
          outline: none;
          border-color: #4f83ff;
        }

        .flight-viewer__converter-checkbox {
          flex-direction: row !important;
          align-items: center;
          gap: 0.75rem !important;
        }

        .flight-viewer__converter-checkbox input[type="checkbox"] {
          width: 18px;
          height: 18px;
          cursor: pointer;
        }

        .flight-viewer__converter-checkbox span {
          text-transform: none !important;
          font-size: 0.9rem !important;
        }

        .flight-viewer__converter-status {
          padding: 0.75rem 1rem;
          border-radius: 8px;
          font-size: 0.9rem;
          text-align: center;
        }

        .flight-viewer__converter-status.success {
          background: rgba(122, 255, 122, 0.1);
          border: 1px solid rgba(122, 255, 122, 0.3);
          color: #7aff7a;
        }

        .flight-viewer__converter-status.error {
          background: rgba(255, 87, 87, 0.1);
          border: 1px solid rgba(255, 87, 87, 0.3);
          color: #ff5757;
        }

        .flight-viewer__modal-actions {
          display: flex;
          gap: 1rem;
          padding-top: 1rem;
          border-top: 1px solid rgba(80, 82, 126, 0.25);
        }

        .flight-viewer__modal-btn {
          flex: 1;
          padding: 0.875rem 1.5rem;
          border-radius: 10px;
          font-size: 0.95rem;
          font-weight: 600;
          cursor: pointer;
          transition: all 0.2s ease;
          border: 1px solid;
        }

        .flight-viewer__modal-btn.secondary {
          background: rgba(80, 82, 126, 0.2);
          border-color: rgba(80, 82, 126, 0.4);
          color: rgba(231, 234, 255, 0.85);
        }

        .flight-viewer__modal-btn.secondary:hover:not(:disabled) {
          background: rgba(80, 82, 126, 0.3);
        }

        .flight-viewer__modal-btn.primary {
          background: linear-gradient(135deg, #4f83ff 0%, #3d6dd9 100%);
          border-color: rgba(79, 131, 255, 0.5);
          color: white;
        }

        .flight-viewer__modal-btn.primary:hover:not(:disabled) {
          transform: translateY(-2px);
          box-shadow: 0 8px 20px rgba(79, 131, 255, 0.3);
        }

        .flight-viewer__modal-btn:disabled {
          opacity: 0.5;
          cursor: not-allowed;
        }

        .flight-viewer__visualizer {
          position: relative;
          border-radius: 24px;
          overflow: hidden;
          background: linear-gradient(160deg, rgba(12, 18, 52, 0.8), rgba(4, 6, 18, 0.95));
          border: 1px solid rgba(65, 68, 104, 0.35);
          min-height: 720px;
          height: 720px;
        }

        .flight-viewer__controls {
          position: absolute;
          top: 1rem;
          left: 1rem;
          z-index: 10;
          background: rgba(11, 14, 36, 0.85);
          backdrop-filter: blur(12px);
          padding: 0.75rem 1rem;
          border-radius: 12px;
          border: 1px solid rgba(79, 131, 255, 0.25);
        }

        .flight-viewer__lens-select {
          display: flex;
          align-items: center;
          gap: 0.75rem;
          font-size: 0.9rem;
        }

        .flight-viewer__lens-select span {
          color: rgba(210, 214, 250, 0.9);
          font-weight: 500;
        }

        .flight-viewer__lens-select select {
          background: rgba(16, 19, 48, 0.8);
          border: 1px solid rgba(80, 82, 126, 0.4);
          color: rgba(231, 234, 255, 0.95);
          padding: 0.5rem 0.75rem;
          border-radius: 8px;
          font-size: 0.85rem;
          cursor: pointer;
          transition: border-color 0.2s ease;
        }

        .flight-viewer__lens-select select:focus {
          outline: none;
          border-color: #4f83ff;
        }

        .flight-viewer__tooltip {
          position: absolute;
          top: 1rem;
          right: 1rem;
          z-index: 10;
          background: rgba(11, 14, 36, 0.95);
          backdrop-filter: blur(12px);
          padding: 1rem;
          border-radius: 12px;
          border: 1px solid rgba(79, 131, 255, 0.35);
          min-width: 240px;
          box-shadow: 0 8px 24px rgba(0, 0, 0, 0.4);
          animation: slideInRight 0.2s ease;
        }

        @keyframes slideInRight {
          from { 
            opacity: 0;
            transform: translateX(10px);
          }
          to { 
            opacity: 1;
            transform: translateX(0);
          }
        }

        .flight-viewer__tooltip-header {
          display: flex;
          align-items: center;
          gap: 0.5rem;
          padding-bottom: 0.75rem;
          margin-bottom: 0.75rem;
          border-bottom: 1px solid rgba(80, 82, 126, 0.25);
          font-size: 0.9rem;
          color: rgba(231, 234, 255, 0.95);
        }

        .flight-viewer__tooltip-marker {
          width: 10px;
          height: 10px;
          border-radius: 50%;
          flex-shrink: 0;
        }

        .flight-viewer__tooltip-body {
          display: flex;
          flex-direction: column;
          gap: 0.5rem;
        }

        .flight-viewer__tooltip-row {
          display: flex;
          justify-content: space-between;
          align-items: center;
          font-size: 0.85rem;
        }

        .flight-viewer__tooltip-row span:first-child {
          color: rgba(174, 180, 228, 0.75);
        }

        .flight-viewer__tooltip-row span:last-child {
          color: rgba(231, 234, 255, 0.95);
          font-weight: 500;
          font-family: 'SF Mono', Monaco, 'Courier New', monospace;
        }

        .flight-viewer__map-placeholder {
          position: absolute;
          inset: 0;
          display: grid;
          place-items: center;
          padding: 2rem;
          text-align: center;
          border-radius: 18px;
          border: 1px dashed rgba(99, 104, 149, 0.4);
          background: rgba(10, 13, 32, 0.45);
          color: rgba(201, 206, 247, 0.85);
        }

        .flight-viewer__map-container {
          position: absolute;
          inset: 0;
          width: 100%;
          height: 100%;
          min-height: 520px;
          border-radius: 18px;
          overflow: hidden;
        }

        .flight-viewer__cesium-canvas {
          position: absolute;
          inset: 0;
          width: 100%;
          height: 100%;
        }
        
        /* Hide Cesium UI elements */
        .flight-viewer__cesium-canvas :global(.cesium-viewer-bottom) {
          display: none !important;
        }
        
        .flight-viewer__cesium-canvas :global(.cesium-credit-logoContainer) {
          display: none !important;
        }
        
        .flight-viewer__cesium-canvas :global(.cesium-credit-textContainer) {
          display: none !important;
        }

        .flight-viewer__map-warning {
          position: absolute;
          bottom: 1rem;
          right: 1rem;
          padding: 0.75rem 1rem;
          border-radius: 10px;
          background: rgba(9, 12, 32, 0.85);
          border: 1px solid rgba(255, 183, 0, 0.4);
          color: rgba(255, 235, 199, 0.95);
          font-size: 0.85rem;
          box-shadow: 0 10px 30px rgba(0, 0, 0, 0.25);
        }

        .flight-viewer__map-support-flag {
          position: absolute;
          width: 0;
          height: 0;
          overflow: hidden;
        }

        .flight-viewer__placeholder {
          position: absolute;
          inset: 0;
          display: grid;
          place-items: center;
          color: rgba(201, 206, 247, 0.6);
          font-size: 1rem;
          letter-spacing: 0.02em;
        }

        .flight-viewer__placeholder-inner {
          border: 1px dashed rgba(99, 104, 149, 0.5);
          padding: 2rem 2.5rem;
          border-radius: 18px;
          backdrop-filter: blur(10px);
          background: rgba(10, 13, 32, 0.4);
        }

        @media (max-width: 960px) {
          .flight-viewer__content {
            grid-template-columns: 1fr;
          }

          .flight-viewer__visualizer {
            min-height: 520px;
            height: 520px;
          }
        }

        @media (max-width: 640px) {
          .flight-viewer {
            padding: 3rem 1.25rem;
          }

          .flight-viewer__visualizer {
            min-height: 420px;
            height: 420px;
          }
        }
      `}</style>
    </main>
  );
}
