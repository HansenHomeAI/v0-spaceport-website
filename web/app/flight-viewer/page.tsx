"use client";

import { ChangeEvent, useCallback, useMemo, useState } from "react";
import Papa from "papaparse";
import { Canvas } from "@react-three/fiber";
import { OrbitControls, Line, PerspectiveCamera, Grid } from "@react-three/drei";
import * as THREE from "three";

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
  localPosition: [number, number, number];
}

interface PoiData {
  latitude: number;
  longitude: number;
  altitudeFt: number;
  altitudeMode: number | null;
  localPosition: [number, number, number];
}

interface FlightData {
  name: string;
  samples: ProcessedSample[];
  poi: PoiData | null;
}

const EARTH_RADIUS_METERS = 6_378_137;
const FEET_TO_METERS = 0.3048;

function toNumber(value: unknown): number {
  if (typeof value === "number" && Number.isFinite(value)) {
    return value;
  }
  if (typeof value === "string" && value.trim().length) {
    const parsed = Number(value);
    return Number.isFinite(parsed) ? parsed : Number.NaN;
  }
  return Number.NaN;
}

function toOptionalNumber(value: unknown): number | null {
  const parsed = toNumber(value);
  return Number.isFinite(parsed) ? parsed : null;
}

function sanitizeRow(row: RawFlightRow): PreparedRow | null {
  const latitude = toNumber(row.latitude);
  const longitude = toNumber(row.longitude);
  const altitudeFt = toNumber(row["altitude(ft)"]);

  if (!Number.isFinite(latitude) || !Number.isFinite(longitude) || !Number.isFinite(altitudeFt)) {
    return null;
  }

  return {
    latitude,
    longitude,
    altitudeFt,
    headingDeg: toOptionalNumber(row["heading(deg)"] ?? row.headingdeg),
    curveSizeFt: toOptionalNumber(row["curvesize(ft)"] ?? row.curvesizeft),
    rotationDir: toOptionalNumber(row.rotationdir),
    gimbalMode: toOptionalNumber(row.gimbalmode),
    gimbalPitchAngle: toOptionalNumber(row.gimbalpitchangle),
    altitudeMode: toOptionalNumber(row.altitudemode),
    speedMs: toOptionalNumber(row["speed(m/s)"] ?? row.speedms),
    poiLatitude: toOptionalNumber(row.poi_latitude),
    poiLongitude: toOptionalNumber(row.poi_longitude),
    poiAltitudeFt: toOptionalNumber(row["poi_altitude(ft)"] ?? row.poi_altitudeft),
    poiAltitudeMode: toOptionalNumber(row.poi_altitudemode),
    photoTimeInterval: toOptionalNumber(row.photo_timeinterval),
    photoDistInterval: toOptionalNumber(row.photo_distinterval),
  };
}

function degreesToRadians(value: number): number {
  return (value * Math.PI) / 180;
}

function buildLocalFrame(samples: PreparedRow[]): { samples: ProcessedSample[]; poi: PoiData | null } {
  if (!samples.length) {
    return { samples: [], poi: null };
  }

  const referenceLat = degreesToRadians(samples[0].latitude);
  const referenceLon = degreesToRadians(samples[0].longitude);
  const cosReferenceLat = Math.cos(referenceLat);

  const toLocal = (lat: number, lon: number, altitudeFt: number): [number, number, number] => {
    const latRad = degreesToRadians(lat);
    const lonRad = degreesToRadians(lon);
    const x = (lonRad - referenceLon) * cosReferenceLat * EARTH_RADIUS_METERS;
    const z = (latRad - referenceLat) * EARTH_RADIUS_METERS;
    const y = altitudeFt * FEET_TO_METERS;
    return [x, y, -z];
  };

  const processedSamples: ProcessedSample[] = samples.map((sample, index) => ({
    ...sample,
    index,
    localPosition: toLocal(sample.latitude, sample.longitude, sample.altitudeFt),
  }));

  const firstPoiSource = samples.find(sample =>
    Number.isFinite(sample.poiLatitude ?? Number.NaN) && Number.isFinite(sample.poiLongitude ?? Number.NaN)
  );

  let poi: PoiData | null = null;
  if (firstPoiSource && firstPoiSource.poiLatitude !== null && firstPoiSource.poiLongitude !== null) {
    const poiAltitudeFt = firstPoiSource.poiAltitudeFt ?? samples[0].altitudeFt;
    poi = {
      latitude: firstPoiSource.poiLatitude,
      longitude: firstPoiSource.poiLongitude,
      altitudeFt: poiAltitudeFt,
      altitudeMode: firstPoiSource.poiAltitudeMode,
      localPosition: toLocal(firstPoiSource.poiLatitude, firstPoiSource.poiLongitude, poiAltitudeFt),
    };
  }

  return { samples: processedSamples, poi };
}

function computeStats(flight: FlightData | null) {
  if (!flight) {
    return null;
  }

  const vectors = flight.samples.map(sample => new THREE.Vector3(...sample.localPosition));
  if (!vectors.length) {
    return null;
  }

  const totalDistanceMeters = vectors.reduce((acc, point, index) => {
    if (index === 0) {
      return 0;
    }
    return acc + point.distanceTo(vectors[index - 1]);
  }, 0);

  const altitudeValues = flight.samples.map(sample => sample.altitudeFt);
  const maxAltitudeFt = Math.max(...altitudeValues);
  const minAltitudeFt = Math.min(...altitudeValues);

  const speedValues = flight.samples
    .map(sample => sample.speedMs)
    .filter((value): value is number => value !== null && Number.isFinite(value));

  const averageSpeedMs = speedValues.length
    ? speedValues.reduce((acc, value) => acc + value, 0) / speedValues.length
    : null;

  return {
    totalDistanceMeters,
    totalDistanceFeet: totalDistanceMeters / FEET_TO_METERS,
    maxAltitudeFt,
    minAltitudeFt,
    averageSpeedMs,
  };
}

function formatNumber(value: number, fractionDigits = 1): string {
  return new Intl.NumberFormat("en-US", {
    maximumFractionDigits: fractionDigits,
  }).format(value);
}

function formatSpeed(speedMs: number | null): string {
  if (speedMs === null) {
    return "n/a";
  }
  const mph = speedMs * 2.23694;
  return `${formatNumber(speedMs, 2)} m/s (${formatNumber(mph, 1)} mph)`;
}

interface FlightPathSceneProps {
  samples: ProcessedSample[];
  poi: PoiData | null;
}

function FlightPathScene({ samples, poi }: FlightPathSceneProps): JSX.Element {
  const vectors = useMemo(() => samples.map(sample => new THREE.Vector3(...sample.localPosition)), [samples]);

  const smoothPath = useMemo(() => {
    if (vectors.length < 2) {
      return vectors;
    }
    const curve = new THREE.CatmullRomCurve3(vectors, false, "centripetal", 0.25);
    const density = Math.min(1_200, Math.max(vectors.length * 16, 200));
    return curve.getPoints(density);
  }, [vectors]);

  const { center, radius } = useMemo(() => {
    if (!vectors.length) {
      return { center: new THREE.Vector3(0, 0, 0), radius: 50 };
    }
    const box = new THREE.Box3().setFromPoints(vectors);
    const dimensions = box.getSize(new THREE.Vector3());
    const computedRadius = Math.max(dimensions.x, dimensions.y, dimensions.z) * 0.75;
    return {
      center: box.getCenter(new THREE.Vector3()),
      radius: Math.max(computedRadius, 30),
    };
  }, [vectors]);

  const cameraPosition = useMemo(() => {
    return [center.x + radius * 1.8, center.y + radius * 1.1, center.z + radius * 1.8];
  }, [center, radius]);

  return (
    <Canvas className="flight-viewer__canvas-inner" shadows>
      <color attach="background" args={["#080810"]} />
      <fog attach="fog" args={["#080810", radius * 0.5, radius * 3.5]} />
      <ambientLight intensity={0.6} />
      <directionalLight position={[radius, radius * 1.5, radius]} intensity={1.1} castShadow />
      <PerspectiveCamera makeDefault position={cameraPosition as [number, number, number]} fov={48} near={0.1} far={radius * 10} />
      <OrbitControls makeDefault target={[center.x, center.y, center.z]} maxDistance={radius * 5} minDistance={radius * 0.2} />
      <Grid args={[radius * 4, radius * 4, 20, 20]} position={[center.x, 0, center.z]} sectionColor={"#1c1c24"} cellColor={"#11111a"} infiniteGrid fadeDistance={radius * 1.5} fadeStrength={2} />

      {smoothPath.length >= 2 && (
        <Line
          points={smoothPath}
          color="#4f83ff"
          lineWidth={2.4}
          transparent
          opacity={0.95}
        />
      )}

      {samples.map(sample => (
        <mesh key={sample.index} position={sample.localPosition} castShadow>
          <sphereGeometry args={[Math.max(radius * 0.01, 0.6), 16, 16]} />
          <meshStandardMaterial color="#ffffff" emissive="#1c2e66" emissiveIntensity={0.4} />
        </mesh>
      ))}

      {poi && (
        <mesh position={poi.localPosition} castShadow>
          <sphereGeometry args={[Math.max(radius * 0.012, 0.8), 24, 24]} />
          <meshStandardMaterial color="#ff7a18" emissive="#ff7a18" emissiveIntensity={0.6} />
        </mesh>
      )}

      <mesh
        rotation={[-Math.PI / 2, 0, 0]}
        position={[center.x, center.y - radius * 0.05, center.z]}
        receiveShadow
      >
        <planeGeometry args={[radius * 6, radius * 6]} />
        <meshStandardMaterial color="#05050a" opacity={0.85} transparent />
      </mesh>
    </Canvas>
  );
}

export default function FlightViewerPage(): JSX.Element {
  const [flight, setFlight] = useState<FlightData | null>(null);
  const [status, setStatus] = useState<string | null>(null);
  const [isParsing, setIsParsing] = useState(false);

  const onFileSelected = useCallback((event: ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) {
      return;
    }
    setIsParsing(true);
    setStatus(null);

    Papa.parse<RawFlightRow>(file, {
      header: true,
      skipEmptyLines: true,
      dynamicTyping: true,
      complete: result => {
        setIsParsing(false);
        if (result.errors.length) {
          setFlight(null);
          setStatus(`CSV parse error: ${result.errors[0].message}`);
          return;
        }

        const prepared = result.data
          .map(sanitizeRow)
          .filter((value): value is PreparedRow => value !== null);

        if (!prepared.length) {
          setFlight(null);
          setStatus("No valid flight samples were found in the file.");
          return;
        }

        const { samples, poi } = buildLocalFrame(prepared);
        setFlight({
          name: file.name,
          samples,
          poi,
        });
      },
      error: err => {
        setIsParsing(false);
        setFlight(null);
        setStatus(`Unable to read file: ${err.message}`);
      },
    });
  }, []);

  const stats = useMemo(() => computeStats(flight), [flight]);

  return (
    <main className="flight-viewer">
      <div className="flight-viewer__intro">
        <h1>Flight Viewer</h1>
        <p>Upload a mission CSV to inspect path curvature, altitude changes, and points of interest in 3D.</p>
      </div>

      <section className="flight-viewer__content">
        <aside className="flight-viewer__sidebar">
          <label className="flight-viewer__upload">
            <span className="flight-viewer__upload-title">Drag or choose CSV</span>
            <span className="flight-viewer__upload-hint">Latitude, longitude, altitude, heading, and POI columns are detected automatically.</span>
            <input
              type="file"
              accept=".csv,text/csv"
              onChange={onFileSelected}
              disabled={isParsing}
            />
          </label>

          {isParsing && <p className="flight-viewer__status">Parsing file…</p>}
          {status && !isParsing && <p className="flight-viewer__status flight-viewer__status--error">{status}</p>}

          {flight && (
            <div className="flight-viewer__details">
              <h2>{flight.name}</h2>
              <dl>
                <div>
                  <dt>Samples</dt>
                  <dd>{flight.samples.length}</dd>
                </div>
                {stats && (
                  <>
                    <div>
                      <dt>Total track length</dt>
                      <dd>
                        {formatNumber(stats.totalDistanceMeters, 1)} m
                        <span> ({formatNumber(stats.totalDistanceFeet, 0)} ft)</span>
                      </dd>
                    </div>
                    <div>
                      <dt>Altitude span</dt>
                      <dd>
                        {formatNumber(stats.minAltitudeFt, 0)}–{formatNumber(stats.maxAltitudeFt, 0)} ft
                      </dd>
                    </div>
                    <div>
                      <dt>Avg. speed</dt>
                      <dd>{formatSpeed(stats.averageSpeedMs)}</dd>
                    </div>
                  </>
                )}
                {flight.samples[0]?.photoTimeInterval !== null && (
                  <div>
                    <dt>Photo cadence</dt>
                    <dd>
                      {flight.samples[0].photoTimeInterval ?? "—"} s / {flight.samples[0].photoDistInterval ?? "—"} m
                    </dd>
                  </div>
                )}
                {flight.poi && (
                  <div>
                    <dt>POI</dt>
                    <dd>
                      {flight.poi.latitude.toFixed(6)}, {flight.poi.longitude.toFixed(6)}
                      <span> ({formatNumber(flight.poi.altitudeFt, 0)} ft)</span>
                    </dd>
                  </div>
                )}
              </dl>
            </div>
          )}

          {!flight && !isParsing && (
            <div className="flight-viewer__details flight-viewer__details--placeholder">
              <h2>How it works</h2>
              <ul>
                <li>Exports from DJI or Litchi style CSVs are supported out of the box.</li>
                <li>We project the mission into a local ENU frame so you can inspect the path curvature accurately.</li>
                <li>The viewer highlights altitude changes, individual waypoints, and POIs.</li>
              </ul>
            </div>
          )}
        </aside>

        <div className="flight-viewer__visualizer" aria-live="polite">
          {flight ? (
            <FlightPathScene samples={flight.samples} poi={flight.poi} />
          ) : (
            <div className="flight-viewer__placeholder">
              <div className="flight-viewer__placeholder-inner">
                <p>Select a flight plan to render its 3D trajectory.</p>
              </div>
            </div>
          )}
        </div>
      </section>

      <style jsx>{`
        .flight-viewer {
          display: flex;
          flex-direction: column;
          gap: 2rem;
          padding: 4rem clamp(1.5rem, 4vw, 4rem);
          color: #f5f6fb;
          background: radial-gradient(circle at top, #0b0b1a, #030309 55%);
          min-height: calc(100vh - 160px);
        }

        .flight-viewer__intro h1 {
          margin: 0;
          font-size: clamp(2rem, 2.8vw, 3rem);
          font-weight: 600;
        }

        .flight-viewer__intro p {
          margin-top: 0.5rem;
          max-width: 40rem;
          line-height: 1.5;
          color: rgba(220, 224, 255, 0.75);
        }

        .flight-viewer__content {
          display: grid;
          grid-template-columns: minmax(260px, 320px) 1fr;
          gap: clamp(1.5rem, 4vw, 3rem);
          align-items: stretch;
        }

        .flight-viewer__sidebar {
          display: flex;
          flex-direction: column;
          gap: 1.5rem;
          backdrop-filter: blur(12px);
        }

        .flight-viewer__upload {
          border: 1px dashed rgba(99, 104, 149, 0.6);
          border-radius: 16px;
          padding: 1.5rem;
          display: flex;
          flex-direction: column;
          gap: 0.5rem;
          background: rgba(13, 16, 42, 0.35);
          position: relative;
          cursor: pointer;
          transition: border-color 0.2s ease, transform 0.2s ease;
        }

        .flight-viewer__upload:hover {
          border-color: #4f83ff;
          transform: translateY(-2px);
        }

        .flight-viewer__upload input {
          position: absolute;
          inset: 0;
          opacity: 0;
          cursor: pointer;
        }

        .flight-viewer__upload-title {
          font-weight: 600;
          letter-spacing: 0.02em;
        }

        .flight-viewer__upload-hint {
          font-size: 0.9rem;
          color: rgba(207, 211, 255, 0.7);
        }

        .flight-viewer__status {
          margin: 0;
          font-size: 0.9rem;
          color: rgba(207, 211, 255, 0.85);
        }

        .flight-viewer__status--error {
          color: #ff766a;
        }

        .flight-viewer__details {
          background: rgba(11, 14, 36, 0.55);
          padding: 1.25rem 1.5rem;
          border-radius: 16px;
          display: flex;
          flex-direction: column;
          gap: 1rem;
          border: 1px solid rgba(80, 82, 126, 0.3);
        }

        .flight-viewer__details h2 {
          margin: 0;
          font-size: 1.1rem;
          font-weight: 600;
        }

        .flight-viewer__details dl {
          display: grid;
          grid-template-columns: max-content 1fr;
          gap: 0.5rem 0.75rem;
          margin: 0;
        }

        .flight-viewer__details dt {
          font-size: 0.85rem;
          text-transform: uppercase;
          letter-spacing: 0.08em;
          color: rgba(174, 180, 228, 0.7);
        }

        .flight-viewer__details dd {
          margin: 0;
          font-size: 0.95rem;
          color: rgba(231, 234, 255, 0.92);
        }

        .flight-viewer__details span {
          display: inline-block;
          margin-left: 0.25rem;
          color: rgba(174, 180, 228, 0.7);
        }

        .flight-viewer__details--placeholder ul {
          margin: 0;
          padding-left: 1.1rem;
          display: flex;
          flex-direction: column;
          gap: 0.5rem;
          font-size: 0.95rem;
          color: rgba(210, 214, 250, 0.8);
        }

        .flight-viewer__visualizer {
          position: relative;
          border-radius: 24px;
          overflow: hidden;
          background: linear-gradient(160deg, rgba(12, 18, 52, 0.8), rgba(4, 6, 18, 0.95));
          border: 1px solid rgba(65, 68, 104, 0.35);
          min-height: 520px;
        }

        .flight-viewer__canvas-inner {
          width: 100%;
          height: 100%;
        }

        .flight-viewer__placeholder {
          position: absolute;
          inset: 0;
          display: grid;
          place-items: center;
          color: rgba(201, 206, 247, 0.6);
          font-size: 1rem;
          letter-spacing: 0.02em;
        }

        .flight-viewer__placeholder-inner {
          border: 1px dashed rgba(99, 104, 149, 0.5);
          padding: 2rem 2.5rem;
          border-radius: 18px;
          backdrop-filter: blur(10px);
          background: rgba(10, 13, 32, 0.4);
        }

        @media (max-width: 960px) {
          .flight-viewer__content {
            grid-template-columns: 1fr;
          }

          .flight-viewer__visualizer {
            min-height: 420px;
          }
        }

        @media (max-width: 640px) {
          .flight-viewer {
            padding: 3rem 1.25rem;
          }

          .flight-viewer__visualizer {
            min-height: 360px;
          }
        }
      `}</style>
    </main>
  );
}
