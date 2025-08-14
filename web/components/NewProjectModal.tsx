"use client";
import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";

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

  const API_ENHANCED_BASE = 'https://7bidiow2t9.execute-api.us-west-2.amazonaws.com/prod';
  const API_UPLOAD = {
    START_UPLOAD: 'https://o7d0i4to5a.execute-api.us-west-2.amazonaws.com/prod/start-multipart-upload',
    GET_PRESIGNED_URL: 'https://o7d0i4to5a.execute-api.us-west-2.amazonaws.com/prod/get-presigned-url',
    COMPLETE_UPLOAD: 'https://o7d0i4to5a.execute-api.us-west-2.amazonaws.com/prod/complete-multipart-upload',
    SAVE_SUBMISSION: 'https://o7d0i4to5a.execute-api.us-west-2.amazonaws.com/prod/save-submission',
    START_ML_PROCESSING: 'https://3xzfdyvwpd.execute-api.us-west-2.amazonaws.com/prod/start-job',
  } as const;

  const CHUNK_SIZE = 24 * 1024 * 1024; // 24MB
  const MAX_FILE_SIZE = 5 * 1024 * 1024 * 1024; // 5GB

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

  const [optimizedParams, setOptimizedParams] = useState<OptimizedParams | null>(null);
  const [optimizationLoading, setOptimizationLoading] = useState<boolean>(false);
  const [batteryDownloading, setBatteryDownloading] = useState<number | null>(null);

  const [error, setError] = useState<string | null>(null);
  const [toast, setToast] = useState<{ type: 'success' | 'error'; message: string } | null>(null);

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

  // Reset state when opening/closing
  useEffect(() => {
    if (!open) return;
    setError(null);
    setUploadProgress(0);
    setUploadLoading(false);
    setMlLoading(false);
    setOptimizedParams(null);
    setBatteryDownloading(null);
    setSetupOpen(true);
    setUploadOpen(false);
    setToast(null);
    // If editing, hydrate fields from project
    if (project) {
      setProjectTitle(project.title || 'Untitled');
      const params = project.params || {};
      setAddressSearch(params.address || '');
      setBatteryMinutes(params.batteryMinutes || '');
      setNumBatteries(params.batteries || '');
      setMinHeightFeet(params.minHeight || '');
      setMaxHeightFeet(params.maxHeight || '');
      setContactEmail(project.email || '');
      setStatus(project.status || 'draft');
      setCurrentProjectId(project.projectId || null);
    } else {
      setStatus('draft');
      setCurrentProjectId(null);
    }
  }, [open]);

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
          markerRef.current = new mapboxgl.default.Marker({ anchor: 'bottom' })
            .setLngLat([lng, lat])
            .addTo(map);
          // Fill address input with coordinates formatted
          setAddressSearch(`${lat.toFixed(6)}, ${lng.toFixed(6)}`);
          // Invalidate previous optimization
          setOptimizedParams(null);
        });
        mapRef.current = map;
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
  }, [open]);

  const canOptimize = useMemo(() => {
    const coords = selectedCoordsRef.current;
    const minutes = parseInt(batteryMinutes || '');
    const batteries = parseInt(numBatteries || '');
    return Boolean(coords && minutes && batteries);
  }, [batteryMinutes, numBatteries]);

  const handleOptimize = useCallback(async () => {
    if (!canOptimize) return;
    setOptimizationLoading(true);
    setError(null);
    try {
      const coords = selectedCoordsRef.current!;
      const minutes = parseInt(batteryMinutes);
      const batteries = parseInt(numBatteries);

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
      setOptimizedParams(params);
    } catch (e: any) {
      setError(e?.message || 'Optimization failed');
    } finally {
      setOptimizationLoading(false);
    }
  }, [API_ENHANCED_BASE, batteryMinutes, numBatteries, minHeightFeet, maxHeightFeet, canOptimize]);

  const downloadBatteryCsv = useCallback(async (batteryIndex1: number) => {
    if (!optimizedParams) {
      setError('Please optimize first');
      return;
    }
    setBatteryDownloading(batteryIndex1);
    setError(null);
    try {
      const res = await fetch(`${API_ENHANCED_BASE}/api/csv/battery/${batteryIndex1}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(optimizedParams),
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
    } catch (e: any) {
      setError(e?.message || 'CSV download failed');
    } finally {
      setBatteryDownloading(null);
    }
  }, [API_ENHANCED_BASE, optimizedParams, projectTitle]);

  // Save metadata changes for existing project
  const handleSaveProject = useCallback(async () => {
    try {
      const { Auth } = await import('aws-amplify');
      const session = await Auth.currentSession();
      const idToken = session.getIdToken().getJwtToken();
      const apiBase = (process.env.NEXT_PUBLIC_PROJECTS_API_URL || 'https://gcqqr7bwpg.execute-api.us-west-2.amazonaws.com/prod/projects').replace(/\/$/, '');
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
        },
      };
      const url = currentProjectId ? `${apiBase}/${encodeURIComponent(currentProjectId)}` : `${apiBase}`;
      const method = currentProjectId ? 'PATCH' : 'POST';
      const res = await fetch(url, {
        method,
        headers: { 'content-type': 'application/json', Authorization: `Bearer ${idToken}` },
        body: JSON.stringify(body),
      });
      if (!res.ok) throw new Error(`Save failed: ${res.status}`);
      // Capture created id on first POST
      if (!currentProjectId) {
        const data = await res.json().catch(() => ({} as any));
        const created = (data && (data.project || data)) as any;
        if (created && created.projectId) setCurrentProjectId(created.projectId);
      }
      onSaved?.();
    } catch (e: any) {
      setError(e?.message || 'Failed to save project');
    }
  }, [addressSearch, batteryMinutes, currentProjectId, maxHeightFeet, minHeightFeet, numBatteries, onSaved, projectTitle, status]);

  // Debounced autosave on any change
  useEffect(() => {
    if (!open) return;
    const t = setTimeout(() => {
      handleSaveProject();
    }, 600);
    return () => clearTimeout(t);
  }, [open, projectTitle, addressSearch, batteryMinutes, numBatteries, minHeightFeet, maxHeightFeet, status, handleSaveProject]);

  // Address search via Mapbox Geocoding
  const handleAddressEnter = useCallback(async (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key !== 'Enter') return;
    e.preventDefault();
    const query = addressSearch.trim();
    if (!query || !mapRef.current) return;
    try {
      const res = await fetch(`https://api.mapbox.com/geocoding/v5/mapbox.places/${encodeURIComponent(query)}.json?access_token=${MAPBOX_TOKEN}&limit=1`);
      const data = await res.json();
      if (data?.features?.length) {
        const [lng, lat] = data.features[0].center;
        mapRef.current.flyTo({ center: [lng, lat], zoom: 15, duration: 2000 });
        selectedCoordsRef.current = { lat, lng };
        // place marker
        const mapboxgl = (await import('mapbox-gl')).default;
        if (markerRef.current) markerRef.current.remove();
        markerRef.current = new mapboxgl.Marker({ anchor: 'bottom' }).setLngLat([lng, lat]).addTo(mapRef.current);
        // keep input text as typed address
      }
    } catch (err) {
      // ignore
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
    if (selectedFile.size > MAX_FILE_SIZE) return 'File size exceeds 5GB limit';
    return null;
  }, [propertyTitle, contactEmail, selectedFile]);

  const startUpload = useCallback(async () => {
    const validationError = validateUpload();
    if (validationError) {
      setError(validationError);
      return;
    }
    if (!selectedFile) return;
    setUploadLoading(true);
    setMlLoading(false);
    setError(null);
    setUploadProgress(0);
    try {
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

      // upload chunks
      const totalChunks = Math.ceil(selectedFile.size / CHUNK_SIZE);
      const parts: Array<{ ETag: string | null; PartNumber: number }> = [];
      for (let i = 0; i < totalChunks; i++) {
        const start = i * CHUNK_SIZE;
        const end = Math.min(start + CHUNK_SIZE, selectedFile.size);
        const chunk = selectedFile.slice(start, end);
        const partNumber = i + 1;
        const urlRes = await fetch(API_UPLOAD.GET_PRESIGNED_URL, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            uploadId: init.uploadId,
            bucketName: init.bucketName,
            objectKey: init.objectKey,
            partNumber,
          }),
        });
        if (!urlRes.ok) throw new Error(`Failed to get upload URL for part ${partNumber}`);
        const { url } = await urlRes.json();
        const putRes = await fetch(url, { method: 'PUT', body: chunk });
        if (!putRes.ok) throw new Error(`Failed to upload part ${partNumber}`);
        const etag = putRes.headers.get('ETag');
        parts.push({ ETag: etag, PartNumber: partNumber });
        setUploadProgress(((partNumber) / totalChunks) * 100);
      }

      // complete multipart
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
      setToast({ type: 'success', message: `Upload successful. ML processing started. Job ID: ${ml.jobId || 'N/A'}` });

      // Persist a project stub for this user
      try {
        const { Auth } = await import('aws-amplify');
        const session = await Auth.currentSession();
        const idToken = session.getIdToken().getJwtToken();
        const api = process.env.NEXT_PUBLIC_PROJECTS_API_URL || 'https://gcqqr7bwpg.execute-api.us-west-2.amazonaws.com/prod/projects';
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
      setError(msg);
      setToast({ type: 'error', message: msg });
    } finally {
      setUploadLoading(false);
      setMlLoading(false);
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
        {/* Project Status quick stepper */}
        <div className="category-outline">
          <div className="popup-section" style={{padding: 12}}>
            <h4>Project Status</h4>
            <div style={{display:'flex', gap:8, flexWrap:'wrap', justifyContent:'center', marginTop:8}}>
              {[
                ['draft','Start'],
                ['path_downloaded','Paths Downloaded'],
                ['photos_uploaded','Photos Uploaded'],
                ['processing','Processing'],
                ['delivered','Delivered'],
              ].map(([value,label]) => (
                <button key={value} type="button" onClick={() => setStatus(value)} style={{
                  padding:'8px 12px', borderRadius:999, border:'1px solid rgba(255,255,255,0.2)',
                  background: status===value ? 'rgba(255,255,255,0.2)' : 'transparent', color:'#fff', cursor:'pointer'
                }}>{label}</button>
              ))}
            </div>
          </div>
        </div>
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
              <div id="map-container" className="map-container" ref={mapContainerRef}>
                <button className="expand-button" id="expand-button">
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
                  <div className="popup-input-wrapper">
                    <span className="input-icon time"></span>
                    <input
                      type="number"
                      className="text-fade-right"
                      placeholder="Duration"
                      value={batteryMinutes}
                      onChange={(e) => { setBatteryMinutes(e.target.value); setOptimizedParams(null); }}
                      min={10}
                      max={60}
                    />
                  </div>
                  <div className="popup-input-wrapper">
                    <span className="input-icon number"></span>
              <input
                      type="number"
                      className="text-fade-right"
                      placeholder="Quantity"
                      value={numBatteries}
                      onChange={(e) => { setNumBatteries(e.target.value); setOptimizedParams(null); }}
                      min={1}
                      max={12}
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
                  <div className="popup-input-wrapper">
                    <span className="input-icon minimum"></span>
              <input
                      type="number"
                      className="text-fade-right"
                      placeholder="Minimum"
                      value={minHeightFeet}
                      onChange={(e) => { setMinHeightFeet(e.target.value); setOptimizedParams(null); }}
                    />
                  </div>
                  <div className="popup-input-wrapper">
                    <span className="input-icon maximum"></span>
              <input
                      type="number"
                      className="text-fade-right"
                      placeholder="Maximum"
                      value={maxHeightFeet}
                      onChange={(e) => { setMaxHeightFeet(e.target.value); setOptimizedParams(null); }}
                    />
                  </div>
                </div>
              </div>
            </div>

            {/* Individual Battery Segments (legacy-correct UI) */}
            <div className="battery-downloads" style={{ display: 'block', marginTop: 12 }}>
              <div className="popup-section">
                <h4>Individual Battery Segments:</h4>
              </div>
              <div id="batteryButtons" className="flight-path-grid">
                {Array.from({ length: batteryCount }).map((_, idx) => (
                  <button
                    key={idx}
                    className={`flight-path-download-btn${batteryDownloading === idx + 1 ? ' loading' : ''}`}
                    onClick={async () => {
                      // Auto-run optimization on first click if needed
                      if (!optimizedParams) {
                        if (!canOptimize) {
                          setError('Please set location and battery params first');
                          return;
                        }
                        await handleOptimize();
                      }
                      await downloadBatteryCsv(idx + 1);
                    }}
                    disabled={batteryDownloading !== null}
                  >
                    <span className={`download-icon${batteryDownloading === idx + 1 ? ' loading' : ''}`}></span>
                    Battery {idx + 1}
                  </button>
                ))}
              </div>
            </div>
          </div>
          )}
        </div>

        {/* SECTION 2: PROPERTY UPLOAD */}
        <div className={`accordion-section${uploadOpen ? ' active' : ''}`} data-section="upload">
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
                  <div className="upload-progress-text">{Math.round(uploadProgress)}%</div>
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
                    <div className="upload-progress-bar" style={{ width: `${uploadProgress}%` }}></div>
                  </div>
                </div>
              </div>

              {error && <p style={{ color: '#ff6b6b', marginTop: 8 }}>{error}</p>}
            </div>
          </div>
          )}
        </div>
        {/* Autosave enabled; no explicit Save button */}
      </div>
    </div>
  );
}


