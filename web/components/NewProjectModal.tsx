"use client";
import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { buildApiUrl } from '../app/api-config';
import { useLitchiAutomation } from '../hooks/useLitchiAutomation';

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
  const [showManualDownloads, setShowManualDownloads] = useState<boolean>(false);

  const [litchiConnectOpen, setLitchiConnectOpen] = useState<boolean>(false);
  const [litchiEmail, setLitchiEmail] = useState<string>('');
  const [litchiPassword, setLitchiPassword] = useState<string>('');
  const [litchiTwoFactor, setLitchiTwoFactor] = useState<string>('');
  const [litchiPrepProgress, setLitchiPrepProgress] = useState<{ current: number; total: number } | null>(null);
  const [litchiSending, setLitchiSending] = useState<boolean>(false);
  const [litchiSendError, setLitchiSendError] = useState<string | null>(null);
  const [litchiShowAllLogs, setLitchiShowAllLogs] = useState<boolean>(false);
  const [litchiSelectedBatteries, setLitchiSelectedBatteries] = useState<Set<number>>(new Set());

  const {
    apiConfigured: litchiApiConfigured,
    status: litchiStatus,
    connected: litchiConnected,
    isConnecting: litchiConnecting,
    isUploading: litchiUploading,
    progress: litchiProgress,
    error: litchiError,
    connectMessage: litchiConnectMessage,
    connect: connectLitchi,
    uploadMissions: uploadLitchiMissions,
  } = useLitchiAutomation();

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

  // Initialize Mapbox on open
  useEffect(() => {
    let isCancelled = false;
    async function initMap() {
      if (!open) return;
      if (!mapContainerRef.current) return;
      try {
        const mapboxgl = await import('mapbox-gl');
        mapboxgl.default.accessToken = MAPBOX_TOKEN;
        if (isCancelled) return;
        const map = new mapboxgl.default.Map({
          container: mapContainerRef.current,
          style: 'mapbox://styles/mapbox/satellite-v9',
          center: [-98.5795, 39.8283],
          zoom: 4,
          attributionControl: false,
        });
        
        map.on('click', (e: any) => {
          const { lng, lat } = e.lngLat;
          selectedCoordsRef.current = { lat, lng };
          // place marker
          if (markerRef.current) {
            markerRef.current.remove();
          }
          
          // Create custom teardrop pin element with inline SVG
          const pinElement = document.createElement('div');
          pinElement.className = 'custom-teardrop-pin';
          pinElement.innerHTML = `
            <svg width="32" height="50" viewBox="0 0 32 50" fill="none" xmlns="http://www.w3.org/2000/svg" style="filter: drop-shadow(0 2px 8px rgba(0, 0, 0, 0.3)) drop-shadow(0 1px 4px rgba(0, 0, 0, 0.2)) drop-shadow(0 0 2px rgba(0, 0, 0, 0.1)); transform: translateY(4px);">
              <path fill-rule="evenodd" clip-rule="evenodd" d="M16.1896 0.32019C7.73592 0.32019 0.882812 7.17329 0.882812 15.627C0.882812 17.3862 1.17959 19.0761 1.72582 20.6494L1.7359 20.6784C1.98336 21.3865 2.2814 22.0709 2.62567 22.7272L13.3424 47.4046L13.3581 47.3897C13.8126 48.5109 14.9121 49.3016 16.1964 49.3016C17.5387 49.3016 18.6792 48.4377 19.0923 47.2355L29.8623 22.516C30.9077 20.4454 31.4965 18.105 31.4965 15.627C31.4965 7.17329 24.6434 0.32019 16.1896 0.32019ZM16.18 9.066C12.557 9.066 9.61992 12.003 9.61992 15.6261C9.61992 19.2491 12.557 22.1861 16.18 22.1861C19.803 22.1861 22.7401 19.2491 22.7401 15.6261C22.7401 12.003 19.803 9.066 16.18 9.066Z" fill="white"/>
            </svg>
          `;
          
          markerRef.current = new mapboxgl.default.Marker({ element: pinElement, anchor: 'bottom' })
            .setLngLat([lng, lat])
            .addTo(map);
          
          // Fill address input with coordinates formatted
          setAddressSearch(`${lat.toFixed(6)}, ${lng.toFixed(6)}`);
          // Invalidate previous optimization
          setOptimizedParamsWithLogging(null, 'Map coordinates changed');
          // Hide instructions after first click
          const inst = document.getElementById('map-instructions');
          if (inst) inst.style.display = 'none';
        });
        
        mapRef.current = map;
        
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
              await restoreSavedLocation(map, coords);
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
      if (mapRef.current) {
        mapRef.current.remove();
        mapRef.current = null;
        markerRef.current = null;
        selectedCoordsRef.current = null;
      }
    };
  }, [open, project]);

  // Helper function to place marker at coordinates
  const placeMarkerAtCoords = useCallback(async (lat: number, lng: number) => {
    if (!mapRef.current) return;
    
    mapRef.current.flyTo({ center: [lng, lat], zoom: 15, duration: 2000 });
    
    // Update both ref and state for coordinates
    const coords = { lat, lng };
    selectedCoordsRef.current = coords;
    setSelectedCoords(coords); // This will trigger autosave
    
    // Place marker
    const mapboxgl = await import('mapbox-gl');
    if (markerRef.current) markerRef.current.remove();
    
    const pinElement = document.createElement('div');
    pinElement.className = 'custom-teardrop-pin';
    pinElement.innerHTML = `
      <svg width="32" height="50" viewBox="0 0 32 50" fill="none" xmlns="http://www.w3.org/2000/svg" style="filter: drop-shadow(0 2px 8px rgba(0, 0, 0, 0.3)) drop-shadow(0 1px 4px rgba(0, 0, 0, 0.2)) drop-shadow(0 0 2px rgba(0, 0, 0, 0.1)); transform: translateY(4px);">
        <path fill-rule="evenodd" clip-rule="evenodd" d="M16.1896 0.32019C7.73592 0.32019 0.882812 7.17329 0.882812 15.627C0.882812 17.3862 1.17959 19.0761 1.72582 20.6494L1.7359 20.6784C1.98336 21.3865 2.2814 22.0709 2.62567 22.7272L13.3424 47.4046L13.3581 47.3897C13.8126 48.5109 14.9121 49.3016 16.1964 49.3016C17.5387 49.3016 18.6792 48.4377 19.0923 47.2355L29.8623 22.516C30.9077 20.4454 31.4965 18.105 31.4965 15.627C31.4965 7.17329 24.6434 0.32019 16.1896 0.32019ZM16.18 9.066C12.557 9.066 9.61992 12.003 9.61992 15.6261C9.61992 19.2491 12.557 22.1861 16.18 22.1861C19.803 22.1861 22.7401 19.2491 22.7401 15.6261C22.7401 12.003 19.803 9.066 16.18 9.066Z" fill="white"/>
      </svg>
    `;
    
    markerRef.current = new mapboxgl.default.Marker({ element: pinElement, anchor: 'bottom' })
      .setLngLat([lng, lat])
      .addTo(mapRef.current);
    
    // Invalidate previous optimization since coordinates changed
    setOptimizedParamsWithLogging(null, 'Address search coordinates changed');
    
    // Hide instructions
    const inst = document.getElementById('map-instructions');
    if (inst) inst.style.display = 'none';
    
    // Save will be triggered by autosave useEffect when selectedCoords changes
  }, []);

  // Function to restore saved location on map - now uses placeMarkerAtCoords for consistency
  const restoreSavedLocation = useCallback(async (map: any, coords: { lat: number; lng: number }) => {
    if (!map || !coords) return;
    
    // Use the same function as user interaction to ensure consistency
    await placeMarkerAtCoords(coords.lat, coords.lng);
    
    // Update the address search field to show the coordinates
    setAddressSearch(`${coords.lat.toFixed(6)}, ${coords.lng.toFixed(6)}`);
  }, [placeMarkerAtCoords]);

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
    
    // Force Mapbox to recalculate after DOM move
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

  const batteryCount = Math.max(0, Math.min(12, parseInt(numBatteries || '0') || 0));

  useEffect(() => {
    setLitchiSelectedBatteries(prev => {
      if (!batteryCount) return new Set();
      if (prev.size === 0) {
        return new Set(Array.from({ length: batteryCount }, (_, idx) => idx + 1));
      }
      const next = new Set<number>();
      for (let idx = 1; idx <= batteryCount; idx += 1) {
        if (prev.has(idx)) next.add(idx);
      }
      return next;
    });
  }, [batteryCount]);

  const toggleLitchiBattery = useCallback((batteryIndex: number) => {
    setLitchiSelectedBatteries(prev => {
      const next = new Set(prev);
      if (next.has(batteryIndex)) {
        next.delete(batteryIndex);
      } else {
        next.add(batteryIndex);
      }
      return next;
    });
  }, []);

  const selectAllLitchiBatteries = useCallback(() => {
    if (!batteryCount) return;
    setLitchiSelectedBatteries(new Set(Array.from({ length: batteryCount }, (_, idx) => idx + 1)));
  }, [batteryCount]);

  const clearLitchiBatterySelection = useCallback(() => {
    setLitchiSelectedBatteries(new Set());
  }, []);

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

  const ensureOptimizedParams = useCallback(async () => {
    const currentOptimizedParams = optimizedParamsRef.current;
    if (currentOptimizedParams && Object.keys(currentOptimizedParams).length > 0) {
      return currentOptimizedParams;
    }

    if (!canOptimize) {
      if (!selectedCoordsRef.current) {
        showSystemNotification('error', 'Please select a location on the map first');
      } else if (!batteryMinutes || !numBatteries) {
        showSystemNotification('error', 'Please enter battery duration and quantity first');
      } else {
        showSystemNotification('error', 'Please set location and battery params first');
      }
      return null;
    }

    try {
      await handleOptimize();
      let checkCount = 0;
      const maxChecks = 60;

      while (checkCount < maxChecks) {
        await new Promise(r => setTimeout(r, 500));
        checkCount++;
        const refreshedParams = optimizedParamsRef.current;
        if (refreshedParams && Object.keys(refreshedParams).length > 0) {
          break;
        }
      }

      const finalParams = optimizedParamsRef.current;
      if (!finalParams || Object.keys(finalParams).length === 0) {
        showSystemNotification('error', 'Optimization timed out after 30 seconds. The server may be busy - please try again.');
        return null;
      }

      return finalParams;
    } catch (e: any) {
      showSystemNotification('error', 'Failed to optimize flight path: ' + (e?.message || 'Unknown error'));
      return null;
    }
  }, [batteryMinutes, canOptimize, handleOptimize, numBatteries, showSystemNotification]);

  const handleLitchiConnect = useCallback(async (event: React.FormEvent) => {
    event.preventDefault();
    const result = await connectLitchi(litchiEmail, litchiPassword, litchiTwoFactor || undefined);
    if (result?.status === 'active') {
      setLitchiConnectOpen(false);
      setLitchiPassword('');
      setLitchiTwoFactor('');
    }
  }, [connectLitchi, litchiEmail, litchiPassword, litchiTwoFactor]);

  const handleSendToLitchi = useCallback(async () => {
    if (!litchiApiConfigured) {
      setLitchiSendError('Litchi automation API is not configured.');
      return;
    }

    if (!batteryCount) {
      setLitchiSendError('Please set battery quantity first');
      return;
    }

    const params = await ensureOptimizedParams();
    if (!params) return;

    setLitchiSendError(null);
    setLitchiSending(true);
    const selectedIndexes = Array.from(litchiSelectedBatteries).sort((a, b) => a - b);
    if (selectedIndexes.length === 0) {
      setLitchiSending(false);
      setLitchiPrepProgress(null);
      setLitchiSendError('Select at least one battery to send to Litchi.');
      return;
    }
    setLitchiPrepProgress({ current: 0, total: selectedIndexes.length });

    try {
      const baseTitle = projectTitle && projectTitle !== 'Untitled' ? projectTitle.trim() : 'Untitled';
      let completed = 0;
      const missions = await Promise.all(
        selectedIndexes.map(async (batteryIndex) => {
          const res = await fetch(`${API_ENHANCED_BASE}/api/csv/battery/${batteryIndex}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(params),
          });
          if (!res.ok) {
            throw new Error(`Failed to generate battery ${batteryIndex} CSV`);
          }
          const csvText = await res.text();
          completed += 1;
          setLitchiPrepProgress({ current: completed, total: batteryCount });
          return {
            name: `${baseTitle} - ${batteryIndex}`,
            csv: csvText,
          };
        })
      );

      setLitchiPrepProgress(null);
      const result = await uploadLitchiMissions(missions);
      if (!result) {
        setLitchiSendError('Upload failed');
      }
    } catch (e: any) {
      const message = e?.message || 'Upload failed';
      setLitchiSendError(message);
    } finally {
      setLitchiSending(false);
      setLitchiPrepProgress(null);
    }
  }, [
    API_ENHANCED_BASE,
    batteryCount,
    ensureOptimizedParams,
    litchiApiConfigured,
    litchiSelectedBatteries,
    projectTitle,
    uploadLitchiMissions,
  ]);

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
  }, [API_ENHANCED_BASE, projectTitle, downloadingBatteries]);

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
    if (!query || !mapRef.current) return;
    
    // Check if input looks like coordinates (lat, lng)
    const coordsMatch = query.match(/^(-?\d+\.?\d*)\s*,\s*(-?\d+\.?\d*)$/);
    
    if (coordsMatch) {
      // Handle direct coordinate input
      const lat = parseFloat(coordsMatch[1]);
      const lng = parseFloat(coordsMatch[2]);
      
      if (lat >= -90 && lat <= 90 && lng >= -180 && lng <= 180) {
        await placeMarkerAtCoords(lat, lng);
        return;
      }
    }
    
    // Handle geocoding search
    try {
      const res = await fetch(`https://api.mapbox.com/geocoding/v5/mapbox.places/${encodeURIComponent(query)}.json?access_token=${MAPBOX_TOKEN}&limit=1`);
      const data = await res.json();
      if (data?.features?.length) {
        const [lng, lat] = data.features[0].center;
        await placeMarkerAtCoords(lat, lng);
      }
    } catch (err) {
      console.warn('Geocoding failed:', err);
    }
  }, [addressSearch, MAPBOX_TOKEN]);

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

  const litchiInlineOpen = litchiConnectOpen || Boolean(litchiStatus?.needsTwoFactor);
  const litchiStatusState = litchiStatus?.status ?? 'unknown';
  const litchiIndicator = litchiStatusState !== 'error' && litchiStatusState !== 'expired'
    ? litchiProgress?.current && litchiProgress?.total
      ? `Uploading ${litchiProgress.current}/${litchiProgress.total}...`
      : litchiPrepProgress
        ? `Preparing ${litchiPrepProgress.current}/${litchiPrepProgress.total}...`
        : ''
    : '';
  const litchiSectionError = litchiSendError || litchiError;
  const litchiLogs = litchiStatus?.logs ?? [];
  const litchiVisibleLogs = litchiShowAllLogs ? litchiLogs : litchiLogs.slice(-5);
  const litchiSelectedCount = litchiSelectedBatteries.size;
  const litchiSelectionLabel = batteryCount
    ? `${litchiSelectedCount}/${batteryCount} batteries selected`
    : 'No batteries selected';
  const litchiStatusLabels: Record<string, string> = {
    not_connected: 'Not connected',
    connecting: 'Connecting',
    active: 'Connected',
    pending_2fa: 'Needs 2FA',
    expired: 'Expired',
    uploading: 'Uploading',
    testing: 'Testing connection',
    rate_limited: 'Rate limited',
    error: 'Error',
  };
  const litchiStatusLabel = litchiStatus ? (litchiStatusLabels[litchiStatusState] || litchiStatusState) : 'Unknown';
  const litchiNeedsReconnect = litchiStatus?.status === 'error' || litchiStatus?.status === 'expired';
  const litchiHasLoginFailure = litchiLogs.some(entry => /login failed/i.test(entry));
  const litchiGuidance = litchiNeedsReconnect
    ? 'Login failed or expired. Re-enter your Litchi credentials to continue.'
    : litchiHasLoginFailure
      ? 'We could not verify these credentials. Please retry or re-enter your password.'
      : litchiStatus?.needsTwoFactor
        ? 'Enter your 2FA code to finish connecting.'
        : litchiStatus?.status === 'connecting'
          ? 'Verifying your Litchi login. This can take up to a minute.'
          : !litchiConnected
            ? 'Connect your Litchi account to enable uploads.'
            : litchiSelectedCount === 0
              ? 'Select the battery segments you want to send below.'
              : 'Uploads run in the background. You can close this window and return later.';
  const litchiConnectStatusMessage = (litchiNeedsReconnect || litchiHasLoginFailure)
    ? 'Login failed. Please re-enter your credentials.'
    : litchiConnectMessage;

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

            {/* Delivery & Automation */}
            <div className="category-outline">
              <div className="popup-section">
                <h4 className="text-fade-right" style={{ marginLeft: '6%', marginRight: '6%', width: 'auto' }}>
                  Delivery & Automation
                </h4>
                {!litchiApiConfigured && (
                  <p className="litchi-muted">Litchi automation API is not configured for this environment.</p>
                )}
                <div className="litchi-card-header">
                  <div>
                    {litchiStatus?.message && <p className="litchi-status-message">{litchiStatus.message}</p>}
                    <p className="litchi-muted">{litchiGuidance}</p>
                  </div>
                  <span className={`litchi-status-pill litchi-status-${litchiStatus?.status || 'unknown'}`}>{litchiStatusLabel}</span>
                </div>
                {litchiSectionError && <p className="litchi-error" role="status">{litchiSectionError}</p>}
                <div className="litchi-actions">
                  {litchiConnected ? (
                    <button
                      className="litchi-primary"
                      type="button"
                      onClick={handleSendToLitchi}
                      disabled={!litchiApiConfigured || litchiSending || litchiUploading || litchiSelectedCount === 0}
                    >
                      {litchiSending
                        ? 'Preparing missions...'
                        : litchiUploading
                          ? 'Queueing upload...'
                          : litchiSelectedCount && litchiSelectedCount < batteryCount
                            ? `Send ${litchiSelectedCount} batteries to Litchi`
                            : 'Send to Litchi'}
                    </button>
                  ) : (
                    <button
                      className="litchi-primary"
                      type="button"
                      onClick={() => setLitchiConnectOpen(v => !v)}
                      disabled={!litchiApiConfigured || litchiConnecting}
                    >
                      {litchiStatus?.needsTwoFactor ? 'Enter 2FA Code' : 'Connect Litchi Account'}
                    </button>
                  )}
                  <button className="litchi-secondary" type="button" onClick={() => setShowManualDownloads(v => !v)}>
                    {showManualDownloads ? 'Hide manual downloads' : 'Download manually'}
                  </button>
                </div>
                {batteryCount > 0 && (
                  <div className="litchi-selection">
                    <div className="litchi-selection-header">
                      <span className="litchi-muted">Choose which batteries to send</span>
                      <div className="litchi-actions">
                        <button className="litchi-secondary" type="button" onClick={selectAllLitchiBatteries}>
                          Select all
                        </button>
                        <button className="litchi-secondary" type="button" onClick={clearLitchiBatterySelection}>
                          Clear
                        </button>
                      </div>
                    </div>
                    <div className="litchi-select-grid">
                      {Array.from({ length: batteryCount }, (_, idx) => {
                        const batteryIndex = idx + 1;
                        const selected = litchiSelectedBatteries.has(batteryIndex);
                        return (
                          <button
                            key={batteryIndex}
                            type="button"
                            className={`litchi-select-btn${selected ? ' selected' : ''}`}
                            onClick={() => toggleLitchiBattery(batteryIndex)}
                            aria-pressed={selected}
                          >
                            Battery {batteryIndex}
                          </button>
                        );
                      })}
                    </div>
                    <p className="litchi-muted">{litchiSelectionLabel}</p>
                  </div>
                )}
                {litchiIndicator && <p className="litchi-muted">{litchiIndicator}</p>}
                {litchiInlineOpen && !litchiConnected && (
                  <form className="litchi-form" onSubmit={handleLitchiConnect}>
                    <label htmlFor="litchi-inline-email">Email</label>
                    <input
                      id="litchi-inline-email"
                      type="email"
                      value={litchiEmail}
                      onChange={(event) => setLitchiEmail(event.target.value)}
                      placeholder="you@example.com"
                    />
                    <label htmlFor="litchi-inline-password">Password</label>
                    <input
                      id="litchi-inline-password"
                      type="password"
                      value={litchiPassword}
                      onChange={(event) => setLitchiPassword(event.target.value)}
                    />
                    {litchiStatus?.needsTwoFactor && (
                      <>
                        <label htmlFor="litchi-inline-2fa">Two-factor code</label>
                        <input
                          id="litchi-inline-2fa"
                          type="text"
                          value={litchiTwoFactor}
                          onChange={(event) => setLitchiTwoFactor(event.target.value)}
                          placeholder="123456"
                        />
                      </>
                    )}
                    {litchiConnectStatusMessage && <p className="litchi-muted" role="status">{litchiConnectStatusMessage}</p>}
                    <div className="litchi-modal-actions">
                      <button type="button" className="litchi-secondary" onClick={() => setLitchiConnectOpen(false)}>
                        Cancel
                      </button>
                      <button type="submit" className="litchi-primary" disabled={litchiConnecting}>
                        {litchiConnecting ? 'Connecting...' : 'Connect'}
                      </button>
                    </div>
                  </form>
                )}
                <div className="litchi-log-panel" aria-live="polite">
                  <h5>Activity</h5>
                  <div className="litchi-logs">
                    {litchiVisibleLogs.length === 0 && <span className="litchi-muted">No activity yet.</span>}
                    {litchiVisibleLogs.map((entry, index) => (
                      <div key={`${entry}-${index}`} className="litchi-log-entry">
                        {entry}
                      </div>
                    ))}
                  </div>
                  {litchiLogs.length > 5 && (
                    <button
                      type="button"
                      className="litchi-secondary"
                      onClick={() => setLitchiShowAllLogs(v => !v)}
                    >
                      {litchiShowAllLogs ? 'Show recent activity' : 'Show full activity'}
                    </button>
                  )}
                </div>
                {showManualDownloads && (
                  <>
                    <h5 className="text-fade-right" style={{ marginLeft: '6%', marginRight: '6%', width: 'auto' }}>
                      {optimizationLoading || downloadingBatteries.size > 0 ? processingMessage : 'Individual Battery Segments:'}
                    </h5>
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
                  </>
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
