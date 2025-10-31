"use client";
import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";
import Papa from "papaparse";
import JSZip from "jszip";
import { XMLParser } from "fast-xml-parser";
import { buildApiUrl } from "../app/api-config";

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

interface FlightData {
  id: string;
  name: string;
  color: string;
  samples: ProcessedSample[];
}

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

function calculateBearing(lat1: number, lon1: number, lat2: number, lon2: number): number {
  const lat1Rad = (lat1 * Math.PI) / 180;
  const lat2Rad = (lat2 * Math.PI) / 180;
  const dLon = ((lon2 - lon1) * Math.PI) / 180;

  const y = Math.sin(dLon) * Math.cos(lat2Rad);
  const x = Math.cos(lat1Rad) * Math.sin(lat2Rad) -
            Math.sin(lat1Rad) * Math.cos(lat2Rad) * Math.cos(dLon);

  let bearing = Math.atan2(y, x);
  bearing = (bearing * 180) / Math.PI;
  bearing = (bearing + 360) % 360;

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

function buildSamples(samples: PreparedRow[]): ProcessedSample[] {
  if (!samples.length) {
    return [];
  }

  const processedSamples: ProcessedSample[] = samples.map((sample, index) => ({
    ...sample,
    index,
  }));

  for (let i = 0; i < processedSamples.length; i += 1) {
    const sample = processedSamples[i];

    if (!sample.headingDeg || sample.headingDeg === 0) {
      let calculatedHeading: number | null = null;

      if (i < processedSamples.length - 1) {
        const nextSample = processedSamples[i + 1];
        calculatedHeading = calculateBearing(
          sample.latitude,
          sample.longitude,
          nextSample.latitude,
          nextSample.longitude,
        );
      } else if (i > 0) {
        const prevSample = processedSamples[i - 1];
        calculatedHeading = calculateBearing(
          prevSample.latitude,
          prevSample.longitude,
          sample.latitude,
          sample.longitude,
        );
      }

      if (calculatedHeading !== null) {
        sample.headingDeg = calculatedHeading;
      }
    }
  }

  return processedSamples;
}

async function parseKMZFile(file: File): Promise<PreparedRow[]> {
  const zip = await JSZip.loadAsync(file);
  const waylineEntry = zip.file(/waylines\.wpml$/i)[0];
  if (!waylineEntry) {
    throw new Error("No waylines.wpml found in KMZ");
  }

  const xmlContent = await waylineEntry.async("text");
  const parser = new XMLParser({ ignoreAttributes: false, attributeNamePrefix: "" });
  const parsed = parser.parse(xmlContent);

  const waypoints = parsed?.DJIWPMission?.Wayline?.Waypoints?.Waypoint;
  if (!waypoints) {
    throw new Error("No waypoints found in KMZ");
  }

  const arrayWaypoints = Array.isArray(waypoints) ? waypoints : [waypoints];

  const prepared: PreparedRow[] = arrayWaypoints
    .map((wp: any) => {
      const latitude = toNumber(wp.latitude ?? wp.Latitude ?? wp.lat);
      const longitude = toNumber(wp.longitude ?? wp.Longitude ?? wp.lon);
      const altitudeFt = toNumber(wp.height ?? wp.Altitude ?? wp.altitude);

      if (!Number.isFinite(latitude) || !Number.isFinite(longitude) || !Number.isFinite(altitudeFt)) {
        return null;
      }

      return {
        latitude,
        longitude,
        altitudeFt,
        headingDeg: toOptionalNumber(wp.heading ?? wp.Heading),
        curveSizeFt: toOptionalNumber(wp.curvesize ?? wp.CurveSize),
        rotationDir: toOptionalNumber(wp.rotationdir ?? wp.RotationDir),
        gimbalMode: toOptionalNumber(wp.gimbalmode ?? wp.GimbalMode),
        gimbalPitchAngle: toOptionalNumber(wp.gimbalpitchangle ?? wp.GimbalPitchAngle),
        altitudeMode: toOptionalNumber(wp.altitudemode ?? wp.AltitudeMode),
        speedMs: toOptionalNumber(wp.speed ?? wp.Speed),
        poiLatitude: toOptionalNumber(wp.poi_latitude ?? wp.poiLatitude),
        poiLongitude: toOptionalNumber(wp.poi_longitude ?? wp.poiLongitude),
        poiAltitudeFt: toOptionalNumber(wp.poi_altitude ?? wp.poiAltitude),
        poiAltitudeMode: toOptionalNumber(wp.poi_altitude_mode ?? wp.poiAltitudeMode),
        photoTimeInterval: toOptionalNumber(wp.photo_timeinterval ?? wp.PhotoTimeInterval),
        photoDistInterval: toOptionalNumber(wp.photo_distinterval ?? wp.PhotoDistInterval),
      } satisfies PreparedRow;
    })
    .filter((value): value is PreparedRow => value !== null);

  if (!prepared.length) {
    throw new Error("KMZ file did not contain any waypoints");
  }

  return prepared;
}

async function parseCsvText(csvText: string): Promise<PreparedRow[]> {
  return new Promise((resolve, reject) => {
    Papa.parse<RawFlightRow>(csvText, {
      header: true,
      skipEmptyLines: true,
      dynamicTyping: true,
      complete: (result) => {
        if (result.errors.length) {
          reject(new Error(`CSV parse error: ${result.errors[0].message}`));
          return;
        }
        const prepared = result.data
          .map(sanitizeRow)
          .filter((value): value is PreparedRow => value !== null);
        resolve(prepared);
      },
      error: (error) => reject(error),
    });
  });
}

declare const CESIUM_BASE_URL: string | undefined;

declare global {
  interface Window {
    CESIUM_BASE_URL?: string;
  }
}

type NewProjectModalProps = {
  open: boolean;
  onClose: () => void;
  project?: any; // when provided, modal acts in edit mode and pre-fills values
  onSaved?: () => void; // callback after successful save/update
};

type OptimizedParams = {
  [key: string]: any;
  center: string;
  minHeight: number;
  maxHeight: number | null;
  elevationFeet: number | null;
};

export default function NewProjectModal({ open, onClose, project, onSaved }: NewProjectModalProps): JSX.Element | null {
  const MAPBOX_GEOCODING_TOKEN = process.env.NEXT_PUBLIC_MAPBOX_TOKEN ?? 'pk.eyJ1Ijoic3BhY2Vwb3J0IiwiYSI6ImNtY3F6MW5jYjBsY2wyanEwbHVnd3BrN2sifQ.z2mk_LJg-ey2xqxZW1vW6Q';
  // Use centralized API configuration instead of hardcoded values
  const API_ENHANCED_BASE = buildApiUrl.dronePath.optimizeSpiral().replace('/api/optimize-spiral', '');
  const API_UPLOAD = {
    START_UPLOAD: buildApiUrl.fileUpload.startUpload(),
    GET_PRESIGNED_URL: buildApiUrl.fileUpload.getPresignedUrl(),
    COMPLETE_UPLOAD: buildApiUrl.fileUpload.completeUpload(),
    SAVE_SUBMISSION: buildApiUrl.fileUpload.saveSubmission(),
    START_ML_PROCESSING: buildApiUrl.mlPipeline.startJob(),
  } as const;

  const CHUNK_SIZE = 64 * 1024 * 1024; // 64MB - industry standard for optimal speed/reliability balance
  const MAX_FILE_SIZE = 20 * 1024 * 1024 * 1024; // 20GB

  // UI state
  const [projectTitle, setProjectTitle] = useState<string>("Untitled");
  const [addressSearch, setAddressSearch] = useState<string>("");
  const [batteryMinutes, setBatteryMinutes] = useState<string>("");
  const [numBatteries, setNumBatteries] = useState<string>("");
  const [minHeightFeet, setMinHeightFeet] = useState<string>("");
  const [maxHeightFeet, setMaxHeightFeet] = useState<string>("");

  const [propertyTitle, setPropertyTitle] = useState<string>("");
  const [listingDescription, setListingDescription] = useState<string>("");
  const [contactEmail, setContactEmail] = useState<string>("");

  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [uploadProgress, setUploadProgress] = useState<number>(0);
  const [uploadLoading, setUploadLoading] = useState<boolean>(false);
  const [mlLoading, setMlLoading] = useState<boolean>(false);
  const [uploadStage, setUploadStage] = useState<string>('');
  const [selectedCoords, setSelectedCoords] = useState<{ lat: number; lng: number } | null>(null);
  const [isSaving, setIsSaving] = useState<boolean>(false);
  const saveTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const initialRenderRef = useRef<boolean>(true);

  const [optimizedParams, setOptimizedParams] = useState<OptimizedParams | null>(null);
  const optimizedParamsRef = useRef<OptimizedParams | null>(null);

  // 🔍 DEBUGGING: Wrapper function to track all optimizedParams changes
  const setOptimizedParamsWithLogging = useCallback((newParams: OptimizedParams | null, reason: string) => {
    const timestamp = new Date().toISOString();
    const stackTrace = new Error().stack?.split('\n').slice(2, 5).join('\n') || 'No stack trace';
    
    console.log(`🔍 [${timestamp}] OPTIMIZATION CACHE ${newParams ? 'SET' : 'CLEARED'}:`);
    console.log(`   Reason: ${reason}`);
    console.log(`   Previous: ${optimizedParamsRef.current ? 'EXISTS' : 'NULL'}`);
    console.log(`   New: ${newParams ? 'EXISTS' : 'NULL'}`);
    console.log(`   Stack trace:`, stackTrace);
    
    if (newParams) {
      console.log(`   Params:`, {
        slices: newParams.slices,
        N: newParams.N,
        center: newParams.center,
        minHeight: newParams.minHeight,
        maxHeight: newParams.maxHeight
      });
    }
    
    setOptimizedParams(newParams);
    optimizedParamsRef.current = newParams;
  }, []);
  const [optimizationLoading, setOptimizationLoading] = useState<boolean>(false);
  const [downloadingBatteries, setDownloadingBatteries] = useState<Set<number>>(new Set());
  const [processingMessage, setProcessingMessage] = useState<string>('');

  const mapContainerRef = useRef<HTMLDivElement | null>(null);
  const cesiumModuleRef = useRef<typeof import("cesium") | null>(null);
  const viewerRef = useRef<import("cesium").Viewer | null>(null);
  const tilesetRef = useRef<import("cesium").Cesium3DTileset | null>(null);
  const markerEntityRef = useRef<import("cesium").Entity | null>(null);
  const flightEntitiesRef = useRef<import("cesium").Entity[]>([]);
  const flightColorIndexRef = useRef<number>(0);
  const handlerRef = useRef<import("cesium").ScreenSpaceEventHandler | null>(null);
  const resizeObserverRef = useRef<ResizeObserver | null>(null);
  const hasFitCameraRef = useRef<boolean>(false);
  const terrainCacheRef = useRef<Map<string, number>>(new Map());
  const [cesiumInitError, setCesiumInitError] = useState<string | null>(null);
  const [tilesetWarning, setTilesetWarning] = useState<string | null>(null);
  const [viewerReady, setViewerReady] = useState<boolean>(false);
  const [flightOverlays, setFlightOverlays] = useState<FlightData[]>([]);

  const mapStatusMessage = useMemo(() => {
    if (cesiumInitError === 'missing-key') {
      return '3D view unavailable. Configure NEXT_PUBLIC_GOOGLE_MAPS_API_KEY to enable terrain.';
    }
    if (cesiumInitError) {
      return '3D view unavailable due to WebGL initialization failure.';
    }
    if (tilesetWarning) {
      return `Photorealistic tiles failed to load (${tilesetWarning}). Showing geometry without terrain.`;
    }
    return null;
  }, [cesiumInitError, tilesetWarning]);

  const [toast, setToast] = useState<{ type: 'success' | 'error'; message: string } | null>(null);

  // Center-screen modal popup system (replacing Safari notifications)
  const [modalPopup, setModalPopup] = useState<{ type: 'success' | 'error'; message: string } | null>(null);
  
  const showSystemNotification = useCallback((type: 'success' | 'error', message: string) => {
    // Show center-screen modal instead of browser notifications
    setModalPopup({ type, message });
    
    // Auto-dismiss success messages after 3 seconds
    if (type === 'success') {
      setTimeout(() => setModalPopup(null), 3000);
    }
  }, []);

  // simple, general progress model
  const STATUS_TO_PROGRESS: Record<string, number> = {
    draft: 5,
    path_downloaded: 20,
    photos_uploaded: 50,
    processing: 75,
    delivered: 100,
  };
  const [status, setStatus] = useState<string>('draft');
  const [currentProjectId, setCurrentProjectId] = useState<string | null>(project?.projectId || null);

  const [setupOpen, setSetupOpen] = useState<boolean>(true);
  const [uploadOpen, setUploadOpen] = useState<boolean>(false);

  const selectedCoordsRef = useRef<{ lat: number; lng: number } | null>(null);

  // Fullscreen state
  const [isFullscreen, setIsFullscreen] = useState<boolean>(false);



  // Reset state when opening/closing
  useEffect(() => {
    if (!open) {
      setFlightOverlays([]);
      flightColorIndexRef.current = 0;
      hasFitCameraRef.current = false;
      selectedCoordsRef.current = null;
      setSelectedCoords(null);
      return;
    }
    setUploadProgress(0);
    setUploadLoading(false);
    setMlLoading(false);
    setUploadStage('');
    setOptimizedParamsWithLogging(null, 'Modal opened/reset');
    setDownloadingBatteries(new Set());
    setSetupOpen(true);
    setUploadOpen(false);
    setToast(null);
    setIsFullscreen(false);
    
    // If editing, hydrate fields from project
    if (project) {
      console.log(`🔍 Loading project data:`, {
        title: project.title,
        params: project.params,
        savedBatteryMinutes: project.params?.batteryMinutes,
        savedBatteries: project.params?.batteries,
        savedMinHeight: project.params?.minHeight,
        savedMaxHeight: project.params?.maxHeight,
        hasCoordinates: !!(project.params?.latitude && project.params?.longitude)
      });
      
      setProjectTitle(project.title || 'Untitled');
      const params = project.params || {};
      // Don't set address search yet if we have coordinates - Cesium restore handles it
      if (!(params.latitude && params.longitude)) {
        setAddressSearch(params.address || '');
      }
      setBatteryMinutes(params.batteryMinutes || '');
      setNumBatteries(params.batteries || '');
      setMinHeightFeet(params.minHeight || '');
      setMaxHeightFeet(params.maxHeight || '');
      setContactEmail(project.email || '');
      setStatus(project.status || 'draft');
      setCurrentProjectId(project.projectId || null);
      
      // CRITICAL FIX: Restore saved coordinates if they exist
      if (params.latitude && params.longitude) {
        const coords = { 
          lat: parseFloat(params.latitude), 
          lng: parseFloat(params.longitude) 
        };
        selectedCoordsRef.current = coords;
        setSelectedCoords(coords);
        
        // Auto-restore optimization params for existing projects with complete data
        setTimeout(async () => {
          const coords = selectedCoordsRef.current;
          const minutes = parseInt(params.batteryMinutes || '');
          const batteries = parseInt(params.batteries || '');
          
          console.log(`🔍 Auto-restore timeout firing:`, {
            coords: coords ? 'EXISTS' : 'NULL',
            savedMinutes: params.batteryMinutes,
            parsedMinutes: minutes,
            savedBatteries: params.batteries,
            parsedBatteries: batteries,
            currentOptimizedParams: optimizedParamsRef.current ? 'EXISTS' : 'NULL'
          });
          
          if (coords && minutes && batteries) {
            try {
              setOptimizationLoading(true);
              
              // Step 1: optimize spiral
              const optRes = await fetch(`${API_ENHANCED_BASE}/api/optimize-spiral`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ batteryMinutes: minutes, batteries, center: `${coords.lat}, ${coords.lng}` }),
              });
              if (!optRes.ok) throw new Error('Flight path optimization failed');
              const optData = await optRes.json();

              // Step 2: elevation
              let elevationFeet: number | null = null;
              const elevRes = await fetch(`${API_ENHANCED_BASE}/api/elevation`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ center: `${coords.lat}, ${coords.lng}` }),
              });
              if (elevRes.ok) {
                const elevData = await elevRes.json();
                elevationFeet = elevData.elevation_feet ?? null;
              }

              const minH = parseFloat(params.minHeight || '120') || 120;
              const maxH = params.maxHeight ? parseFloat(params.maxHeight) : null;

              const optimizedParams: OptimizedParams = {
                ...optData.optimized_params,
                center: `${coords.lat}, ${coords.lng}`,
                minHeight: minH,
                maxHeight: maxH,
                elevationFeet,
              };
              setOptimizedParamsWithLogging(optimizedParams, 'Auto-restore optimization completed');
            } catch (e) {
              console.warn('Failed to auto-restore optimization params:', e);
            } finally {
              setOptimizationLoading(false);
            }
          }
        }, 2000); // Increased delay to ensure map is fully loaded
      }
    } else {
      // CRITICAL FIX: Reset all fields to blank state for new projects
      setProjectTitle('Untitled');
      setAddressSearch('');
      setBatteryMinutes('');
      setNumBatteries('');
      setMinHeightFeet('');
      setMaxHeightFeet('');
      setPropertyTitle('');
      setListingDescription('');
      setContactEmail('');
      setSelectedFile(null);
      setStatus('draft');
      setCurrentProjectId(null);
      selectedCoordsRef.current = null;
      setSelectedCoords(null);
    }

    // Cleanup timeout on unmount
    return () => {
      if (saveTimeoutRef.current) {
        clearTimeout(saveTimeoutRef.current);
      }
    };
  }, [open, project]);

  const fetchTerrainElevationMeters = useCallback(async (lat: number, lng: number): Promise<number | null> => {
    const cacheKey = `${lat.toFixed(5)},${lng.toFixed(5)}`;
    if (terrainCacheRef.current.has(cacheKey)) {
      return terrainCacheRef.current.get(cacheKey) ?? null;
    }

    try {
      const response = await fetch('/api/elevation-proxy', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ center: `${lat}, ${lng}` }),
      });

      if (!response.ok) {
        console.warn('[NewProjectModal] Elevation proxy failed', response.status);
        return null;
      }

      const data = await response.json();
      const meters: number | undefined = data.elevation_meters ?? data.elevationMeters;
      if (typeof meters === 'number' && Number.isFinite(meters)) {
        terrainCacheRef.current.set(cacheKey, meters);
        return meters;
      }

      return null;
    } catch (err) {
      console.warn('[NewProjectModal] Elevation lookup error', err);
      return null;
    }
  }, []);

  const placeMarkerAtCoords = useCallback(async (
    lat: number,
    lng: number,
    options: { reason: string; updateAddress?: boolean; flyCamera?: boolean } = { reason: 'manual' },
  ) => {
    if (!viewerRef.current || !cesiumModuleRef.current) {
      selectedCoordsRef.current = { lat, lng };
      setSelectedCoords({ lat, lng });
      if (options.updateAddress) {
        setAddressSearch(`${lat.toFixed(6)}, ${lng.toFixed(6)}`);
      }
      setOptimizedParamsWithLogging(null, `Coordinates changed (${options.reason})`);
      return;
    }

    const Cesium = cesiumModuleRef.current;
    const viewer = viewerRef.current;

    const terrainMeters = await fetchTerrainElevationMeters(lat, lng);
    const height = typeof terrainMeters === 'number' && Number.isFinite(terrainMeters) ? terrainMeters : 0;

    const position = Cesium.Cartesian3.fromDegrees(lng, lat, height);

    if (!markerEntityRef.current) {
      markerEntityRef.current = viewer.entities.add({
        position,
        billboard: {
          image: '/assets/SpaceportIcons/TeardropPin.svg',
          verticalOrigin: Cesium.VerticalOrigin.BOTTOM,
          scale: 0.9,
          disableDepthTestDistance: Number.POSITIVE_INFINITY,
          pixelOffset: new Cesium.Cartesian2(0, -6),
        },
      });
    } else {
      markerEntityRef.current.position = new Cesium.ConstantPositionProperty(position);
    }

    selectedCoordsRef.current = { lat, lng };
    setSelectedCoords({ lat, lng });

    if (options.updateAddress) {
      setAddressSearch(`${lat.toFixed(6)}, ${lng.toFixed(6)}`);
    }

    setOptimizedParamsWithLogging(null, `Coordinates changed (${options.reason})`);

    if (options.flyCamera !== false) {
      viewer.camera.flyTo({
        destination: Cesium.Cartesian3.fromDegrees(lng, lat, 1500),
        orientation: {
          heading: viewer.camera.heading,
          pitch: Cesium.Math.toRadians(-55),
          roll: 0,
        },
        duration: 1.6,
      });
    }

    const inst = document.getElementById('map-instructions');
    if (inst) inst.style.display = 'none';

    try { viewer.scene.requestRender(); } catch (_) {}
  }, [fetchTerrainElevationMeters, setOptimizedParamsWithLogging]);

  useEffect(() => {
    if (!open) {
      return;
    }

    let cancelled = false;

    const initViewer = async () => {
      if (!mapContainerRef.current) {
        return;
      }

      setCesiumInitError(null);
      setTilesetWarning(null);
      setViewerReady(false);
      hasFitCameraRef.current = false;

      const apiKey = process.env.NEXT_PUBLIC_GOOGLE_MAPS_API_KEY || "";
      if (!apiKey) {
        setCesiumInitError('missing-key');
        return;
      }

      try {
        const Cesium = await import('cesium');
        cesiumModuleRef.current = Cesium;
        Cesium.Ion.defaultAccessToken = '';

        if (typeof window !== 'undefined') {
          window.CESIUM_BASE_URL = window.CESIUM_BASE_URL ?? (typeof CESIUM_BASE_URL !== 'undefined' ? CESIUM_BASE_URL : '/cesium');
        }

        if (cancelled || !mapContainerRef.current) {
          return;
        }

        const viewer = new Cesium.Viewer(mapContainerRef.current, {
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

        viewerRef.current = viewer;

        if (viewer.cesiumWidget?.creditContainer) {
          const container = viewer.cesiumWidget.creditContainer as HTMLElement;
          if (container?.style) {
            container.style.display = 'none';
          }
        }

        viewer.scene.globe.show = false;
        viewer.scene.skyAtmosphere.show = false;
        viewer.scene.skyBox.show = false;
        viewer.scene.backgroundColor = Cesium.Color.BLACK;
        viewer.scene.fog.enabled = false;
        viewer.scene.globe.depthTestAgainstTerrain = false;
        viewer.imageryLayers.removeAll();

        viewer.camera.setView({
          destination: Cesium.Cartesian3.fromDegrees(-98.5795, 39.8283, 2_500_000),
        });

        try { viewer.scene.requestRender(); } catch (_) {}

        if (mapContainerRef.current) {
          viewer.resize();
          if (resizeObserverRef.current) {
            resizeObserverRef.current.disconnect();
          }
          resizeObserverRef.current = new ResizeObserver(() => {
            viewerRef.current?.resize();
          });
          resizeObserverRef.current.observe(mapContainerRef.current);
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
            },
          );

          if (cancelled) {
            tileset.destroy();
            return;
          }

          viewer.scene.primitives.add(tileset);
          tilesetRef.current = tileset;

          tileset.initialTilesLoaded.addEventListener(() => {
            if (!cancelled) {
              setViewerReady(true);
              try { viewer.scene.requestRender(); } catch (_) {}
            }
          });

          tileset.tileFailed.addEventListener((error: any) => {
            console.error('[NewProjectModal] Photorealistic tiles failed', error);
            const message = error?.message ?? 'tileset';
            setTilesetWarning(message);
          });
        } catch (tilesetErr) {
          console.error('[NewProjectModal] Photorealistic tiles failed', tilesetErr);
          const message = tilesetErr instanceof Error ? tilesetErr.message : 'tileset';
          setTilesetWarning(message);
          setViewerReady(true);
        }

        if (!tilesetRef.current) {
          setViewerReady(true);
        }

        if (handlerRef.current) {
          try {
            if (typeof (handlerRef.current as any).destroy === 'function') {
              handlerRef.current.destroy();
            }
          } catch (_) {}
        }
        handlerRef.current = new Cesium.ScreenSpaceEventHandler(viewer.scene.canvas);
        handlerRef.current.setInputAction(async (movement: any) => {
          if (!viewerRef.current || !cesiumModuleRef.current) return;
          const CesiumLocal = cesiumModuleRef.current;
          const viewerInstance = viewerRef.current;

          let cartesian = viewerInstance.scene.pickPosition(movement.position);
          if (!CesiumLocal.defined(cartesian)) {
            cartesian = viewerInstance.camera.pickEllipsoid(
              movement.position,
              viewerInstance.scene.globe.ellipsoid,
            );
          }

          if (!CesiumLocal.defined(cartesian)) {
            return;
          }

          const cartographic = CesiumLocal.Cartographic.fromCartesian(cartesian);
          const lat = CesiumLocal.Math.toDegrees(cartographic.latitude);
          const lng = CesiumLocal.Math.toDegrees(cartographic.longitude);

          await placeMarkerAtCoords(lat, lng, {
            reason: 'double-click',
            updateAddress: true,
          });
        }, Cesium.ScreenSpaceEventType.LEFT_DOUBLE_CLICK);

        if (project?.params?.latitude && project?.params?.longitude) {
          const lat = parseFloat(project.params.latitude);
          const lng = parseFloat(project.params.longitude);
          if (Number.isFinite(lat) && Number.isFinite(lng)) {
            await placeMarkerAtCoords(lat, lng, {
              reason: 'restore',
              updateAddress: true,
              flyCamera: false,
            });
            const inst = document.getElementById('map-instructions');
            if (inst) inst.style.display = 'none';
          }
        }
      } catch (err) {
        console.error('[NewProjectModal] Cesium initialization failed', err);
        setCesiumInitError('init');
      }
    };

    initViewer();

    return () => {
      cancelled = true;
      setViewerReady(false);
      hasFitCameraRef.current = false;

      if (handlerRef.current) {
        try {
          if (typeof (handlerRef.current as any).destroy === 'function') {
            handlerRef.current.destroy();
          }
        } catch (_) {}
        handlerRef.current = null;
      }

      if (resizeObserverRef.current) {
        resizeObserverRef.current.disconnect();
        resizeObserverRef.current = null;
      }

      if (flightEntitiesRef.current.length && viewerRef.current) {
        flightEntitiesRef.current.forEach((entity) => {
          try { viewerRef.current?.entities.remove(entity); } catch (_) {}
        });
      }
      flightEntitiesRef.current = [];

      if (markerEntityRef.current && viewerRef.current) {
        try { viewerRef.current.entities.remove(markerEntityRef.current); } catch (_) {}
        markerEntityRef.current = null;
      }

      if (tilesetRef.current) {
        try {
          if (viewerRef.current) {
            viewerRef.current.scene.primitives.remove(tilesetRef.current);
          }
        } catch (_) {}
        try { tilesetRef.current.destroy(); } catch (_) {}
        tilesetRef.current = null;
      }

      if (viewerRef.current) {
        try { viewerRef.current.entities.removeAll(); } catch (_) {}
        try { viewerRef.current.dataSources.removeAll(); } catch (_) {}
        try { (viewerRef.current as any).scene?.tweens?.removeAll?.(); } catch (_) {}
        try {
          if (typeof (viewerRef.current as any).destroy === 'function') {
            viewerRef.current.destroy();
          }
        } catch (_) {}
        viewerRef.current = null;
      }

      cesiumModuleRef.current = null;
      terrainCacheRef.current.clear();
      setTilesetWarning(null);
    };
  }, [open, project, placeMarkerAtCoords]);

  // Fullscreen toggle handler
  const toggleFullscreen = useCallback(() => {
    if (!mapContainerRef.current) return;
    
    const newFullscreen = !isFullscreen;
    setIsFullscreen(newFullscreen);
    
    // Find the map-wrapper (parent of map-container)
    const mapWrapper = mapContainerRef.current.parentElement;
    if (!mapWrapper) return;
    
    if (newFullscreen) {
      // Enter fullscreen - move wrapper to body
      document.body.appendChild(mapWrapper);
      mapWrapper.classList.add('fullscreen');
    } else {
      // Exit fullscreen - move wrapper back to original parent
      const mapSection = document.querySelector('.popup-map-section');
      if (mapSection) {
        mapSection.appendChild(mapWrapper);
      }
      mapWrapper.classList.remove('fullscreen');
    }
    
    // Allow Cesium to resize after DOM move
    setTimeout(() => {
      if (viewerRef.current) {
        viewerRef.current.resize();
        try { viewerRef.current.scene.requestRender(); } catch (_) {}
      }
    }, 300);
  }, [isFullscreen]);

  // ESC key to exit fullscreen
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && isFullscreen) {
        toggleFullscreen();
      }
    };
    
    if (open) {
      document.addEventListener('keydown', handleKeyDown);
      return () => document.removeEventListener('keydown', handleKeyDown);
    }
  }, [open, isFullscreen, toggleFullscreen]);

  // Keep coordinates synchronized between state and ref
  useEffect(() => {
    console.log('🔍 Coordinate sync effect:', {
      selectedCoords: selectedCoords ? 'EXISTS' : 'NULL',
      refCoords: selectedCoordsRef.current ? 'EXISTS' : 'NULL'
    });
    
    if (selectedCoords) {
      selectedCoordsRef.current = selectedCoords;
      console.log('🔍 Updated coordinates ref:', selectedCoords);
    }
  }, [selectedCoords]);

  const canOptimize = useMemo(() => {
    // Always use ref as source of truth for coordinates
    const coords = selectedCoordsRef.current;
    const minutes = parseInt(batteryMinutes || '');
    const batteries = parseInt(numBatteries || '');
    const isValid = Boolean(coords && minutes && batteries);
    
    // Debug logging to help track state
    console.log('🔍 Optimization validation:', {
      hasCoords: !!coords,
      coordsValue: coords,
      minutes,
      batteries,
      isValid
    });
    
    return isValid;
  }, [batteryMinutes, numBatteries]); // Only depend on battery params since we use ref for coords

  // Rotating processing messages for optimization
  const processingMessages = [
    "This may take a moment...",
    "Running binary search optimization",
    "Forming to elevation data", 
    "Maximizing battery usage",
    "Calculating optimal flight paths",
    "Analyzing terrain features"
  ];

  const startProcessingMessages = useCallback(() => {
    let messageIndex = 0;
    setProcessingMessage(processingMessages[0]);
    
    const interval = setInterval(() => {
      messageIndex = (messageIndex + 1) % processingMessages.length;
      setProcessingMessage(processingMessages[messageIndex]);
    }, 2000); // Change message every 2 seconds
    
    return interval;
  }, []);

  const registerFlightOverlay = useCallback((name: string, samples: ProcessedSample[]) => {
    if (!samples.length) {
      return false;
    }

    const colorIndex = flightColorIndexRef.current % FLIGHT_COLORS.length;
    flightColorIndexRef.current = (flightColorIndexRef.current + 1) % FLIGHT_COLORS.length;

    const flight: FlightData = {
      id: `${name}-${Date.now()}`,
      name,
      color: FLIGHT_COLORS[colorIndex],
      samples,
    };

    setFlightOverlays(prev => {
      const existingIndex = prev.findIndex(item => item.name === name);
      if (existingIndex >= 0) {
        const copy = [...prev];
        copy[existingIndex] = flight;
        return copy;
      }
      return [...prev, flight];
    });

    hasFitCameraRef.current = false;
    return true;
  }, []);

  const ingestFlightFromCsvText = useCallback(async (name: string, csvText: string) => {
    try {
      const prepared = await parseCsvText(csvText);
      if (!prepared.length) {
        showSystemNotification('error', `${name} did not contain any waypoints`);
        return;
      }

      const samples = buildSamples(prepared);
      if (!samples.length) {
        showSystemNotification('error', `${name} did not contain valid waypoints`);
        return;
      }

      registerFlightOverlay(name, samples);
    } catch (err) {
      console.error('[NewProjectModal] Failed to parse flight CSV', err);
      showSystemNotification('error', `Failed to parse ${name}`);
    }
  }, [registerFlightOverlay, showSystemNotification]);

  const ingestFlightFiles = useCallback(async (files: FileList | File[]) => {
    const iterable = Array.from(files as ArrayLike<File>);

    for (const file of iterable) {
      const extension = file.name.toLowerCase().split('.').pop();
      try {
        let prepared: PreparedRow[] = [];
        if (extension === 'csv') {
          const text = await file.text();
          prepared = await parseCsvText(text);
        } else if (extension === 'kmz') {
          prepared = await parseKMZFile(file);
        } else {
          showSystemNotification('error', `${file.name}: Unsupported format (use CSV or KMZ)`);
          continue;
        }

        if (!prepared.length) {
          showSystemNotification('error', `${file.name}: No waypoints found`);
          continue;
        }

        const samples = buildSamples(prepared);
        if (!samples.length) {
          showSystemNotification('error', `${file.name}: No valid waypoints`);
          continue;
        }

        registerFlightOverlay(file.name, samples);
      } catch (err) {
        console.error('[NewProjectModal] Failed to parse flight file', err);
        showSystemNotification('error', `${file.name}: Failed to parse`);
      }
    }
  }, [registerFlightOverlay, showSystemNotification]);

  const handleFlightDrop = useCallback(async (event: React.DragEvent<HTMLDivElement>) => {
    event.preventDefault();
    const files = event.dataTransfer?.files;
    if (files && files.length) {
      await ingestFlightFiles(files);
    }
  }, [ingestFlightFiles]);

  const handleFlightDragOver = useCallback((event: React.DragEvent<HTMLDivElement>) => {
    event.preventDefault();
    if (event.dataTransfer) {
      event.dataTransfer.dropEffect = 'copy';
    }
  }, []);

  const handleOptimize = useCallback(async () => {
    if (!canOptimize) return;
    setOptimizationLoading(true);
    const messageInterval = startProcessingMessages();
    console.log('Starting optimization...');
    try {
      const coords = selectedCoordsRef.current!;
      const minutes = parseInt(batteryMinutes);
      const batteries = parseInt(numBatteries);
      
      // Validate parameters to prevent API errors
      if (!coords || !coords.lat || !coords.lng) {
        throw new Error('Invalid coordinates');
      }
      if (isNaN(minutes) || minutes <= 0 || minutes > 60) {
        throw new Error('Battery minutes must be between 1-60');
      }
      if (isNaN(batteries) || batteries <= 0 || batteries > 12) {
        throw new Error('Number of batteries must be between 1-12');
      }
      
      console.log('Optimization params:', { 
        coords, 
        minutes, 
        batteries, 
        minHeight: minHeightFeet, 
        maxHeight: maxHeightFeet 
      });

      // Step 1: optimize spiral
      const optRes = await fetch(`${API_ENHANCED_BASE}/api/optimize-spiral`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ batteryMinutes: minutes, batteries, center: `${coords.lat}, ${coords.lng}` }),
      });
      if (!optRes.ok) throw new Error('Flight path optimization failed');
      const optData = await optRes.json();

      // Step 2: elevation
      let elevationFeet: number | null = null;
      const elevRes = await fetch(`${API_ENHANCED_BASE}/api/elevation`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ center: `${coords.lat}, ${coords.lng}` }),
      });
      if (elevRes.ok) {
        const elevData = await elevRes.json();
        elevationFeet = elevData.elevation_feet ?? null;
      }

      const minH = parseFloat(minHeightFeet || '120') || 120;
      const maxH = maxHeightFeet ? parseFloat(maxHeightFeet) : null;

      const params: OptimizedParams = {
        ...optData.optimized_params,
        center: `${coords.lat}, ${coords.lng}`,
        minHeight: minH,
        maxHeight: maxH,
        elevationFeet,
      };
      setOptimizedParamsWithLogging(params, 'Optimization completed successfully');
      console.log('Optimization completed successfully:', params);
    } catch (e: any) {
      console.error('Optimization failed:', e);
      showSystemNotification('error', e?.message || 'Optimization failed');
    } finally {
      clearInterval(messageInterval);
      setProcessingMessage('');
      setOptimizationLoading(false);
    }
  }, [API_ENHANCED_BASE, batteryMinutes, numBatteries, minHeightFeet, maxHeightFeet, canOptimize]);

  // Processing messages for battery downloads
  const batteryProcessingMessages = [
    "Running binary search optimization",
    "Forming to the terrain",
    "Calculating altitude adjustments", 
    "Optimizing flight coverage",
    "Generating waypoint data",
    "Finalizing flight path"
  ];

  const downloadBatteryCsv = useCallback(async (batteryIndex1: number) => {
    // Check if already downloading this battery
    if (downloadingBatteries.has(batteryIndex1)) {
      return;
    }
    
    // Use ref to get current optimized params (not stale closure)
    const currentOptimizedParams = optimizedParamsRef.current;
    
    console.log(`🔍 downloadBatteryCsv called for battery ${batteryIndex1}:`, {
      currentOptimizedParams: currentOptimizedParams ? 'EXISTS' : 'NULL',
      optimizedParamsState: optimizedParams ? 'EXISTS' : 'NULL'
    });
    
    if (!currentOptimizedParams) {
      console.log(`🔍 No optimized params found - showing error`);
      showSystemNotification('error', 'Please optimize first');
      return;
    }
    
    // Add to downloading set
    setDownloadingBatteries(prev => new Set([...prev, batteryIndex1]));
    
    // Start processing messages only if this is the first download
    let messageInterval: NodeJS.Timeout | null = null;
    if (downloadingBatteries.size === 0) {
      let messageIndex = 0;
      setProcessingMessage(batteryProcessingMessages[0]);
      messageInterval = setInterval(() => {
        messageIndex = (messageIndex + 1) % batteryProcessingMessages.length;
        setProcessingMessage(batteryProcessingMessages[messageIndex]);
      }, 2000);
    }
    
    try {
      console.log(`🔍 Sending to API for battery ${batteryIndex1}:`, currentOptimizedParams);
      
      const res = await fetch(`${API_ENHANCED_BASE}/api/csv/battery/${batteryIndex1}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(currentOptimizedParams),
      });
      if (!res.ok) throw new Error(`Failed to generate battery ${batteryIndex1} CSV`);
      const csvText = await res.text();
      const safeTitle = (projectTitle && projectTitle !== 'Untitled')
        ? projectTitle.replace(/[^a-zA-Z0-9-_]/g, '_').substring(0, 50)
        : 'Untitled';
      const filename = `${safeTitle}-${batteryIndex1}.csv`;
      await ingestFlightFromCsvText(filename, csvText);
      const blob = new Blob([csvText], { type: 'text/csv' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
      
      // Update project status to indicate drone path has been downloaded
      if (status === 'draft') {
        setStatus('path_downloaded');
      }
    } catch (e: any) {
      showSystemNotification('error', e?.message || 'CSV download failed');
    } finally {
      if (messageInterval) {
        clearInterval(messageInterval);
      }
      setDownloadingBatteries(prev => {
        const newSet = new Set(prev);
        newSet.delete(batteryIndex1);
        // Only clear processing message if this was the last battery downloading
        if (newSet.size === 0) {
          setProcessingMessage('');
        }
        return newSet;
      });
    }
  }, [API_ENHANCED_BASE, projectTitle, downloadingBatteries, ingestFlightFromCsvText]);

  // SIMPLE, ROBUST save function with rate limiting
  const saveProject = useCallback(async () => {
    // Prevent multiple simultaneous saves
    if (isSaving) return;
    
    try {
      setIsSaving(true);
      console.log('Saving project...', { currentProjectId, projectTitle });
      
      const { Auth } = await import('aws-amplify');
      const session = await Auth.currentSession();
      const idToken = session.getIdToken().getJwtToken();
      const apiEnv = process.env.NEXT_PUBLIC_PROJECTS_API_URL;
      if (!apiEnv) throw new Error('Projects API URL is not configured');
      const apiBase = apiEnv.replace(/\/$/, '');
      const progress = STATUS_TO_PROGRESS[status] ?? 0;
      
      const body = {
        title: projectTitle,
        status,
        progress,
        params: {
          address: addressSearch,
          batteryMinutes,
          batteries: numBatteries,
          minHeight: minHeightFeet,
          maxHeight: maxHeightFeet,
          latitude: selectedCoordsRef.current?.lat || null,
          longitude: selectedCoordsRef.current?.lng || null,
        },
      };
      
      const url = currentProjectId ? `${apiBase}/${encodeURIComponent(currentProjectId)}` : `${apiBase}`;
      const method = currentProjectId ? 'PATCH' : 'POST';
      
      const res = await fetch(url, {
        method,
        headers: { 'content-type': 'application/json', Authorization: `Bearer ${idToken}` },
        body: JSON.stringify(body),
      });
      
      if (!res.ok) {
        const errorText = await res.text().catch(() => 'Unknown error');
        console.error('Save failed:', res.status, errorText);
        throw new Error(`Save failed: ${res.status} - ${errorText}`);
      }
      
      console.log('Project saved successfully');
      
      // Capture created id on first POST
      if (!currentProjectId) {
        const data = await res.json().catch(() => ({} as any));
        const created = (data && (data.project || data)) as any;
        if (created && created.projectId) setCurrentProjectId(created.projectId);
      }
      
      onSaved?.();
    } catch (e: any) {
      console.error('Save failed:', e);
      showSystemNotification('error', e?.message || 'Failed to save project');
    } finally {
      setIsSaving(false);
    }
  }, [addressSearch, batteryMinutes, currentProjectId, maxHeightFeet, minHeightFeet, numBatteries, onSaved, projectTitle, status, isSaving]);

  // Check if project has meaningful content
  const hasMeaningfulContent = useCallback(() => {
    // Always save if editing existing project
    if (currentProjectId) return true;
    
    // For new projects, check if any meaningful data is entered
    const hasLocation = Boolean(addressSearch.trim() || selectedCoords);
    const hasBatteryData = Boolean(batteryMinutes || numBatteries);
    const hasAltitudeData = Boolean(minHeightFeet || maxHeightFeet);
    const hasTitleChange = projectTitle !== 'Untitled' && projectTitle.trim();
    const hasUploadData = Boolean(propertyTitle.trim() || listingDescription.trim() || contactEmail.trim() || selectedFile);
    
    return hasLocation || hasBatteryData || hasAltitudeData || hasTitleChange || hasUploadData;
  }, [currentProjectId, addressSearch, batteryMinutes, numBatteries, minHeightFeet, maxHeightFeet, projectTitle, propertyTitle, listingDescription, contactEmail, selectedFile, selectedCoords]);

  // SIMPLE debounced save trigger
  const triggerSave = useCallback(() => {
    // Clear any existing timeout
    if (saveTimeoutRef.current) {
      clearTimeout(saveTimeoutRef.current);
    }
    
    // Only save if we have meaningful content
    if (hasMeaningfulContent()) {
      saveTimeoutRef.current = setTimeout(() => {
        saveProject();
      }, 1000); // Longer debounce to prevent spam
    }
  }, [hasMeaningfulContent, saveProject]);

  // Simple autosave trigger - much more controlled
  useEffect(() => {
    if (!open) return;
    
    // Skip saving on initial render to avoid render-phase updates
    if (initialRenderRef.current) {
      initialRenderRef.current = false;
      return;
    }
    
    console.log(`🔍 Autosave useEffect triggered:`, {
      projectTitle,
      addressSearch,
      batteryMinutes,
      numBatteries,
      minHeightFeet,
      maxHeightFeet,
      status,
      selectedCoords: selectedCoords ? 'EXISTS' : 'NULL',
      optimizedParams: optimizedParams ? 'EXISTS' : 'NULL'
    });
    
    // Don't trigger save immediately, use timeout to avoid render-phase updates
    const timer = setTimeout(() => {
      triggerSave();
    }, 100); // Small delay to avoid render-phase updates
    
    return () => clearTimeout(timer);
  }, [open, projectTitle, addressSearch, batteryMinutes, numBatteries, minHeightFeet, maxHeightFeet, status, selectedCoords]);

  // Delete project function
  const handleDeleteProject = useCallback(async () => {
    if (!currentProjectId) return;
    if (!confirm('Are you sure you want to delete this project? This action cannot be undone.')) return;
    
    try {
      const { Auth } = await import('aws-amplify');
      const session = await Auth.currentSession();
      const idToken = session.getIdToken().getJwtToken();
      const apiEnv2 = process.env.NEXT_PUBLIC_PROJECTS_API_URL;
      if (!apiEnv2) throw new Error('Projects API URL is not configured');
      const apiBase = apiEnv2.replace(/\/$/, '');
      
      const res = await fetch(`${apiBase}/${encodeURIComponent(currentProjectId)}`, {
        method: 'DELETE',
        headers: { Authorization: `Bearer ${idToken}` },
      });
      
      if (!res.ok) throw new Error(`Delete failed: ${res.status}`);
      
      showSystemNotification('success', 'Project deleted successfully');
      onSaved?.(); // Refresh the projects list
      onClose(); // Close the modal
    } catch (e: any) {
      showSystemNotification('error', e?.message || 'Failed to delete project');
    }
  }, [currentProjectId, onSaved, onClose]);

  // Address search via Mapbox Geocoding or direct coordinates
  const handleAddressEnter = useCallback(async (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key !== 'Enter') return;
    e.preventDefault();
    const query = addressSearch.trim();
    if (!query) return;
    
    // Check if input looks like coordinates (lat, lng)
    const coordsMatch = query.match(/^(-?\d+\.?\d*)\s*,\s*(-?\d+\.?\d*)$/);
    
    if (coordsMatch) {
      // Handle direct coordinate input
      const lat = parseFloat(coordsMatch[1]);
      const lng = parseFloat(coordsMatch[2]);
      
      if (lat >= -90 && lat <= 90 && lng >= -180 && lng <= 180) {
        await placeMarkerAtCoords(lat, lng, {
          reason: 'coordinate-input',
          updateAddress: true,
        });
        return;
      }
    }
    
    // Handle geocoding search
    try {
      if (!MAPBOX_GEOCODING_TOKEN) {
        showSystemNotification('error', 'Mapbox geocoding token missing');
        return;
      }
      const res = await fetch(`https://api.mapbox.com/geocoding/v5/mapbox.places/${encodeURIComponent(query)}.json?access_token=${MAPBOX_GEOCODING_TOKEN}&limit=1`);
      const data = await res.json();
      if (data?.features?.length) {
        const [lng, lat] = data.features[0].center;
        await placeMarkerAtCoords(lat, lng, {
          reason: 'geocode',
          updateAddress: true,
        });
      }
    } catch (err) {
      console.warn('Geocoding failed:', err);
    }
  }, [addressSearch, MAPBOX_GEOCODING_TOKEN, placeMarkerAtCoords, showSystemNotification]);

  useEffect(() => {
    if (!viewerReady || !viewerRef.current || !cesiumModuleRef.current) {
      return;
    }

    const Cesium = cesiumModuleRef.current;
    const viewer = viewerRef.current;
    let cancelled = false;

    const removeExistingEntities = () => {
      if (!viewer) return;
      if (flightEntitiesRef.current.length) {
        flightEntitiesRef.current.forEach((entity) => {
          try { viewer.entities.remove(entity); } catch (_) {}
        });
        flightEntitiesRef.current = [];
      }
    };

    const renderFlights = async () => {
      removeExistingEntities();

      if (!flightOverlays.length) {
        hasFitCameraRef.current = false;
        try { viewer.scene.requestRender(); } catch (_) {}
        return;
      }

      const referenceFlight = flightOverlays.find(flight => flight.samples.length > 0);
      let terrainMeters = 0;
      if (referenceFlight) {
        const firstSample = referenceFlight.samples[0];
        const terrain = await fetchTerrainElevationMeters(firstSample.latitude, firstSample.longitude);
        if (cancelled) return;
        if (typeof terrain === 'number' && Number.isFinite(terrain)) {
          terrainMeters = terrain;
        } else {
          console.warn('[NewProjectModal] Terrain lookup failed, falling back to AGL heights');
        }
      }

      const fitPositions: import('cesium').Cartesian3[] = [];
      const newEntities: import('cesium').Entity[] = [];

      flightOverlays.forEach((flight) => {
        if (cancelled) {
          return;
        }

        const positions = flight.samples.map(sample => {
          const absoluteMeters = terrainMeters + (sample.altitudeFt * FEET_TO_METERS);
          const position = Cesium.Cartesian3.fromDegrees(sample.longitude, sample.latitude, absoluteMeters);
          fitPositions.push(position);
          return position;
        });

        if (positions.length >= 2) {
          const polyline = viewer.entities.add({
            polyline: {
              positions,
              width: 2.2,
              material: Cesium.Color.fromCssColorString(flight.color).withAlpha(0.95),
              arcType: Cesium.ArcType.GEODESIC,
            },
          });
          newEntities.push(polyline);
        }

        positions.forEach((position) => {
          const waypointEntity = viewer.entities.add({
            position,
            point: {
              pixelSize: 5,
              color: Cesium.Color.fromCssColorString(flight.color),
              outlineColor: Cesium.Color.fromCssColorString('#182036'),
              outlineWidth: 1,
            },
          });
          newEntities.push(waypointEntity);
        });
      });

      flightEntitiesRef.current = newEntities;

      if (!hasFitCameraRef.current && fitPositions.length) {
        const boundingSphere = Cesium.BoundingSphere.fromPoints(fitPositions);
        if (Number.isFinite(boundingSphere.radius) && boundingSphere.radius > 0) {
          const expandedSphere = new Cesium.BoundingSphere(
            boundingSphere.center,
            boundingSphere.radius * 1.3,
          );
          try {
            viewer.camera.flyToBoundingSphere(expandedSphere, {
              offset: new Cesium.HeadingPitchRange(
                viewer.camera.heading,
                Cesium.Math.toRadians(-35),
                expandedSphere.radius * 2.1,
              ),
              duration: 1.4,
            });
            hasFitCameraRef.current = true;
          } catch (_) {}
        }
      }

      try { viewer.scene.requestRender(); } catch (_) {}
    };

    renderFlights();

    return () => {
      cancelled = true;
      removeExistingEntities();
    };
  }, [flightOverlays, fetchTerrainElevationMeters, viewerReady]);

  // Upload flow
  const onFileChosen = useCallback((file: File | null) => {
    setSelectedFile(file);
  }, []);

  const validateUpload = useCallback(() => {
    if (!propertyTitle.trim()) return 'Property title is required';
    if (!contactEmail.trim()) return 'Email address is required';
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailRegex.test(contactEmail.trim())) return 'Please enter a valid email address';
    if (!selectedFile) return 'Please select a .zip file to upload';
    if (!selectedFile.name.toLowerCase().endsWith('.zip')) return 'Please upload a .zip file only';
    if (selectedFile.size > MAX_FILE_SIZE) return 'File size exceeds 20GB limit';
    return null;
  }, [propertyTitle, contactEmail, selectedFile]);

  const startUpload = useCallback(async () => {
    const validationError = validateUpload();
    if (validationError) {
      showSystemNotification('error', validationError);
      return;
    }
    if (!selectedFile) return;
    setUploadLoading(true);
    setMlLoading(false);
    setUploadProgress(0);
    setUploadStage('Initializing upload...');
    try {
      // Show initial progress to indicate activity
      setUploadProgress(5);
      
      // init multipart
      const initRes = await fetch(API_UPLOAD.START_UPLOAD, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          fileName: selectedFile.name,
          fileType: selectedFile.type || 'application/zip',
          propertyTitle: propertyTitle.trim(),
          email: contactEmail.trim(),
          listingDescription: listingDescription.trim(),
        }),
      });
      if (!initRes.ok) throw new Error(`Failed to start upload: ${initRes.status}`);
      const init = await initRes.json();

      // upload chunks with parallel processing
      const totalChunks = Math.ceil(selectedFile.size / CHUNK_SIZE);
      setUploadStage(`Uploading file (${Math.round(selectedFile.size / 1024 / 1024)}MB) in ${totalChunks} chunks (parallel)...`);
      
      const parts: Array<{ ETag: string | null; PartNumber: number }> = [];
      const MAX_RETRIES = 3;
      const RETRY_DELAY = 1000; // 1 second
      const MAX_CONCURRENT_UPLOADS = 10; // Optimized for high-bandwidth connections
      
      console.log(`📤 Starting parallel chunked upload: ${totalChunks} chunks of ${Math.round(CHUNK_SIZE / 1024 / 1024)}MB each`);
      console.log(`🚀 Uploading up to ${MAX_CONCURRENT_UPLOADS} chunks in parallel`);
      
      let completedChunks = 0;
      
      // Process chunks in batches to control concurrency
      for (let i = 0; i < totalChunks; i += MAX_CONCURRENT_UPLOADS) {
        const batch = [];
        
        // Create batch of concurrent uploads
        for (let j = 0; j < MAX_CONCURRENT_UPLOADS && (i + j) < totalChunks; j++) {
          const chunkIndex = i + j;
          const partNumber = chunkIndex + 1;
          
          // Create upload promise for this chunk
          const uploadPromise = uploadChunkWithRetry(
            selectedFile, // Pass the original file
            chunkIndex, // Pass the chunk index
            partNumber, 
            init, 
            MAX_RETRIES, 
            RETRY_DELAY
          ).then(result => {
            completedChunks++;
            const progress = 5 + ((completedChunks / totalChunks) * 90);
            setUploadProgress(progress);
            console.log(`✅ Part ${partNumber}/${totalChunks} uploaded successfully (${completedChunks}/${totalChunks} complete)`);
            return result;
          });
          
          batch.push(uploadPromise);
        }
        
        // Wait for this batch to complete before starting next batch
        try {
          const batchResults = await Promise.all(batch);
          parts.push(...batchResults);
        } catch (error: any) {
          throw new Error(`Batch upload failed: ${error.message}`);
        }
      }
      
      // Sort parts by part number to ensure correct order
      parts.sort((a, b) => a.PartNumber - b.PartNumber);
      
      console.log(`🎉 All ${totalChunks} chunks uploaded successfully!`);
      
      // Helper function for chunk upload with retry
      async function uploadChunkWithRetry(file: File, chunkIndex: number, partNumber: number, uploadInit: any, maxRetries: number, retryDelay: number) {
        let retryCount = 0;
        
        while (retryCount < maxRetries) {
          try {
            // Create fresh chunk for each retry attempt
            const start = chunkIndex * CHUNK_SIZE;
            const end = Math.min(start + CHUNK_SIZE, file.size);
            const chunk = file.slice(start, end);
            
            const urlRes = await fetch(API_UPLOAD.GET_PRESIGNED_URL, {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({
                uploadId: uploadInit.uploadId,
                bucketName: uploadInit.bucketName,
                objectKey: uploadInit.objectKey,
                partNumber,
              }),
            });
            if (!urlRes.ok) throw new Error(`Failed to get upload URL for part ${partNumber}: ${urlRes.status}`);
            
            const { url } = await urlRes.json();
            const putRes = await fetch(url, { method: 'PUT', body: chunk });
            if (!putRes.ok) throw new Error(`Failed to upload part ${partNumber}: ${putRes.status}`);
            
            const etag = putRes.headers.get('ETag');
            if (!etag) throw new Error(`No ETag received for part ${partNumber}`);
            
            return { ETag: etag, PartNumber: partNumber };
            
          } catch (error: any) {
            retryCount++;
            console.warn(`⚠️ Part ${partNumber} upload failed (attempt ${retryCount}/${maxRetries}):`, error.message);
            
            if (retryCount >= maxRetries) {
              throw new Error(`Failed to upload part ${partNumber} after ${maxRetries} attempts: ${error.message}`);
            }
            
            // Wait before retry (exponential backoff)
            await new Promise(resolve => setTimeout(resolve, retryDelay * retryCount));
          }
        }
      }

      // complete multipart
      setUploadStage('Finalizing upload...');
      setUploadProgress(100);
      const completeRes = await fetch(API_UPLOAD.COMPLETE_UPLOAD, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          uploadId: init.uploadId,
          bucketName: init.bucketName,
          objectKey: init.objectKey,
          parts,
        }),
      });
      if (!completeRes.ok) throw new Error('Failed to complete upload');

      // save metadata
      setUploadStage('Saving metadata...');
      const saveRes = await fetch(API_UPLOAD.SAVE_SUBMISSION, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          objectKey: init.objectKey,
          propertyTitle: propertyTitle.trim(),
          email: contactEmail.trim(),
          listingDescription: listingDescription.trim(),
        }),
      });
      if (!saveRes.ok) throw new Error('Failed to save submission metadata');

      // start ML processing
      setUploadStage('Starting ML processing...');
      setMlLoading(true);
      const s3Url = `s3://${init.bucketName}/${init.objectKey}`;
      const mlRes = await fetch(API_UPLOAD.START_ML_PROCESSING, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ s3Url, email: contactEmail.trim(), pipelineStep: 'sfm' }),
      });
      if (!mlRes.ok) {
        const errData = await mlRes.json().catch(() => ({}));
        throw new Error(errData?.error || `ML processing failed: ${mlRes.status}`);
      }
      const ml = await mlRes.json();
      setUploadStage('Upload completed successfully!');
      setStatus('photos_uploaded');
      showSystemNotification('success', 'Upload successful! Your 3D model is being processed and will be delivered via email.');

      // Persist a project stub for this user
      try {
        const { Auth } = await import('aws-amplify');
        const session = await Auth.currentSession();
        const idToken = session.getIdToken().getJwtToken();
        const api = process.env.NEXT_PUBLIC_PROJECTS_API_URL;
        if (!api) throw new Error('Projects API URL is not configured');
        await fetch(api, {
          method: 'POST',
          headers: { 'content-type': 'application/json', Authorization: `Bearer ${idToken}` },
          body: JSON.stringify({
            title: projectTitle,
            status: 'uploading',
            progress: 10,
            params: {
              address: addressSearch,
              batteryMinutes: batteryMinutes,
              batteries: numBatteries,
              minHeight: minHeightFeet,
              maxHeight: maxHeightFeet,
            },
            upload: { objectKey: init.objectKey },
          }),
        });
      } catch (e) {
        console.warn('Failed to persist project:', e);
      }
      setSetupOpen(false);
      setUploadOpen(true);
    } catch (e: any) {
      const msg = e?.message || 'Upload failed';
      showSystemNotification('error', msg);
    } finally {
      setUploadLoading(false);
      setMlLoading(false);
      // Keep stage text visible for a few seconds after completion
      setTimeout(() => setUploadStage(''), 3000);
    }
  }, [API_UPLOAD, CHUNK_SIZE, MAX_FILE_SIZE, propertyTitle, contactEmail, listingDescription, selectedFile, validateUpload]);

  if (!open) return null;

  const batteryCount = Math.max(0, Math.min(12, parseInt(numBatteries || '0') || 0));

  return (
    <div id="newProjectPopup" role="dialog" aria-modal="true" className="popup-overlay" style={{ display: 'block' }}>
      <div className="popup-header">
        <div className="popup-title-section">
          <textarea
            id="projectTitle"
            className="popup-title-input"
            rows={1}
            placeholder="Untitled"
            value={projectTitle}
            onChange={(e) => setProjectTitle(e.target.value)}
          />
          <span className="edit-icon" />
        </div>
        <button className="popup-close" onClick={onClose} />
      </div>

      {toast && (
        <div aria-live="polite" style={{ position: 'fixed', right: 16, top: 16, zIndex: 1100 }}>
          <div style={{
            background: toast.type === 'success' ? '#163a24' : '#3a1616',
            border: `1px solid ${toast.type === 'success' ? '#1f6f46' : '#7a2e2e'}`,
            color: '#fff',
            padding: '10px 12px',
            borderRadius: 8,
            boxShadow: '0 10px 32px rgba(0,0,0,0.3)'
          }}>
            {toast.message}
          </div>
        </div>
      )}

      <div className="popup-content-scroll">
        {/* Status is automatic and displayed on the dashboard cards only */}
        {/* SECTION 1: CREATE FLIGHT PLAN */}
        <div className={`accordion-section${setupOpen ? ' active' : ''}`} data-section="setup">
          <div className="accordion-header" onClick={() => setSetupOpen(v => !v)}>
            <div className="accordion-title">
              <h3>Create Flight Plan</h3>
            </div>
            <span className="accordion-chevron"></span>
          </div>
          {setupOpen && (
          <div className="accordion-content">
            <div className="popup-map-section">
                            <div className="map-wrapper" onDragOver={handleFlightDragOver} onDrop={handleFlightDrop}>
                {/* Empty map container for Mapbox - avoids the warning */}
                <div id="map-container" className="map-container" ref={mapContainerRef}></div>

                {/* Map overlays and controls as siblings */}
                <button className={`expand-button${isFullscreen ? ' expanded' : ''}`} id="expand-button" onClick={toggleFullscreen}>
                  <span className="expand-icon"></span>
                </button>
                {mapStatusMessage && (
                  <div
                    className="map-warning-overlay"
                    style={{
                      position: 'absolute',
                      top: 16,
                      left: '50%',
                      transform: 'translateX(-50%)',
                      background: 'rgba(12, 16, 30, 0.86)',
                      color: '#f1f5f9',
                      padding: '12px 16px',
                      borderRadius: 12,
                      border: '1px solid rgba(148, 163, 184, 0.4)',
                      zIndex: 20,
                      maxWidth: '340px',
                      textAlign: 'center',
                      fontSize: '0.85rem',
                      lineHeight: 1.4,
                    }}
                  >
                    <strong style={{ display: 'block', marginBottom: 4 }}>Heads up</strong>
                    {mapStatusMessage}
                  </div>
                )}
                <div className="map-dim-overlay"></div>
                <div className="map-blur-background"></div>
                <div className="map-blur-overlay top"></div>
                <div className="map-blur-overlay bottom"></div>
                <div className="map-progressive-bottom-blur"></div>

                <div className="map-instructions-center" id="map-instructions">
                  <div className="instruction-content">
                    <div className="instruction-pin"></div>
                    <h3>Select the focus point for your drone flight.</h3>
                  </div>
                </div>

                <div className="address-search-overlay">
                  <div className="address-search-wrapper">
                    <input
                      type="text"
                      id="address-search"
                      className="text-fade-right"
                      placeholder="Enter location"
                      value={addressSearch}
                      onChange={(e) => setAddressSearch(e.target.value)}
                      onKeyDown={handleAddressEnter}
                      style={{}}
                    />
                  </div>
                </div>
              </div>
            </div>

            {/* Batteries */}
            <div className="category-outline">
              <div className="popup-section">
                <h4>Batteries</h4>
                <div className="input-row-popup">
                  <div className="popup-input-wrapper" style={{ position: 'relative' }}>
                    <span className="input-icon time"></span>
                    <input
                      type="text"
                      className="text-fade-right"
                      placeholder="Duration"
                      value={batteryMinutes ? `${batteryMinutes} min/battery` : ''}
                      onChange={(e) => { 
                        const value = e.target.value.replace(/[^0-9]/g, '');
                        console.log(`🔍 Battery minutes changing from "${batteryMinutes}" to "${value}"`);
                        setBatteryMinutes(value); 
                        setOptimizedParamsWithLogging(null, `Battery minutes changed to: ${value}`); 
                      }}
                      onKeyDown={(e) => {
                        // Allow only numbers, backspace, delete, arrow keys
                        if (!/[0-9]/.test(e.key) && !['Backspace', 'Delete', 'ArrowLeft', 'ArrowRight', 'Tab'].includes(e.key)) {
                          e.preventDefault();
                        }
                      }}
                      style={{}}
                    />
                  </div>
                  <div className="popup-input-wrapper" style={{ position: 'relative' }}>
                    <span className="input-icon number"></span>
                    <input
                      type="text"
                      className="text-fade-right"
                      placeholder="Quantity"
                      value={numBatteries ? `${numBatteries} ${parseInt(numBatteries) === 1 ? 'battery' : 'batteries'}` : ''}
                      onChange={(e) => { 
                        const value = e.target.value.replace(/[^0-9]/g, '');
                        console.log(`🔍 Number of batteries changing from "${numBatteries}" to "${value}"`);
                        setNumBatteries(value); 
                        setOptimizedParamsWithLogging(null, `Number of batteries changed to: ${value}`); 
                      }}
                      onKeyDown={(e) => {
                        // Allow only numbers, backspace, delete, arrow keys
                        if (!/[0-9]/.test(e.key) && !['Backspace', 'Delete', 'ArrowLeft', 'ArrowRight', 'Tab'].includes(e.key)) {
                          e.preventDefault();
                        }
                      }}
                      style={{}}
                    />
                  </div>
                </div>
              </div>
            </div>

            {/* Altitude */}
            <div className="category-outline">
              <div className="popup-section">
                <h4>Altitude</h4>
                <div className="input-row-popup">
                  <div className="popup-input-wrapper" style={{ position: 'relative' }}>
                    <span className="input-icon minimum"></span>
                    <input
                      type="text"
                      className="text-fade-right"
                      placeholder="Minimum"
                      value={minHeightFeet ? `${minHeightFeet} ft AGL` : ''}
                      onChange={(e) => { 
                        const value = e.target.value.replace(/[^0-9]/g, '');
                        console.log(`🔍 Min height changing from "${minHeightFeet}" to "${value}"`);
                        setMinHeightFeet(value); 
                        setOptimizedParamsWithLogging(null, `Min height changed to: ${value}`); 
                      }}
                      onKeyDown={(e) => {
                        // Allow only numbers, backspace, delete, arrow keys
                        if (!/[0-9]/.test(e.key) && !['Backspace', 'Delete', 'ArrowLeft', 'ArrowRight', 'Tab'].includes(e.key)) {
                          e.preventDefault();
                        }
                      }}
                      style={{}}
                    />
                  </div>
                  <div className="popup-input-wrapper" style={{ position: 'relative' }}>
                    <span className="input-icon maximum"></span>
                    <input
                      type="text"
                      className="text-fade-right"
                      placeholder="Maximum"
                      value={maxHeightFeet ? `${maxHeightFeet} ft AGL` : ''}
                      onChange={(e) => { 
                        const value = e.target.value.replace(/[^0-9]/g, '');
                        console.log(`🔍 Max height changing from "${maxHeightFeet}" to "${value}"`);
                        setMaxHeightFeet(value); 
                        setOptimizedParamsWithLogging(null, `Max height changed to: ${value}`); 
                      }}
                      onKeyDown={(e) => {
                        // Allow only numbers, backspace, delete, arrow keys
                        if (!/[0-9]/.test(e.key) && !['Backspace', 'Delete', 'ArrowLeft', 'ArrowRight', 'Tab'].includes(e.key)) {
                          e.preventDefault();
                        }
                      }}
                      style={{}}
                    />
                  </div>
                </div>
              </div>
            </div>

            {/* Individual Battery Segments (legacy-correct UI) */}
            <div className="category-outline">
              <div className="popup-section">
                <h4 className="text-fade-right" style={{ marginLeft: '6%', marginRight: '6%', width: 'auto' }}>
                  {optimizationLoading || downloadingBatteries.size > 0 ? processingMessage : "Individual Battery Segments:"}
                </h4>
                <div id="batteryButtons" className="flight-path-grid">
                {Array.from({ length: batteryCount }).map((_, idx) => (
                  <button
                    key={idx}
                    className={`flight-path-download-btn${downloadingBatteries.has(idx + 1) ? ' loading' : ''}`}
                    onClick={async () => {
                      console.log(`🔍 Battery ${idx + 1} clicked:`, {
                        optimizedParams: optimizedParams ? 'EXISTS' : 'NULL',
                        optimizedParamsRef: optimizedParamsRef.current ? 'EXISTS' : 'NULL',
                        canOptimize,
                        batteryMinutes,
                        numBatteries,
                        selectedCoords: selectedCoordsRef.current ? 'EXISTS' : 'NULL'
                      });
                      
                      // Auto-run optimization on first click if needed
                      if (!optimizedParams) {
                        if (!canOptimize) {
                          // Set specific error messages for missing fields
                          if (!selectedCoordsRef.current) {
                            showSystemNotification('error', 'Please select a location on the map first');
                          } else if (!batteryMinutes || !numBatteries) {
                            showSystemNotification('error', 'Please enter battery duration and quantity first');
                          } else {
                            showSystemNotification('error', 'Please set location and battery params first');
                          }
                          return;
                        }
                        
                        // Run optimization first
                        try {
                          await handleOptimize();
                          // Poll optimizedParams until set (max ~30s) with improved checking
                          let checkCount = 0;
                          const maxChecks = 60; // 30 seconds with 500ms intervals
                          
                          while (checkCount < maxChecks) {
                            await new Promise(r => setTimeout(r, 500));
                            checkCount++;
                            
                            // Use ref to get current optimizedParams (not stale closure)
                            const currentOptimizedParams = optimizedParamsRef.current;
                            if (currentOptimizedParams && Object.keys(currentOptimizedParams).length > 0) {
                              console.log('Optimization completed successfully after', (checkCount * 500), 'ms');
                              break;
                            }
                            
                            // Log progress every 5 seconds
                            if (checkCount % 10 === 0) {
                              console.log(`Still waiting for optimization... ${checkCount * 500}ms elapsed`);
                            }
                          }
                          
                          // Final check after polling using ref
                          const finalOptimizedParams = optimizedParamsRef.current;
                          if (!finalOptimizedParams || Object.keys(finalOptimizedParams).length === 0) {
                            showSystemNotification('error', 'Optimization timed out after 30 seconds. The server may be busy - please try again.');
                            return;
                          }
                        } catch (e: any) {
                          showSystemNotification('error', 'Failed to optimize flight path: ' + (e?.message || 'Unknown error'));
                          return;
                        }
                      }
                      
                      // Add to download queue
                      downloadBatteryCsv(idx + 1);
                    }}
                  >
                    <span className={`download-icon${downloadingBatteries.has(idx + 1) ? ' loading' : ''}`}></span>
                    Battery {idx + 1}
                  </button>
                ))}
                </div>
              </div>
            </div>
          </div>
          )}
        </div>

        {/* SECTION 2: PROPERTY UPLOAD */}
        <div className={`accordion-section${uploadOpen ? ' active' : ''}`} data-section="upload" style={{ marginTop: '16px' }}>
          <div className="accordion-header" onClick={() => setUploadOpen(v => !v)}>
            <div className="accordion-title"><h3>Property Upload</h3></div>
            <span className="accordion-chevron"></span>
          </div>
          {uploadOpen && (
          <div className="accordion-content">
            <div className="popup-section">
              <div className="category-outline">
                <div className="popup-section">
                  <div className="upload-zone" onClick={() => document.getElementById('fileInputHidden')?.click()} onDragOver={(e) => { e.preventDefault(); }} onDrop={(e) => { e.preventDefault(); const f = e.dataTransfer.files?.[0]; if (f) onFileChosen(f); }}>
                    <div className="upload-icon"></div>
                    {!selectedFile && <p>Upload .jpg photos as a .zip file</p>}
                    {selectedFile && (
                      <p id="selectedFileDisplay">Selected file: <span id="selectedFileName">{selectedFile.name}</span> <span className="close-icon" onClick={(e) => { e.stopPropagation(); onFileChosen(null); }}>&times;</span></p>
                    )}
                    <input id="fileInputHidden" type="file" accept=".zip" style={{ display: 'none' }} onChange={(e) => onFileChosen(e.target.files?.[0] || null)} />
                  </div>
                </div>
              </div>

              <div className="category-outline">
                <div className="popup-section">
                  <h4>Property Details</h4>
                  <div className="input-row-popup">
                    <div className="popup-input-wrapper">
                      <span className="input-icon home"></span>
                      <input type="text" className="text-fade-right" placeholder="Property Title" value={propertyTitle} onChange={(e) => setPropertyTitle(e.target.value)} />
                    </div>
                  </div>
                  <div className="popup-input-wrapper listing-description-wrapper">
                    <span className="input-icon paragraph"></span>
                    <textarea id="listingDescription" className="text-fade-right" placeholder="Listing Description" rows={3} value={listingDescription} onChange={(e) => setListingDescription(e.target.value)} />
                  </div>
                </div>
              </div>

              <div className="category-outline">
                <div className="popup-section">
                  <h4>Delivery Method</h4>
                  <div className="input-row-popup">
                    <div className="popup-input-wrapper">
                      <span className="input-icon email"></span>
                      <input type="email" className="text-fade-right" placeholder="Email Address" value={contactEmail} onChange={(e) => setContactEmail(e.target.value)} />
                    </div>
                  </div>
                </div>
              </div>

              <div className="category-outline upload-button-only no-outline">
                <div className="popup-section" style={{ display: 'flex', justifyContent: 'center', position: 'relative' }}>
                  {uploadLoading && uploadStage && (
                    <div className="upload-stage-text" style={{ 
                      position: 'absolute', 
                      top: '-30px', 
                      left: '50%', 
                      transform: 'translateX(-50%)', 
                      fontSize: '0.85rem', 
                      color: 'rgba(255, 255, 255, 0.8)',
                      textAlign: 'center',
                      width: '100%'
                    }}>
                      {uploadStage}
                    </div>
                  )}
                  <div className="upload-progress-text" style={{ 
                    opacity: uploadLoading ? 1 : 0.5 
                  }}>
                    {uploadLoading ? `${Math.round(uploadProgress)}%` : ''}
                  </div>
                  <div className="upload-button-container">
                    <button className={`upload-btn-with-icon${uploadLoading ? ' loading' : ''}`} onClick={startUpload} disabled={uploadLoading}>
                      <span className="upload-btn-icon"></span>
                      {uploadLoading ? 'Uploading…' : mlLoading ? 'Starting ML…' : 'Upload'}
                    </button>
                    <button className="cancel-btn-with-icon" disabled={uploadLoading} onClick={() => onClose()}>
                      <span className="cancel-btn-icon"></span>
                      Cancel
                    </button>
                  </div>
                  <div className="upload-progress-container">
                    <div className="upload-progress-bar" style={{ 
                      width: `${uploadProgress}%`,
                      background: uploadProgress === 100 && mlLoading 
                        ? 'linear-gradient(90deg, #4ade80, #22c55e)' 
                        : 'linear-gradient(90deg, #3b82f6, #1d4ed8)',
                      transition: 'all 0.3s ease'
                    }}></div>
                  </div>
                </div>
              </div>

              {/* Error messages now shown as popups via toast state */}
            </div>
          </div>
          )}
        </div>
        {/* Autosave enabled; no explicit Save button */}
        
        {/* Delete Project Button - Only show when editing existing project */}
        {currentProjectId && (
          <div className="popup-section" style={{ marginTop: 24, borderTop: '1px solid rgba(255,255,255,0.1)', paddingTop: 16 }}>
            <div style={{ display: 'flex', justifyContent: 'center' }}>
              <button 
                className="delete-project-btn"
                onClick={handleDeleteProject}
                style={{
                  display: 'inline-block',
                  textDecoration: 'none',
                  padding: '12px 24px',
                  borderRadius: '999px',
                  transition: 'background 0.3s ease',
                  position: 'relative',
                  cursor: 'pointer',
                  userSelect: 'none',
                  border: '2.5px solid #ff4757',
                  color: '#ff4757',
                  background: 'transparent',
                  fontSize: '1rem',
                  fontWeight: '500',
                }}
                onMouseOver={(e) => {
                  e.currentTarget.style.background = '#ff4757';
                  e.currentTarget.style.color = '#fff';
                }}
                onMouseOut={(e) => {
                  e.currentTarget.style.background = 'transparent';
                  e.currentTarget.style.color = '#ff4757';
                }}
              >
                Delete Project
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Center-screen modal popup system */}
      {modalPopup && (
        <div className="modal-popup-overlay" onClick={() => setModalPopup(null)}>
          <div className="modal-popup-content" onClick={(e) => e.stopPropagation()}>
            <div className={`modal-popup-icon ${modalPopup.type}`}>
              {modalPopup.type === 'success' ? '✓' : '⚠'}
            </div>
            <h3 className="modal-popup-title">
              {modalPopup.type === 'success' ? 'Success' : 'Error'}
            </h3>
            <p className="modal-popup-message">{modalPopup.message}</p>
            <button 
              className="modal-popup-button"
              onClick={() => setModalPopup(null)}
            >
              OK
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
