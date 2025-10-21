"use client";
import React, { ChangeEvent, useCallback, useEffect, useMemo, useRef, useState } from "react";
import Papa from "papaparse";
import JSZip from "jszip";
import { XMLParser } from "fast-xml-parser";
import { buildApiUrl } from '../app/api-config';
import FlightPathScene from './FlightPathScene';

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

// Flight viewer types
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
    gimbalPitchAngle: toOptionalNumber(row["gimbalpitchangle"] ?? row.gimbalpitch),
    altitudeMode: toOptionalNumber(row.altitudemode),
    speedMs: toOptionalNumber(row["speed(m/s)"] ?? row.speedms ?? row.speed),
    poiLatitude: toOptionalNumber(row.poi_latitude ?? row.poilatitude),
    poiLongitude: toOptionalNumber(row.poi_longitude ?? row.poilongitude),
    poiAltitudeFt: toOptionalNumber(row["poi_altitude(ft)"] ?? row.poialtitudeft ?? row.poialtitude),
    poiAltitudeMode: toOptionalNumber(row.poi_altitudemode ?? row.poialtmode),
    photoTimeInterval: toOptionalNumber(row.phototimeinterval ?? row.photo_time),
    photoDistInterval: toOptionalNumber(row.photodistinterval ?? row.photo_dist),
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

  for (let i = 0; i < processedSamples.length; i++) {
    const sample = processedSamples[i];
    
    if (!sample.headingDeg || sample.headingDeg === 0) {
      let calculatedHeading: number | null = null;
      
      if (i < processedSamples.length - 1) {
        const nextSample = processedSamples[i + 1];
        calculatedHeading = calculateBearing(
          sample.latitude,
          sample.longitude,
          nextSample.latitude,
          nextSample.longitude
        );
      } else if (i > 0) {
        const prevSample = processedSamples[i - 1];
        calculatedHeading = calculateBearing(
          prevSample.latitude,
          prevSample.longitude,
          sample.latitude,
          sample.longitude
        );
      }
      
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

  return rows;
}

export default function NewProjectModal({ open, onClose, project, onSaved }: NewProjectModalProps): JSX.Element | null {
  const MAPBOX_TOKEN = 'pk.eyJ1Ijoic3BhY2Vwb3J0IiwiYSI6ImNtY3F6MW5jYjBsY2wyanEwbHVnd3BrN2sifQ.z2mk_LJg-ey2xqxZW1vW6Q';

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

  const [error, setError] = useState<string | null>(null);
  const [toast, setToast] = useState<{ type: 'success' | 'error'; message: string } | null>(null);

  // Flight viewer state
  const [flights, setFlights] = useState<FlightData[]>([]);
  const [selectedLens, setSelectedLens] = useState("mavic3_wide");
  const [isParsing, setIsParsing] = useState(false);

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

  // Map refs
  const mapContainerRef = useRef<HTMLDivElement | null>(null);
  const mapRef = useRef<any>(null);
  const markerRef = useRef<any>(null);
  const selectedCoordsRef = useRef<{ lat: number; lng: number } | null>(null);

  // Fullscreen state
  const [isFullscreen, setIsFullscreen] = useState<boolean>(false);



  // Reset state when opening/closing
  useEffect(() => {
    if (!open) return;
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
      // Don't set address search yet if we have coordinates - restoreSavedLocation will handle it
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

  // No longer need Mapbox initialization - using Cesium 3D viewer instead

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
    
    // Cesium will auto-resize via ResizeObserver in FlightPathScene
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

  // File upload handler for flight paths
  const onFlightFilesSelected = useCallback(async (event: ChangeEvent<HTMLInputElement>) => {
    const fileList = event.target.files;
    if (!fileList || fileList.length === 0) {
      return;
    }

    setIsParsing(true);

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
    }

    if (errors.length > 0 && newFlights.length === 0) {
      showSystemNotification('error', errors.join("; "));
    }
  }, [flights.length]);

  const removeFlight = useCallback((id: string) => {
    setFlights(prev => prev.filter(f => f.id !== id));
  }, []);

  // Handle double-click pin placement from 3D viewer
  const handleDoubleClickPin = useCallback((lat: number, lng: number) => {
    selectedCoordsRef.current = { lat, lng };
    setSelectedCoords({ lat, lng });
    setAddressSearch(`${lat.toFixed(6)}, ${lng.toFixed(6)}`);
    setOptimizedParamsWithLogging(null, 'Map coordinates changed via double-click');
    
    // Hide instructions after first click
    const inst = document.getElementById('map-instructions');
    if (inst) inst.style.display = 'none';
  }, [setOptimizedParamsWithLogging]);

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
      const blob = new Blob([csvText], { type: 'text/csv' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
      
      // AUTO-LOAD to 3D viewer: Parse and add to flights
      try {
        const parsed = Papa.parse<RawFlightRow>(csvText, { header: true, skipEmptyLines: true, dynamicTyping: true });
        const preparedRows = parsed.data
          .map(sanitizeRow)
          .filter((value): value is PreparedRow => value !== null);
        
        if (preparedRows.length > 0) {
          const { samples, poi } = buildSamples(preparedRows);
          const flightData: FlightData = {
            id: `battery-${batteryIndex1}-${Date.now()}`,
            name: filename,
            color: FLIGHT_COLORS[flights.length % FLIGHT_COLORS.length],
            samples,
            poi
          };
          setFlights(prev => [...prev, flightData]);
        }
      } catch (parseErr) {
        console.warn('Failed to auto-load CSV to 3D viewer:', parseErr);
      }
      
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
  }, [API_ENHANCED_BASE, projectTitle, downloadingBatteries, flights.length]);

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
        handleDoubleClickPin(lat, lng);
        return;
      }
    }
    
    // Handle geocoding search
    try {
      const res = await fetch(`https://api.mapbox.com/geocoding/v5/mapbox.places/${encodeURIComponent(query)}.json?access_token=${MAPBOX_TOKEN}&limit=1`);
      const data = await res.json();
      if (data?.features?.length) {
        const [lng, lat] = data.features[0].center;
        handleDoubleClickPin(lat, lng);
      }
    } catch (err) {
      console.warn('Geocoding failed:', err);
    }
  }, [addressSearch, MAPBOX_TOKEN, handleDoubleClickPin]);

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
                            <div className="map-wrapper">
                {/* Cesium 3D Flight Viewer */}
                <div id="map-container" className="map-container" ref={mapContainerRef}>
                  {open && <FlightPathScene 
                    flights={flights}
                    selectedLens={selectedLens}
                    onWaypointHover={() => {}}
                    onDoubleClick={handleDoubleClickPin}
                  />}
                </div>
                
                {/* Map overlays and controls as siblings */}
                <button className={`expand-button${isFullscreen ? ' expanded' : ''}`} id="expand-button" onClick={toggleFullscreen}>
                  <span className="expand-icon"></span>
                </button>
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

            {/* 3D Flight Path Viewer */}
            <div className="category-outline">
              <div className="popup-section">
                <h4>3D Flight Path Viewer</h4>
                <label style={{
                  display: 'block',
                  padding: '16px',
                  background: 'rgba(255, 255, 255, 0.05)',
                  border: '2px dashed rgba(255, 255, 255, 0.2)',
                  borderRadius: '25px',
                  cursor: 'pointer',
                  transition: 'all 0.2s ease',
                  textAlign: 'center'
                }}>
                  <span style={{ color: 'rgba(255, 255, 255, 0.7)', fontSize: '0.95rem' }}>
                    {isParsing ? 'Parsing files...' : 'Upload flight files (CSV or KMZ)'}
                  </span>
                  <input
                    type="file"
                    accept=".csv,text/csv,.kmz,application/vnd.google-earth.kmz"
                    multiple
                    onChange={onFlightFilesSelected}
                    disabled={isParsing}
                    style={{ display: 'none' }}
                  />
                </label>
                {flights.length > 0 && (
                  <div style={{
                    marginTop: '12px',
                    display: 'flex',
                    flexDirection: 'column',
                    gap: '8px'
                  }}>
                    {flights.map(flight => (
                      <div key={flight.id} style={{
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'space-between',
                        padding: '8px 12px',
                        background: 'rgba(255, 255, 255, 0.05)',
                        borderRadius: '20px'
                      }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                          <div style={{
                            width: '12px',
                            height: '12px',
                            borderRadius: '50%',
                            background: flight.color
                          }} />
                          <span style={{ color: 'rgba(255, 255, 255, 0.9)', fontSize: '0.9rem' }}>
                            {flight.name}
                          </span>
                        </div>
                        <button
                          onClick={() => removeFlight(flight.id)}
                          style={{
                            background: 'none',
                            border: 'none',
                            color: 'rgba(255, 255, 255, 0.5)',
                            cursor: 'pointer',
                            fontSize: '1.2rem',
                            lineHeight: 1,
                            padding: '0 4px'
                          }}
                        >
                          ×
                        </button>
                      </div>
                    ))}
                  </div>
                )}
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


