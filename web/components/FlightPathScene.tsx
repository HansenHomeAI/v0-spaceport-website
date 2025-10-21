"use client";
import React, { useCallback, useEffect, useRef, useState } from "react";
import { buildApiUrl } from '../app/api-config';

interface PreparedRow {
  latitude: number;
  longitude: number;
  altitudeFt: number;
  headingDeg: number | null;
  gimbalPitchAngle: number | null;
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
  onDoubleClick?: (lat: number, lng: number) => void;
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

const DRONE_LENSES: Record<string, { name: string; fov: number; aspectRatio: number }> = {
  mavic3_wide: { name: "Mavic 3 Wide (24mm)", fov: 84, aspectRatio: 4 / 3 },
  mavic3_tele: { name: "Mavic 3 Tele (162mm)", fov: 15, aspectRatio: 4 / 3 },
  air3_wide: { name: "Air 3 Wide (24mm)", fov: 82, aspectRatio: 4 / 3 },
  mini4_wide: { name: "Mini 4 Pro (24mm)", fov: 82.1, aspectRatio: 4 / 3 },
  phantom4: { name: "Phantom 4 Pro (24mm)", fov: 73.7, aspectRatio: 3 / 2 },
};

function degreesToRadians(value: number): number {
  return (value * Math.PI) / 180;
}

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

export default function FlightPathScene({ flights, selectedLens, onWaypointHover, onDoubleClick }: FlightPathSceneProps): JSX.Element {
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

  const fetchTerrainElevation = useCallback(async (lat: number, lon: number): Promise<number> => {
    try {
      let elevationUrl: string;
      const isLocalHost = typeof window !== 'undefined' && (/^(localhost|127\.0\.0\.1)$/).test(window.location.hostname);
      if (isLocalHost) {
        elevationUrl = '/api/elevation-proxy';
      } else {
        elevationUrl = buildApiUrl.dronePath.elevation();
      }
      const response = await fetch(elevationUrl, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ center: `${lat}, ${lon}` }),
      });
      
      if (!response.ok) {
        console.error('[FlightPathScene] Elevation API HTTP error:', response.status);
        return 0;
      }
      
      const data = await response.json();
      if (!data.elevation_meters) {
        console.error('[FlightPathScene] Elevation API missing data:', data);
        return 0;
      }
      
      const elevationMeters = data.elevation_meters;
      console.log(`[FlightPathScene] Terrain elevation: ${data.elevation_feet.toFixed(1)}ft (${elevationMeters.toFixed(1)}m)`);
      return elevationMeters;
    } catch (error) {
      console.error('[FlightPathScene] Elevation API error:', error);
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
        
        Cesium.Ion.defaultAccessToken = "";
        
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
        
        if (viewer.cesiumWidget?.creditContainer) {
          const container = viewer.cesiumWidget.creditContainer as HTMLElement;
          if (container.style) {
            container.style.display = "none";
          }
        }

        viewer.scene.globe.show = false;
        viewer.scene.skyAtmosphere.show = false;
        viewer.scene.skyBox.show = false;
        viewer.scene.backgroundColor = Cesium.Color.BLACK;
        viewer.scene.fog.enabled = false;
        viewer.imageryLayers.removeAll();
        viewer.scene.globe.depthTestAgainstTerrain = false;
        
        viewerRef.current = viewer;
        
        if (containerRef.current) {
          viewer.resize();
          resizeObserverRef.current = new ResizeObserver(() => {
            if (viewerRef.current) {
              viewerRef.current.resize();
            }
          });
          resizeObserverRef.current.observe(containerRef.current);
        }

        try {
          const tileset = await Cesium.Cesium3DTileset.fromUrl(
            `https://tile.googleapis.com/v1/3dtiles/root.json?key=${apiKey}`,
            {
              maximumScreenSpaceError: 16,
              showCreditsOnScreen: false,
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

          tileset.initialTilesLoaded.addEventListener(() => {
            if (!cancelled && viewerRef.current) {
              viewerRef.current.scene.requestRender();
              setViewerReady(true);
            }
          });

          tileset.tileFailed.addEventListener((error: any) => {
            console.error("[FlightPathScene] Tile failed to load", error);
          });

        } catch (tilesetErr) {
          console.error("[FlightPathScene] Photorealistic tiles failed", tilesetErr);
          const message = tilesetErr instanceof Error ? tilesetErr.message : "";
          setInitError(message ? `tileset:${message}` : "tileset");
          setViewerReady(true);
        }

        // Mouse hover for waypoints
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
                if (hoverRef.current) {
                  const previousEntity = waypointEntityMapRef.current.get(hoverRef.current.key);
                  setPointPixelSize(Cesium, previousEntity, 6);
                }
                const currentEntity = waypointEntityMapRef.current.get(key);
                setPointPixelSize(Cesium, currentEntity, 9);
                viewerRef.current?.scene.requestRender();
                onWaypointHover(flightId, index);
                hoverRef.current = { flightId, index, key };
              }
              return;
            }
          }

          if (hoverRef.current) {
            const previousEntity = waypointEntityMapRef.current.get(hoverRef.current.key);
            setPointPixelSize(Cesium, previousEntity, 6);
            onWaypointHover(hoverRef.current.flightId, null);
            hoverRef.current = null;
            viewerRef.current?.scene.requestRender();
          }
        }, Cesium.ScreenSpaceEventType.MOUSE_MOVE);

        // Double-click to place pin
        if (onDoubleClick) {
          handlerRef.current.setInputAction((click: any) => {
            const ray = viewer.camera.getPickRay(click.position);
            if (ray) {
              const cartesian = viewer.scene.globe.pick(ray, viewer.scene);
              if (cartesian) {
                const cartographic = Cesium.Cartographic.fromCartesian(cartesian);
                const lat = Cesium.Math.toDegrees(cartographic.latitude);
                const lng = Cesium.Math.toDegrees(cartographic.longitude);
                onDoubleClick(lat, lng);
              }
            }
          }, Cesium.ScreenSpaceEventType.LEFT_DOUBLE_CLICK);
        }
        
      } catch (err) {
        console.error("[FlightPathScene] Cesium initialization failed", err);
        setInitError("init");
      }
    })();

    return () => {
      cancelled = true;

      if (hoverRef.current) {
        const previousEntity = waypointEntityMapRef.current.get(hoverRef.current.key);
        setPointPixelSize(cesiumRef.current, previousEntity, 6);
        onWaypointHover(hoverRef.current.flightId, null);
        hoverRef.current = null;
      }

      if (viewerRef.current) {
        try {
          flightEntitiesRef.current.forEach((entity) => {
            try {
              viewerRef.current?.entities.remove(entity);
            } catch (_) {}
          });
        } finally {
          flightEntitiesRef.current = [];
        }
      } else {
        flightEntitiesRef.current = [];
      }
      waypointEntityMapRef.current.clear();

      if (resizeObserverRef.current) {
        resizeObserverRef.current.disconnect();
        resizeObserverRef.current = null;
      }
      if (handlerRef.current && typeof (handlerRef.current as any).isDestroyed === 'function') {
        if (!(handlerRef.current as any).isDestroyed()) {
          handlerRef.current.destroy();
        }
      } else if (handlerRef.current) {
        try { handlerRef.current.destroy(); } catch (_) {}
      }
      handlerRef.current = null;

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
  }, [apiKey, onWaypointHover, onDoubleClick]);

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

    if (flights.length > 0 && flights[0].samples.length > 0) {
      const firstWaypoint = flights[0].samples[0];
      
      fetchTerrainElevation(firstWaypoint.latitude, firstWaypoint.longitude)
        .then((terrainElevationMeters) => {
          if (disposed) return;
          const viewer = viewerRef.current as any;
          if (!viewer || viewer.isDestroyed?.()) return;
          
          flights.forEach(flight => {
            const positions: import("cesium").Cartesian3[] = [];

            flight.samples.forEach((sample) => {
              const aglHeightMeters = sample.altitudeFt * FEET_TO_METERS;
              const absoluteHeightMSL = terrainElevationMeters + aglHeightMeters;

              const position = Cesium.Cartesian3.fromDegrees(
                sample.longitude,
                sample.latitude,
                absoluteHeightMSL
              );
              positions.push(position);
            });

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

          try {
            viewer.camera.flyToBoundingSphere(expandedSphere, {
              duration: 1.5,
              offset: new Cesium.HeadingPitchRange(
                0,
                Cesium.Math.toRadians(-45),
                expandedRadius
              ),
            });
          } catch {}
        }

          try { viewer.scene.requestRender(); } catch {}
      })
      .catch((error: Error) => {
        console.error('[FlightPathScene] Elevation API failed, rendering without terrain correction:', error);
          if (disposed) return;
          const viewer = viewerRef.current as any;
          if (!viewer || viewer.isDestroyed?.()) return;
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

          try {
            viewer.camera.flyToBoundingSphere(expandedSphere, {
              duration: 1.5,
              offset: new Cesium.HeadingPitchRange(
                0,
                Cesium.Math.toRadians(-45),
                expandedRadius
              ),
            });
          } catch {}
        }

        try { viewer.scene.requestRender(); } catch {}
      });
    }
    return () => { disposed = true; };
  }, [flights, selectedLens, viewerReady, fetchTerrainElevation]);

  if (!apiKey) {
    return (
      <div style={{
        width: '100%',
        height: '100%',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        background: 'rgba(0,0,0,0.8)',
        color: 'white',
        padding: '20px',
        textAlign: 'center'
      }}>
        <p>Google Maps API key missing. Set NEXT_PUBLIC_GOOGLE_MAPS_API_KEY to enable 3D terrain.</p>
      </div>
    );
  }

  return (
    <div style={{ width: '100%', height: '100%', position: 'relative' }}>
      <div ref={containerRef} style={{ width: '100%', height: '100%' }} />
      {initError && (
        <div style={{
          position: 'absolute',
          top: '10px',
          left: '10px',
          right: '10px',
          background: 'rgba(255, 200, 0, 0.9)',
          color: '#000',
          padding: '10px',
          borderRadius: '8px',
          fontSize: '14px'
        }}>
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

