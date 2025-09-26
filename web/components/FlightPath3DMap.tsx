'use client';

import { useEffect, useMemo, useRef, useState } from 'react';
import { Loader } from '@googlemaps/js-api-loader';
import {
  AmbientLight,
  BufferAttribute,
  BufferGeometry,
  Color,
  DirectionalLight,
  Float32BufferAttribute,
  Line,
  LineBasicMaterial,
  Matrix4,
  PerspectiveCamera,
  Points,
  PointsMaterial,
  Scene,
  WebGLRenderer,
} from 'three';
import type {
  FlightPoi,
  FlightWaypointRuntime,
  MapBoundsLiteral,
} from 'lib/flightPath';

export type FlightPathColorMode = 'slope' | 'curvature';

interface FlightPath3DMapProps {
  waypoints: FlightWaypointRuntime[];
  poi: FlightPoi | null;
  bounds: MapBoundsLiteral | null;
  center: { lat: number; lng: number; altitudeMeters: number } | null;
  colorMode: FlightPathColorMode;
  className?: string;
}

type OverlayState = {
  scene: Scene | null;
  camera: PerspectiveCamera | null;
  renderer: WebGLRenderer | null;
  line: Line<BufferGeometry, LineBasicMaterial> | null;
  points: Points<BufferGeometry, PointsMaterial> | null;
  geometry: BufferGeometry | null;
  positionAttribute: BufferAttribute | null;
  colorAttribute: BufferAttribute | null;
  needsUpdate: boolean;
};

const INITIAL_OVERLAY_STATE: OverlayState = {
  scene: null,
  camera: null,
  renderer: null,
  line: null,
  points: null,
  geometry: null,
  positionAttribute: null,
  colorAttribute: null,
  needsUpdate: false,
};

const DEFAULT_TILT = 67.5;
const DEFAULT_ZOOM = 18;
const MAX_SLOPE_FOR_COLOR = 60; // percent grade mapped to red
const MIN_CURVE_METERS = 5;
const MAX_CURVE_METERS = 80;

function colorForSlope(slopePercent: number | null): Color {
  const slope = Math.min(Math.abs(slopePercent ?? 0), MAX_SLOPE_FOR_COLOR);
  const t = slope / MAX_SLOPE_FOR_COLOR; // 0 -> flat (green), 1 -> steep (red)
  const color = new Color();
  color.setHSL(0.33 - 0.33 * t, 0.85, 0.5);
  return color;
}

function colorForCurvature(curveSizeMeters: number | null): Color {
  if (!curveSizeMeters || curveSizeMeters <= 0) {
    return new Color(0x037d50); // default green when unknown / straight
  }
  const clamped = Math.max(MIN_CURVE_METERS, Math.min(MAX_CURVE_METERS, curveSizeMeters));
  const t = (clamped - MIN_CURVE_METERS) / (MAX_CURVE_METERS - MIN_CURVE_METERS);
  // t=0 -> tight turn (red), t=1 -> wide turn (green)
  const color = new Color();
  color.setHSL(0.02 + 0.31 * t, 0.85, 0.5);
  return color;
}

function computeVertexSlope(
  waypoints: FlightWaypointRuntime[],
  index: number
): number | null {
  const current = waypoints[index];
  const prev = index > 0 ? waypoints[index - 1] : null;
  const next = index < waypoints.length - 1 ? waypoints[index + 1] : null;

  if (!prev && !next) return null;
  const slopes: number[] = [];
  if (current.slopePercentFromPrev !== null) slopes.push(current.slopePercentFromPrev);
  if (next?.slopePercentFromPrev !== null) slopes.push(next.slopePercentFromPrev);
  if (slopes.length === 0 && prev?.slopePercentFromPrev !== null) slopes.push(prev.slopePercentFromPrev);
  if (slopes.length === 0) return null;
  const sum = slopes.reduce((acc, value) => acc + value, 0);
  return sum / slopes.length;
}

export default function FlightPath3DMap({
  waypoints,
  poi,
  bounds,
  center,
  colorMode,
  className,
}: FlightPath3DMapProps): JSX.Element {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const overlayRef = useRef<google.maps.WebGLOverlayView | null>(null);
  const overlayStateRef = useRef<OverlayState>({ ...INITIAL_OVERLAY_STATE });
  const mapRef = useRef<google.maps.Map | null>(null);
  const polylineRef = useRef<google.maps.Polyline | null>(null);
  const [initialised, setInitialised] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const loaderRef = useRef<Loader | null>(null);
  const poiMarkerRef = useRef<google.maps.marker.AdvancedMarkerElement | null>(null);

  const apiKey = process.env.NEXT_PUBLIC_GOOGLE_MAPS_API_KEY;
  const mapId = process.env.NEXT_PUBLIC_GOOGLE_MAPS_MAP_ID;

  useEffect(() => {
    if (!containerRef.current) return;
    if (!apiKey) {
      setError('Missing NEXT_PUBLIC_GOOGLE_MAPS_API_KEY.');
      return;
    }

    const loader = new Loader({
      apiKey,
      version: 'beta',
      libraries: ['maps3d', 'marker'],
    });
    loaderRef.current = loader;

    let isMounted = true;

    const init = async () => {
      try {
        const [{ Map }, markerLib] = await Promise.all([
          loader.importLibrary('maps') as Promise<google.maps.MapsLibrary>,
          loader.importLibrary('marker') as Promise<google.maps.MarkerLibrary>,
          loader.importLibrary('maps3d'),
        ]);
        const mapOptions: google.maps.MapOptions = {
          mapId: mapId || undefined,
          tilt: DEFAULT_TILT,
          heading: waypoints[0]?.headingDeg ?? 0,
          zoom: DEFAULT_ZOOM,
          center: waypoints[0]
            ? { lat: waypoints[0].latitude, lng: waypoints[0].longitude }
            : { lat: 0, lng: 0 },
          mapTypeControl: false,
          streetViewControl: false,
          fullscreenControl: false,
          controlSize: 28,
          disableDefaultUI: false,
          gestureHandling: 'greedy',
        };

        const mapElement = containerRef.current as HTMLElement;
        const map = new Map(mapElement, mapOptions);
        mapRef.current = map;

        const fallbackPolyline = new google.maps.Polyline({
          map,
          strokeColor: '#ffffff',
          strokeOpacity: 0.58,
          strokeWeight: 2,
        });
        polylineRef.current = fallbackPolyline;

        const overlay = new google.maps.WebGLOverlayView();
        overlayRef.current = overlay;
        const overlayState = overlayStateRef.current;

        overlay.onAdd = () => {
          overlayState.scene = new Scene();
          overlayState.camera = new PerspectiveCamera();

          const ambientLight = new AmbientLight(0xffffff, 0.75);
          const directionalLight = new DirectionalLight(0xffffff, 0.4);
          directionalLight.position.set(0.5, -1, 0.75);
          overlayState.scene.add(ambientLight, directionalLight);

          overlayState.geometry = new BufferGeometry();
          overlayState.positionAttribute = new Float32BufferAttribute([], 3);
          overlayState.colorAttribute = new Float32BufferAttribute([], 3);
          overlayState.geometry.setAttribute('position', overlayState.positionAttribute);
          overlayState.geometry.setAttribute('color', overlayState.colorAttribute);

          const lineMaterial = new LineBasicMaterial({ vertexColors: true, linewidth: 2 });
          overlayState.line = new Line(overlayState.geometry, lineMaterial);
          overlayState.scene.add(overlayState.line);

          const pointsMaterial = new PointsMaterial({ size: 6, sizeAttenuation: false, vertexColors: true });
          overlayState.points = new Points(overlayState.geometry, pointsMaterial);
          overlayState.scene.add(overlayState.points);
        };

        overlay.onContextRestored = ({ gl }) => {
          overlayState.renderer = new WebGLRenderer({
            canvas: gl.canvas,
            context: gl,
            ...gl.getContextAttributes(),
          });
          overlayState.renderer.autoClear = false;
        };

        overlay.onDraw = (options: google.maps.WebGLDrawOptions) => {
          const { transformer } = options;
          const overlayStateInner = overlayStateRef.current;
          if (!overlayStateInner.scene || !overlayStateInner.camera || !overlayStateInner.renderer) {
            return;
          }

          if (overlayStateInner.needsUpdate) {
            updateGeometryForWaypoints(overlayStateInner, transformer, waypoints, colorMode);
            overlayStateInner.needsUpdate = false;
          }

          if (center) {
            const cameraMatrix = transformer.fromLatLngAltitude({
              lat: center.lat,
              lng: center.lng,
              altitude: center.altitudeMeters,
            });
            overlayStateInner.camera.projectionMatrix = new Matrix4().fromArray(cameraMatrix);
          }

          overlayStateInner.renderer.render(overlayStateInner.scene, overlayStateInner.camera);
          overlayStateInner.renderer.resetState();
          overlay.requestRedraw();
        };

        overlay.setMap(map);

        // Add POI marker if available
        if (poi) {
          addOrUpdatePoiMarker(markerLib, poi);
        }

        setInitialised(true);
      } catch (err) {
        if (!isMounted) return;
        setError(err instanceof Error ? err.message : 'Failed to initialise Google Maps.');
      }
    };

    init();

    return () => {
      isMounted = false;
      overlayRef.current?.setMap(null);
      overlayRef.current = null;
      overlayStateRef.current = { ...INITIAL_OVERLAY_STATE };
      if (poiMarkerRef.current) {
        poiMarkerRef.current.map = null;
      }
      poiMarkerRef.current = null;
      if (polylineRef.current) {
        polylineRef.current.setMap(null);
      }
      polylineRef.current = null;
    };
  }, [apiKey, mapId]);

  useEffect(() => {
    if (!initialised) return;
    const overlayState = overlayStateRef.current;
    overlayState.needsUpdate = true;
    overlayRef.current?.requestRedraw();
  }, [initialised, waypoints, colorMode]);

  useEffect(() => {
    if (!initialised || !mapRef.current || !polylineRef.current) return;
    if (waypoints.length < 2) {
      polylineRef.current.setMap(null);
      return;
    }

    const path = waypoints.map((wp) => ({ lat: wp.latitude, lng: wp.longitude }));
    polylineRef.current.setPath(path);
    polylineRef.current.setMap(mapRef.current);
  }, [initialised, waypoints]);

  useEffect(() => {
    if (!initialised || !mapRef.current || waypoints.length === 0) return;
    const map = mapRef.current;

    if (bounds) {
      const mapBounds = new google.maps.LatLngBounds();
      mapBounds.extend({ lat: bounds.south, lng: bounds.west });
      mapBounds.extend({ lat: bounds.north, lng: bounds.east });
      map.fitBounds(mapBounds, { top: 32, right: 32, bottom: 32, left: 32 });
    } else if (center) {
      map.setCenter({ lat: center.lat, lng: center.lng });
      map.setZoom(DEFAULT_ZOOM);
    }

    map.moveCamera({ tilt: DEFAULT_TILT, heading: waypoints[0]?.headingDeg ?? 0 });
  }, [initialised, bounds, center, waypoints]);

  useEffect(() => {
    if (!initialised || !loaderRef.current) return;
    if (!poi) {
      if (poiMarkerRef.current) {
        poiMarkerRef.current.map = null;
        poiMarkerRef.current = null;
      }
      return;
    }

    const addMarker = async () => {
      const markerLib = (await loaderRef.current!.importLibrary('marker')) as google.maps.MarkerLibrary;
      addOrUpdatePoiMarker(markerLib, poi);
    };
    addMarker();
  }, [initialised, poi]);

  if (error) {
    return (
      <div className={className} role="alert">
        {error}
      </div>
    );
  }

  return <div ref={containerRef} className={className} />;

  function addOrUpdatePoiMarker(markerLib: google.maps.MarkerLibrary, poiValue: FlightPoi) {
    const position: google.maps.LatLngAltitudeLiteral = {
      lat: poiValue.latitude,
      lng: poiValue.longitude,
      altitude: poiValue.altitudeMeters,
    };

    if (poiMarkerRef.current) {
      poiMarkerRef.current.position = position;
      poiMarkerRef.current.map = mapRef.current;
      return;
    }

    const { AdvancedMarkerElement } = markerLib;
    poiMarkerRef.current = new AdvancedMarkerElement({
      map: mapRef.current,
      position,
      title: 'Point of Interest',
    });
  }
}

function ensureGeometryCapacity(
  overlayState: OverlayState,
  requiredVertices: number
) {
  if (!overlayState.geometry) {
    overlayState.geometry = new BufferGeometry();
  }

  const currentAttribute = overlayState.positionAttribute;
  if (!currentAttribute || currentAttribute.count !== requiredVertices) {
    overlayState.geometry?.dispose();
    const positions = new Float32Array(requiredVertices * 3);
    const colors = new Float32Array(requiredVertices * 3);
    overlayState.geometry = new BufferGeometry();
    overlayState.positionAttribute = new Float32BufferAttribute(positions, 3);
    overlayState.colorAttribute = new Float32BufferAttribute(colors, 3);
    overlayState.geometry.setAttribute('position', overlayState.positionAttribute);
    overlayState.geometry.setAttribute('color', overlayState.colorAttribute);

    if (overlayState.line) {
      overlayState.line.geometry = overlayState.geometry;
    }
    if (overlayState.points) {
      overlayState.points.geometry = overlayState.geometry;
    }
  }
}

function updateGeometryForWaypoints(
  overlayState: OverlayState,
  transformer: google.maps.CoordinateTransformer,
  waypoints: FlightWaypointRuntime[],
  colorMode: FlightPathColorMode
) {
  if (!overlayState.geometry || !overlayState.positionAttribute || !overlayState.colorAttribute) {
    return;
  }

  const vertexCount = Math.max(waypoints.length, 1);
  ensureGeometryCapacity(overlayState, vertexCount);

  const positions = overlayState.positionAttribute.array as Float32Array;
  const colors = overlayState.colorAttribute.array as Float32Array;

  if (waypoints.length === 0) {
    positions[0] = 0;
    positions[1] = 0;
    positions[2] = 0;
    const baseColor = colorForSlope(0);
    colors[0] = baseColor.r;
    colors[1] = baseColor.g;
    colors[2] = baseColor.b;
  }

  for (let i = 0; i < waypoints.length; i += 1) {
    const waypoint = waypoints[i];
    const matrix = transformer.fromLatLngAltitude({
      lat: waypoint.latitude,
      lng: waypoint.longitude,
      altitude: waypoint.altitudeMeters,
    });
    const baseIndex = i * 3;
    positions[baseIndex] = matrix[12];
    positions[baseIndex + 1] = matrix[13];
    positions[baseIndex + 2] = matrix[14];

    let color: Color;
    if (colorMode === 'curvature') {
      color = colorForCurvature(waypoint.curveSizeMeters);
    } else {
      const slope = computeVertexSlope(waypoints, i);
      color = colorForSlope(slope);
    }
    colors[baseIndex] = color.r;
    colors[baseIndex + 1] = color.g;
    colors[baseIndex + 2] = color.b;
  }

  overlayState.positionAttribute.needsUpdate = true;
  overlayState.colorAttribute.needsUpdate = true;
  overlayState.geometry.computeBoundingSphere();
}

export function formatDistanceMeters(value: number | null | undefined, fractionDigits = 1): string {
  if (value === null || value === undefined || Number.isNaN(value)) {
    return '—';
  }
  if (value >= 1000) {
    return `${(value / 1000).toFixed(fractionDigits)} km`;
  }
  return `${value.toFixed(fractionDigits)} m`;
}

export function formatFeet(value: number | null | undefined, fractionDigits = 1): string {
  if (value === null || value === undefined || Number.isNaN(value)) {
    return '—';
  }
  return `${value.toFixed(fractionDigits)} ft`;
}

export function formatSlopePercent(value: number | null | undefined, fractionDigits = 1): string {
  if (value === null || value === undefined || Number.isNaN(value)) {
    return '—';
  }
  return `${value.toFixed(fractionDigits)} %`;
}

export function formatSpeed(valueMs: number | null | undefined, fractionDigits = 2): string {
  if (valueMs === null || valueMs === undefined || Number.isNaN(valueMs)) {
    return '—';
  }
  const mph = valueMs * 2.23694;
  return `${valueMs.toFixed(fractionDigits)} m/s (${mph.toFixed(2)} mph)`;
}

export function formatDurationSeconds(valueSeconds: number | null | undefined): string {
  if (valueSeconds === null || valueSeconds === undefined || Number.isNaN(valueSeconds)) {
    return '—';
  }
  const minutes = Math.floor(valueSeconds / 60);
  const seconds = Math.round(valueSeconds % 60);
  return `${minutes}m ${seconds}s`;
}
