"use client";

import React, { ChangeEvent, useCallback, useMemo, useState, useEffect, useRef } from "react";
import Papa from "papaparse";
import JSZip from "jszip";
import { XMLParser } from "fast-xml-parser";
import { Loader } from "@googlemaps/js-api-loader";
import { ThreeJSOverlayView } from "@googlemaps/three";
import * as THREE from "three";
import { convertLitchiCSVToKMZ, downloadBlob } from "../../lib/flightConverter";

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
  localPosition: [number, number, number];
}

interface PoiData {
  latitude: number;
  longitude: number;
  altitudeFt: number;
  altitudeMode: number | null;
  localPosition: [number, number, number];
}

interface FlightData {
  id: string;
  name: string;
  color: string;
  samples: ProcessedSample[];
  poi: PoiData | null;
}

interface CameraFrustumProps {
  position: [number, number, number];
  heading: number;
  gimbalPitch: number;
  color: string;
  fov: number;
  scale: number;
  onPointerOver: () => void;
  onPointerOut: () => void;
}

const EARTH_RADIUS_METERS = 6_378_137;
const FEET_TO_METERS = 0.3048;

const FLIGHT_COLORS = [
  "#4f83ff", "#ff7a18", "#00d9ff", "#ff4d94", "#7aff7a",
  "#ffbb00", "#bb7aff", "#ff5757", "#00ffaa", "#ffcc66"
];

// Drone lens specifications (horizontal FOV in degrees)
const DRONE_LENSES: Record<string, { name: string; fov: number; aspectRatio: number }> = {
  "mavic3_wide": { name: "Mavic 3 Wide (24mm)", fov: 84, aspectRatio: 4/3 },
  "mavic3_tele": { name: "Mavic 3 Tele (162mm)", fov: 15, aspectRatio: 4/3 },
  "air3_wide": { name: "Air 3 Wide (24mm)", fov: 82, aspectRatio: 4/3 },
  "mini4_wide": { name: "Mini 4 Pro (24mm)", fov: 82.1, aspectRatio: 4/3 },
  "phantom4": { name: "Phantom 4 Pro (24mm)", fov: 73.7, aspectRatio: 3/2 },
};

function toNumber(value: unknown): number {
  if (typeof value === "number" && Number.isFinite(value)) {
    return value;
  }
  if (typeof value === "string" && value.trim().length) {
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
  const altitudeFt = toNumber(row["altitude(ft)"]);

  if (!Number.isFinite(latitude) || !Number.isFinite(longitude) || !Number.isFinite(altitudeFt)) {
    return null;
  }

  return {
    latitude,
    longitude,
    altitudeFt,
    headingDeg: toOptionalNumber(row["heading(deg)"] ?? row.headingdeg),
    curveSizeFt: toOptionalNumber(row["curvesize(ft)"] ?? row.curvesizeft),
    rotationDir: toOptionalNumber(row.rotationdir),
    gimbalMode: toOptionalNumber(row.gimbalmode),
    gimbalPitchAngle: toOptionalNumber(row.gimbalpitchangle),
    altitudeMode: toOptionalNumber(row.altitudemode),
    speedMs: toOptionalNumber(row["speed(m/s)"] ?? row.speedms),
    poiLatitude: toOptionalNumber(row.poi_latitude),
    poiLongitude: toOptionalNumber(row.poi_longitude),
    poiAltitudeFt: toOptionalNumber(row["poi_altitude(ft)"] ?? row.poi_altitudeft),
    poiAltitudeMode: toOptionalNumber(row.poi_altitudemode),
    photoTimeInterval: toOptionalNumber(row.photo_timeinterval),
    photoDistInterval: toOptionalNumber(row.photo_distinterval),
  };
}

function degreesToRadians(value: number): number {
  return (value * Math.PI) / 180;
}

function buildLocalFrame(
  samples: PreparedRow[], 
  referencePoint?: { lat: number; lon: number }
): { samples: ProcessedSample[]; poi: PoiData | null } {
  if (!samples.length) {
    return { samples: [], poi: null };
  }

  const refLat = referencePoint?.lat ?? samples[0].latitude;
  const refLon = referencePoint?.lon ?? samples[0].longitude;
  const referenceLat = degreesToRadians(refLat);
  const referenceLon = degreesToRadians(refLon);
  const cosReferenceLat = Math.cos(referenceLat);

  const toLocal = (lat: number, lon: number, altitudeFt: number): [number, number, number] => {
    const latRad = degreesToRadians(lat);
    const lonRad = degreesToRadians(lon);
    const x = (lonRad - referenceLon) * cosReferenceLat * EARTH_RADIUS_METERS;
    const z = (latRad - referenceLat) * EARTH_RADIUS_METERS;
    const y = altitudeFt * FEET_TO_METERS;
    return [x, y, -z];
  };

  const processedSamples: ProcessedSample[] = samples.map((sample, index) => ({
    ...sample,
    index,
    localPosition: toLocal(sample.latitude, sample.longitude, sample.altitudeFt),
  }));

  const firstPoiSource = samples.find(sample =>
    Number.isFinite(sample.poiLatitude ?? Number.NaN) && Number.isFinite(sample.poiLongitude ?? Number.NaN)
  );

  let poi: PoiData | null = null;
  if (firstPoiSource && firstPoiSource.poiLatitude !== null && firstPoiSource.poiLongitude !== null) {
    const poiAltitudeFt = firstPoiSource.poiAltitudeFt ?? samples[0].altitudeFt;
    poi = {
      latitude: firstPoiSource.poiLatitude,
      longitude: firstPoiSource.poiLongitude,
      altitudeFt: poiAltitudeFt,
      altitudeMode: firstPoiSource.poiAltitudeMode,
      localPosition: toLocal(firstPoiSource.poiLatitude, firstPoiSource.poiLongitude, poiAltitudeFt),
    };
  }

  return { samples: processedSamples, poi };
}

async function parseKMZFile(file: File): Promise<PreparedRow[]> {
  const zip = new JSZip();
  const contents = await zip.loadAsync(file);
  
  const wpmlFile = contents.file("wpmz/waylines.wpml");
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
    
    // Extract gimbal pitch from action groups (can be array or single object)
    let gimbalPitch = null;
    const actionGroups = mark?.["wpml:actionGroup"];
    if (actionGroups) {
      const groups = Array.isArray(actionGroups) ? actionGroups : [actionGroups];
      for (const group of groups) {
        const action = group?.["wpml:action"];
        const actions = Array.isArray(action) ? action : [action];
        for (const act of actions) {
          const func = act?.["wpml:actionActuatorFunc"];
          if (func === "gimbalRotate" || func === "gimbalEvenlyRotate") {
            const pitch = act?.["wpml:actionActuatorFuncParam"]?.["wpml:gimbalPitchRotateAngle"];
            if (pitch !== undefined && pitch !== null) {
              gimbalPitch = pitch;
              break;
            }
          }
        }
        if (gimbalPitch !== null) break;
      }
    }
    
    if (!coords || !executeHeight) continue;
    
    const [lon, lat] = coords.split(",").map(Number);
    if (!Number.isFinite(lat) || !Number.isFinite(lon)) continue;
    
    const altitudeMeters = Number(executeHeight);
    const altitudeFt = altitudeMeters / FEET_TO_METERS;
    
    let poiLat = null;
    let poiLon = null;
    let poiAltFt = null;
    if (poiPoint && typeof poiPoint === "string") {
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
      gimbalPitchAngle: toOptionalNumber(gimbalPitch),
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
  
  return rows;
}

function computeStats(flight: FlightData | null) {
  if (!flight) {
    return null;
  }

  const vectors = flight.samples.map(sample => new THREE.Vector3(...sample.localPosition));
  if (!vectors.length) {
    return null;
  }

  const totalDistanceMeters = vectors.reduce((acc, point, index) => {
    if (index === 0) {
      return 0;
    }
    return acc + point.distanceTo(vectors[index - 1]);
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
  return new Intl.NumberFormat("en-US", {
    maximumFractionDigits: fractionDigits,
  }).format(value);
}

function formatSpeed(speedMs: number | null): string {
  if (speedMs === null) {
    return "n/a";
  }
  const mph = speedMs * 2.23694;
  return `${formatNumber(speedMs, 2)} m/s (${formatNumber(mph, 1)} mph)`;
}

interface FlightPathSceneProps {
  flights: FlightData[];
  selectedLens: string;
  onWaypointHover: (flightId: string, waypointIndex: number | null) => void;
  centerCoords?: { lat: number; lon: number };
}

interface WaypointVisual {
  key: string;
  flightId: string;
  index: number;
  targets: THREE.Object3D[];
  setHover: (hovered: boolean) => void;
}

const GOOGLE_MAP_CAMERA_TILT = 67;
const GOOGLE_MAP_CAMERA_HEADING = 0;
const GOOGLE_MAP_DEFAULT_ZOOM = 18;

function disposeObject3D(object: THREE.Object3D) {
  object.traverse(child => {
    const mesh = child as THREE.Mesh;
    if (mesh.geometry) {
      mesh.geometry.dispose();
    }
    const material = mesh.material as THREE.Material | THREE.Material[] | undefined;
    if (material) {
      if (Array.isArray(material)) {
        material.forEach(mat => mat.dispose());
      } else if (typeof material.dispose === "function") {
        material.dispose();
      }
    }
  });
}

function createCameraFrustumVisual({
  sample,
  lensSpec,
  color,
  flightId,
}: {
  sample: ProcessedSample;
  lensSpec: { fov: number; aspectRatio: number };
  color: string;
  flightId: string;
}): { group: THREE.Group; waypoint: WaypointVisual } {
  const group = new THREE.Group();

  const sizeScale = Math.max(sample.altitudeFt * FEET_TO_METERS * 0.02, 1.2);
  const baseWidth = sizeScale * 0.8;
  const baseHeight = baseWidth * (1 / lensSpec.aspectRatio);
  const depth = sizeScale * 1.5;

  const baseCorners = [
    new THREE.Vector3(-baseWidth, -baseHeight, 0),
    new THREE.Vector3(baseWidth, -baseHeight, 0),
    new THREE.Vector3(baseWidth, baseHeight, 0),
    new THREE.Vector3(-baseWidth, baseHeight, 0),
  ];

  const apex = new THREE.Vector3(0, 0, depth);

  const pyramidVertices: number[] = [];
  for (let i = 0; i < 4; i += 1) {
    const current = baseCorners[i];
    const next = baseCorners[(i + 1) % 4];
    pyramidVertices.push(current.x, current.y, current.z);
    pyramidVertices.push(next.x, next.y, next.z);
  }
  baseCorners.forEach(corner => {
    pyramidVertices.push(corner.x, corner.y, corner.z);
    pyramidVertices.push(apex.x, apex.y, apex.z);
  });

  const pyramidGeometry = new THREE.BufferGeometry();
  pyramidGeometry.setAttribute("position", new THREE.Float32BufferAttribute(pyramidVertices, 3));

  const frameMaterial = new THREE.LineBasicMaterial({ color, transparent: true, opacity: 0.85 });
  const wireframe = new THREE.LineSegments(pyramidGeometry, frameMaterial);

  const halfFovH = THREE.MathUtils.degToRad(lensSpec.fov / 2);
  const halfFovV = Math.atan(Math.tan(halfFovH) / lensSpec.aspectRatio);
  const distance = sizeScale * 60;

  const farCorners = [
    new THREE.Vector3(Math.tan(halfFovH) * distance, Math.tan(halfFovV) * distance, distance),
    new THREE.Vector3(-Math.tan(halfFovH) * distance, Math.tan(halfFovV) * distance, distance),
    new THREE.Vector3(-Math.tan(halfFovH) * distance, -Math.tan(halfFovV) * distance, distance),
    new THREE.Vector3(Math.tan(halfFovH) * distance, -Math.tan(halfFovV) * distance, distance),
  ];

  const frustumPoints: number[] = [];
  farCorners.forEach(corner => {
    frustumPoints.push(apex.x, apex.y, apex.z, corner.x, corner.y, corner.z);
  });

  const frustumGeometry = new THREE.BufferGeometry();
  frustumGeometry.setAttribute("position", new THREE.Float32BufferAttribute(frustumPoints, 3));
  const frustumMaterial = new THREE.LineDashedMaterial({
    color,
    transparent: true,
    opacity: 0.45,
    dashSize: sizeScale * 0.8,
    gapSize: sizeScale * 0.4,
  });
  const frustumLines = new THREE.LineSegments(frustumGeometry, frustumMaterial);
  frustumLines.computeLineDistances();
  frustumLines.visible = false;

  group.add(wireframe);
  group.add(frustumLines);

  const headingRad = THREE.MathUtils.degToRad(sample.headingDeg ?? 0);
  const pitchRad = THREE.MathUtils.degToRad(sample.gimbalPitchAngle ?? -90);
  group.setRotationFromEuler(new THREE.Euler(pitchRad, headingRad, 0, "YXZ"));

  const key = `${flightId}:${sample.index}`;
  wireframe.userData = { type: "waypoint", flightId, index: sample.index };
  frustumLines.userData = { type: "waypoint", flightId, index: sample.index };

  const waypoint: WaypointVisual = {
    key,
    flightId,
    index: sample.index,
    targets: [wireframe],
    setHover: hovered => {
      frameMaterial.opacity = hovered ? 1 : 0.85;
      frustumLines.visible = hovered;
      frustumMaterial.opacity = hovered ? 0.65 : 0.45;
    },
  };

  return { group, waypoint };
}

function buildFlightOverlay(
  flight: FlightData,
  overlay: ThreeJSOverlayView,
  lensSpec: { fov: number; aspectRatio: number }
): { group: THREE.Group; waypoints: WaypointVisual[] } {
  const flightGroup = new THREE.Group();
  flightGroup.name = `flight-${flight.id}`;

  const waypointEntries: WaypointVisual[] = [];

  const worldPoints = flight.samples.map(sample =>
    overlay.latLngAltitudeToVector3({
      lat: sample.latitude,
      lng: sample.longitude,
      altitude: sample.altitudeFt * FEET_TO_METERS,
    })
  );

  if (worldPoints.length >= 2) {
    const curve = new THREE.CatmullRomCurve3(worldPoints, false, "centripetal", 0.25);
    const detail = Math.min(2_000, Math.max(worldPoints.length * 8, 256));
    const smoothPoints = curve.getPoints(detail);
    const pathGeometry = new THREE.BufferGeometry().setFromPoints(smoothPoints);
    const pathMaterial = new THREE.LineBasicMaterial({ color: flight.color, transparent: true, opacity: 0.95 });
    const pathLine = new THREE.Line(pathGeometry, pathMaterial);
    pathLine.name = `flight-path-${flight.id}`;
    flightGroup.add(pathLine);
  }

  flight.samples.forEach(sample => {
    const { group, waypoint } = createCameraFrustumVisual({
      sample,
      lensSpec,
      color: flight.color,
      flightId: flight.id,
    });

    const worldPosition = overlay.latLngAltitudeToVector3({
      lat: sample.latitude,
      lng: sample.longitude,
      altitude: sample.altitudeFt * FEET_TO_METERS,
    });

    group.position.copy(worldPosition);
    waypointEntries.push(waypoint);
    flightGroup.add(group);
  });

  if (flight.poi) {
    const poiPosition = overlay.latLngAltitudeToVector3({
      lat: flight.poi.latitude,
      lng: flight.poi.longitude,
      altitude: (flight.poi.altitudeFt ?? flight.samples[0]?.altitudeFt ?? 0) * FEET_TO_METERS,
    });

    const pathBox = new THREE.Box3().setFromPoints(worldPoints);
    const sizeVector = pathBox.getSize(new THREE.Vector3());
    const poiRadius = Math.max(sizeVector.length() * 0.01, 0.8);

    const poiGeometry = new THREE.SphereGeometry(poiRadius, 24, 24);
    const poiMaterial = new THREE.MeshStandardMaterial({ color: "#ff7a18", emissive: "#ff7a18", emissiveIntensity: 0.6 });
    const poiMesh = new THREE.Mesh(poiGeometry, poiMaterial);
    poiMesh.position.copy(poiPosition);
    flightGroup.add(poiMesh);
  }

  return { group: flightGroup, waypoints: waypointEntries };
}

function FlightPathScene({ flights, selectedLens, onWaypointHover, centerCoords }: FlightPathSceneProps): JSX.Element {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const overlayRef = useRef<ThreeJSOverlayView | null>(null);
  const mapRef = useRef<google.maps.Map | null>(null);
  const googleRef = useRef<typeof google | null>(null);
  const initializingRef = useRef(false);
  const flightsGroupRef = useRef<THREE.Group | null>(null);
  const waypointLookupRef = useRef<Map<string, WaypointVisual>>(new Map());
  const waypointTargetsRef = useRef<THREE.Object3D[]>([]);
  const pointerVecRef = useRef(new THREE.Vector2(0, 0));
  const pointerActiveRef = useRef(false);
  const hoverKeyRef = useRef<string | null>(null);
  const onWaypointHoverRef = useRef(onWaypointHover);

  const GOOGLE_MAPS_API_KEY = process.env.NEXT_PUBLIC_GOOGLE_MAPS_API_KEY || "";
  const GOOGLE_MAPS_MAP_ID = process.env.NEXT_PUBLIC_GOOGLE_MAPS_MAP_ID || "";

  useEffect(() => {
    onWaypointHoverRef.current = onWaypointHover;
  }, [onWaypointHover]);

  useEffect(() => {
    if (!centerCoords || !GOOGLE_MAPS_API_KEY) {
      return;
    }

    if (overlayRef.current && mapRef.current) {
      overlayRef.current.setAnchor({ lat: centerCoords.lat, lng: centerCoords.lon, altitude: 0 });
      mapRef.current.moveCamera?.({ center: { lat: centerCoords.lat, lng: centerCoords.lon } });
      return;
    }

    if (!containerRef.current || initializingRef.current) {
      return;
    }

    initializingRef.current = true;
    let cancelled = false;
    let overlayInstance: ThreeJSOverlayView | null = null;
    let mapInstance: google.maps.Map | null = null;
    const listeners: google.maps.MapsEventListener[] = [];

    const loader = new Loader({
      apiKey: GOOGLE_MAPS_API_KEY,
      version: "weekly",
      mapIds: GOOGLE_MAPS_MAP_ID ? [GOOGLE_MAPS_MAP_ID] : undefined,
    });

    loader
      .load()
      .then(googleMaps => {
        if (cancelled) {
          return;
        }

        googleRef.current = googleMaps;

        mapInstance = new googleMaps.maps.Map(containerRef.current as HTMLElement, {
          center: { lat: centerCoords.lat, lng: centerCoords.lon },
          zoom: GOOGLE_MAP_DEFAULT_ZOOM,
          tilt: GOOGLE_MAP_CAMERA_TILT,
          heading: GOOGLE_MAP_CAMERA_HEADING,
          mapId: GOOGLE_MAPS_MAP_ID || undefined,
          mapTypeControl: false,
          streetViewControl: false,
          rotateControl: true,
          fullscreenControl: false,
        });

        mapRef.current = mapInstance;

        overlayInstance = new ThreeJSOverlayView({
          map: mapInstance,
          anchor: { lat: centerCoords.lat, lng: centerCoords.lon, altitude: 0 },
          upAxis: "Z",
          animationMode: "whenMapIdle",
        });

        overlayInstance.onBeforeDraw = () => {
          if (!overlayRef.current) {
            return;
          }

          if (!pointerActiveRef.current || waypointTargetsRef.current.length === 0) {
            if (hoverKeyRef.current) {
              const previous = waypointLookupRef.current.get(hoverKeyRef.current);
              if (previous) {
                previous.setHover(false);
                const [prevFlightId] = hoverKeyRef.current.split(":");
                onWaypointHoverRef.current(prevFlightId, null);
              }
              hoverKeyRef.current = null;
            }
            return;
          }

          const intersections = overlayRef.current.raycast(
            pointerVecRef.current,
            waypointTargetsRef.current,
            { recursive: false }
          );

          const hit = intersections.find(item => item.object.userData?.type === "waypoint");
          if (!hit) {
            if (hoverKeyRef.current) {
              const previous = waypointLookupRef.current.get(hoverKeyRef.current);
              if (previous) {
                previous.setHover(false);
                const [prevFlightId] = hoverKeyRef.current.split(":");
                onWaypointHoverRef.current(prevFlightId, null);
              }
              hoverKeyRef.current = null;
            }
            return;
          }

          const { flightId, index } = hit.object.userData as { flightId: string; index: number };
          const key = `${flightId}:${index}`;

          if (hoverKeyRef.current === key) {
            return;
          }

          if (hoverKeyRef.current) {
            const previous = waypointLookupRef.current.get(hoverKeyRef.current);
            if (previous) {
              previous.setHover(false);
              const [prevFlightId] = hoverKeyRef.current.split(":");
              onWaypointHoverRef.current(prevFlightId, null);
            }
          }

          const current = waypointLookupRef.current.get(key);
          if (current) {
            current.setHover(true);
            hoverKeyRef.current = key;
            onWaypointHoverRef.current(current.flightId, current.index);
          }
        };

        overlayRef.current = overlayInstance;

        const mapDiv = mapInstance.getDiv();

        listeners.push(
          mapInstance.addListener("mousemove", event => {
            if (!event.domEvent) {
              return;
            }
            const rect = mapDiv.getBoundingClientRect();
            const x = event.domEvent.clientX - rect.left;
            const y = event.domEvent.clientY - rect.top;
            pointerVecRef.current.set(2 * (x / rect.width) - 1, 1 - 2 * (y / rect.height));
            pointerActiveRef.current = true;
            overlayInstance?.requestRedraw();
          })
        );

        listeners.push(
          mapInstance.addListener("mouseout", () => {
            pointerActiveRef.current = false;
            if (hoverKeyRef.current) {
              const previous = waypointLookupRef.current.get(hoverKeyRef.current);
              if (previous) {
                previous.setHover(false);
                const [prevFlightId] = hoverKeyRef.current.split(":");
                onWaypointHoverRef.current(prevFlightId, null);
              }
              hoverKeyRef.current = null;
            }
            overlayInstance?.requestRedraw();
          })
        );

        listeners.push(
          mapInstance.addListener("zoom_changed", () => {
            overlayInstance?.requestRedraw();
          })
        );

        overlayInstance.setMap(mapInstance);
      })
      .catch(error => {
        console.error("[FlightPathScene] Failed to load Google Maps API", error);
      })
      .finally(() => {
        initializingRef.current = false;
      });

    return () => {
      cancelled = true;
      pointerActiveRef.current = false;

      listeners.forEach(listener => listener.remove());

      if (overlayInstance) {
        overlayInstance.setMap(null);
      }

      overlayRef.current = null;
      if (mapInstance) {
        mapInstance = null;
      }

      if (hoverKeyRef.current) {
        const previous = waypointLookupRef.current.get(hoverKeyRef.current);
        if (previous) {
          previous.setHover(false);
          const [prevFlightId] = hoverKeyRef.current.split(":");
          onWaypointHoverRef.current(prevFlightId, null);
        }
        hoverKeyRef.current = null;
      }

      waypointLookupRef.current.clear();
      waypointTargetsRef.current = [];

      if (flightsGroupRef.current) {
        disposeObject3D(flightsGroupRef.current);
        flightsGroupRef.current = null;
      }
    };
  }, [centerCoords, GOOGLE_MAPS_API_KEY, GOOGLE_MAPS_MAP_ID]);

  useEffect(() => {
    const overlay = overlayRef.current;
    if (!overlay) {
      return;
    }

    if (flightsGroupRef.current) {
      overlay.scene.remove(flightsGroupRef.current);
      disposeObject3D(flightsGroupRef.current);
      flightsGroupRef.current = null;
    }

    if (hoverKeyRef.current) {
      const previous = waypointLookupRef.current.get(hoverKeyRef.current);
      if (previous) {
        previous.setHover(false);
        const [prevFlightId] = hoverKeyRef.current.split(":");
        onWaypointHoverRef.current(prevFlightId, null);
      }
      hoverKeyRef.current = null;
    }

    waypointLookupRef.current = new Map();
    waypointTargetsRef.current = [];

    if (flights.length === 0) {
      overlay.requestRedraw();
      return;
    }

    const lensSpec = DRONE_LENSES[selectedLens] || DRONE_LENSES["mavic3_wide"];

    const rootGroup = new THREE.Group();
    const lookup = new Map<string, WaypointVisual>();
    const targets: THREE.Object3D[] = [];

    flights.forEach(flight => {
      const { group, waypoints } = buildFlightOverlay(flight, overlay, lensSpec);
      rootGroup.add(group);
      waypoints.forEach(entry => {
        lookup.set(entry.key, entry);
        targets.push(...entry.targets);
      });
    });

    overlay.scene.add(rootGroup);
    flightsGroupRef.current = rootGroup;
    waypointLookupRef.current = lookup;
    waypointTargetsRef.current = targets;

    overlay.requestRedraw();
  }, [flights, selectedLens]);

  useEffect(() => {
    const map = mapRef.current;
    const googleMaps = googleRef.current;
    if (!map || !googleMaps || flights.length === 0) {
      return;
    }

    const bounds = new googleMaps.maps.LatLngBounds();
    flights.forEach(flight => {
      flight.samples.forEach(sample => {
        bounds.extend({ lat: sample.latitude, lng: sample.longitude });
      });
    });

    if (!bounds.isEmpty()) {
      map.fitBounds(bounds, 48);
      const zoom = map.getZoom() ?? GOOGLE_MAP_DEFAULT_ZOOM;
      if (zoom > 19) {
        map.setZoom(19);
      }
      map.setTilt(GOOGLE_MAP_CAMERA_TILT);
      map.setHeading(GOOGLE_MAP_CAMERA_HEADING);
    }
  }, [flights]);

  if (!GOOGLE_MAPS_API_KEY) {
    return (
      <div className="flight-viewer__map-placeholder">
        <p>Google Maps API key missing. Set NEXT_PUBLIC_GOOGLE_MAPS_API_KEY to enable map rendering.</p>
      </div>
    );
  }

  return <div ref={containerRef} className="flight-viewer__map" role="presentation" />;
}

export default function FlightViewerPage(): JSX.Element {
  const [flights, setFlights] = useState<FlightData[]>([]);
  const [status, setStatus] = useState<string | null>(null);
  const [isParsing, setIsParsing] = useState(false);
  const [centerCoords, setCenterCoords] = useState<{ lat: number; lon: number } | undefined>(undefined);
  
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

  const globalReferencePoint = useMemo(() => {
    if (!flights.length) return undefined;
    const first = flights[0].samples[0];
    if (!first) return undefined;
    return { lat: first.latitude, lon: first.longitude };
  }, [flights]);

  const onFilesSelected = useCallback(async (event: ChangeEvent<HTMLInputElement>) => {
    const fileList = event.target.files;
    if (!fileList || fileList.length === 0) {
      return;
    }
    
    setIsParsing(true);
    setStatus(null);

    const newFlights: FlightData[] = [];
    const errors: string[] = [];

    for (let i = 0; i < fileList.length; i++) {
      const file = fileList[i];
      const fileExtension = file.name.toLowerCase().split(".").pop();
      
      try {
        let prepared: PreparedRow[] = [];

        if (fileExtension === "kmz") {
          prepared = await parseKMZFile(file);
        } else if (fileExtension === "csv") {
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

        const referencePoint = globalReferencePoint || { lat: prepared[0].latitude, lon: prepared[0].longitude };
        const { samples, poi } = buildLocalFrame(prepared, referencePoint);
        
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
      
      // Calculate center coordinates from all samples
      const allSamples = newFlights.flatMap(f => f.samples);
      if (allSamples.length > 0) {
        const avgLat = allSamples.reduce((sum, s) => sum + s.latitude, 0) / allSamples.length;
        const avgLon = allSamples.reduce((sum, s) => sum + s.longitude, 0) / allSamples.length;
        setCenterCoords({ lat: avgLat, lon: avgLon });
        console.log('[FlightViewer] Center coordinates:', { lat: avgLat, lon: avgLon });
      }
    }
    
    if (errors.length > 0 && newFlights.length === 0) {
      setStatus(errors.join("; "));
    }
  }, [flights.length, globalReferencePoint]);

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
      
      setConverterStatus(`✓ Converted to ${outputName}`);
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
          Convert CSV → KMZ
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

          {isParsing && <p className="flight-viewer__status">Parsing files…</p>}
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
                          ×
                        </button>
                      </div>
                      <div className="flight-viewer__flight-stats">
                        <span>{flight.samples.length} pts</span>
                        {stats && (
                          <>
                            <span>·</span>
                            <span>{formatNumber(stats.totalDistanceMeters, 0)}m</span>
                            <span>·</span>
                            <span>{formatNumber(stats.minAltitudeFt, 0)}–{formatNumber(stats.maxAltitudeFt, 0)}ft</span>
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
                  <span>{hoveredData.sample.headingDeg?.toFixed(1) || "—"}°</span>
                </div>
                <div className="flight-viewer__tooltip-row">
                  <span>Gimbal Pitch:</span>
                  <span>{hoveredData.sample.gimbalPitchAngle?.toFixed(1) || "—"}°</span>
                </div>
                <div className="flight-viewer__tooltip-row">
                  <span>Altitude:</span>
                  <span>{hoveredData.sample.altitudeFt.toFixed(1)} ft</span>
                </div>
                <div className="flight-viewer__tooltip-row">
                  <span>Speed:</span>
                  <span>{hoveredData.sample.speedMs?.toFixed(1) || "—"} m/s</span>
                </div>
              </div>
            </div>
          )}
          
          {flights.length > 0 ? (
            <FlightPathScene 
              flights={flights} 
              selectedLens={selectedLens}
              onWaypointHover={handleWaypointHover}
              centerCoords={centerCoords}
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
              <h2>CSV → KMZ Converter</h2>
              <button 
                className="flight-viewer__modal-close"
                onClick={() => setShowConverter(false)}
              >
                ×
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
                <div className={`flight-viewer__converter-status ${converterStatus.startsWith("✓") ? "success" : "error"}`}>
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
          min-height: 520px;
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

        .flight-viewer__canvas-inner {
          width: 100%;
          height: 100%;
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
            min-height: 420px;
          }
        }

        @media (max-width: 640px) {
          .flight-viewer {
            padding: 3rem 1.25rem;
          }

          .flight-viewer__visualizer {
            min-height: 360px;
          }
        }
      `}</style>
    </main>
  );
}
