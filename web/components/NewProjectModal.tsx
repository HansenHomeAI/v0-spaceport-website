"use client";
import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { buildApiUrl } from '../app/api-config';
import {
  BoundaryEllipse,
  BoundaryOptimizationResponse,
  BoundaryPlan,
  BoundaryPreviewPath,
  boundaryHandlePositions,
  buildBoundaryGuideCoordinates,
  buildEllipseOutlineCoordinates,
  computeAutoFitCircle,
  latLngToLocalFeet,
  normalizeBoundary,
  normalizeRotationDeg,
  rotatePoint,
} from '../lib/flightBoundary';
import {
  WaypointOverrides,
  applyWaypointOverridesToPreviewPaths,
  buildBoundarySignature,
  clearWaypointOverrides,
  cloneWaypointOverrides,
  createEmptyWaypointOverrides,
  normalizeWaypointOverrides,
  rebuildBatteryCsvWithLiveCoords,
  upsertBatteryWaypointOverride,
} from '../lib/waypointOverrides';

type NewProjectModalProps = {
  open: boolean;
  onClose: () => void;
  project?: any; // when provided, modal acts in edit mode and pre-fills values
  onSaved?: () => void; // callback after successful save/update
};

type OptimizationInfo = {
  adjustments?: string[];
  requested_constraints?: {
    batteryMinutes?: number;
    batteries?: number;
    minExpansionDist?: number | null;
    maxExpansionDist?: number | null;
  };
  final_constraints?: {
    N?: number;
    r0?: number;
    rHold?: number;
    actualMinExpansionDist?: number | null;
    actualMaxExpansionDist?: number | null;
    estimated_time_minutes?: number;
    battery_utilization?: number;
  };
};

type OptimizedParams = {
  [key: string]: any;
  center: string;
  minHeight: number;
  maxHeight: number | null;
  elevationFeet: number | null;
  formToTerrain: boolean;
  spinMode?: boolean;
  expansionMode?: 'default' | 'custom';
  actualMinExpansionDist?: number | null;
  actualMaxExpansionDist?: number | null;
  actualOuterRadius?: number;
  requestedBounceSeed?: number;
  adjustedBounceCount?: boolean;
  adjustedExpansion?: boolean;
  optimizationInfo?: OptimizationInfo | null;
};

type MapboxMarkerRefMap = {
  center: any | null;
  major: any | null;
  minor: any | null;
};

type MapViewportState = {
  centerLat: number;
  centerLng: number;
  zoom: number;
  bearing: number;
  pitch: number;
};

type MapHistorySnapshot = {
  selectedCoords: { lat: number; lng: number } | null;
  addressSearch: string;
  optimizedParams: OptimizedParams | null;
  appliedBoundary: BoundaryEllipse | null;
  appliedBoundaryPlan: BoundaryPlan | null;
  draftBoundary: BoundaryEllipse | null;
  isBoundaryMode: boolean;
  boundaryDirty: boolean;
  waypointOverrides: WaypointOverrides;
  visibleBatteryPaths: BoundaryPreviewPath[];
  viewport: MapViewportState | null;
};

type MapHistoryEntry = {
  action: string;
  prev: MapHistorySnapshot;
  next: MapHistorySnapshot;
};

type WaypointInsertCandidate = {
  batteryIndex: number;
  segmentIndex: number;
  coord: [number, number];
};

const WAYPOINT_INSERT_HOVER_DISTANCE_PX = 16;
const WAYPOINT_INSERT_TOUCH_DISTANCE_PX = 30;
const WAYPOINT_INSERT_TOUCH_CANCEL_DISTANCE_PX = 16;

function normalizeTerrainToggle(value: unknown): boolean {
  return value === true || value === "true";
}

async function readApiErrorMessage(response: Response, fallback: string): Promise<string> {
  try {
    const payload = await response.json();
    if (typeof payload?.error === "string" && payload.error.trim()) {
      return payload.error;
    }
  } catch {}
  return fallback;
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
  const [formToTerrain, setFormToTerrain] = useState<boolean>(false);
  const [minExpansionDist, setMinExpansionDist] = useState<string>("");
  const [maxExpansionDist, setMaxExpansionDist] = useState<string>("");
  const [spinMode, setSpinMode] = useState<boolean>(false);

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
        maxHeight: newParams.maxHeight,
        formToTerrain: newParams.formToTerrain,
      });
    }
    
    setOptimizedParams(newParams);
    optimizedParamsRef.current = newParams;
  }, []);
  const [optimizationLoading, setOptimizationLoading] = useState<boolean>(false);
  const [downloadingBatteries, setDownloadingBatteries] = useState<Set<number>>(new Set());
  const [processingMessage, setProcessingMessage] = useState<string>('');
  const [isBoundaryMode, setIsBoundaryMode] = useState<boolean>(false);
  const [draftBoundary, setDraftBoundary] = useState<BoundaryEllipse | null>(null);
  const [appliedBoundary, setAppliedBoundary] = useState<BoundaryEllipse | null>(null);
  const [appliedBoundaryPlan, setAppliedBoundaryPlan] = useState<BoundaryPlan | null>(null);
  const [isApplyingBoundary, setIsApplyingBoundary] = useState<boolean>(false);
  const [boundaryDirty, setBoundaryDirty] = useState<boolean>(false);
  const [waypointOverrides, setWaypointOverridesState] = useState<WaypointOverrides>(() => createEmptyWaypointOverrides(null));

  const [visibleBatteryPaths, setVisibleBatteryPaths] = useState<Map<number, Array<[number, number]>>>(new Map());
  const [loadingBatteryPaths, setLoadingBatteryPaths] = useState<Set<number>>(new Set());

  const BATTERY_PATH_COLORS = [
    '#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4', '#FFEAA7', '#DDA0DD',
    '#98D8C8', '#F7DC6F', '#BB8FCE', '#85C1E9', '#F0B27A', '#AED6F1',
  ];

  const [error, setError] = useState<string | null>(null);
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

  // Map refs
  const mapContainerRef = useRef<HTMLDivElement | null>(null);
  const mapRef = useRef<any>(null);
  const markerRef = useRef<any>(null);
  const selectedCoordsRef = useRef<{ lat: number; lng: number } | null>(null);
  const [mapReady, setMapReady] = useState<boolean>(false);
  const mapReadyRef = useRef<boolean>(false);
  const resolvingLocationRef = useRef<boolean>(false);
  const boundaryMarkersRef = useRef<MapboxMarkerRefMap>({ center: null, major: null, minor: null });
  const draftBoundaryRef = useRef<BoundaryEllipse | null>(null);
  const appliedBoundaryRef = useRef<BoundaryEllipse | null>(null);
  const appliedBoundaryPlanRef = useRef<BoundaryPlan | null>(null);
  const boundaryDirtyRef = useRef<boolean>(false);
  const isBoundaryModeRef = useRef<boolean>(false);
  const isApplyingBoundaryRef = useRef<boolean>(false);
  const isRestoringHistoryRef = useRef<boolean>(false);
  const isMarkerInteractionActiveRef = useRef<boolean>(false);
  const lastMarkerInteractionEndedAtRef = useRef<number>(0);
  const markerInteractionVersionRef = useRef<number>(0);
  const pendingViewportHistoryRef = useRef<{
    action: string;
    snapshot: MapHistorySnapshot;
    markerInteractionVersion: number;
  } | null>(null);
  const handleCancelBoundaryModeRef = useRef<(() => Promise<void>) | null>(null);
  const triggerSaveRef = useRef<(() => void) | null>(null);
  const boundaryEntryVisiblePathsRef = useRef<Map<number, Array<[number, number]>>>(new Map());
  const clearAllBatteryPathsRef = useRef<() => void>(() => {});
  const replaceBatteryPreviewPathsRef = useRef<(
    previewPaths: BoundaryPreviewPath[],
    options?: { fitBounds?: boolean; useOverrides?: boolean }
  ) => Promise<void>>(async () => {});
  const insertionCandidateRef = useRef<WaypointInsertCandidate | null>(null);
  const insertionMarkerRef = useRef<any | null>(null);
  const insertionTouchTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const insertionTouchStartPointRef = useRef<{ x: number; y: number } | null>(null);
  const ignoreInsertionPointerHoverUntilRef = useRef<number>(0);
  const ignoreInsertionMarkerActivationUntilTouchStartRef = useRef<boolean>(false);
  const handleMapPointerMoveForInsertionRef = useRef<(event: any) => void>(() => {});
  const handleMapTouchStartForInsertionRef = useRef<(event: any) => void>(() => {});
  const handleMapTouchMoveForInsertionRef = useRef<(event: any) => void>(() => {});
  const handleMapTouchEndForInsertionRef = useRef<() => void>(() => {});
  const captureMapHistorySnapshotRef = useRef<() => MapHistorySnapshot>(() => ({
    selectedCoords: null,
    addressSearch: '',
    optimizedParams: null,
    appliedBoundary: null,
    appliedBoundaryPlan: null,
    draftBoundary: null,
    isBoundaryMode: false,
    boundaryDirty: false,
    waypointOverrides: createEmptyWaypointOverrides(null),
    visibleBatteryPaths: [],
    viewport: null,
  }));
  const pushMapHistoryEntryRef = useRef<(action: string, prev: MapHistorySnapshot, next: MapHistorySnapshot) => void>(() => {});
  const clearBoundaryPlanStateRef = useRef<(reason: string) => void>(() => {});
  const flushPendingViewportHistoryRef = useRef<() => void>(() => {});
  const setCenterMarkerOnMapRef = useRef<(lat: number, lng: number) => Promise<void>>(async () => {});
  const setOptimizedParamsWithLoggingRef = useRef<(params: OptimizedParams | null, reason: string) => void>(() => {});
  const restoreSavedLocationRef = useRef<(map: any, coords: { lat: number; lng: number }) => Promise<void>>(async () => {});

  // Waypoint drag refs
  const waypointMarkersRef = useRef<Map<number, any[]>>(new Map());
  const waypointCoordsRef = useRef<Map<number, [number, number][]>>(new Map());
  const waypointOverridesRef = useRef<WaypointOverrides>(createEmptyWaypointOverrides(null));

  // Fullscreen state
  const [isFullscreen, setIsFullscreen] = useState<boolean>(false);

  // Undo/Redo State
  const [history, setHistory] = useState<MapHistoryEntry[]>([]);
  const [historyIndex, setHistoryIndex] = useState<number>(-1);
  const historyIndexRef = useRef<number>(-1);
  useEffect(() => {
    historyIndexRef.current = historyIndex;
  }, [historyIndex]);

  useEffect(() => {
    draftBoundaryRef.current = draftBoundary;
  }, [draftBoundary]);

  useEffect(() => {
    appliedBoundaryRef.current = appliedBoundary;
  }, [appliedBoundary]);

  useEffect(() => {
    appliedBoundaryPlanRef.current = appliedBoundaryPlan;
  }, [appliedBoundaryPlan]);

  useEffect(() => {
    boundaryDirtyRef.current = boundaryDirty;
  }, [boundaryDirty]);

  useEffect(() => {
    isBoundaryModeRef.current = isBoundaryMode;
  }, [isBoundaryMode]);

  useEffect(() => {
    isApplyingBoundaryRef.current = isApplyingBoundary;
  }, [isApplyingBoundary]);

  useEffect(() => {
    mapReadyRef.current = mapReady;
  }, [mapReady]);

  const buildTouchInsertionEventFromDom = useCallback((target: HTMLElement | null, touch: Touch | null) => {
    if (!target || !touch) {
      return null;
    }

    const rect = target.getBoundingClientRect();
    return {
      point: {
        x: touch.clientX - rect.left,
        y: touch.clientY - rect.top,
      },
    };
  }, []);

  const cloneVisiblePaths = useCallback((source: Map<number, Array<[number, number]>>) => {
    const clone = new Map<number, Array<[number, number]>>();
    source.forEach((coords, batteryIndex) => {
      clone.set(batteryIndex, coords.map(([lng, lat]) => [lng, lat]));
    });
    return clone;
  }, []);

  const resolveMapbox = useCallback(async () => {
    const mapboxModule = await import('mapbox-gl');
    const mapboxgl: any = (mapboxModule as any)?.default ?? mapboxModule;
    if (!mapboxgl?.Map || !mapboxgl?.Marker) {
      throw new Error('Mapbox GL module did not expose Map/Marker');
    }
    return mapboxgl;
  }, []);

  const commitWaypointOverrides = useCallback((next: WaypointOverrides) => {
    waypointOverridesRef.current = next;
    setWaypointOverridesState(next);
  }, []);

  const waitForMapReady = useCallback(async (timeoutMs = 5000): Promise<boolean> => {
    if (mapReadyRef.current) {
      return true;
    }

    const deadline = Date.now() + timeoutMs;
    while (Date.now() < deadline) {
      await new Promise((resolve) => setTimeout(resolve, 100));
      if (mapReadyRef.current) {
        return true;
      }
    }

    return mapReadyRef.current;
  }, []);

  const waitForSelectedCoords = useCallback(async (timeoutMs = 5000): Promise<{ lat: number; lng: number } | null> => {
    if (selectedCoordsRef.current) {
      return selectedCoordsRef.current;
    }

    const deadline = Date.now() + timeoutMs;
    while (Date.now() < deadline) {
      await new Promise((resolve) => setTimeout(resolve, 100));
      if (selectedCoordsRef.current) {
        return selectedCoordsRef.current;
      }
      if (!resolvingLocationRef.current) {
        break;
      }
    }

    return selectedCoordsRef.current;
  }, []);

  const createCenterPinElement = useCallback(() => {
    const pinElement = document.createElement('div');
    pinElement.className = 'custom-teardrop-pin';
    pinElement.innerHTML = `
      <svg width="32" height="50" viewBox="0 0 32 50" fill="none" xmlns="http://www.w3.org/2000/svg" style="filter: drop-shadow(0 2px 8px rgba(0, 0, 0, 0.3)) drop-shadow(0 1px 4px rgba(0, 0, 0, 0.2)) drop-shadow(0 0 2px rgba(0, 0, 0, 0.1)); transform: translateY(4px);">
        <path fill-rule="evenodd" clip-rule="evenodd" d="M16.1896 0.32019C7.73592 0.32019 0.882812 7.17329 0.882812 15.627C0.882812 17.3862 1.17959 19.0761 1.72582 20.6494L1.7359 20.6784C1.98336 21.3865 2.2814 22.0709 2.62567 22.7272L13.3424 47.4046L13.3581 47.3897C13.8126 48.5109 14.9121 49.3016 16.1964 49.3016C17.5387 49.3016 18.6792 48.4377 19.0923 47.2355L29.8623 22.516C30.9077 20.4454 31.4965 18.105 31.4965 15.627C31.4965 7.17329 24.6434 0.32019 16.1896 0.32019ZM16.18 9.066C12.557 9.066 9.61992 12.003 9.61992 15.6261C9.61992 19.2491 12.557 22.1861 16.18 22.1861C19.803 22.1861 22.7401 19.2491 22.7401 15.6261C22.7401 12.003 19.803 9.066 16.18 9.066Z" fill="white"/>
      </svg>
    `;
    return pinElement;
  }, []);

  const waitForMapCanvasHost = useCallback(async (map: any, timeoutMs = 2000): Promise<boolean> => {
    const deadline = Date.now() + timeoutMs;
    while (Date.now() < deadline) {
      if (map?.getCanvasContainer?.()) {
        return true;
      }
      await new Promise((resolve) => setTimeout(resolve, 50));
    }

    return !!map?.getCanvasContainer?.();
  }, []);

  const setCenterMarkerOnMap = useCallback(async (lat: number, lng: number) => {
    const initialMap = mapRef.current;
    if (!initialMap) return;

    const mapboxgl = await resolveMapbox();
    const activeMap = mapRef.current;
    if (!activeMap || !(await waitForMapCanvasHost(activeMap))) {
      return;
    }

    if (markerRef.current) {
      markerRef.current.setLngLat([lng, lat]);
      return;
    }

    const attachMarker = (mapInstance: any) => new mapboxgl.Marker({ element: createCenterPinElement(), anchor: 'bottom' })
      .setLngLat([lng, lat])
      .addTo(mapInstance);

    try {
      markerRef.current = attachMarker(activeMap);
    } catch (error) {
      console.warn('Center marker attachment failed; retrying with current map instance', error);
      markerRef.current = null;
      const retryMap = mapRef.current;
      if (!retryMap || !(await waitForMapCanvasHost(retryMap, 1000))) {
        return;
      }
      try {
        markerRef.current = attachMarker(retryMap);
      } catch (retryError) {
        console.warn('Center marker attachment failed after retry', retryError);
      }
    }
  }, [createCenterPinElement, resolveMapbox, waitForMapCanvasHost]);

  const clearCenterMarkerFromMap = useCallback(() => {
    markerRef.current?.remove?.();
    markerRef.current = null;
  }, []);

  const clearBoundaryPlanState = useCallback((reason: string) => {
    if (appliedBoundaryPlanRef.current) {
      console.log(`🔍 Clearing boundary plan: ${reason}`);
    }
    setAppliedBoundaryPlan(null);
    appliedBoundaryPlanRef.current = null;
    if (!isBoundaryModeRef.current) {
      setDraftBoundary(null);
      setBoundaryDirty(false);
    }
  }, []);

  const captureMapViewportState = useCallback((): MapViewportState | null => {
    const map = mapRef.current;
    if (!map) return null;

    const center = map.getCenter();
    return {
      centerLat: Number(center.lat.toFixed(6)),
      centerLng: Number(center.lng.toFixed(6)),
      zoom: Number(map.getZoom().toFixed(4)),
      bearing: Number(map.getBearing().toFixed(4)),
      pitch: Number(map.getPitch().toFixed(4)),
    };
  }, []);

  const clonePathCoords = useCallback((coords: Array<[number, number]>) => {
    return coords.map(([lng, lat]) => [lng, lat] as [number, number]);
  }, []);

  const cloneBoundaryPreviewPaths = useCallback((paths: BoundaryPreviewPath[]) => {
    return paths.map((path) => ({
      batteryIndex: path.batteryIndex,
      coordinates: clonePathCoords(path.coordinates),
    }));
  }, [clonePathCoords]);

  const clearPendingInsertionTouchTimer = useCallback(() => {
    if (insertionTouchTimerRef.current) {
      clearTimeout(insertionTouchTimerRef.current);
      insertionTouchTimerRef.current = null;
    }
  }, []);

  const logTouchInsertionDebug = useCallback((event: string, detail?: Record<string, unknown>) => {
    if (typeof window === 'undefined' || !(window as any).__BOUNDARY_TOUCH_DEBUG) {
      return;
    }
    console.log('[boundary-touch-debug]', event, detail ?? {});
  }, []);

  const clearInsertionCandidateMarker = useCallback(() => {
    logTouchInsertionDebug('clear-marker', {
      hadTimer: Boolean(insertionTouchTimerRef.current),
      hadTouchStart: Boolean(insertionTouchStartPointRef.current),
      hadMarker: Boolean(insertionMarkerRef.current),
    });
    clearPendingInsertionTouchTimer();
    insertionTouchStartPointRef.current = null;
    insertionCandidateRef.current = null;
    insertionMarkerRef.current?.remove?.();
    insertionMarkerRef.current = null;
  }, [clearPendingInsertionTouchTimer, logTouchInsertionDebug]);

  const clearInsertionCandidateMarkerOnMapMove = useCallback(() => {
    const preservePendingTouchHold = Boolean(insertionTouchTimerRef.current && insertionTouchStartPointRef.current);
    logTouchInsertionDebug('clear-on-map-move', {
      preservePendingTouchHold,
      hadTimer: Boolean(insertionTouchTimerRef.current),
      hadTouchStart: Boolean(insertionTouchStartPointRef.current),
      hadMarker: Boolean(insertionMarkerRef.current),
    });
    if (!preservePendingTouchHold) {
      clearPendingInsertionTouchTimer();
      insertionTouchStartPointRef.current = null;
    }
    insertionCandidateRef.current = null;
    insertionMarkerRef.current?.remove?.();
    insertionMarkerRef.current = null;
  }, [clearPendingInsertionTouchTimer, logTouchInsertionDebug]);

  const updateWaypointOverridesForBattery = useCallback((batteryIndex: number, coords: Array<[number, number]>) => {
    const boundarySignature = buildBoundarySignature(appliedBoundaryRef.current);
    const next = upsertBatteryWaypointOverride(
      waypointOverridesRef.current,
      batteryIndex,
      coords,
      boundarySignature
    );
    commitWaypointOverrides(next);
  }, [commitWaypointOverrides]);

  const resetWaypointOverrides = useCallback((boundarySignature: string | null = null) => {
    const next = clearWaypointOverrides(boundarySignature);
    commitWaypointOverrides(next);
  }, [commitWaypointOverrides]);

  const cloneWaypointOverridesState = useCallback((overrides: WaypointOverrides) => {
    return cloneWaypointOverrides(overrides);
  }, []);

  const resolvePreviewPathsWithOverrides = useCallback((paths: BoundaryPreviewPath[]) => {
    const currentSignature = buildBoundarySignature(appliedBoundaryRef.current);
    return applyWaypointOverridesToPreviewPaths(paths, waypointOverridesRef.current, currentSignature);
  }, []);

  const captureVisibleBatteryPreviewPaths = useCallback((): BoundaryPreviewPath[] => {
    return Array.from(visibleBatteryPaths.entries())
      .sort(([left], [right]) => left - right)
      .map(([batteryIndex, coordinates]) => ({
        batteryIndex,
        coordinates: clonePathCoords(waypointCoordsRef.current.get(batteryIndex) ?? coordinates),
      }));
  }, [clonePathCoords, visibleBatteryPaths]);

  const cloneOptimizedParams = useCallback((params: OptimizedParams | null): OptimizedParams | null => {
    return params ? JSON.parse(JSON.stringify(params)) : null;
  }, []);

  const cloneBoundaryPlan = useCallback((plan: BoundaryPlan | null): BoundaryPlan | null => {
    return plan ? JSON.parse(JSON.stringify(plan)) : null;
  }, []);

  const captureMapHistorySnapshot = useCallback((): MapHistorySnapshot => {
    const selected = selectedCoordsRef.current ?? selectedCoords;

    return {
      selectedCoords: selected ? { ...selected } : null,
      addressSearch,
      optimizedParams: cloneOptimizedParams(optimizedParamsRef.current),
      appliedBoundary: appliedBoundaryRef.current ? normalizeBoundary(appliedBoundaryRef.current) : null,
      appliedBoundaryPlan: cloneBoundaryPlan(appliedBoundaryPlanRef.current),
      draftBoundary: draftBoundaryRef.current ? normalizeBoundary(draftBoundaryRef.current) : null,
      isBoundaryMode: isBoundaryModeRef.current,
      boundaryDirty: boundaryDirtyRef.current,
      waypointOverrides: cloneWaypointOverridesState(waypointOverridesRef.current),
      visibleBatteryPaths: captureVisibleBatteryPreviewPaths(),
      viewport: captureMapViewportState(),
    };
  }, [
    addressSearch,
    captureMapViewportState,
    captureVisibleBatteryPreviewPaths,
    cloneBoundaryPlan,
    cloneOptimizedParams,
    cloneWaypointOverridesState,
    selectedCoords,
  ]);

  const serializeMapHistorySnapshot = useCallback((snapshot: MapHistorySnapshot) => {
    return JSON.stringify(snapshot);
  }, []);

  const pushMapHistoryEntry = useCallback((action: string, prev: MapHistorySnapshot, next: MapHistorySnapshot) => {
    if (isRestoringHistoryRef.current) {
      return;
    }

    if (serializeMapHistorySnapshot(prev) === serializeMapHistorySnapshot(next)) {
      return;
    }

    const nextEntry: MapHistoryEntry = { action, prev, next };
    const nextIndex = historyIndexRef.current + 1;
    historyIndexRef.current = nextIndex >= 100 ? 99 : nextIndex;
    setHistory((currentHistory) => {
      const truncated = currentHistory.slice(0, nextIndex);
      const appended = [...truncated, nextEntry];
      if (appended.length > 100) {
        return appended.slice(appended.length - 100);
      }
      return appended;
    });
    setHistoryIndex((currentIndex) => {
      const computedIndex = currentIndex + 1;
      return computedIndex >= 100 ? 99 : computedIndex;
    });
  }, [serializeMapHistorySnapshot]);

  const flushPendingViewportHistory = useCallback(() => {
    const pending = pendingViewportHistoryRef.current;
    if (!pending || isRestoringHistoryRef.current) {
      pendingViewportHistoryRef.current = null;
      return;
    }

    if (pending.markerInteractionVersion !== markerInteractionVersionRef.current) {
      pendingViewportHistoryRef.current = null;
      return;
    }

    pendingViewportHistoryRef.current = null;
    pushMapHistoryEntry(pending.action, pending.snapshot, captureMapHistorySnapshot());
  }, [captureMapHistorySnapshot, pushMapHistoryEntry]);

  useEffect(() => {
    captureMapHistorySnapshotRef.current = captureMapHistorySnapshot;
  }, [captureMapHistorySnapshot]);

  useEffect(() => {
    pushMapHistoryEntryRef.current = pushMapHistoryEntry;
  }, [pushMapHistoryEntry]);

  useEffect(() => {
    flushPendingViewportHistoryRef.current = flushPendingViewportHistory;
  }, [flushPendingViewportHistory]);

  useEffect(() => {
    clearBoundaryPlanStateRef.current = clearBoundaryPlanState;
  }, [clearBoundaryPlanState]);

  useEffect(() => {
    setCenterMarkerOnMapRef.current = setCenterMarkerOnMap;
  }, [setCenterMarkerOnMap]);

  useEffect(() => {
    setOptimizedParamsWithLoggingRef.current = setOptimizedParamsWithLogging;
  }, [setOptimizedParamsWithLogging]);

  const bindMarkerInteractionGuards = useCallback((element: HTMLElement) => {
    let dragPanWasEnabled = false;

    const releaseMapPan = () => {
      isMarkerInteractionActiveRef.current = false;
      lastMarkerInteractionEndedAtRef.current = Date.now();
      markerInteractionVersionRef.current += 1;
      if (dragPanWasEnabled && mapRef.current?.dragPan) {
        mapRef.current.dragPan.enable();
      }
      dragPanWasEnabled = false;
      window.removeEventListener('pointerup', releaseMapPan, true);
      window.removeEventListener('pointercancel', releaseMapPan, true);
    };

    const handlePointerDown = (event: PointerEvent) => {
      // Do NOT preventDefault/stopPropagation - Mapbox Marker needs the event to initiate drag.
      // We only disable map dragPan to prevent map panning during marker drag.
      markerInteractionVersionRef.current += 1;
      isMarkerInteractionActiveRef.current = true;
      const map = mapRef.current;
      if (map?.dragPan?.isEnabled?.()) {
        dragPanWasEnabled = true;
        map.dragPan.disable();
      }
      window.addEventListener('pointerup', releaseMapPan, true);
      window.addEventListener('pointercancel', releaseMapPan, true);
    };

    const stopClickPropagation = (event: MouseEvent) => {
      event.stopPropagation();
    };

    element.style.touchAction = 'none';
    element.addEventListener('pointerdown', handlePointerDown, true);
    element.addEventListener('click', stopClickPropagation);

    return releaseMapPan;
  }, []);

  const restoreMapHistorySnapshot = useCallback(async (snapshot: MapHistorySnapshot, reason: string) => {
    isRestoringHistoryRef.current = true;
    pendingViewportHistoryRef.current = null;

    try {
      const selected = snapshot.selectedCoords ? { ...snapshot.selectedCoords } : null;
      selectedCoordsRef.current = selected;
      setSelectedCoords(selected);
      setAddressSearch(snapshot.addressSearch);

      setOptimizedParamsWithLogging(cloneOptimizedParams(snapshot.optimizedParams), reason);

      const restoredAppliedBoundary = snapshot.appliedBoundary ? normalizeBoundary(snapshot.appliedBoundary) : null;
      const restoredAppliedPlan = cloneBoundaryPlan(snapshot.appliedBoundaryPlan);
      const restoredDraftBoundary = snapshot.draftBoundary ? normalizeBoundary(snapshot.draftBoundary) : null;
      const restoredWaypointOverrides = cloneWaypointOverridesState(snapshot.waypointOverrides ?? createEmptyWaypointOverrides(null));

      appliedBoundaryRef.current = restoredAppliedBoundary;
      appliedBoundaryPlanRef.current = restoredAppliedPlan;
      draftBoundaryRef.current = restoredDraftBoundary;

      setAppliedBoundary(restoredAppliedBoundary);
      setAppliedBoundaryPlan(restoredAppliedPlan);
      setDraftBoundary(restoredDraftBoundary);
      setIsBoundaryMode(snapshot.isBoundaryMode);
      setBoundaryDirty(snapshot.boundaryDirty);
      commitWaypointOverrides(restoredWaypointOverrides);

      const restoredPaths = cloneBoundaryPreviewPaths(snapshot.visibleBatteryPaths);
      boundaryEntryVisiblePathsRef.current = new Map(
        restoredPaths.map((path) => [path.batteryIndex, clonePathCoords(path.coordinates)])
      );

      await new Promise((resolve) => setTimeout(resolve, 0));

      if (selected) {
        await setCenterMarkerOnMap(selected.lat, selected.lng);
      } else {
        clearCenterMarkerFromMap();
      }

      if (restoredPaths.length > 0) {
        await replaceBatteryPreviewPathsRef.current(restoredPaths, { fitBounds: false, useOverrides: false });
      } else {
        clearAllBatteryPathsRef.current();
      }

      if (snapshot.viewport && mapRef.current) {
        mapRef.current.jumpTo({
          center: [snapshot.viewport.centerLng, snapshot.viewport.centerLat],
          zoom: snapshot.viewport.zoom,
          bearing: snapshot.viewport.bearing,
          pitch: snapshot.viewport.pitch,
        });
      }
    } finally {
      setTimeout(() => {
        isRestoringHistoryRef.current = false;
      }, 0);
    }
  }, [
    clearCenterMarkerFromMap,
    commitWaypointOverrides,
    cloneBoundaryPlan,
    cloneBoundaryPreviewPaths,
    cloneOptimizedParams,
    cloneWaypointOverridesState,
    clonePathCoords,
    setCenterMarkerOnMap,
    setOptimizedParamsWithLogging,
  ]);

  // UNDO HANDLER
  const handleUndo = useCallback(async () => {
    if (historyIndex < 0 || !history[historyIndex]) return;
    await restoreMapHistorySnapshot(history[historyIndex].prev, `Undo ${history[historyIndex].action}`);
    historyIndexRef.current = historyIndex - 1;
    setHistoryIndex((prev) => prev - 1);
  }, [history, historyIndex, restoreMapHistorySnapshot]);

  // REDO HANDLER
  const handleRedo = useCallback(async () => {
    if (historyIndex >= history.length - 1 || !history[historyIndex + 1]) return;
    await restoreMapHistorySnapshot(history[historyIndex + 1].next, `Redo ${history[historyIndex + 1].action}`);
    historyIndexRef.current = historyIndex + 1;
    setHistoryIndex((prev) => prev + 1);
  }, [history, historyIndex, restoreMapHistorySnapshot]);

  const buildOptimizationRequestBody = useCallback((
    coords: { lat: number; lng: number },
    minutes: number,
    batteries: number,
    requestedMinExpansion?: string | null,
    requestedMaxExpansion?: string | null,
    terrainEnabled?: boolean,
  ): Record<string, any> => {
    const body: Record<string, any> = {
      batteryMinutes: minutes,
      batteries,
      center: `${coords.lat}, ${coords.lng}`,
      formToTerrain: terrainEnabled ?? formToTerrain,
    };

    if (requestedMinExpansion && requestedMinExpansion.trim()) {
      body.minExpansionDist = parseFloat(requestedMinExpansion);
    }
    if (requestedMaxExpansion && requestedMaxExpansion.trim()) {
      body.maxExpansionDist = parseFloat(requestedMaxExpansion);
    }

    return body;
  }, [formToTerrain]);

  const buildResolvedFlightRequestBody = useCallback((params: OptimizedParams): Record<string, any> => {
    const body: Record<string, any> = { ...params };
    const resolvedMin = params.actualMinExpansionDist ?? null;
    const resolvedMax = params.actualMaxExpansionDist ?? null;

    if (resolvedMin !== null) {
      body.minExpansionDist = resolvedMin;
    } else {
      delete body.minExpansionDist;
    }

    if (resolvedMax !== null) {
      body.maxExpansionDist = resolvedMax;
    } else {
      delete body.maxExpansionDist;
    }

    delete body.optimizationInfo;
    return body;
  }, []);

  const runOptimizationRequest = useCallback(async ({
    coords,
    minutes,
    batteries,
    minHeightValue,
    maxHeightValue,
    requestedMinExpansion,
    requestedMaxExpansion,
    terrainEnabled,
  }: {
    coords: { lat: number; lng: number };
    minutes: number;
    batteries: number;
    minHeightValue?: string | null;
    maxHeightValue?: string | null;
    requestedMinExpansion?: string | null;
    requestedMaxExpansion?: string | null;
    terrainEnabled?: boolean;
  }): Promise<OptimizedParams> => {
    const effectiveFormToTerrain = terrainEnabled ?? formToTerrain;
    const optRes = await fetch(`${API_ENHANCED_BASE}/api/optimize-spiral`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(
        buildOptimizationRequestBody(
          coords,
          minutes,
          batteries,
          requestedMinExpansion,
          requestedMaxExpansion,
          effectiveFormToTerrain,
        )
      ),
    });
    if (!optRes.ok) {
      const errorText = await optRes.text().catch(() => '');
      let parsedError: string | null = null;
      try {
        const parsed = JSON.parse(errorText);
        parsedError = parsed?.error || null;
      } catch {
        parsedError = null;
      }
      throw new Error(parsedError || errorText || 'Flight path optimization failed');
    }
    const optData = await optRes.json();

    let elevationFeet: number | null = null;
    if (effectiveFormToTerrain) {
      const elevRes = await fetch(`${API_ENHANCED_BASE}/api/elevation`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ center: `${coords.lat}, ${coords.lng}` }),
      });
      if (!elevRes.ok) {
        throw new Error(await readApiErrorMessage(
          elevRes,
          'Terrain following is unavailable right now. Please try again later.'
        ));
      }
      const elevData = await elevRes.json();
      elevationFeet = elevData.elevation_feet ?? null;
    }

    const minH = parseFloat(minHeightValue || '120') || 120;
    const maxH = maxHeightValue ? parseFloat(maxHeightValue) : null;

    return {
      ...optData.optimized_params,
      center: `${coords.lat}, ${coords.lng}`,
      minHeight: minH,
      maxHeight: maxH,
      elevationFeet,
      formToTerrain: effectiveFormToTerrain,
      optimizationInfo: optData.optimization_info ?? null,
    };
  }, [API_ENHANCED_BASE, buildOptimizationRequestBody, formToTerrain]);

  const formatExpansionSummary = useCallback((minValue?: string | number | null, maxValue?: string | number | null): string => {
    const normalize = (value?: string | number | null): number | null => {
      if (value === null || value === undefined || value === '') return null;
      const parsed = typeof value === 'number' ? value : parseFloat(String(value));
      return Number.isFinite(parsed) ? parsed : null;
    };

    const minNum = normalize(minValue);
    const maxNum = normalize(maxValue);
    if (minNum === null && maxNum === null) return 'Default exponential';

    const resolvedMin = minNum ?? maxNum;
    const resolvedMax = maxNum ?? minNum;
    if (resolvedMin === null || resolvedMax === null) return 'Default exponential';
    if (Math.abs(resolvedMin - resolvedMax) < 0.01) return `${resolvedMin.toFixed(0)} ft / bounce`;
    return `${resolvedMin.toFixed(0)} ft -> ${resolvedMax.toFixed(0)} ft`;
  }, []);



  // Reset state when opening/closing
  useEffect(() => {
    if (!open) return;
    setUploadProgress(0);
    setUploadLoading(false);
    setMlLoading(false);
    setUploadStage('');
    setOptimizedParamsWithLogging(null, 'Modal opened/reset');
    setDownloadingBatteries(new Set());
    setVisibleBatteryPaths(new Map());
    setLoadingBatteryPaths(new Set());
    waypointMarkersRef.current.forEach(markers => markers.forEach(m => m.remove()));
    waypointMarkersRef.current.clear();
    waypointCoordsRef.current.clear();
    setHistory([]);
    setHistoryIndex(-1);
    historyIndexRef.current = -1;
    isMarkerInteractionActiveRef.current = false;
    lastMarkerInteractionEndedAtRef.current = 0;
    pendingViewportHistoryRef.current = null;
    isRestoringHistoryRef.current = false;
    setSetupOpen(true);
    setUploadOpen(false);
    setToast(null);
    setIsFullscreen(false);
    setIsBoundaryMode(false);
    setDraftBoundary(null);
    setAppliedBoundary(null);
    setAppliedBoundaryPlan(null);
    setIsApplyingBoundary(false);
    setBoundaryDirty(false);
    resetWaypointOverrides(null);
    clearInsertionCandidateMarker();
    boundaryEntryVisiblePathsRef.current = new Map();
    
    // If editing, hydrate fields from project
    if (project) {
      console.log(`🔍 Loading project data:`, {
        title: project.title,
        params: project.params,
        savedBatteryMinutes: project.params?.batteryMinutes,
        savedBatteries: project.params?.batteries,
        savedMinHeight: project.params?.minHeight,
        savedMaxHeight: project.params?.maxHeight,
        savedFormToTerrain: project.params?.formToTerrain,
        hasCoordinates: !!(project.params?.latitude && project.params?.longitude)
      });
      
      setProjectTitle(project.title || 'Untitled');
      const params = project.params || {};
      const savedSpinMode = params.spinMode === true || params.spinMode === 'true' || params.spinMode === 1 || params.spinMode === '1';
      // Don't set address search yet if we have coordinates - restoreSavedLocation will handle it
      if (!(params.latitude && params.longitude)) {
        setAddressSearch(params.address || '');
      }
      setBatteryMinutes(params.batteryMinutes || '');
      setNumBatteries(params.batteries || '');
      setMinHeightFeet(params.minHeight || '');
      setFormToTerrain(normalizeTerrainToggle(params.formToTerrain));
      setMinExpansionDist(params.minExpansionDist || '');
      setMaxExpansionDist(params.maxExpansionDist || '');
      setMaxHeightFeet(params.maxHeight || '');
      if (params.boundary?.enabled) {
        setAppliedBoundary(normalizeBoundary(params.boundary as BoundaryEllipse));
      }
      if (params.boundaryPlan?.batteries?.length) {
        setAppliedBoundaryPlan(params.boundaryPlan as BoundaryPlan);
      }
      const normalizedWaypointOverrides = normalizeWaypointOverrides(params.waypointOverrides);
      commitWaypointOverrides(normalizedWaypointOverrides);
      setSpinMode(savedSpinMode);
      setSpinMode(savedSpinMode);
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
              const terrainEnabled = normalizeTerrainToggle(params.formToTerrain);
              const optimizedParams = await runOptimizationRequest({
                coords,
                minutes,
                batteries,
                minHeightValue: params.minHeight || '120',
                maxHeightValue: params.maxHeight || '',
                requestedMinExpansion: params.minExpansionDist || '',
                requestedMaxExpansion: params.maxExpansionDist || '',
                terrainEnabled,
              });
              optimizedParams.spinMode = savedSpinMode;
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
      setFormToTerrain(false);
      setMinExpansionDist('');
      setMaxExpansionDist('');
      setSpinMode(false);
      setPropertyTitle('');
      setListingDescription('');
      setContactEmail('');
      setSelectedFile(null);
      setStatus('draft');
      setCurrentProjectId(null);
      resetWaypointOverrides(null);
      selectedCoordsRef.current = null;
      setSelectedCoords(null);
      boundaryEntryVisiblePathsRef.current = new Map();
    }

    // Cleanup timeout on unmount
    return () => {
      if (saveTimeoutRef.current) {
        clearTimeout(saveTimeoutRef.current);
      }
    };
  }, [clearInsertionCandidateMarker, commitWaypointOverrides, open, project, resetWaypointOverrides, runOptimizationRequest]);

  // Initialize Mapbox on open
  useEffect(() => {
    let isCancelled = false;
    let touchTarget: HTMLElement | null = null;
    let handleTouchStart: ((event: TouchEvent) => void) | null = null;
    let handleTouchMove: ((event: TouchEvent) => void) | null = null;
    let handleTouchEnd: (() => void) | null = null;

    async function initMap() {
      if (!open) return;
      if (!mapContainerRef.current) return;
      try {
        const mapboxgl = await resolveMapbox();
        mapboxgl.accessToken = MAPBOX_TOKEN;
        if (isCancelled) return;
        const map = new mapboxgl.Map({
          container: mapContainerRef.current,
          style: 'mapbox://styles/mapbox/satellite-v9',
          center: [-98.5795, 39.8283],
          zoom: 4,
          attributionControl: false,
        });
        
        map.on('click', (e: any) => {
          const clickedElement = e?.originalEvent?.target as HTMLElement | null;
          const clickedMarkerElement = !!clickedElement?.closest?.('.waypoint-marker, .boundary-handle-marker, .mapboxgl-marker');
          const clickedOverlayControl = !!clickedElement?.closest?.(
            '.map-toolbar, .map-toolbar-button, .map-battery-panel, .map-battery-button, .expand-button, .boundary-editor-bar, .boundary-editor-button, .address-search-overlay, .address-search-wrapper, .waypoint-insert-marker'
          );
          const recentMarkerInteraction = Date.now() - lastMarkerInteractionEndedAtRef.current < 300;
          if (
            isBoundaryModeRef.current
            || isApplyingBoundaryRef.current
            || isRestoringHistoryRef.current
            || isMarkerInteractionActiveRef.current
            || recentMarkerInteraction
            || clickedMarkerElement
            || clickedOverlayControl
          ) {
            return;
          }

          flushPendingViewportHistoryRef.current();
          const previousSnapshot = captureMapHistorySnapshotRef.current();
          const { lng, lat } = e.lngLat;
          selectedCoordsRef.current = { lat, lng };
          setSelectedCoords({ lat, lng });
          void setCenterMarkerOnMapRef.current(lat, lng);
          // Fill address input with coordinates formatted
          setAddressSearch(`${lat.toFixed(6)}, ${lng.toFixed(6)}`);
          // Invalidate previous optimization
          setOptimizedParamsWithLoggingRef.current(null, 'Map coordinates changed');
          clearBoundaryPlanStateRef.current('Map coordinates changed');
          resetWaypointOverrides(null);
          clearInsertionCandidateMarker();
          // Hide instructions after first click
          const inst = document.getElementById('map-instructions');
          if (inst) inst.style.display = 'none';

          setTimeout(() => {
            pushMapHistoryEntryRef.current('map center change', previousSnapshot, captureMapHistorySnapshotRef.current());
          }, 0);
        });

        const beginViewportHistory = (action: string, event: any) => {
          if (!event?.originalEvent || isRestoringHistoryRef.current || isMarkerInteractionActiveRef.current) {
            return;
          }
          pendingViewportHistoryRef.current = {
            action,
            snapshot: captureMapHistorySnapshotRef.current(),
            markerInteractionVersion: markerInteractionVersionRef.current,
          };
        };

        const commitViewportHistory = () => {
          const pending = pendingViewportHistoryRef.current;
          if (!pending || isRestoringHistoryRef.current) {
            pendingViewportHistoryRef.current = null;
            return;
          }
          if (pending.markerInteractionVersion !== markerInteractionVersionRef.current) {
            pendingViewportHistoryRef.current = null;
            return;
          }
          pendingViewportHistoryRef.current = null;
          pushMapHistoryEntryRef.current(pending.action, pending.snapshot, captureMapHistorySnapshotRef.current());
        };

        const finalizeViewportHistoryOnPointerRelease = (event: any) => {
          if (!event?.originalEvent || isRestoringHistoryRef.current || isMarkerInteractionActiveRef.current) {
            return;
          }
          if (!pendingViewportHistoryRef.current) {
            return;
          }
          map.stop();
          commitViewportHistory();
        };

        map.on('dragstart', (event: any) => beginViewportHistory('map pan', event));
        map.on('dragend', commitViewportHistory);
        map.on('mouseup', finalizeViewportHistoryOnPointerRelease);
        map.on('touchend', finalizeViewportHistoryOnPointerRelease);
        map.on('zoomstart', (event: any) => beginViewportHistory('map zoom', event));
        map.on('zoomend', commitViewportHistory);
        map.on('rotatestart', (event: any) => beginViewportHistory('map rotate', event));
        map.on('rotateend', commitViewportHistory);
        map.on('pitchstart', (event: any) => beginViewportHistory('map pitch', event));
        map.on('pitchend', commitViewportHistory);
        map.on('mousemove', (event: any) => handleMapPointerMoveForInsertionRef.current(event));
        map.on('dragstart', clearInsertionCandidateMarkerOnMapMove);
        map.on('movestart', clearInsertionCandidateMarkerOnMapMove);
        map.on('zoomstart', clearInsertionCandidateMarkerOnMapMove);
        touchTarget = map.getCanvasContainer();
        handleTouchStart = (event: TouchEvent) => {
          const mappedEvent = buildTouchInsertionEventFromDom(touchTarget, event.touches[0] ?? null);
          if (mappedEvent) {
            handleMapTouchStartForInsertionRef.current(mappedEvent);
          }
        };
        handleTouchMove = (event: TouchEvent) => {
          const mappedEvent = buildTouchInsertionEventFromDom(touchTarget, event.touches[0] ?? null);
          if (mappedEvent) {
            handleMapTouchMoveForInsertionRef.current(mappedEvent);
          }
        };
        handleTouchEnd = () => {
          handleMapTouchEndForInsertionRef.current();
        };
        touchTarget.addEventListener('touchstart', handleTouchStart, { passive: true });
        touchTarget.addEventListener('touchmove', handleTouchMove, { passive: true });
        touchTarget.addEventListener('touchend', handleTouchEnd, { passive: true });
        touchTarget.addEventListener('touchcancel', handleTouchEnd, { passive: true });
        
        mapRef.current = map;
        setMapReady(true);
        
        // CRITICAL FIX: Restore saved location marker if editing existing project
        if (project) {
          // Check if we have saved coordinates to restore
          const params = project.params || {};
          if (params.latitude && params.longitude) {
            const coords = { 
              lat: parseFloat(params.latitude), 
              lng: parseFloat(params.longitude) 
            };
            
            // Wait a bit longer for map to be fully ready, then restore coordinates
            setTimeout(async () => {
              await restoreSavedLocationRef.current(map, coords);
            }, 1000); // Increased delay to ensure map is fully ready
          }
        }
      } catch (err: any) {
        console.error('Map init failed', err);
      }
    }
    initMap();
    return () => {
      isCancelled = true;
      if (touchTarget && handleTouchStart && handleTouchMove && handleTouchEnd) {
        touchTarget.removeEventListener('touchstart', handleTouchStart);
        touchTarget.removeEventListener('touchmove', handleTouchMove);
        touchTarget.removeEventListener('touchend', handleTouchEnd);
        touchTarget.removeEventListener('touchcancel', handleTouchEnd);
      }
      waypointMarkersRef.current.forEach(markers => markers.forEach(m => m.remove()));
      waypointMarkersRef.current.clear();
      waypointCoordsRef.current.clear();
      clearInsertionCandidateMarker();
      Object.values(boundaryMarkersRef.current).forEach((marker) => marker?.remove?.());
      boundaryMarkersRef.current = { center: null, major: null, minor: null };
      isMarkerInteractionActiveRef.current = false;
      lastMarkerInteractionEndedAtRef.current = 0;
      pendingViewportHistoryRef.current = null;
      if (mapRef.current) {
        mapRef.current.remove();
        mapRef.current = null;
        setMapReady(false);
        markerRef.current = null;
        selectedCoordsRef.current = null;
      }
    };
  }, [
    buildTouchInsertionEventFromDom,
    clearInsertionCandidateMarker,
    clearInsertionCandidateMarkerOnMapMove,
    open,
    project,
    resetWaypointOverrides,
    resolveMapbox,
  ]);

  // Helper function to place marker at coordinates
  const placeMarkerAtCoords = useCallback(async (
    lat: number,
    lng: number,
    options?: { historyAction?: string }
  ) => {
    if (!mapRef.current) return;

    const previousSnapshot = options?.historyAction && !isRestoringHistoryRef.current
      ? captureMapHistorySnapshot()
      : null;
    let historyCommitted = false;
    const commitHistory = () => {
      if (!previousSnapshot || historyCommitted) return;
      historyCommitted = true;
      pushMapHistoryEntry(options!.historyAction!, previousSnapshot, captureMapHistorySnapshot());
    };

    mapRef.current.once?.('moveend', commitHistory);
    mapRef.current.flyTo({ center: [lng, lat], zoom: 15, duration: 2000 });
    
    // Update both ref and state for coordinates
    const coords = { lat, lng };
    selectedCoordsRef.current = coords;
    setSelectedCoords(coords); // This will trigger autosave
    await setCenterMarkerOnMap(lat, lng);
    
    // Invalidate previous optimization since coordinates changed
    setOptimizedParamsWithLogging(null, 'Address search coordinates changed');
    clearBoundaryPlanState('Address search coordinates changed');
    resetWaypointOverrides(null);
    clearInsertionCandidateMarker();
    
    // Hide instructions
    const inst = document.getElementById('map-instructions');
    if (inst) inst.style.display = 'none';
    
    // Save will be triggered by autosave useEffect when selectedCoords changes
    if (previousSnapshot) {
      setTimeout(commitHistory, 2100);
    }
  }, [
    captureMapHistorySnapshot,
    clearBoundaryPlanState,
    clearInsertionCandidateMarker,
    pushMapHistoryEntry,
    resetWaypointOverrides,
    setCenterMarkerOnMap,
    setOptimizedParamsWithLogging,
  ]);

  // Function to restore saved location on map - now uses placeMarkerAtCoords for consistency
  const restoreSavedLocation = useCallback(async (map: any, coords: { lat: number; lng: number }) => {
    if (!map || !coords) return;
    
    map.flyTo({ center: [coords.lng, coords.lat], zoom: 15, duration: 0 });
    selectedCoordsRef.current = coords;
    setSelectedCoords(coords);
    await setCenterMarkerOnMap(coords.lat, coords.lng);
    
    // Update the address search field to show the coordinates
    setAddressSearch(`${coords.lat.toFixed(6)}, ${coords.lng.toFixed(6)}`);
  }, [setCenterMarkerOnMap]);

  useEffect(() => {
    restoreSavedLocationRef.current = restoreSavedLocation;
  }, [restoreSavedLocation]);

  // Fullscreen toggle handler
  const toggleFullscreen = useCallback(() => {
    if (!mapContainerRef.current) return;
    
    const newFullscreen = !isFullscreen;
    if (!newFullscreen && isBoundaryModeRef.current) {
      void handleCancelBoundaryModeRef.current?.();
    }
    setIsFullscreen(newFullscreen);
    
    // Find the map-wrapper (parent of map-container)
    const mapWrapper = mapContainerRef.current.parentElement;
    if (!mapWrapper) return;

    if (newFullscreen) {
      mapWrapper.classList.add('fullscreen');
    } else {
      mapWrapper.classList.remove('fullscreen');
    }
    
    // Force Mapbox to recalculate after fullscreen layout change
    setTimeout(() => {
      if (mapRef.current) {
        mapRef.current.resize();
        // Force coordinate system recalculation
        const currentCenter = mapRef.current.getCenter();
        const currentZoom = mapRef.current.getZoom();
        mapRef.current.jumpTo({
          center: [currentCenter.lng + 0.0000001, currentCenter.lat + 0.0000001],
          zoom: currentZoom
        });
        setTimeout(() => {
          if (mapRef.current) {
            mapRef.current.jumpTo({
              center: currentCenter,
              zoom: currentZoom
            });
            mapRef.current.resize();
          }
        }, 100);
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

  useEffect(() => {
    waypointMarkersRef.current.forEach((markers) => {
      markers.forEach(m => m.setDraggable(isFullscreen));
    });
  }, [isFullscreen]);

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

  // Clear all battery paths and waypoint markers when optimization is invalidated
  useEffect(() => {
    if (!optimizedParams) {
      clearInsertionCandidateMarker();
      const map = mapRef.current;
      if (map) {
        for (let i = 1; i <= 12; i++) {
          try {
            if (map.getLayer(`battery-path-layer-${i}`)) map.removeLayer(`battery-path-layer-${i}`);
            if (map.getSource(`battery-path-${i}`)) map.removeSource(`battery-path-${i}`);
          } catch { /* map may not be ready yet */ }
        }
      }
      waypointMarkersRef.current.forEach(markers => markers.forEach(m => m.remove()));
      waypointMarkersRef.current.clear();
      waypointCoordsRef.current.clear();
      setVisibleBatteryPaths(new Map());
    }
  }, [clearInsertionCandidateMarker, optimizedParams]);

  const parsedBatteryCount = useMemo(() => {
    return Math.max(0, Math.min(12, parseInt(numBatteries || '0') || 0));
  }, [numBatteries]);

  // Rotating processing messages for optimization
  const processingMessages = useMemo(() => [
    "This may take a moment...",
    "Running binary search optimization",
    formToTerrain ? "Forming to the terrain" : "Skipping terrain sampling",
    "Maximizing battery usage",
    "Calculating optimal flight paths",
    formToTerrain ? "Analyzing terrain features" : "Preparing flat flight path"
  ], [formToTerrain]);

  const startProcessingMessages = useCallback(() => {
    let messageIndex = 0;
    setProcessingMessage(processingMessages[0]);
    
    const interval = setInterval(() => {
      messageIndex = (messageIndex + 1) % processingMessages.length;
      setProcessingMessage(processingMessages[messageIndex]);
    }, 2000); // Change message every 2 seconds
    
    return interval;
  }, [processingMessages]);

  const handleTerrainToggle = useCallback(() => {
    setFormToTerrain((prev) => {
      const next = !prev;
      setOptimizedParamsWithLogging(null, `Form to terrain toggled ${next ? 'on' : 'off'}`);
      return next;
    });
  }, [setOptimizedParamsWithLogging]);

  const handleOptimize = useCallback(async () => {
    const coords = selectedCoordsRef.current ?? await waitForSelectedCoords();
    const minutes = parseInt(batteryMinutes);
    const batteries = parseInt(numBatteries);

    if (!coords || !minutes || !batteries) return;

    setOptimizationLoading(true);
    const messageInterval = startProcessingMessages();
    console.log('Starting optimization...');
    try {
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
        formToTerrain,
        minHeight: minHeightFeet, 
        maxHeight: maxHeightFeet 
      });

      const params = await runOptimizationRequest({
        coords,
        minutes,
        batteries,
        minHeightValue: minHeightFeet,
        maxHeightValue: maxHeightFeet,
        requestedMinExpansion: minExpansionDist,
        requestedMaxExpansion: maxExpansionDist,
        terrainEnabled: formToTerrain,
      });
      params.spinMode = spinMode;
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
  }, [batteryMinutes, formToTerrain, maxHeightFeet, minExpansionDist, maxExpansionDist, minHeightFeet, numBatteries, runOptimizationRequest, showSystemNotification, startProcessingMessages, spinMode, waitForSelectedCoords]);

  const ensureMissionReady = useCallback(async (): Promise<boolean> => {
    if (optimizedParamsRef.current || appliedBoundaryPlanRef.current) {
      return true;
    }

    const coords = selectedCoordsRef.current ?? await waitForSelectedCoords();
    const minutes = parseInt(batteryMinutes || '');
    const batteries = parseInt(numBatteries || '');

    if (!(coords && minutes && batteries)) {
      if (!coords) {
        showSystemNotification('error', 'Please select a location on the map first');
      } else if (!minutes || !batteries) {
        showSystemNotification('error', 'Please enter battery duration and quantity first');
      } else {
        showSystemNotification('error', 'Please set location and battery params first');
      }
      return false;
    }

    await handleOptimize();
    let checkCount = 0;
    while (checkCount < 60) {
      await new Promise(r => setTimeout(r, 500));
      checkCount += 1;
      if (optimizedParamsRef.current) {
        return true;
      }
    }

    showSystemNotification('error', 'Optimization timed out after 30 seconds. The server may be busy - please try again.');
    return false;
  }, [batteryMinutes, handleOptimize, numBatteries, showSystemNotification, waitForSelectedCoords]);

  // Processing messages for battery downloads
  const batteryProcessingMessages = useMemo(() => [
    "Running binary search optimization",
    formToTerrain ? "Forming to the terrain" : "Skipping terrain sampling",
    "Calculating altitude adjustments", 
    "Optimizing flight coverage",
    "Generating waypoint data",
    "Finalizing flight path"
  ], [formToTerrain]);

  const buildBatteryRequestBody = useCallback((batteryIndex1: number): Record<string, any> | null => {
    const currentOptimizedParams = optimizedParamsRef.current;
    const boundary = appliedBoundaryRef.current;
    const boundaryPlan = appliedBoundaryPlanRef.current;

    if (!currentOptimizedParams && !(boundary && boundaryPlan)) {
      return null;
    }

    const body: Record<string, any> = currentOptimizedParams
      ? buildResolvedFlightRequestBody(currentOptimizedParams)
      : {};
    const minH = parseFloat(minHeightFeet || '120') || 120;
    const maxH = maxHeightFeet ? parseFloat(maxHeightFeet) : null;

    if (boundary && boundaryPlan) {
      const planEntry = boundaryPlan.batteries.find((entry) => entry.batteryIndex === batteryIndex1);
      body.boundary = boundary;
      body.boundaryPlan = boundaryPlan;
      body.center = `${boundary.centerLat}, ${boundary.centerLng}`;
      body.slices = parsedBatteryCount || boundaryPlan.batteries.length;
      body.r0 = body.r0 ?? 200;
      body.rHold = body.rHold ?? boundary.majorRadiusFt;
      if (planEntry) {
        body.N = planEntry.bounceCount;
      }
    }

    body.minHeight = body.minHeight ?? minH;
    body.maxHeight = body.maxHeight ?? maxH;
    body.formToTerrain = currentOptimizedParams?.formToTerrain ?? formToTerrain;
    body.spinMode = currentOptimizedParams?.spinMode ?? spinMode;

    if (minExpansionDist) body.minExpansionDist = parseFloat(minExpansionDist);
    if (maxExpansionDist) body.maxExpansionDist = parseFloat(maxExpansionDist);

    return body;
  }, [buildResolvedFlightRequestBody, formToTerrain, maxHeightFeet, minExpansionDist, maxExpansionDist, minHeightFeet, parsedBatteryCount, spinMode]);

  const downloadBatteryCsv = useCallback(async (batteryIndex1: number) => {
    // Check if already downloading this battery
    if (downloadingBatteries.has(batteryIndex1)) {
      return;
    }

    const downloadBody = buildBatteryRequestBody(batteryIndex1);

    console.log(`🔍 downloadBatteryCsv called for battery ${batteryIndex1}:`, {
      hasRequestBody: !!downloadBody,
      optimizedParamsState: optimizedParams ? 'EXISTS' : 'NULL',
      hasBoundaryPlan: appliedBoundaryPlanRef.current ? 'YES' : 'NO',
    });

    if (!downloadBody) {
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
      console.log(`🔍 Sending to API for battery ${batteryIndex1}:`, downloadBody);
      
      const res = await fetch(`${API_ENHANCED_BASE}/api/csv/battery/${batteryIndex1}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(downloadBody),
      });
      const spinApplied = res.headers.get('X-Spin-Mode-Applied');
      const poiUsed = res.headers.get('X-POI-Used');
      if (spinApplied != null || poiUsed != null) {
        console.log(`🔍 [Battery CSV] X-Spin-Mode-Applied: ${spinApplied ?? 'n/a'}, X-POI-Used: ${poiUsed ?? 'n/a'}`);
      }
      if (!res.ok) {
        throw new Error(await readApiErrorMessage(
          res,
          `Failed to generate battery ${batteryIndex1} CSV`
        ));
      }
      const originalCsvText = await res.text();

      // Patch with live coordinates if they exist
      let finalCsvText = originalCsvText;
      const liveCoords = waypointCoordsRef.current.get(batteryIndex1)
        ?? waypointOverridesRef.current.batteries[String(batteryIndex1)];

      if (liveCoords && liveCoords.length > 0) {
        finalCsvText = rebuildBatteryCsvWithLiveCoords(originalCsvText, liveCoords);
        console.log(`Using modified coordinates for CSV download (${liveCoords.length} waypoints)`);
      }
      const safeTitle = (projectTitle && projectTitle !== 'Untitled')
        ? projectTitle.replace(/[^a-zA-Z0-9-_]/g, '_').substring(0, 50)
        : 'Untitled';
      const filename = `${safeTitle}-${batteryIndex1}.csv`;
      const blob = new Blob([finalCsvText], { type: 'text/csv' });
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
  }, [API_ENHANCED_BASE, batteryProcessingMessages, buildBatteryRequestBody, projectTitle, downloadingBatteries, optimizedParams, showSystemNotification]);

  const fetchBatteryPathCoords = useCallback(async (batteryIndex1: number): Promise<Array<[number, number]>> => {
    const body = buildBatteryRequestBody(batteryIndex1);
    if (!body) return [];

    const res = await fetch(`${API_ENHANCED_BASE}/api/csv/battery/${batteryIndex1}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
    if (!res.ok) {
      throw new Error(await readApiErrorMessage(
        res,
        `Failed to fetch battery ${batteryIndex1} path`
      ));
    }
    const csvText = await res.text();

    const lines = csvText.trim().split('\n');
    const coords: Array<[number, number]> = [];
    for (let i = 1; i < lines.length; i++) {
      const parts = lines[i].split(',');
      const lat = parseFloat(parts[0]);
      const lng = parseFloat(parts[1]);
      if (!isNaN(lat) && !isNaN(lng)) {
        coords.push([lng, lat]);
      }
    }
    return coords;
  }, [API_ENHANCED_BASE, buildBatteryRequestBody]);


  const removeWaypointMarkers = useCallback((batteryIndex: number) => {
    const existing = waypointMarkersRef.current.get(batteryIndex);
    if (existing) {
      existing.forEach(m => m.remove());
    }
    waypointMarkersRef.current.delete(batteryIndex);
    waypointCoordsRef.current.delete(batteryIndex);
  }, []);

  const setBatteryPathSourceData = useCallback((batteryIndex: number, coords: Array<[number, number]>) => {
    const map = mapRef.current;
    if (!map) return;

    const source = map.getSource(`battery-path-${batteryIndex}`);
    if (!source) return;
    source.setData({
      type: 'Feature',
      properties: {},
      geometry: { type: 'LineString', coordinates: coords },
    });
  }, []);

  const setVisibleBatteryPathCoords = useCallback((batteryIndex: number, coords: Array<[number, number]>) => {
    const cloned = clonePathCoords(coords);
    waypointCoordsRef.current.set(batteryIndex, cloned);
    setVisibleBatteryPaths((current) => {
      const next = new Map(current);
      next.set(batteryIndex, cloned);
      return next;
    });
  }, [clonePathCoords]);

  const createWaypointMarkers = useCallback(async (
    batteryIndex: number,
    coords: [number, number][],
    color: string
  ) => {
    const map = mapRef.current;
    if (!map) return;

    removeWaypointMarkers(batteryIndex);
    waypointCoordsRef.current.set(batteryIndex, clonePathCoords(coords));

    const mapboxModule = await import('mapbox-gl');
    const mapboxgl: any = (mapboxModule as any)?.default ?? mapboxModule;
    const markerDraggable = true;

    const markers: any[] = [];

    coords.forEach((coord, markerIndex) => {
      const el = document.createElement('div');
      el.className = 'waypoint-marker';
      el.dataset.batteryIndex = String(batteryIndex);
      el.dataset.waypointIndex = String(markerIndex);
      el.style.backgroundColor = color;

      const marker = new mapboxgl.Marker({ element: el, draggable: markerDraggable, anchor: 'center' })
        .setLngLat(coord)
        .addTo(map);
      const releaseMapPan = bindMarkerInteractionGuards(el);

      let dragStartSnapshot: MapHistorySnapshot | null = null;
      let markerMoved = false;
      let mergeTargetIndex: number | null = null;
      let mergeArmed = false;
      let mergeHoldTimer: ReturnType<typeof setTimeout> | null = null;
      let markerDragPanWasEnabled = false;

      const clearMergeHoldTimer = () => {
        if (mergeHoldTimer) {
          clearTimeout(mergeHoldTimer);
          mergeHoldTimer = null;
        }
      };

      const clearMergeTargetStyles = () => {
        if (mergeTargetIndex === null) return;
        const targetMarker = markers[mergeTargetIndex];
        const targetElement = targetMarker?.getElement?.();
        targetElement?.classList.remove('merge-target');
        targetElement?.classList.remove('merge-armed');
      };

      const resetMergeState = () => {
        clearMergeHoldTimer();
        clearMergeTargetStyles();
        mergeTargetIndex = null;
        mergeArmed = false;
      };

      const setMergeCandidate = (nextTargetIndex: number | null) => {
        if (nextTargetIndex === mergeTargetIndex) {
          return;
        }

        clearMergeHoldTimer();
        clearMergeTargetStyles();
        mergeTargetIndex = nextTargetIndex;
        mergeArmed = false;

        if (mergeTargetIndex === null) {
          return;
        }

        const targetMarker = markers[mergeTargetIndex];
        const targetElement = targetMarker?.getElement?.();
        if (!targetElement) {
          mergeTargetIndex = null;
          return;
        }

        targetElement.classList.add('merge-target');
        mergeHoldTimer = setTimeout(() => {
          mergeArmed = true;
          targetElement.classList.add('merge-armed');
        }, 500);
      };

      const findMergeCandidateIndex = (liveCoords: Array<[number, number]>, lngLat: { lng: number; lat: number }): number | null => {
        if (liveCoords.length <= 2) {
          return null;
        }

        const markerPoint = map.project([lngLat.lng, lngLat.lat]);
        let bestIndex: number | null = null;
        let bestDistance = Number.POSITIVE_INFINITY;

        liveCoords.forEach(([lng, lat], idx) => {
          if (idx === markerIndex) return;
          const point = map.project([lng, lat]);
          const distance = Math.hypot(point.x - markerPoint.x, point.y - markerPoint.y);
          if (distance < bestDistance) {
            bestDistance = distance;
            bestIndex = idx;
          }
        });

        return bestDistance <= 24 ? bestIndex : null;
      };

      const captureWaypointDragStart = () => {
        flushPendingViewportHistory();
        dragStartSnapshot = captureMapHistorySnapshot();
        markerMoved = false;
        resetMergeState();
      };
      el.addEventListener('pointerdown', captureWaypointDragStart, true);

      // Capture state before drag starts
      marker.on('dragstart', () => {
        isMarkerInteractionActiveRef.current = true;
        markerInteractionVersionRef.current += 1;
        const mapInstance = mapRef.current;
        if (mapInstance?.dragPan?.isEnabled?.()) {
          markerDragPanWasEnabled = true;
          mapInstance.dragPan.disable();
        }
        if (!dragStartSnapshot) {
          captureWaypointDragStart();
        }
      });

      marker.on('drag', () => {
        const lngLat = marker.getLngLat();
        const liveCoords = waypointCoordsRef.current.get(batteryIndex);
        if (!liveCoords) return;
        liveCoords[markerIndex] = [lngLat.lng, lngLat.lat];
        markerMoved = true;
        setBatteryPathSourceData(batteryIndex, liveCoords);

        const candidate = findMergeCandidateIndex(liveCoords, lngLat);
        setMergeCandidate(candidate);
      });

      // Commit to history when drag ends
      marker.on('dragend', async () => {
        releaseMapPan();
        isMarkerInteractionActiveRef.current = false;
        lastMarkerInteractionEndedAtRef.current = Date.now();
        markerInteractionVersionRef.current += 1;
        const mapInstance = mapRef.current;
        if (markerDragPanWasEnabled && mapInstance?.dragPan) {
          mapInstance.dragPan.enable();
        }
        markerDragPanWasEnabled = false;
        // Avoid a delayed map dragend from landing after marker history and consuming the first undo.
        pendingViewportHistoryRef.current = null;
        const liveCoords = waypointCoordsRef.current.get(batteryIndex) ?? [];
        let finalCoords = clonePathCoords(liveCoords);
        let historyAction = `waypoint ${batteryIndex} drag`;

        if (mergeArmed && mergeTargetIndex !== null && markerMoved) {
          if (liveCoords.length <= 2) {
            showSystemNotification('error', 'A flight segment needs at least two waypoints');
          } else {
            finalCoords = liveCoords.filter((_, idx) => idx !== markerIndex);
            historyAction = `waypoint ${batteryIndex} merge`;
            waypointCoordsRef.current.set(batteryIndex, finalCoords);
            setBatteryPathSourceData(batteryIndex, finalCoords);
            setVisibleBatteryPathCoords(batteryIndex, finalCoords);
            updateWaypointOverridesForBattery(batteryIndex, finalCoords);
            await createWaypointMarkers(batteryIndex, finalCoords, color);
          }
        } else if (markerMoved) {
          setVisibleBatteryPathCoords(batteryIndex, liveCoords);
          updateWaypointOverridesForBattery(batteryIndex, liveCoords);
        }

        const nextSnapshot = captureMapHistorySnapshot();
        if (dragStartSnapshot && markerMoved) {
          pushMapHistoryEntry(historyAction, dragStartSnapshot, nextSnapshot);
          triggerSaveRef.current?.();
        }
        resetMergeState();
        dragStartSnapshot = null;
        markerMoved = false;
      });

      markers.push(marker);
    });

    waypointMarkersRef.current.set(batteryIndex, markers);
  }, [
    bindMarkerInteractionGuards,
    captureMapHistorySnapshot,
    clonePathCoords,
    flushPendingViewportHistory,
    pushMapHistoryEntry,
    removeWaypointMarkers,
    setBatteryPathSourceData,
    setVisibleBatteryPathCoords,
    showSystemNotification,
    updateWaypointOverridesForBattery,
  ]);

  const findNearestInsertionCandidate = useCallback((
    point: { x: number; y: number },
    maxDistancePx = WAYPOINT_INSERT_HOVER_DISTANCE_PX
  ): WaypointInsertCandidate | null => {
    const map = mapRef.current;
    if (!map) return null;

    const pathEntries = waypointCoordsRef.current.size > 0
      ? Array.from(waypointCoordsRef.current.entries())
      : Array.from(visibleBatteryPaths.entries());

    let bestCandidate: WaypointInsertCandidate | null = null;
    let bestDistance = Number.POSITIVE_INFINITY;

    pathEntries.forEach(([batteryIndex, coords]) => {
      if (!coords || coords.length < 2) return;

      for (let segmentIndex = 0; segmentIndex < coords.length - 1; segmentIndex += 1) {
        const [startLng, startLat] = coords[segmentIndex];
        const [endLng, endLat] = coords[segmentIndex + 1];
        const startPoint = map.project([startLng, startLat]);
        const endPoint = map.project([endLng, endLat]);
        const segmentDx = endPoint.x - startPoint.x;
        const segmentDy = endPoint.y - startPoint.y;
        const segmentLengthSq = segmentDx * segmentDx + segmentDy * segmentDy;

        if (segmentLengthSq <= Number.EPSILON) {
          continue;
        }

        const pointerDx = point.x - startPoint.x;
        const pointerDy = point.y - startPoint.y;
        const t = Math.max(0, Math.min(1, (pointerDx * segmentDx + pointerDy * segmentDy) / segmentLengthSq));
        const projectedX = startPoint.x + segmentDx * t;
        const projectedY = startPoint.y + segmentDy * t;
        const distance = Math.hypot(point.x - projectedX, point.y - projectedY);

        if (distance < bestDistance) {
          const projectedLngLat = map.unproject([projectedX, projectedY]);
          bestDistance = distance;
          bestCandidate = {
            batteryIndex,
            segmentIndex,
            coord: [projectedLngLat.lng, projectedLngLat.lat],
          };
        }
      }
    });

    return bestDistance <= maxDistancePx ? bestCandidate : null;
  }, [visibleBatteryPaths]);

  const insertWaypointAtCandidate = useCallback(async (candidate: WaypointInsertCandidate) => {
    const existingCoords = waypointCoordsRef.current.get(candidate.batteryIndex)
      ?? visibleBatteryPaths.get(candidate.batteryIndex);
    if (!existingCoords || existingCoords.length < 2) {
      return;
    }

    const previousSnapshot = captureMapHistorySnapshot();
    const nextCoords = clonePathCoords(existingCoords);
    nextCoords.splice(candidate.segmentIndex + 1, 0, candidate.coord);

    setBatteryPathSourceData(candidate.batteryIndex, nextCoords);
    setVisibleBatteryPathCoords(candidate.batteryIndex, nextCoords);
    updateWaypointOverridesForBattery(candidate.batteryIndex, nextCoords);

    const color = BATTERY_PATH_COLORS[(candidate.batteryIndex - 1) % BATTERY_PATH_COLORS.length];
    await createWaypointMarkers(candidate.batteryIndex, nextCoords, color);

    const nextSnapshot = captureMapHistorySnapshot();
    pushMapHistoryEntry(`waypoint ${candidate.batteryIndex} insert`, previousSnapshot, nextSnapshot);
    triggerSaveRef.current?.();
    clearInsertionCandidateMarker();
  }, [
    BATTERY_PATH_COLORS,
    captureMapHistorySnapshot,
    clearInsertionCandidateMarker,
    clonePathCoords,
    createWaypointMarkers,
    pushMapHistoryEntry,
    setBatteryPathSourceData,
    setVisibleBatteryPathCoords,
    updateWaypointOverridesForBattery,
    visibleBatteryPaths,
  ]);

  const showInsertionCandidateMarker = useCallback(async (
    candidate: WaypointInsertCandidate,
    options?: { suppressImmediateTouchTap?: boolean }
  ) => {
    const map = mapRef.current;
    if (!map) return;

    logTouchInsertionDebug('show-marker', candidate);
    insertionCandidateRef.current = candidate;
    if (options?.suppressImmediateTouchTap) {
      ignoreInsertionMarkerActivationUntilTouchStartRef.current = true;
    }
    const mapboxgl = await resolveMapbox();

    if (!insertionMarkerRef.current) {
      const element = document.createElement('div');
      element.className = 'waypoint-insert-marker';
      element.textContent = '+';
      let lastInsertHandledAt = 0;
      const triggerInsert = () => {
        const now = Date.now();
        if (now - lastInsertHandledAt < 250) {
          return;
        }
        lastInsertHandledAt = now;
        const activeCandidate = insertionCandidateRef.current;
        if (activeCandidate) {
          void insertWaypointAtCandidate(activeCandidate);
        }
      };
      element.addEventListener('pointerdown', (event) => {
        if ((event as PointerEvent).pointerType === 'touch' && ignoreInsertionMarkerActivationUntilTouchStartRef.current) {
          ignoreInsertionMarkerActivationUntilTouchStartRef.current = false;
        }
        event.stopPropagation();
      }, true);
      element.addEventListener('touchstart', (event) => {
        if (ignoreInsertionMarkerActivationUntilTouchStartRef.current) {
          ignoreInsertionMarkerActivationUntilTouchStartRef.current = false;
        }
        event.stopPropagation();
      }, { passive: true, capture: true });
      element.addEventListener('click', (event) => {
        event.preventDefault();
        event.stopPropagation();
        if ((event as MouseEvent).detail === 0) {
          return;
        }
        if (ignoreInsertionMarkerActivationUntilTouchStartRef.current) {
          return;
        }
        triggerInsert();
      });
      element.addEventListener('touchend', (event) => {
        event.preventDefault();
        event.stopPropagation();
        if (ignoreInsertionMarkerActivationUntilTouchStartRef.current) {
          return;
        }
        triggerInsert();
      }, { passive: false });
      element.addEventListener('pointerup', (event) => {
        if ((event as PointerEvent).pointerType !== 'touch') {
          return;
        }
        event.preventDefault();
        event.stopPropagation();
        if (ignoreInsertionMarkerActivationUntilTouchStartRef.current) {
          return;
        }
        triggerInsert();
      });

      insertionMarkerRef.current = new mapboxgl.Marker({ element, anchor: 'center' })
        .setLngLat(candidate.coord)
        .addTo(map);
      return;
    }

    insertionMarkerRef.current.setLngLat(candidate.coord);
  }, [insertWaypointAtCandidate, logTouchInsertionDebug, resolveMapbox]);

  const handleMapPointerMoveForInsertion = useCallback((event: any) => {
    if (!isFullscreen || isBoundaryModeRef.current || isApplyingBoundaryRef.current || isMarkerInteractionActiveRef.current) {
      clearInsertionCandidateMarker();
      return;
    }
    if (Date.now() < ignoreInsertionPointerHoverUntilRef.current) {
      return;
    }
    const candidate = event?.point ? findNearestInsertionCandidate(event.point) : null;
    if (!candidate) {
      clearInsertionCandidateMarker();
      return;
    }
    void showInsertionCandidateMarker(candidate);
  }, [clearInsertionCandidateMarker, findNearestInsertionCandidate, isFullscreen, showInsertionCandidateMarker]);

  const handleMapTouchStartForInsertion = useCallback((event: any) => {
    logTouchInsertionDebug('touchstart', {
      isFullscreen,
      isBoundaryMode: isBoundaryModeRef.current,
      isApplyingBoundary: isApplyingBoundaryRef.current,
      isMarkerInteractionActive: isMarkerInteractionActiveRef.current,
      point: event?.point ?? null,
    });
    if (!isFullscreen || isBoundaryModeRef.current || isApplyingBoundaryRef.current || isMarkerInteractionActiveRef.current) {
      clearInsertionCandidateMarker();
      return;
    }
    if (!event?.point) {
      return;
    }

    const touchPoint = { x: event.point.x, y: event.point.y };
    ignoreInsertionPointerHoverUntilRef.current = Date.now() + 1200;
    clearPendingInsertionTouchTimer();
    insertionTouchStartPointRef.current = touchPoint;
    insertionTouchTimerRef.current = setTimeout(() => {
      const candidate = findNearestInsertionCandidate(touchPoint, WAYPOINT_INSERT_TOUCH_DISTANCE_PX);
      logTouchInsertionDebug('touch-hold-fired', {
        touchPoint,
        candidate,
      });
      if (candidate) {
        void showInsertionCandidateMarker(candidate, { suppressImmediateTouchTap: true });
      }
    }, 450);
  }, [
    clearInsertionCandidateMarker,
    clearPendingInsertionTouchTimer,
    findNearestInsertionCandidate,
    isFullscreen,
    logTouchInsertionDebug,
    showInsertionCandidateMarker,
  ]);

  const handleMapTouchMoveForInsertion = useCallback((event: any) => {
    if (!insertionTouchStartPointRef.current || !event?.point) {
      return;
    }
    ignoreInsertionPointerHoverUntilRef.current = Date.now() + 1200;

    const moved = Math.hypot(
      event.point.x - insertionTouchStartPointRef.current.x,
      event.point.y - insertionTouchStartPointRef.current.y
    );

    logTouchInsertionDebug('touchmove', {
      moved,
      point: event.point,
      touchStartPoint: insertionTouchStartPointRef.current,
    });
    if (moved > WAYPOINT_INSERT_TOUCH_CANCEL_DISTANCE_PX) {
      clearPendingInsertionTouchTimer();
    }
  }, [clearPendingInsertionTouchTimer, logTouchInsertionDebug]);

  const handleMapTouchEndForInsertion = useCallback(() => {
    ignoreInsertionPointerHoverUntilRef.current = Date.now() + 1200;
    logTouchInsertionDebug('touchend', {
      hadTimer: Boolean(insertionTouchTimerRef.current),
      hadTouchStart: Boolean(insertionTouchStartPointRef.current),
    });
    clearPendingInsertionTouchTimer();
    insertionTouchStartPointRef.current = null;
  }, [clearPendingInsertionTouchTimer, logTouchInsertionDebug]);

  useEffect(() => {
    handleMapPointerMoveForInsertionRef.current = handleMapPointerMoveForInsertion;
  }, [handleMapPointerMoveForInsertion]);

  useEffect(() => {
    handleMapTouchStartForInsertionRef.current = handleMapTouchStartForInsertion;
  }, [handleMapTouchStartForInsertion]);

  useEffect(() => {
    handleMapTouchMoveForInsertionRef.current = handleMapTouchMoveForInsertion;
  }, [handleMapTouchMoveForInsertion]);

  useEffect(() => {
    handleMapTouchEndForInsertionRef.current = handleMapTouchEndForInsertion;
  }, [handleMapTouchEndForInsertion]);

  useEffect(() => {
    if (!open || !isFullscreen || isBoundaryMode || isApplyingBoundary) {
      clearInsertionCandidateMarker();
    }
  }, [clearInsertionCandidateMarker, isApplyingBoundary, isBoundaryMode, isFullscreen, open]);

  const removeBatteryPathVisualization = useCallback((batteryIndex: number) => {
    const map = mapRef.current;
    if (map) {
      const layerId = `battery-path-layer-${batteryIndex}`;
      const hitLayerId = `battery-path-hit-layer-${batteryIndex}`;
      const sourceId = `battery-path-${batteryIndex}`;
      try {
        if (map.getLayer(layerId)) map.removeLayer(layerId);
        if (map.getLayer(hitLayerId)) map.removeLayer(hitLayerId);
        if (map.getSource(sourceId)) map.removeSource(sourceId);
      } catch {
        // Ignore teardown races while the map is resizing or unmounting.
      }
    }
    removeWaypointMarkers(batteryIndex);
  }, [removeWaypointMarkers]);

  const drawBatteryPathVisualization = useCallback(async (
    batteryIndex: number,
    coords: [number, number][]
  ) => {
    const map = mapRef.current;
    if (!map || !coords.length) return;

    const sourceId = `battery-path-${batteryIndex}`;
    const layerId = `battery-path-layer-${batteryIndex}`;
    const color = BATTERY_PATH_COLORS[(batteryIndex - 1) % BATTERY_PATH_COLORS.length];

    try {
      if (map.getLayer(layerId)) map.removeLayer(layerId);
      if (map.getLayer(`battery-path-hit-layer-${batteryIndex}`)) map.removeLayer(`battery-path-hit-layer-${batteryIndex}`);
      if (map.getSource(sourceId)) map.removeSource(sourceId);
    } catch {
      // Ignore replacement races while redrawing the preview.
    }

    map.addSource(sourceId, {
      type: 'geojson',
      data: {
        type: 'Feature',
        properties: {},
        geometry: { type: 'LineString', coordinates: coords },
      },
    });

    map.addLayer({
      id: layerId,
      type: 'line',
      source: sourceId,
      paint: {
        'line-color': color,
        'line-width': 2.5,
        'line-opacity': 0.85,
      },
    });

    map.addLayer({
      id: `battery-path-hit-layer-${batteryIndex}`,
      type: 'line',
      source: sourceId,
      paint: {
        'line-color': '#ffffff',
        'line-width': 18,
        'line-opacity': 0.001,
      },
    });

    await createWaypointMarkers(batteryIndex, coords, color);
  }, [BATTERY_PATH_COLORS, createWaypointMarkers]);

  const fitMapToPreviewPaths = useCallback((previewPaths: BoundaryPreviewPath[]) => {
    const map = mapRef.current;
    if (!map || previewPaths.length === 0) return;

    const allCoords = previewPaths.flatMap((path) => path.coordinates);
    if (!allCoords.length) return;

    const lngs = allCoords.map((coord) => coord[0]);
    const lats = allCoords.map((coord) => coord[1]);
    map.fitBounds(
      [[Math.min(...lngs), Math.min(...lats)], [Math.max(...lngs), Math.max(...lats)]],
      { padding: 50, duration: 1000 }
    );
  }, []);

  const clearAllBatteryPaths = useCallback(() => {
    clearInsertionCandidateMarker();
    visibleBatteryPaths.forEach((_, batteryIdx) => {
      removeBatteryPathVisualization(batteryIdx);
    });
    setVisibleBatteryPaths(new Map());
  }, [clearInsertionCandidateMarker, removeBatteryPathVisualization, visibleBatteryPaths]);

  useEffect(() => {
    clearAllBatteryPathsRef.current = clearAllBatteryPaths;
  }, [clearAllBatteryPaths]);

  const replaceBatteryPreviewPaths = useCallback(async (
    previewPaths: BoundaryPreviewPath[],
    options?: { fitBounds?: boolean; useOverrides?: boolean }
  ) => {
    const nextPaths = options?.useOverrides === false
      ? cloneBoundaryPreviewPaths(previewPaths)
      : resolvePreviewPathsWithOverrides(previewPaths);

    visibleBatteryPaths.forEach((_, batteryIdx) => {
      removeBatteryPathVisualization(batteryIdx);
    });

    for (const previewPath of nextPaths) {
      await drawBatteryPathVisualization(previewPath.batteryIndex, previewPath.coordinates);
    }

    setVisibleBatteryPaths(new Map(nextPaths.map((path) => [path.batteryIndex, clonePathCoords(path.coordinates)])));

    if (options?.fitBounds !== false) {
      fitMapToPreviewPaths(nextPaths);
    }
  }, [
    cloneBoundaryPreviewPaths,
    clonePathCoords,
    drawBatteryPathVisualization,
    fitMapToPreviewPaths,
    removeBatteryPathVisualization,
    resolvePreviewPathsWithOverrides,
    visibleBatteryPaths,
  ]);

  useEffect(() => {
    replaceBatteryPreviewPathsRef.current = replaceBatteryPreviewPaths;
  }, [replaceBatteryPreviewPaths]);

  const loadAllBatteryPathPreviews = useCallback(async (options?: { fitBounds?: boolean }): Promise<BoundaryPreviewPath[]> => {
    const readyMap = mapReadyRef.current || await waitForMapReady();
    if (!readyMap) return [];

    const batteryCount = parsedBatteryCount;
    if (!batteryCount) return [];

    const ready = await ensureMissionReady();
    if (!ready) return [];

    const previews: BoundaryPreviewPath[] = [];
    for (let batteryIndex = 1; batteryIndex <= batteryCount; batteryIndex += 1) {
      const cached = visibleBatteryPaths.get(batteryIndex);
      const coords = cached && cached.length > 0 ? cached : await fetchBatteryPathCoords(batteryIndex);
      if (coords.length > 0) {
        previews.push({ batteryIndex, coordinates: coords });
      }
    }

    const resolvedPreviews = resolvePreviewPathsWithOverrides(previews);
    await replaceBatteryPreviewPaths(resolvedPreviews, { ...options, useOverrides: false });
    return resolvedPreviews;
  }, [
    ensureMissionReady,
    fetchBatteryPathCoords,
    parsedBatteryCount,
    replaceBatteryPreviewPaths,
    resolvePreviewPathsWithOverrides,
    visibleBatteryPaths,
    waitForMapReady,
  ]);

  const toggleBatteryPathVisibility = useCallback(async (batteryIndex1: number) => {
    const map = mapRef.current;
    if (!map) return;

    const isCurrentlyVisible = visibleBatteryPaths.has(batteryIndex1);

    if (isCurrentlyVisible) {
      removeBatteryPathVisualization(batteryIndex1);
      setVisibleBatteryPaths(prev => {
        const next = new Map(prev);
        next.delete(batteryIndex1);
        if (next.size === 0) {
          clearInsertionCandidateMarker();
        }
        return next;
      });
      return;
    }

    setLoadingBatteryPaths(prev => new Set([...prev, batteryIndex1]));
    try {
      const ready = await ensureMissionReady();
      if (!ready) {
        return;
      }

      const coords = await fetchBatteryPathCoords(batteryIndex1);
      if (!coords || coords.length === 0) {
        showSystemNotification('error', 'No path data received');
        return;
      }

      const resolvedPath = resolvePreviewPathsWithOverrides([
        { batteryIndex: batteryIndex1, coordinates: coords },
      ])[0];
      const resolvedCoords = resolvedPath?.coordinates ?? coords;
      await drawBatteryPathVisualization(batteryIndex1, resolvedCoords);

      setVisibleBatteryPaths(prev => {
        const next = new Map(prev);
        next.set(batteryIndex1, clonePathCoords(resolvedCoords));
        return next;
      });

      fitMapToPreviewPaths([{ batteryIndex: batteryIndex1, coordinates: resolvedCoords }]);
    } catch (e: any) {
      showSystemNotification('error', e?.message || 'Failed to visualize path');
    } finally {
      setLoadingBatteryPaths(prev => {
        const next = new Set(prev);
        next.delete(batteryIndex1);
        return next;
      });
    }
  }, [
    clonePathCoords,
    clearInsertionCandidateMarker,
    drawBatteryPathVisualization,
    ensureMissionReady,
    fetchBatteryPathCoords,
    fitMapToPreviewPaths,
    removeBatteryPathVisualization,
    resolvePreviewPathsWithOverrides,
    showSystemNotification,
    visibleBatteryPaths,
  ]);

  const upsertBoundaryLineLayer = useCallback((
    sourceId: string,
    layerId: string,
    coordinates: Array<[number, number]>,
    paint: Record<string, any>
  ) => {
    const map = mapRef.current;
    if (!map) return;

    const data = {
      type: 'Feature',
      properties: {},
      geometry: {
        type: 'LineString',
        coordinates,
      },
    };

    const source = map.getSource(sourceId);
    if (source) {
      source.setData(data);
      return;
    }

    map.addSource(sourceId, {
      type: 'geojson',
      data,
    });

    map.addLayer({
      id: layerId,
      type: 'line',
      source: sourceId,
      layout: {
        'line-join': 'round',
        'line-cap': 'round',
      },
      paint,
    });
  }, []);

  const removeBoundaryOverlay = useCallback(() => {
    Object.values(boundaryMarkersRef.current).forEach((marker) => marker?.remove?.());
    boundaryMarkersRef.current = { center: null, major: null, minor: null };

    const map = mapRef.current;
    if (!map) return;

    [
      ['boundary-ellipse-layer', 'boundary-ellipse-source'],
      ['boundary-major-guide-layer', 'boundary-major-guide-source'],
      ['boundary-minor-guide-layer', 'boundary-minor-guide-source'],
    ].forEach(([layerId, sourceId]) => {
      try {
        if (map.getLayer(layerId)) map.removeLayer(layerId);
        if (map.getSource(sourceId)) map.removeSource(sourceId);
      } catch {
        // Ignore teardown races while resizing or unmounting.
      }
    });
  }, []);

  const ensureBoundaryMarkers = useCallback(async (boundary: BoundaryEllipse, interactive: boolean) => {
    const map = mapRef.current;
    if (!map) return;

    const mapboxgl = await resolveMapbox();
    const handles = boundaryHandlePositions(boundary);
    const markerDefinitions: Array<{
      key: keyof MapboxMarkerRefMap;
      lat: number;
      lng: number;
      className: string;
    }> = [
      { key: 'center', lat: handles.center.lat, lng: handles.center.lng, className: 'boundary-handle-marker center' },
      { key: 'major', lat: handles.major.lat, lng: handles.major.lng, className: 'boundary-handle-marker major' },
      { key: 'minor', lat: handles.minor.lat, lng: handles.minor.lng, className: 'boundary-handle-marker minor' },
    ];

    markerDefinitions.forEach(({ key, lat, lng, className }) => {
      let marker = boundaryMarkersRef.current[key];
      if (!marker) {
        const element = document.createElement('div');
        element.className = className;
        marker = new mapboxgl.Marker({ element, draggable: interactive, anchor: 'center' })
          .setLngLat([lng, lat])
          .addTo(map);
        const releaseMapPan = bindMarkerInteractionGuards(element);
        let dragStartSnapshot: MapHistorySnapshot | null = null;
        let markerMoved = false;
        const captureBoundaryDragStart = () => {
          flushPendingViewportHistory();
          dragStartSnapshot = captureMapHistorySnapshot();
          markerMoved = false;
        };
        element.addEventListener('pointerdown', captureBoundaryDragStart, true);

        marker.on('dragstart', () => {
          if (!dragStartSnapshot) {
            captureBoundaryDragStart();
          }
        });

        marker.on('drag', () => {
          const current = draftBoundaryRef.current;
          if (!current) return;
          const lngLat = marker.getLngLat();

          if (key === 'center') {
            setDraftBoundary(normalizeBoundary({
              ...current,
              centerLat: lngLat.lat,
              centerLng: lngLat.lng,
            }));
          } else if (key === 'major') {
            const local = latLngToLocalFeet(lngLat.lat, lngLat.lng, current.centerLat, current.centerLng);
            const majorRadiusFt = Math.max(150, Math.hypot(local.xFt, local.yFt));
            const rotationDeg = normalizeRotationDeg((Math.atan2(local.yFt, local.xFt) * 180) / Math.PI);
            setDraftBoundary(normalizeBoundary({
              ...current,
              majorRadiusFt,
              minorRadiusFt: Math.min(majorRadiusFt, current.minorRadiusFt),
              rotationDeg,
            }));
          } else {
            const local = latLngToLocalFeet(lngLat.lat, lngLat.lng, current.centerLat, current.centerLng);
            const unrotated = rotatePoint(local, -current.rotationDeg);
            const minorRadiusFt = Math.min(current.majorRadiusFt, Math.max(150, Math.abs(unrotated.yFt)));
            setDraftBoundary(normalizeBoundary({
              ...current,
              minorRadiusFt,
            }));
          }

          setBoundaryDirty(true);
          markerMoved = true;
        });

        marker.on('dragend', () => {
          releaseMapPan();
          // Avoid a delayed map dragend from landing after boundary history and consuming the first undo.
          pendingViewportHistoryRef.current = null;
          setBoundaryDirty(true);
          const nextSnapshot = captureMapHistorySnapshot();
          if (dragStartSnapshot && markerMoved) {
            pushMapHistoryEntry(`boundary ${key} drag`, dragStartSnapshot, nextSnapshot);
          }
          dragStartSnapshot = null;
          markerMoved = false;
        });

        boundaryMarkersRef.current[key] = marker;
      }

      marker.setDraggable(interactive);
      marker.setLngLat([lng, lat]);
    });
  }, [bindMarkerInteractionGuards, captureMapHistorySnapshot, flushPendingViewportHistory, pushMapHistoryEntry, resolveMapbox]);

  const optimizeBoundaryMission = useCallback(async (boundary: BoundaryEllipse): Promise<BoundaryOptimizationResponse> => {
    const minutes = parseInt(batteryMinutes);
    const batteries = parseInt(numBatteries);
    const minH = parseFloat(minHeightFeet || '120') || 120;
    const maxH = maxHeightFeet ? parseFloat(maxHeightFeet) : null;
    const centerText = `${boundary.centerLat}, ${boundary.centerLng}`;

    const body: Record<string, any> = {
      batteryMinutes: minutes,
      batteries,
      center: centerText,
      minHeight: minH,
      maxHeight: maxH,
      boundary,
    };

    if (minExpansionDist) body.minExpansionDist = parseFloat(minExpansionDist);
    if (maxExpansionDist) body.maxExpansionDist = parseFloat(maxExpansionDist);

    const endpoints = [
      `${API_ENHANCED_BASE}/api/optimize-boundary`,
      `${API_ENHANCED_BASE}/api/optimize-spiral`,
    ];

    let lastError: Error | null = null;

    for (const endpoint of endpoints) {
      try {
        const res = await fetch(endpoint, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(body),
        });

        if (!res.ok) {
          const errorText = await res.text().catch(() => 'Unknown error');
          throw new Error(errorText || 'Boundary optimization failed');
        }

        const data = await res.json();
        if (data?.boundaryPlan && Array.isArray(data?.previewPaths)) {
          return data as BoundaryOptimizationResponse;
        }

        throw new Error('Boundary optimization response was missing boundary plan data');
      } catch (error: any) {
        lastError = error instanceof Error ? error : new Error(error?.message || 'Boundary optimization failed');
        if (endpoint.endsWith('/api/optimize-boundary')) {
          console.warn('Boundary endpoint unavailable, retrying via optimize-spiral fallback', lastError);
          continue;
        }
      }
    }

    throw lastError || new Error('Boundary optimization failed');
  }, [API_ENHANCED_BASE, batteryMinutes, maxExpansionDist, maxHeightFeet, minExpansionDist, minHeightFeet, numBatteries]);

  const handleCancelBoundaryMode = useCallback(async () => {
    setIsBoundaryMode(false);
    setBoundaryDirty(false);
    setDraftBoundary(appliedBoundaryRef.current ? normalizeBoundary(appliedBoundaryRef.current) : null);

    const snapshot = Array.from(boundaryEntryVisiblePathsRef.current.entries()).map(([batteryIndex, coordinates]) => ({
      batteryIndex,
      coordinates,
    }));

    if (snapshot.length > 0) {
      await replaceBatteryPreviewPaths(snapshot, { fitBounds: false, useOverrides: false });
    } else {
      clearAllBatteryPaths();
    }
  }, [clearAllBatteryPaths, replaceBatteryPreviewPaths]);

  useEffect(() => {
    handleCancelBoundaryModeRef.current = handleCancelBoundaryMode;
  }, [handleCancelBoundaryMode]);

  const handleEnterBoundaryMode = useCallback(async () => {
    if (!isFullscreen) {
      showSystemNotification('error', 'Boundary editing is only available in fullscreen mode');
      return;
    }

    try {
      setIsApplyingBoundary(true);
      const ready = await ensureMissionReady();
      if (!ready) {
        return;
      }

      boundaryEntryVisiblePathsRef.current = cloneVisiblePaths(visibleBatteryPaths);
      const previewPaths = await loadAllBatteryPathPreviews({ fitBounds: true });
      if (!previewPaths.length) {
        showSystemNotification('error', 'Failed to generate flight path previews');
        return;
      }

      const currentCenter = appliedBoundaryRef.current
        ? { lat: appliedBoundaryRef.current.centerLat, lng: appliedBoundaryRef.current.centerLng }
        : selectedCoordsRef.current;
      if (!currentCenter) {
        showSystemNotification('error', 'Please select a location on the map first');
        return;
      }

      const nextBoundary = appliedBoundaryRef.current
        ? normalizeBoundary(appliedBoundaryRef.current)
        : computeAutoFitCircle(
            previewPaths.flatMap((path) => path.coordinates),
            currentCenter.lat,
            currentCenter.lng,
            1.05
          );

      setDraftBoundary(nextBoundary);
      setBoundaryDirty(!appliedBoundaryRef.current || !appliedBoundaryPlanRef.current);
      setIsBoundaryMode(true);
    } catch (e: any) {
      showSystemNotification('error', e?.message || 'Failed to start boundary editing');
    } finally {
      setIsApplyingBoundary(false);
    }
  }, [cloneVisiblePaths, ensureMissionReady, isFullscreen, loadAllBatteryPathPreviews, showSystemNotification, visibleBatteryPaths]);

  const handleApplyBoundary = useCallback(async () => {
    const currentDraft = draftBoundaryRef.current;
    if (!currentDraft || isApplyingBoundary) return;

    try {
      setIsApplyingBoundary(true);
      flushPendingViewportHistory();
      const previousSnapshot = captureMapHistorySnapshot();
      const response = await optimizeBoundaryMission(currentDraft);
      const normalizedBoundary = normalizeBoundary(response.boundary);
      const previousBoundarySignature = buildBoundarySignature(appliedBoundaryRef.current);
      const nextBoundarySignature = buildBoundarySignature(normalizedBoundary);
      const boundaryGeometryChanged = previousBoundarySignature !== nextBoundarySignature;

      appliedBoundaryRef.current = normalizedBoundary;
      appliedBoundaryPlanRef.current = response.boundaryPlan;
      setAppliedBoundary(normalizedBoundary);
      setAppliedBoundaryPlan(response.boundaryPlan);
      setDraftBoundary(normalizedBoundary);
      setBoundaryDirty(false);
      setIsBoundaryMode(false);

      const updatedCenter = {
        lat: normalizedBoundary.centerLat,
        lng: normalizedBoundary.centerLng,
      };
      selectedCoordsRef.current = updatedCenter;
      setSelectedCoords(updatedCenter);
      setAddressSearch(`${updatedCenter.lat.toFixed(6)}, ${updatedCenter.lng.toFixed(6)}`);
      await setCenterMarkerOnMap(updatedCenter.lat, updatedCenter.lng);

      if (boundaryGeometryChanged) {
        resetWaypointOverrides(nextBoundarySignature);
      } else {
        const next = cloneWaypointOverrides(waypointOverridesRef.current);
        next.boundarySignature = nextBoundarySignature;
        commitWaypointOverrides(next);
      }

      const previewPaths = boundaryGeometryChanged
        ? response.previewPaths
        : resolvePreviewPathsWithOverrides(response.previewPaths);
      await replaceBatteryPreviewPaths(previewPaths, { fitBounds: true, useOverrides: false });
      boundaryEntryVisiblePathsRef.current = new Map(
        previewPaths.map((path) => [path.batteryIndex, clonePathCoords(path.coordinates)])
      );

      if (response.boundaryPlan.fitStatus === 'best_effort' && response.toastMessage) {
        showSystemNotification('error', response.toastMessage);
      } else {
        showSystemNotification('success', 'Boundary applied');
      }

      setTimeout(() => {
        pushMapHistoryEntry('boundary apply', previousSnapshot, captureMapHistorySnapshot());
      }, 0);
      triggerSaveRef.current?.();
    } catch (e: any) {
      showSystemNotification('error', e?.message || 'Failed to apply boundary');
    } finally {
      setIsApplyingBoundary(false);
    }
  }, [
    captureMapHistorySnapshot,
    clonePathCoords,
    commitWaypointOverrides,
    flushPendingViewportHistory,
    isApplyingBoundary,
    optimizeBoundaryMission,
    pushMapHistoryEntry,
    replaceBatteryPreviewPaths,
    resetWaypointOverrides,
    resolvePreviewPathsWithOverrides,
    setCenterMarkerOnMap,
    showSystemNotification,
  ]);

  useEffect(() => {
    const activeBoundary = isFullscreen
      ? (isBoundaryMode ? draftBoundary : appliedBoundary)
      : null;

    if (!mapReady || !activeBoundary) {
      removeBoundaryOverlay();
      return;
    }

    const boundary = normalizeBoundary(activeBoundary);
    const outlineCoordinates = buildEllipseOutlineCoordinates(boundary, 120);
    const guideCoordinates = buildBoundaryGuideCoordinates(boundary);

    upsertBoundaryLineLayer('boundary-ellipse-source', 'boundary-ellipse-layer', outlineCoordinates, {
      'line-color': '#ffffff',
      'line-width': 2,
      'line-opacity': 0.92,
    });
    upsertBoundaryLineLayer('boundary-major-guide-source', 'boundary-major-guide-layer', guideCoordinates.major, {
      'line-color': '#ffffff',
      'line-width': 1.5,
      'line-opacity': 0.6,
      'line-dasharray': [2, 2],
    });
    upsertBoundaryLineLayer('boundary-minor-guide-source', 'boundary-minor-guide-layer', guideCoordinates.minor, {
      'line-color': '#ffffff',
      'line-width': 1.5,
      'line-opacity': 0.4,
      'line-dasharray': [2, 2],
    });
    void ensureBoundaryMarkers(boundary, isBoundaryMode);
  }, [appliedBoundary, draftBoundary, ensureBoundaryMarkers, isBoundaryMode, isFullscreen, mapReady, removeBoundaryOverlay, upsertBoundaryLineLayer]);

  useEffect(() => {
    if (!open || !mapReady || !appliedBoundary || !appliedBoundaryPlan || visibleBatteryPaths.size > 0) {
      return;
    }

    void loadAllBatteryPathPreviews({ fitBounds: false });
  }, [appliedBoundary, appliedBoundaryPlan, loadAllBatteryPathPreviews, mapReady, open, visibleBatteryPaths.size]);

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
          formToTerrain,
          spinMode,
          minExpansionDist: minExpansionDist || null,
          maxExpansionDist: maxExpansionDist || null,
          latitude: selectedCoordsRef.current?.lat || null,
          longitude: selectedCoordsRef.current?.lng || null,
          boundary: appliedBoundaryRef.current || null,
          boundaryPlan: appliedBoundaryPlanRef.current || null,
          waypointOverrides: waypointOverridesRef.current,
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
  }, [addressSearch, batteryMinutes, currentProjectId, formToTerrain, maxHeightFeet, minHeightFeet, minExpansionDist, maxExpansionDist, numBatteries, onSaved, projectTitle, status, isSaving, spinMode]);

  // Check if project has meaningful content
  const hasMeaningfulContent = useCallback(() => {
    // Always save if editing existing project
    if (currentProjectId) return true;
    
    // For new projects, check if any meaningful data is entered
    const hasLocation = Boolean(addressSearch.trim() || selectedCoords);
    const hasBatteryData = Boolean(batteryMinutes || numBatteries);
    const hasAltitudeData = Boolean(minHeightFeet || maxHeightFeet);
    const hasSpinMode = spinMode;
    const hasTitleChange = projectTitle !== 'Untitled' && projectTitle.trim();
    const hasUploadData = Boolean(propertyTitle.trim() || listingDescription.trim() || contactEmail.trim() || selectedFile);
    
    return hasLocation || hasBatteryData || hasAltitudeData || hasSpinMode || hasTitleChange || hasUploadData;
  }, [currentProjectId, addressSearch, batteryMinutes, numBatteries, minHeightFeet, maxHeightFeet, spinMode, projectTitle, propertyTitle, listingDescription, contactEmail, selectedFile, selectedCoords]);

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

  useEffect(() => {
    triggerSaveRef.current = triggerSave;
  }, [triggerSave]);

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
      formToTerrain,
      spinMode,
      status,
      selectedCoords: selectedCoords ? 'EXISTS' : 'NULL',
      optimizedParams: optimizedParams ? 'EXISTS' : 'NULL',
          appliedBoundary: appliedBoundary ? 'EXISTS' : 'NULL',
          appliedBoundaryPlan: appliedBoundaryPlan ? 'EXISTS' : 'NULL',
          waypointOverridesCount: Object.keys(waypointOverridesRef.current?.batteries || {}).length,
        });
    
    // Don't trigger save immediately, use timeout to avoid render-phase updates
    const timer = setTimeout(() => {
      triggerSave();
    }, 100); // Small delay to avoid render-phase updates
    
    return () => clearTimeout(timer);
  }, [open, projectTitle, addressSearch, batteryMinutes, numBatteries, minHeightFeet, maxHeightFeet, formToTerrain, spinMode, status, selectedCoords, appliedBoundary, appliedBoundaryPlan, waypointOverrides]);

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
    resolvingLocationRef.current = true;

    try {
      let waitCount = 0;
      while (!mapRef.current && waitCount < 50) {
        await new Promise((resolve) => setTimeout(resolve, 100));
        waitCount += 1;
      }

      if (!mapRef.current) {
        showSystemNotification('error', 'Map is still loading. Please try again in a moment.');
        return;
      }

      // Check if input looks like coordinates (lat, lng)
      const coordsMatch = query.match(/^(-?\d+\.?\d*)\s*,\s*(-?\d+\.?\d*)$/);

      if (coordsMatch) {
        // Handle direct coordinate input
        const lat = parseFloat(coordsMatch[1]);
        const lng = parseFloat(coordsMatch[2]);

        if (lat >= -90 && lat <= 90 && lng >= -180 && lng <= 180) {
        await placeMarkerAtCoords(lat, lng, { historyAction: 'address center change' });
        return;
      }
      }

      // Handle geocoding search
      try {
        const res = await fetch(`https://api.mapbox.com/geocoding/v5/mapbox.places/${encodeURIComponent(query)}.json?access_token=${MAPBOX_TOKEN}&limit=1`);
        const data = await res.json();
        if (data?.features?.length) {
          const [lng, lat] = data.features[0].center;
          await placeMarkerAtCoords(lat, lng, { historyAction: 'address center change' });
        }
      } catch (err) {
        console.warn('Geocoding failed:', err);
      }
    } finally {
      resolvingLocationRef.current = false;
    }
  }, [addressSearch, MAPBOX_TOKEN, showSystemNotification]);

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
              formToTerrain,
              boundary: appliedBoundaryRef.current || null,
              boundaryPlan: appliedBoundaryPlanRef.current || null,
              waypointOverrides: waypointOverridesRef.current,
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
  }, [API_UPLOAD, CHUNK_SIZE, MAX_FILE_SIZE, addressSearch, batteryMinutes, contactEmail, formToTerrain, listingDescription, maxHeightFeet, minHeightFeet, numBatteries, projectTitle, propertyTitle, selectedFile, validateUpload]);

  if (!open) return null;

  const batteryCount = parsedBatteryCount;
  const optimizationInfo = optimizedParams?.optimizationInfo ?? null;
  const optimizationAdjustments = optimizationInfo?.adjustments ?? [];
  const requestedExpansionSummary = formatExpansionSummary(minExpansionDist, maxExpansionDist);
  const actualExpansionSummary = optimizedParams
    ? formatExpansionSummary(
        optimizedParams.actualMinExpansionDist ?? null,
        optimizedParams.actualMaxExpansionDist ?? null,
      )
    : 'Not optimized yet';

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
                {/* Empty map container for Mapbox - avoids the warning */}
                <div id="map-container" className="map-container" ref={mapContainerRef}></div>
                
                {/* Map overlays and controls as siblings */}
                {isFullscreen && (
                  <div className="map-toolbar">
                    <button 
                      onClick={handleUndo} 
                      disabled={historyIndex < 0}
                      className="map-toolbar-button"
                      title="Undo"
                    >
                      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                        <path d="M9 14L4 9l5-5"/>
                        <path d="M4 9h10.5a5.5 5.5 0 0 1 5.5 5.5v0a5.5 5.5 0 0 1-5.5 5.5H11"/>
                      </svg>
                    </button>
                    <button 
                      onClick={handleRedo} 
                      disabled={historyIndex >= history.length - 1}
                      className="map-toolbar-button"
                      title="Redo"
                    >
                      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                        <path d="M15 14l5-5-5-5"/>
                        <path d="M20 9H9.5A5.5 5.5 0 0 0 4 14.5v0A5.5 5.5 0 0 0 9.5 20H13"/>
                      </svg>
                    </button>
                    <button
                      onClick={isBoundaryMode ? handleCancelBoundaryMode : handleEnterBoundaryMode}
                      disabled={isApplyingBoundary}
                      className={`map-toolbar-button map-toolbar-button--text${isBoundaryMode ? ' active' : ''}`}
                      title={isBoundaryMode ? 'Cancel boundary editing' : 'Edit boundary'}
                    >
                      {isBoundaryMode ? 'Boundary On' : 'Boundary'}
                    </button>
                  </div>
                )}
                {isFullscreen && batteryCount > 0 && (
                  <div className="map-battery-panel">
                    {Array.from({ length: batteryCount }).map((_, idx) => (
                      <button
                        key={`fullscreen-battery-${idx + 1}`}
                        className={`map-battery-button${downloadingBatteries.has(idx + 1) ? ' loading' : ''}`}
                        onClick={async () => {
                          const ready = await ensureMissionReady();
                          if (!ready) {
                            return;
                          }
                          downloadBatteryCsv(idx + 1);
                        }}
                      >
                        {downloadingBatteries.has(idx + 1) ? `Battery ${idx + 1}...` : `Battery ${idx + 1}`}
                      </button>
                    ))}
                  </div>
                )}
                <button className={`expand-button${isFullscreen ? ' expanded' : ''}`} id="expand-button" onClick={toggleFullscreen}>
                  <span className="expand-icon"></span>
                </button>
                {isFullscreen && isBoundaryMode && (
                  <div className="boundary-editor-bar">
                    <div className="boundary-editor-copy">
                      Drag the center, long-axis, and minor-axis handles, then apply the boundary.
                    </div>
                    <div className="boundary-editor-actions">
                      <button
                        type="button"
                        className="boundary-editor-button secondary"
                        onClick={() => void handleCancelBoundaryMode()}
                        disabled={isApplyingBoundary}
                      >
                        Cancel
                      </button>
                      <button
                        type="button"
                        className="boundary-editor-button primary"
                        onClick={() => void handleApplyBoundary()}
                        disabled={isApplyingBoundary || (!boundaryDirty && !!appliedBoundaryPlan)}
                      >
                        {isApplyingBoundary ? 'Applying...' : 'Apply'}
                      </button>
                    </div>
                  </div>
                )}
                {isFullscreen && visibleBatteryPaths.size > 0 && (
                  <div className="waypoint-drag-hint">Drag waypoints to adjust path</div>
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
                        clearBoundaryPlanState(`Battery minutes changed to: ${value}`);
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
                        clearBoundaryPlanState(`Number of batteries changed to: ${value}`);
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
                        clearBoundaryPlanState(`Min height changed to: ${value}`);
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
                        clearBoundaryPlanState(`Max height changed to: ${value}`);
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

            <div className="category-outline category-outline--hug">
              <div className="popup-section terrain-toggle-row">
                <button
                  type="button"
                  role="switch"
                  aria-checked={formToTerrain}
                  aria-label="Terrain avoidance"
                  className={`terrain-toggle-switch${formToTerrain ? ' is-on' : ''}`}
                  onClick={handleTerrainToggle}
                >
                  <span className="terrain-toggle-switch-thumb" />
                </button>
                <span className="terrain-toggle-label">Terrain avoidance</span>
              </div>
            </div>

            {/* Expansion */}
            <div className="category-outline">
              <div className="popup-section">
                <h4>Expansion</h4>
                <div className="input-row-popup">
                  <div className="popup-input-wrapper" style={{ position: 'relative' }}>
                    <span className="input-icon minimum"></span>
                    <input
                      type="text"
                      className="text-fade-right"
                      placeholder="Min Distance"
                      value={minExpansionDist ? `${minExpansionDist} ft` : ''}
                      onChange={(e) => {
                        const value = e.target.value.replace(/[^0-9]/g, '');
                        setMinExpansionDist(value);
                        clearBoundaryPlanState(`Min expansion changed to: ${value}`);
                        clearAllBatteryPaths();
                        setOptimizedParamsWithLogging(null, `Min expansion distance changed to: ${value}`);
                      }}
                      onKeyDown={(e) => {
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
                      placeholder="Max Distance"
                      value={maxExpansionDist ? `${maxExpansionDist} ft` : ''}
                      onChange={(e) => {
                        const value = e.target.value.replace(/[^0-9]/g, '');
                        setMaxExpansionDist(value);
                        clearBoundaryPlanState(`Max expansion changed to: ${value}`);
                        clearAllBatteryPaths();
                        setOptimizedParamsWithLogging(null, `Max expansion distance changed to: ${value}`);
                      }}
                      onKeyDown={(e) => {
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

            <div className="category-outline">
              <div className="popup-section">
                <h4>Capture Mode</h4>
                <div className="input-row-popup" style={{ alignItems: 'center', gap: '12px' }}>
                  <label style={{ display: 'flex', alignItems: 'center', gap: '8px', cursor: 'pointer' }}>
                    <input
                      type="checkbox"
                      checked={spinMode}
                      onChange={(e) => {
                        const nextSpinMode = e.target.checked;
                        setSpinMode(nextSpinMode);
                        clearAllBatteryPaths();
                      }}
                    />
                    <span style={{ color: 'rgba(255,255,255,0.9)' }}>
                      Multi-angle parallax spin mode (2s interval)
                    </span>
                  </label>
                </div>
              </div>
            </div>

            {optimizedParams && (
              <div className="category-outline">
                <div className="popup-section">
                  <h4>Optimization Summary</h4>
                  <div style={{
                    display: 'grid',
                    gap: 10,
                    marginTop: 8,
                    color: '#f5f5f5',
                    fontSize: 13,
                    lineHeight: 1.5,
                  }}>
                    <div style={{
                      display: 'grid',
                      gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))',
                      gap: 10,
                    }}>
                      <div>
                        <strong>Requested Expansion:</strong><br />
                        <span>{requestedExpansionSummary}</span>
                      </div>
                      <div>
                        <strong>Actual Expansion Used:</strong><br />
                        <span>{actualExpansionSummary}</span>
                      </div>
                      <div>
                        <strong>Bounce Seed / Final:</strong><br />
                        <span>{optimizedParams.requestedBounceSeed ?? '-'}{' -> '}{optimizedParams.N ?? '-'}</span>
                      </div>
                      <div>
                        <strong>Estimated Time / Utilization:</strong><br />
                        <span>
                          {optimizedParams.estimated_time_minutes ?? '-'} min / {optimizedParams.battery_utilization ?? '-'}%
                        </span>
                      </div>
                    </div>

                    {optimizationAdjustments.length > 0 && (
                      <div style={{
                        padding: '10px 12px',
                        borderRadius: 10,
                        border: '1px solid rgba(255, 205, 96, 0.45)',
                        background: 'rgba(255, 205, 96, 0.12)',
                        color: '#ffe8b0',
                      }}>
                        <strong style={{ display: 'block', marginBottom: 6 }}>Optimizer Adjustments</strong>
                        {optimizationAdjustments.map((adjustment, index) => (
                          <div key={`${adjustment}-${index}`}>{adjustment}</div>
                        ))}
                      </div>
                    )}

                    {optimizationInfo?.final_constraints?.rHold && (
                      <div style={{ opacity: 0.82 }}>
                        Final hold radius: {Number(optimizationInfo.final_constraints.rHold).toFixed(0)} ft
                        {typeof optimizedParams.actualOuterRadius === 'number' && (
                          <> | Actual outer radius: {optimizedParams.actualOuterRadius.toFixed(0)} ft</>
                        )}
                      </div>
                    )}
                  </div>
                </div>
              </div>
            )}

            {/* Individual Battery Segments (legacy-correct UI) */}
            <div className="category-outline">
              <div className="popup-section">
                <h4 className="text-fade-right" style={{ marginLeft: '6%', marginRight: '6%', width: 'auto' }}>
                  {optimizationLoading || downloadingBatteries.size > 0 ? processingMessage : "Individual Battery Segments:"}
                </h4>
                {optimizationAdjustments.length > 0 && (
                  <div style={{
                    margin: '8px 6% 12px',
                    padding: '8px 10px',
                    borderRadius: 10,
                    border: '1px solid rgba(255, 205, 96, 0.35)',
                    background: 'rgba(255, 205, 96, 0.08)',
                    color: '#ffe8b0',
                    fontSize: 12,
                    lineHeight: 1.45,
                  }}>
                    Battery-fit notice: the optimizer adjusted bounce count and/or spacing before download.
                  </div>
                )}
                <div id="batteryButtons" className="flight-path-grid">
                {Array.from({ length: batteryCount }).map((_, idx) => (
                  <div key={idx} className="battery-segment-item">
                    <button
                      className={`flight-path-download-btn${downloadingBatteries.has(idx + 1) ? ' loading' : ''}`}
                      onClick={async () => {
                        const ready = await ensureMissionReady();
                        if (!ready) {
                          return;
                        }
                        downloadBatteryCsv(idx + 1);
                      }}
                    >
                      <span className={`download-icon${downloadingBatteries.has(idx + 1) ? ' loading' : ''}`}></span>
                      Battery {idx + 1}
                    </button>
                    <button
                      className={`battery-view-btn${visibleBatteryPaths.has(idx + 1) ? ' active' : ''}${loadingBatteryPaths.has(idx + 1) ? ' loading' : ''}`}
                      onClick={() => toggleBatteryPathVisibility(idx + 1)}
                      title={visibleBatteryPaths.has(idx + 1) ? 'Hide flight path' : 'Show flight path on map'}
                    >
                      {loadingBatteryPaths.has(idx + 1) ? (
                        <span className="view-loading-spinner" />
                      ) : visibleBatteryPaths.has(idx + 1) ? (
                        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                          <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94"/>
                          <path d="M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19"/>
                          <line x1="1" y1="1" x2="23" y2="23"/>
                        </svg>
                      ) : (
                        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                          <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/>
                          <circle cx="12" cy="12" r="3"/>
                        </svg>
                      )}
                    </button>
                  </div>
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
