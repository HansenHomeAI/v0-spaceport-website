"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import {
  buildBatteryPathElevatedFeature,
  buildLineZOffsetExpression,
  type BatteryPathWaypoint3D,
} from "../../lib/flightPath3d";
import {
  averageRealPathOverlapIou,
  buildRealPathFootprintFeatureCollection,
  type RealPathPreviewBattery,
} from "../../lib/realPathSpin";
import styles from "./page.module.css";

const MAPBOX_TOKEN = "pk.eyJ1Ijoic3BhY2Vwb3J0IiwiYSI6ImNtY3F6MW5jYjBsY2wyanEwbHVnd3BrN2sifQ.z2mk_LJg-ey2xqxZW1vW6Q";
const BATTERY_COLORS = [
  "#FF6B6B",
  "#4ECDC4",
  "#45B7D1",
  "#96CEB4",
  "#FFEAA7",
  "#DDA0DD",
  "#98D8C8",
  "#F7DC6F",
  "#BB8FCE",
  "#85C1E9",
  "#F0B27A",
  "#AED6F1",
];

type RealPathMapProps = {
  batteries: RealPathPreviewBattery[];
  selectedBatteryIndex: number | null;
};

type MapboxModule = typeof import("mapbox-gl");
type MapboxMap = import("mapbox-gl").Map;

function emptyFeatureCollection(): GeoJSON.FeatureCollection<GeoJSON.Polygon> {
  return {
    type: "FeatureCollection",
    features: [],
  };
}

function toWaypoints(battery: RealPathPreviewBattery): BatteryPathWaypoint3D[] {
  return battery.waypoints.map((waypoint) => ({
    lat: waypoint.lat,
    lng: waypoint.lng,
    altitudeFeet: waypoint.altitudeFeet,
    curveFeet: waypoint.curveFeet,
  }));
}

function buildWaypointFeatureCollection(
  battery: RealPathPreviewBattery | null,
): GeoJSON.FeatureCollection<GeoJSON.Point> {
  if (!battery) {
    return {
      type: "FeatureCollection",
      features: [],
    };
  }

  return {
    type: "FeatureCollection",
    features: battery.waypoints.map((waypoint, waypointIndex) => ({
      type: "Feature",
      properties: {
        batteryIndex: battery.batteryIndex,
        waypointIndex: waypointIndex + 1,
        altitudeFeet: waypoint.altitudeFeet,
        headingDeg: waypoint.headingDeg,
        gimbalPitchDeg: waypoint.gimbalPitchDeg,
      },
      geometry: {
        type: "Point",
        coordinates: [waypoint.lng, waypoint.lat],
      },
    })),
  };
}

export default function RealPathMap({
  batteries,
  selectedBatteryIndex,
}: RealPathMapProps) {
  const mapContainerRef = useRef<HTMLDivElement | null>(null);
  const mapRef = useRef<MapboxMap | null>(null);
  const mapboxRef = useRef<MapboxModule | null>(null);
  const renderedIdsRef = useRef<{ layers: string[]; sources: string[] }>({ layers: [], sources: [] });
  const [mapPitchDegrees, setMapPitchDegrees] = useState(55);

  const selectedBattery = useMemo(
    () => batteries.find((battery) => battery.batteryIndex === selectedBatteryIndex) ?? batteries[0] ?? null,
    [batteries, selectedBatteryIndex],
  );

  const footprintCollection = useMemo(
    () => (selectedBattery ? buildRealPathFootprintFeatureCollection(selectedBattery.waypoints, 12) : emptyFeatureCollection()),
    [selectedBattery],
  );
  const waypointCollection = useMemo(
    () => buildWaypointFeatureCollection(selectedBattery),
    [selectedBattery],
  );
  const selectedBatteryOverlapPct = useMemo(
    () => (selectedBattery ? averageRealPathOverlapIou(selectedBattery.waypoints) * 100 : 0),
    [selectedBattery],
  );

  useEffect(() => {
    let cancelled = false;

    async function initMap() {
      if (mapRef.current || !mapContainerRef.current) {
        return;
      }

      const mapboxModule = await import("mapbox-gl");
      const mapboxgl: any = (mapboxModule as any).default ?? mapboxModule;
      if (cancelled) {
        return;
      }

      mapboxgl.accessToken = MAPBOX_TOKEN;
      mapboxRef.current = mapboxgl;

      const map = new mapboxgl.Map({
        container: mapContainerRef.current,
        style: "mapbox://styles/mapbox/satellite-v9",
        center: [-98.5795, 39.8283],
        zoom: 3.2,
        pitch: 55,
        bearing: -20,
        attributionControl: false,
      });

      const syncPitch = () => {
        setMapPitchDegrees(Number(map.getPitch().toFixed(2)));
      };

      map.on("load", syncPitch);
      map.on("pitchend", syncPitch);
      map.on("moveend", syncPitch);
      mapRef.current = map;
    }

    void initMap();

    return () => {
      cancelled = true;
      renderedIdsRef.current = { layers: [], sources: [] };
      mapRef.current?.remove();
      mapRef.current = null;
      mapboxRef.current = null;
    };
  }, []);

  useEffect(() => {
    const map = mapRef.current;
    const mapboxgl: any = mapboxRef.current;
    if (!map || !mapboxgl) {
      return;
    }

    const removeRenderedLayers = () => {
      const existing = renderedIdsRef.current;
      existing.layers.slice().reverse().forEach((layerId) => {
        if (map.getLayer(layerId)) {
          map.removeLayer(layerId);
        }
      });
      existing.sources.forEach((sourceId) => {
        if (map.getSource(sourceId)) {
          map.removeSource(sourceId);
        }
      });
      renderedIdsRef.current = { layers: [], sources: [] };
    };

    const render = () => {
      removeRenderedLayers();

      if (batteries.length === 0) {
        return;
      }

      const elevatedLineLayout: any = {
        "line-cap": "round" as const,
        "line-join": "round" as const,
        "line-z-offset": buildLineZOffsetExpression(),
        "line-elevation-reference": "ground" as const,
      };

      batteries.forEach((battery) => {
        if (battery.waypoints.length < 2) {
          return;
        }

        const batteryIndex = battery.batteryIndex;
        const selected = batteryIndex === selectedBattery?.batteryIndex;
        const color = BATTERY_COLORS[(batteryIndex - 1) % BATTERY_COLORS.length];
        const sourceId = `real-path-battery-${batteryIndex}`;
        const shadowLayerId = `real-path-battery-shadow-${batteryIndex}`;
        const casingLayerId = `real-path-battery-casing-${batteryIndex}`;
        const layerId = `real-path-battery-line-${batteryIndex}`;

        map.addSource(sourceId, {
          type: "geojson",
          lineMetrics: true,
          data: buildBatteryPathElevatedFeature(
            battery.waypoints.map((waypoint) => [waypoint.lng, waypoint.lat]),
            toWaypoints(battery),
          ),
        });
        renderedIdsRef.current.sources.push(sourceId);

        map.addLayer({
          id: shadowLayerId,
          type: "line",
          source: sourceId,
          layout: elevatedLineLayout,
          paint: {
            "line-blur": 1.2,
            "line-color": "#02040c",
            "line-emissive-strength": 0.18,
            "line-opacity": selected ? 0.45 : 0.2,
            "line-width": selected ? 16 : 11,
          },
        });
        map.addLayer({
          id: casingLayerId,
          type: "line",
          source: sourceId,
          layout: elevatedLineLayout,
          paint: {
            "line-color": "rgba(5, 10, 18, 0.88)",
            "line-opacity": selected ? 0.95 : 0.45,
            "line-width": selected ? 9 : 6,
          },
        });
        map.addLayer({
          id: layerId,
          type: "line",
          source: sourceId,
          layout: elevatedLineLayout,
          paint: {
            "line-color": color,
            "line-emissive-strength": selected ? 0.75 : 0.35,
            "line-opacity": selected ? 0.98 : 0.55,
            "line-width": selected ? 5.5 : 3.25,
          },
        });

        renderedIdsRef.current.layers.push(shadowLayerId, casingLayerId, layerId);
      });

      if (selectedBattery) {
        const pointSourceId = "real-path-selected-waypoints";
        const pointLayerId = "real-path-selected-waypoints-layer";
        const pointLabelLayerId = "real-path-selected-waypoints-labels";

        map.addSource(pointSourceId, {
          type: "geojson",
          data: waypointCollection,
        });
        renderedIdsRef.current.sources.push(pointSourceId);

        map.addLayer({
          id: pointLayerId,
          type: "circle",
          source: pointSourceId,
          paint: {
            "circle-color": BATTERY_COLORS[(selectedBattery.batteryIndex - 1) % BATTERY_COLORS.length],
            "circle-opacity": 0.92,
            "circle-radius": [
              "interpolate",
              ["linear"],
              ["get", "altitudeFeet"],
              0,
              4,
              Math.max(1, selectedBattery.telemetry.pathDistanceFeet),
              8,
            ],
            "circle-stroke-color": "#f5f5f7",
            "circle-stroke-opacity": 0.8,
            "circle-stroke-width": 1.25,
          },
        });
        map.addLayer({
          id: pointLabelLayerId,
          type: "symbol",
          source: pointSourceId,
          minzoom: 12,
          layout: {
            "text-field": ["to-string", ["get", "waypointIndex"]],
            "text-font": ["Open Sans Bold", "Arial Unicode MS Bold"],
            "text-offset": [0, 1.2],
            "text-size": 10,
          },
          paint: {
            "text-color": "#f5f5f7",
            "text-halo-color": "#000",
            "text-halo-width": 1,
          },
        });
        renderedIdsRef.current.layers.push(pointLayerId, pointLabelLayerId);

        const footprintSourceId = "real-path-footprints";
        const footprintFillLayerId = "real-path-footprints-fill";
        const footprintLineLayerId = "real-path-footprints-line";

        map.addSource(footprintSourceId, {
          type: "geojson",
          data: footprintCollection,
        });
        renderedIdsRef.current.sources.push(footprintSourceId);

        map.addLayer({
          id: footprintFillLayerId,
          type: "fill",
          source: footprintSourceId,
          paint: {
            "fill-color": BATTERY_COLORS[(selectedBattery.batteryIndex - 1) % BATTERY_COLORS.length],
            "fill-opacity": 0.11,
          },
        });
        map.addLayer({
          id: footprintLineLayerId,
          type: "line",
          source: footprintSourceId,
          paint: {
            "line-color": "#f5f5f7",
            "line-dasharray": [1.3, 1],
            "line-opacity": 0.45,
            "line-width": 1.1,
          },
        });
        renderedIdsRef.current.layers.push(footprintFillLayerId, footprintLineLayerId);
      }

      const fitCoordinates = (
        selectedBattery?.waypoints.length
          ? selectedBattery.waypoints
          : batteries.flatMap((battery) => battery.waypoints)
      ).map((waypoint) => [waypoint.lng, waypoint.lat] as [number, number]);

      if (fitCoordinates.length > 0) {
        const bounds = fitCoordinates.reduce(
          (accumulator, [lng, lat]) => accumulator.extend([lng, lat]),
          new mapboxgl.LngLatBounds(fitCoordinates[0], fitCoordinates[0]),
        );

        map.fitBounds(bounds, {
          animate: false,
          bearing: -20,
          maxZoom: 17,
          padding: 56,
          pitch: 55,
        });
      }
    };

    if (map.isStyleLoaded()) {
      render();
      return;
    }

    map.once("load", render);
    return () => {
      map.off("load", render);
    };
  }, [batteries, footprintCollection, selectedBattery, waypointCollection]);

  return (
    <div
      className={`map-wrapper ${styles.realPathMapWrapper}`}
      data-elevated-line-count={batteries.filter((battery) => battery.waypoints.length > 1).length}
      data-footprint-count={footprintCollection.features.length}
      data-map-pitch={mapPitchDegrees}
      data-rendered-path-point-count={selectedBattery?.waypoints.length ?? 0}
      data-selected-battery={selectedBattery?.batteryIndex ?? ""}
      data-selected-overlap-pct={selectedBatteryOverlapPct.toFixed(2)}
    >
      <div className={styles.realPathMapHeader}>
        <div>
          <p className={styles.realPathMapEyebrow}>Mapbox Preview</p>
          <p className={styles.realPathMapTitle}>
            {selectedBattery ? `Battery ${selectedBattery.batteryIndex}` : "Awaiting route"}
          </p>
        </div>
        <div className={styles.realPathMapMeta}>
          <span>{selectedBattery?.telemetry.waypointCount ?? 0} waypoints</span>
          <span>{selectedBatteryOverlapPct.toFixed(0)}% avg overlap</span>
        </div>
      </div>
      <div ref={mapContainerRef} className={styles.realPathMapCanvas} />
      {batteries.length === 0 ? (
        <div className={styles.realPathMapEmpty}>
          Generate a real-path mission to preview the curved line, waypoint elevations, and overlap footprints.
        </div>
      ) : null}
    </div>
  );
}
