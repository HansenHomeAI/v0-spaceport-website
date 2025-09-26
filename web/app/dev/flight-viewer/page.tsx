'use client';

import { ChangeEvent, DragEvent, useCallback, useMemo, useRef, useState } from 'react';
import FlightPath3DMap, {
  FlightPathColorMode,
  formatDistanceMeters,
  formatDurationSeconds,
  formatFeet,
  formatSlopePercent,
  formatSpeed,
} from 'components/FlightPath3DMap';
import { parseFlightCsv, type FlightPathAnalysis } from 'lib/flightPath';
import styles from './flight-viewer.module.css';

type LegendToken = {
  label: string;
  gradient: string;
};

export default function FlightViewerPage(): JSX.Element {
  const [analysis, setAnalysis] = useState<FlightPathAnalysis | null>(null);
  const [fileName, setFileName] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [colorMode, setColorMode] = useState<FlightPathColorMode>('slope');
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const googleMapsApiKey = process.env.NEXT_PUBLIC_GOOGLE_MAPS_API_KEY;
  const googleMapsMapId = process.env.NEXT_PUBLIC_GOOGLE_MAPS_MAP_ID;

  const handleFiles = useCallback(async (files: FileList | null) => {
    if (!files || files.length === 0) return;
    const file = files[0];
    try {
      const text = await file.text();
      const parsed = parseFlightCsv(text);
      setAnalysis(parsed);
      setFileName(file.name);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to parse CSV file.');
      setAnalysis(null);
      setFileName(null);
    } finally {
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }
    }
  }, []);

  const onFileChange = useCallback(
    (event: ChangeEvent<HTMLInputElement>) => {
      handleFiles(event.target.files);
    },
    [handleFiles]
  );

  const onDrop = useCallback(
    (event: DragEvent<HTMLLabelElement>) => {
      event.preventDefault();
      handleFiles(event.dataTransfer.files);
    },
    [handleFiles]
  );

  const onDragOver = useCallback((event: DragEvent<HTMLLabelElement>) => {
    event.preventDefault();
  }, []);

  const statsEntries = useMemo(() => {
    if (!analysis) return [];
    const { stats } = analysis;
    return [
      {
        label: 'Waypoints',
        value: stats.totalWaypoints.toLocaleString(),
      },
      {
        label: 'Horizontal Distance',
        value: formatDistanceMeters(stats.totalHorizontalDistanceMeters),
      },
      {
        label: '3D Distance',
        value: formatDistanceMeters(stats.total3dDistanceMeters),
      },
      {
        label: 'Vertical Gain',
        value: formatDistanceMeters(stats.totalVerticalGainMeters),
      },
      {
        label: 'Vertical Drop',
        value: formatDistanceMeters(stats.totalVerticalDropMeters),
      },
      {
        label: 'Altitude Range',
        value: `${formatFeet(stats.minAltitudeFt, 0)} → ${formatFeet(stats.maxAltitudeFt, 0)}`,
      },
      {
        label: 'Tightest Curve',
        value:
          stats.tightestCurveRadiusMeters !== null
            ? formatDistanceMeters(stats.tightestCurveRadiusMeters)
            : '—',
      },
      {
        label: 'Average Speed',
        value: formatSpeed(stats.averageSpeedMs),
      },
      {
        label: 'Est. Duration',
        value: formatDurationSeconds(stats.estimatedDurationSeconds),
      },
      {
        label: 'Max Slope',
        value: `${formatSlopePercent(stats.maxSlopePercent)} (${stats.maxSlopeDegrees?.toFixed(1) ?? '—'}°)`,
      },
      {
        label: 'Average Slope',
        value: formatSlopePercent(stats.averageSlopePercent),
      },
    ];
  }, [analysis]);

  const legend = useMemo<LegendToken>(() => {
    if (colorMode === 'curvature') {
      return {
        label: 'Color encodes curve tightness — red is tighter radius, green is wide arcs.',
        gradient: 'linear-gradient(90deg, #ff5a5a 0%, #f39c12 45%, #0fbf7d 100%)',
      };
    }
    return {
      label: 'Color encodes slope — green is flat, red is steep climb/descend.',
      gradient: 'linear-gradient(90deg, #0fbf7d 0%, #f1c40f 45%, #f95e5e 100%)',
    };
  }, [colorMode]);

  return (
    <div className={styles.viewerPage}>
      <header className={styles.header}>
        <div className={styles.titleRow}>
          <h1>Flight Path 3D Sandbox</h1>
          <span className={styles.badge}>Experimental Tools</span>
        </div>
        <p>
          Upload a generated Litchi CSV to inspect the precise 3D geometry of the planned mission.
          The viewer renders Google Maps photorealistic tiles with altitude-aware path overlays so
          you can confirm clearances, curvature, and camera behaviour before flying.
        </p>
      </header>

      <div className={styles.mainContent}>
        <aside className={styles.leftColumn}>
          <section className={styles.panel}>
            <h2>Load Flight CSV</h2>
            <label
              htmlFor="flightPathCsv"
              className={styles.dropZone}
              onDrop={onDrop}
              onDragOver={onDragOver}
            >
              <input
                id="flightPathCsv"
                ref={fileInputRef}
                type="file"
                accept=".csv,text/csv"
                onChange={onFileChange}
              />
              <strong>{fileName ?? 'Drop your CSV here or browse files'}</strong>
              <button type="button" onClick={() => fileInputRef.current?.click()}>
                Choose CSV
              </button>
              <small>We keep everything client-side. No uploads leave this tab.</small>
            </label>
            {error ? <div className={styles.errorBox}>{error}</div> : null}
            {!googleMapsApiKey ? (
              <small style={{ color: '#ff9aac' }}>
                Set <code>NEXT_PUBLIC_GOOGLE_MAPS_API_KEY</code> to enable the photorealistic map tiles.
              </small>
            ) : null}
            {googleMapsApiKey && !googleMapsMapId ? (
              <small style={{ color: 'rgba(235, 210, 120, 0.9)' }}>
                Tip: provide a <code>NEXT_PUBLIC_GOOGLE_MAPS_MAP_ID</code> linked to a Photorealistic 3D style for
                accurate terrain context.
              </small>
            ) : null}
            {analysis?.warnings?.length ? (
              <ul className={styles.warningList}>
                {analysis.warnings.map((warning) => (
                  <li key={warning}>⚠️ {warning}</li>
                ))}
              </ul>
            ) : null}
          </section>

          {analysis ? (
            <section className={styles.panel}>
              <h2>Flight Metrics</h2>
              <div className={styles.statsGrid}>
                {statsEntries.map((entry) => (
                  <div key={entry.label} className={styles.statCard}>
                    <span className={styles.statLabel}>{entry.label}</span>
                    <span className={styles.statValue}>{entry.value}</span>
                  </div>
                ))}
              </div>
            </section>
          ) : null}

          {analysis ? (
            <section className={styles.panel}>
              <h2>Waypoints Preview</h2>
              <table className={styles.waypointTable}>
                <thead>
                  <tr>
                    <th>#</th>
                    <th>Latitude</th>
                    <th>Longitude</th>
                    <th>Altitude (ft)</th>
                    <th>Slope %</th>
                    <th>Curve (ft)</th>
                    <th>Heading°</th>
                    <th>Speed (m/s)</th>
                  </tr>
                </thead>
                <tbody>
                  {analysis.waypoints.slice(0, 16).map((waypoint) => (
                    <tr key={waypoint.index}>
                      <td>{waypoint.index + 1}</td>
                      <td>{waypoint.latitude.toFixed(6)}</td>
                      <td>{waypoint.longitude.toFixed(6)}</td>
                      <td>{waypoint.altitudeFt.toFixed(1)}</td>
                      <td>{waypoint.slopePercentFromPrev?.toFixed(1) ?? '—'}</td>
                      <td>{waypoint.curveSizeFt.toFixed(2)}</td>
                      <td>{waypoint.headingDeg.toFixed(0)}</td>
                      <td>{waypoint.speedMs.toFixed(2)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
              {analysis.waypoints.length > 16 ? (
                <small>
                  Showing first 16 waypoints — CSV contains {analysis.waypoints.length.toLocaleString()}.
                </small>
              ) : null}
            </section>
          ) : null}
        </aside>

        <section className={styles.mapPanel}>
          <div className={styles.mapLegend}>
            <span className={styles.toggleGroup}>
              <button
                type="button"
                className={`${styles.toggleButton} ${colorMode === 'slope' ? styles.toggleButtonActive : ''}`}
                onClick={() => setColorMode('slope')}
              >
                Slope
              </button>
              <button
                type="button"
                className={`${styles.toggleButton} ${colorMode === 'curvature' ? styles.toggleButtonActive : ''}`}
                onClick={() => setColorMode('curvature')}
              >
                Curvature
              </button>
            </span>
            <span>
              <span className={styles.legendSwatch} style={{ background: legend.gradient }} />
              {legend.label}
            </span>
          </div>

          {analysis ? (
            <FlightPath3DMap
              key={`${fileName ?? 'no-file'}-${colorMode}`}
              waypoints={analysis.waypoints}
              poi={analysis.poi}
              bounds={analysis.bounds}
              center={analysis.center}
              colorMode={colorMode}
              className={styles.mapCanvas}
            />
          ) : (
            <div className={styles.mapCallout}>
              Upload a CSV to render the 3D path. We recommend using the latest generator output so the
              curvature, POI focus, and altitude ladders match your planned flight.
            </div>
          )}
        </section>
      </div>
    </div>
  );
}
