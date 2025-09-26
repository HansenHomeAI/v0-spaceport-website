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

  type StatsEntry = {
    label: string;
    value: string;
    testId?: string;
  };

  const statsEntries = useMemo<StatsEntry[]>(() => {
    if (!analysis) return [];
    const { stats } = analysis;
    return [
      {
        label: 'Waypoints',
        value: stats.totalWaypoints.toLocaleString(),
        testId: 'metric-waypoints',
      },
      {
        label: 'Horizontal Distance',
        value: formatDistanceMeters(stats.totalHorizontalDistanceMeters),
        testId: 'metric-horizontal-distance',
      },
      {
        label: '3D Distance',
        value: formatDistanceMeters(stats.total3dDistanceMeters),
        testId: 'metric-3d-distance',
      },
      {
        label: 'Vertical Gain',
        value: formatDistanceMeters(stats.totalVerticalGainMeters),
        testId: 'metric-vertical-gain',
      },
      {
        label: 'Vertical Drop',
        value: formatDistanceMeters(stats.totalVerticalDropMeters),
        testId: 'metric-vertical-drop',
      },
      {
        label: 'Altitude Range',
        value: `${formatFeet(stats.minAltitudeFt, 0)} → ${formatFeet(stats.maxAltitudeFt, 0)}`,
        testId: 'metric-altitude-range',
      },
      {
        label: 'Tightest Curve',
        value:
          stats.tightestCurveRadiusMeters !== null
            ? formatDistanceMeters(stats.tightestCurveRadiusMeters)
            : '—',
        testId: 'metric-tightest-curve',
      },
      {
        label: 'Average Speed',
        value: formatSpeed(stats.averageSpeedMs),
        testId: 'metric-average-speed',
      },
      {
        label: 'Est. Duration',
        value: formatDurationSeconds(stats.estimatedDurationSeconds),
        testId: 'metric-estimated-duration',
      },
      {
        label: 'Max Slope',
        value: `${formatSlopePercent(stats.maxSlopePercent)} (${stats.maxSlopeDegrees?.toFixed(1) ?? '—'}°)`,
        testId: 'metric-max-slope',
      },
      {
        label: 'Average Slope',
        value: formatSlopePercent(stats.averageSlopePercent),
        testId: 'metric-average-slope',
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
          <h1>Flight Path 3D Viewer</h1>
          <span className={styles.badge}>internal</span>
        </div>
        <p>
          Inspect generated flight plans in a photorealistic 3D context. Drop a Litchi CSV to review
          actual curvature, altitude envelopes, and POI alignment before flying.
        </p>
      </header>

      <section className={styles.layout}>
        <div className={styles.mapStage}>
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
            <FlightPath3DMap
              key="empty-map"
              waypoints={[]}
              poi={null}
              bounds={null}
              center={null}
              colorMode={colorMode}
              className={styles.mapCanvas}
            />
          )}

          <aside className={styles.mapOverlay}>
            <div>
              <h2 className={styles.panelTitle}>Load Flight CSV</h2>
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
                <small>Processing stays in-browser. No files are uploaded.</small>
              </label>
              {error ? <div className={styles.errorBox}>{error}</div> : null}
            </div>

            <div className={styles.overlayFooter}>
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

              <span className={styles.legendRow}>
                <span className={styles.legendSwatch} style={{ background: legend.gradient }} />
                {legend.label}
              </span>

              {!googleMapsApiKey ? (
                <small>
                  Set <code>NEXT_PUBLIC_GOOGLE_MAPS_API_KEY</code> to stream Photorealistic 3D tiles.
                </small>
              ) : null}
              {googleMapsApiKey && !googleMapsMapId ? (
                <small>
                  Tip: provide a <code>NEXT_PUBLIC_GOOGLE_MAPS_MAP_ID</code> linked to a 3D style for best
                  results.
                </small>
              ) : null}

              {analysis?.warnings?.length ? (
                <ul className={styles.warningList}>
                  {analysis.warnings.map((warning) => (
                    <li key={warning}>{warning}</li>
                  ))}
                </ul>
              ) : null}
            </div>
          </aside>

          {!analysis ? (
            <div className={styles.mapCallout}>
              Upload a CSV to render the 3D path. Use generator output so curvature, POI focus, and altitude
              ladders match your planned flight.
            </div>
          ) : null}
        </div>

        {analysis ? (
          <>
            <h2 className={styles.srOnly}>Flight Metrics</h2>
            <div className={styles.metricsStrip}>
              {statsEntries.map((entry) => (
                <div
                  key={entry.label}
                  className={styles.statCard}
                  data-testid={entry.testId}
                >
                  <span className={styles.statLabel}>{entry.label}</span>
                  <span className={styles.statValue}>{entry.value}</span>
                </div>
              ))}
            </div>

            <section className={styles.waypointsPanel}>
              <h2 className={styles.panelHeading}>Waypoints Preview</h2>
              <div className={styles.tableScroll}>
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
                    {analysis.waypoints.slice(0, 32).map((waypoint) => (
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
              </div>
              {analysis.waypoints.length > 32 ? (
                <small>
                  Showing first 32 waypoints — CSV contains {analysis.waypoints.length.toLocaleString()}.
                </small>
              ) : null}
            </section>
          </>
        ) : null}
      </section>
    </div>
  );
}
