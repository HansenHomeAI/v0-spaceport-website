"use client";

import {
  CSSProperties,
  FormEvent,
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";
import * as THREE from "three";
import { OrbitControls } from "three/examples/jsm/controls/OrbitControls";

const DEFAULT_COMPRESSED_BUNDLE =
  "https://spaceport-ml-processing.s3.amazonaws.com/compressed/sogs-test-1763664401/supersplat_bundle/meta.json";
const VIEWER_BASE = "/supersplat-viewer/index.html";
const PROXY_HOSTS = new Set([
  "spaceport-ml-processing.s3.amazonaws.com",
  "spaceport-ml-processing.s3.us-west-2.amazonaws.com",
]);

type SfmData = {
  points: Float32Array;
  colors: Float32Array;
  cameraLines: Float32Array;
  pointCount: number;
  cameraCount: number;
  bounds: {
    min: [number, number, number];
    max: [number, number, number];
  };
};

type TransformOption = "native" | "rotateX90" | "rotateX-90" | "rotateY90" | "rotateZ90";

type SupersplatPanelProps = {
  label: string;
  description: string;
  defaultUrl: string;
  buttonLabel: string;
  helperText: string;
  inputPlaceholder: string;
  ensureMetaJson?: boolean;
  onNormalize?: (url: string | null) => void;
};

const pageStyles: CSSProperties = {
  minHeight: "100vh",
  backgroundColor: "#05050a",
  color: "#f8f8fb",
  padding: "48px 28px 64px",
  fontFamily: "'Space Grotesk', 'Inter', -apple-system, BlinkMacSystemFont, sans-serif",
};

const headerStyles: CSSProperties = {
  maxWidth: "1120px",
  margin: "0 auto 32px",
};

const titleStyles: CSSProperties = {
  fontSize: "2.6rem",
  fontWeight: 600,
  letterSpacing: "-0.02em",
  marginBottom: "12px",
};

const subtitleStyles: CSSProperties = {
  fontSize: "1rem",
  color: "rgba(255, 255, 255, 0.75)",
  maxWidth: "860px",
  lineHeight: 1.6,
};

const cardStyles: CSSProperties = {
  background: "rgba(14, 14, 22, 0.7)",
  borderRadius: "28px",
  border: "1px solid rgba(255, 255, 255, 0.08)",
  boxShadow: "0 24px 60px rgba(5, 5, 8, 0.6)",
  padding: "24px",
};

const sectionGridStyles: CSSProperties = {
  display: "grid",
  gridTemplateColumns: "minmax(0, 1.1fr) minmax(0, 1fr)",
  gap: "24px",
  maxWidth: "1120px",
  margin: "0 auto 36px",
};

const fullWidthSectionStyles: CSSProperties = {
  maxWidth: "1120px",
  margin: "0 auto",
};

const labelStyles: CSSProperties = {
  fontSize: "0.8rem",
  fontWeight: 600,
  letterSpacing: "0.08em",
  textTransform: "uppercase",
  color: "rgba(255, 255, 255, 0.7)",
  marginBottom: "8px",
  display: "block",
};

const inputStyles: CSSProperties = {
  width: "100%",
  padding: "12px 14px",
  borderRadius: "12px",
  border: "1px solid rgba(255, 255, 255, 0.14)",
  background: "rgba(10, 10, 16, 0.8)",
  color: "#ffffff",
  fontSize: "0.95rem",
  outline: "none",
};

const buttonStyles: CSSProperties = {
  padding: "10px 18px",
  borderRadius: "999px",
  border: "1px solid rgba(255, 255, 255, 0.2)",
  background: "linear-gradient(90deg, #ff6b00, #ff9a2b)",
  color: "#09090f",
  fontWeight: 600,
  fontSize: "0.9rem",
  cursor: "pointer",
};

const mutedTextStyles: CSSProperties = {
  fontSize: "0.85rem",
  color: "rgba(255, 255, 255, 0.6)",
  lineHeight: 1.5,
};

const tabListStyles: CSSProperties = {
  display: "flex",
  gap: "10px",
  marginBottom: "18px",
  flexWrap: "wrap",
};

const tabButtonStyles: CSSProperties = {
  padding: "8px 16px",
  borderRadius: "999px",
  border: "1px solid rgba(255, 255, 255, 0.2)",
  background: "rgba(255, 255, 255, 0.04)",
  color: "rgba(255, 255, 255, 0.75)",
  fontSize: "0.85rem",
  cursor: "pointer",
};

const activeTabButtonStyles: CSSProperties = {
  ...tabButtonStyles,
  background: "rgba(255, 123, 0, 0.18)",
  border: "1px solid rgba(255, 123, 0, 0.5)",
  color: "#ffffff",
};

const viewerShellStyles: CSSProperties = {
  position: "relative",
  width: "100%",
  height: "520px",
  borderRadius: "20px",
  overflow: "hidden",
  border: "1px solid rgba(255, 255, 255, 0.1)",
  background: "rgba(5, 5, 8, 0.9)",
};

const overlayCardStyles: CSSProperties = {
  display: "flex",
  flexDirection: "column",
  gap: "14px",
};

const statusPillStyles: CSSProperties = {
  padding: "6px 12px",
  borderRadius: "999px",
  background: "rgba(255, 255, 255, 0.08)",
  fontSize: "0.75rem",
  letterSpacing: "0.05em",
  textTransform: "uppercase",
};

const toggleRowStyles: CSSProperties = {
  display: "flex",
  flexWrap: "wrap",
  gap: "12px",
  alignItems: "center",
};

const inlineInputStyles: CSSProperties = {
  ...inputStyles,
  maxWidth: "120px",
};

const calloutStyles: CSSProperties = {
  padding: "14px 16px",
  background: "rgba(255, 126, 0, 0.12)",
  borderRadius: "16px",
  border: "1px solid rgba(255, 126, 0, 0.35)",
  fontSize: "0.85rem",
  color: "rgba(255, 255, 255, 0.8)",
};

const derivedListStyles: CSSProperties = {
  display: "grid",
  gap: "6px",
  fontSize: "0.85rem",
  color: "rgba(255, 255, 255, 0.7)",
};

const mobileStackStyles: CSSProperties = {
  display: "grid",
  gap: "12px",
};

const transformOptions: { value: TransformOption; label: string; rotation: [number, number, number] }[] = [
  { value: "native", label: "Native", rotation: [0, 0, 0] },
  { value: "rotateX90", label: "Rotate +90° X", rotation: [Math.PI / 2, 0, 0] },
  { value: "rotateX-90", label: "Rotate -90° X", rotation: [-Math.PI / 2, 0, 0] },
  { value: "rotateY90", label: "Rotate +90° Y", rotation: [0, Math.PI / 2, 0] },
  { value: "rotateZ90", label: "Rotate +90° Z", rotation: [0, 0, Math.PI / 2] },
];

const toHttpsFromS3 = (raw: string) => {
  if (!raw.startsWith("s3://")) {
    return raw;
  }
  const withoutScheme = raw.replace("s3://", "");
  const [bucket, ...rest] = withoutScheme.split("/");
  if (!bucket) {
    return raw;
  }
  const path = rest.join("/");
  return `https://${bucket}.s3.amazonaws.com/${path}`;
};

const normalizeUrl = (rawValue: string, options?: { ensureMetaJson?: boolean; ensureTrailingSlash?: boolean }) => {
  const trimmed = rawValue.trim();
  if (!trimmed) {
    return null;
  }
  const normalized = toHttpsFromS3(trimmed);
  try {
    const baseOrigin = typeof window !== "undefined" ? window.location.origin : "https://spaceport.space";
    const parsed = normalized.startsWith("http://") || normalized.startsWith("https://")
      ? new URL(normalized)
      : new URL(normalized, baseOrigin);

    if (options?.ensureTrailingSlash && !parsed.pathname.endsWith("/")) {
      parsed.pathname = `${parsed.pathname.replace(/\/?$/, "/")}`;
    }

    if (options?.ensureMetaJson && !parsed.pathname.endsWith(".json")) {
      parsed.pathname = parsed.pathname.replace(/\/?$/, "/meta.json");
    }

    return parsed;
  } catch {
    return null;
  }
};

const withProxyIfNeeded = (url: URL) => {
  if (PROXY_HOSTS.has(url.host)) {
    const base = `${url.protocol}//${url.host}`;
    const encodedBase = base.replace("://", ":/");
    return `/api/sogs-proxy/${encodedBase}${url.pathname}${url.search}`;
  }
  return url.toString();
};

const derivePipelineFromCompressed = (rawCompressed: string) => {
  const parsed = normalizeUrl(rawCompressed, { ensureMetaJson: true });
  if (!parsed) {
    return null;
  }
  const match = parsed.pathname.match(/\/compressed\/([^/]+)\//);
  if (!match) {
    return null;
  }

  const jobId = match[1];
  const baseOrigin = `${parsed.protocol}//${parsed.host}`;
  return {
    jobId,
    compressedBundle: parsed.toString(),
    colmapBase: `${baseOrigin}/colmap/${jobId}/`,
    gaussianPly: `${baseOrigin}/3dgs/${jobId}/splat.ply`,
  };
};

const buildSfmFileUrls = (baseUrl: string, sparsePath: string) => {
  const normalized = normalizeUrl(baseUrl, { ensureTrailingSlash: true });
  if (!normalized) {
    return null;
  }
  const safeSparse = sparsePath.replace(/^\/+/, "").replace(/\/?$/, "/");
  const base = normalized.toString();
  return {
    cameras: `${base}${safeSparse}cameras.txt`,
    images: `${base}${safeSparse}images.txt`,
    points: `${base}${safeSparse}points3D.txt`,
  };
};

const parsePoints = (text: string, maxPoints: number) => {
  const positions: number[] = [];
  const colors: number[] = [];
  let count = 0;
  let minX = Infinity;
  let minY = Infinity;
  let minZ = Infinity;
  let maxX = -Infinity;
  let maxY = -Infinity;
  let maxZ = -Infinity;

  const lines = text.split(/\r?\n/);
  for (const line of lines) {
    if (!line || line.startsWith("#")) {
      continue;
    }
    const parts = line.trim().split(/\s+/);
    if (parts.length < 7) {
      continue;
    }
    const x = Number(parts[1]);
    const y = Number(parts[2]);
    const z = Number(parts[3]);
    const r = Number(parts[4]);
    const g = Number(parts[5]);
    const b = Number(parts[6]);
    if (!Number.isFinite(x) || !Number.isFinite(y) || !Number.isFinite(z)) {
      continue;
    }

    positions.push(x, y, z);
    colors.push(r / 255, g / 255, b / 255);

    minX = Math.min(minX, x);
    minY = Math.min(minY, y);
    minZ = Math.min(minZ, z);
    maxX = Math.max(maxX, x);
    maxY = Math.max(maxY, y);
    maxZ = Math.max(maxZ, z);

    count += 1;
    if (count >= maxPoints) {
      break;
    }
  }

  if (count === 0) {
    minX = minY = minZ = 0;
    maxX = maxY = maxZ = 0;
  }

  return {
    positions: new Float32Array(positions),
    colors: new Float32Array(colors),
    count,
    bounds: {
      min: [minX, minY, minZ] as [number, number, number],
      max: [maxX, maxY, maxZ] as [number, number, number],
    },
  };
};

const parseImages = (text: string, maxCameras: number) => {
  const linePositions: number[] = [];
  let count = 0;
  let minX = Infinity;
  let minY = Infinity;
  let minZ = Infinity;
  let maxX = -Infinity;
  let maxY = -Infinity;
  let maxZ = -Infinity;

  const lines = text.split(/\r?\n/);
  let skipNext = false;

  const pushLine = (a: THREE.Vector3, b: THREE.Vector3) => {
    linePositions.push(a.x, a.y, a.z, b.x, b.y, b.z);
  };

  for (const line of lines) {
    if (skipNext) {
      skipNext = false;
      continue;
    }
    if (!line || line.startsWith("#")) {
      continue;
    }
    const parts = line.trim().split(/\s+/);
    if (parts.length < 9) {
      continue;
    }

    const qw = Number(parts[1]);
    const qx = Number(parts[2]);
    const qy = Number(parts[3]);
    const qz = Number(parts[4]);
    const tx = Number(parts[5]);
    const ty = Number(parts[6]);
    const tz = Number(parts[7]);

    if (![qw, qx, qy, qz, tx, ty, tz].every(Number.isFinite)) {
      continue;
    }

    const worldToCam = new THREE.Quaternion(qx, qy, qz, qw);
    const camToWorld = worldToCam.clone().invert();
    const t = new THREE.Vector3(tx, ty, tz);
    const center = t.clone().applyQuaternion(camToWorld).multiplyScalar(-1);

    minX = Math.min(minX, center.x);
    minY = Math.min(minY, center.y);
    minZ = Math.min(minZ, center.z);
    maxX = Math.max(maxX, center.x);
    maxY = Math.max(maxY, center.y);
    maxZ = Math.max(maxZ, center.z);

    const depth = 0.4;
    const half = depth * 0.35;
    const localCorners = [
      new THREE.Vector3(-half, -half, depth),
      new THREE.Vector3(half, -half, depth),
      new THREE.Vector3(half, half, depth),
      new THREE.Vector3(-half, half, depth),
    ];

    const worldCorners = localCorners.map((corner) => corner.applyQuaternion(camToWorld).add(center));

    for (const corner of worldCorners) {
      pushLine(center, corner);
    }

    pushLine(worldCorners[0], worldCorners[1]);
    pushLine(worldCorners[1], worldCorners[2]);
    pushLine(worldCorners[2], worldCorners[3]);
    pushLine(worldCorners[3], worldCorners[0]);

    count += 1;
    if (count >= maxCameras) {
      break;
    }

    skipNext = true;
  }

  if (count === 0) {
    minX = minY = minZ = 0;
    maxX = maxY = maxZ = 0;
  }

  return {
    positions: new Float32Array(linePositions),
    count,
    bounds: {
      min: [minX, minY, minZ] as [number, number, number],
      max: [maxX, maxY, maxZ] as [number, number, number],
    },
  };
};

const mergeBounds = (a: SfmData["bounds"], b: SfmData["bounds"]) => {
  const min: [number, number, number] = [
    Math.min(a.min[0], b.min[0]),
    Math.min(a.min[1], b.min[1]),
    Math.min(a.min[2], b.min[2]),
  ];
  const max: [number, number, number] = [
    Math.max(a.max[0], b.max[0]),
    Math.max(a.max[1], b.max[1]),
    Math.max(a.max[2], b.max[2]),
  ];
  return { min, max };
};

const SfmCanvas = ({
  data,
  showAxes,
  showCameras,
  pointSize,
  transform,
}: {
  data: SfmData | null;
  showAxes: boolean;
  showCameras: boolean;
  pointSize: number;
  transform: TransformOption;
}) => {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const sceneRef = useRef<THREE.Scene | null>(null);
  const rendererRef = useRef<THREE.WebGLRenderer | null>(null);
  const cameraRef = useRef<THREE.PerspectiveCamera | null>(null);
  const controlsRef = useRef<OrbitControls | null>(null);
  const dataGroupRef = useRef<THREE.Group | null>(null);
  const pointsRef = useRef<THREE.Points | null>(null);
  const cameraLinesRef = useRef<THREE.LineSegments | null>(null);
  const axesRef = useRef<THREE.AxesHelper | null>(null);
  const frameRef = useRef<number | null>(null);

  useEffect(() => {
    const container = containerRef.current;
    if (!container) {
      return undefined;
    }

    const scene = new THREE.Scene();
    scene.background = new THREE.Color("#050508");
    sceneRef.current = scene;

    const camera = new THREE.PerspectiveCamera(60, 1, 0.01, 1000);
    camera.position.set(1, 1, 2);
    cameraRef.current = camera;

    const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
    renderer.setPixelRatio(window.devicePixelRatio || 1);
    renderer.setSize(container.clientWidth, container.clientHeight, false);
    rendererRef.current = renderer;
    container.appendChild(renderer.domElement);

    const controls = new OrbitControls(camera, renderer.domElement);
    controls.enableDamping = true;
    controlsRef.current = controls;

    const dataGroup = new THREE.Group();
    scene.add(dataGroup);
    dataGroupRef.current = dataGroup;

    const axes = new THREE.AxesHelper(1);
    axes.visible = showAxes;
    scene.add(axes);
    axesRef.current = axes;

    const resizeObserver = new ResizeObserver(() => {
      if (!rendererRef.current || !cameraRef.current || !containerRef.current) {
        return;
      }
      const { clientWidth, clientHeight } = containerRef.current;
      rendererRef.current.setSize(clientWidth, clientHeight, false);
      cameraRef.current.aspect = clientWidth / Math.max(clientHeight, 1);
      cameraRef.current.updateProjectionMatrix();
    });

    resizeObserver.observe(container);

    const animate = () => {
      if (controlsRef.current) {
        controlsRef.current.update();
      }
      if (rendererRef.current && sceneRef.current && cameraRef.current) {
        rendererRef.current.render(sceneRef.current, cameraRef.current);
      }
      frameRef.current = requestAnimationFrame(animate);
    };
    frameRef.current = requestAnimationFrame(animate);

    return () => {
      if (frameRef.current) {
        cancelAnimationFrame(frameRef.current);
      }
      resizeObserver.disconnect();
      controls.dispose();
      renderer.dispose();
      container.removeChild(renderer.domElement);
      scene.clear();
    };
  }, []);

  useEffect(() => {
    if (!dataGroupRef.current || !sceneRef.current) {
      return;
    }
    const rotation = transformOptions.find((option) => option.value === transform)?.rotation ?? [0, 0, 0];
    dataGroupRef.current.rotation.set(rotation[0], rotation[1], rotation[2]);
  }, [transform]);

  useEffect(() => {
    if (axesRef.current) {
      axesRef.current.visible = showAxes;
    }
  }, [showAxes]);

  useEffect(() => {
    if (!dataGroupRef.current || !sceneRef.current || !cameraRef.current || !controlsRef.current) {
      return;
    }

    if (pointsRef.current) {
      pointsRef.current.geometry.dispose();
      if (Array.isArray(pointsRef.current.material)) {
        pointsRef.current.material.forEach((material) => material.dispose());
      } else {
        pointsRef.current.material.dispose();
      }
      dataGroupRef.current.remove(pointsRef.current);
      pointsRef.current = null;
    }

    if (cameraLinesRef.current) {
      cameraLinesRef.current.geometry.dispose();
      if (Array.isArray(cameraLinesRef.current.material)) {
        cameraLinesRef.current.material.forEach((material) => material.dispose());
      } else {
        cameraLinesRef.current.material.dispose();
      }
      dataGroupRef.current.remove(cameraLinesRef.current);
      cameraLinesRef.current = null;
    }

    if (!data) {
      return;
    }

    const pointGeometry = new THREE.BufferGeometry();
    pointGeometry.setAttribute("position", new THREE.BufferAttribute(data.points, 3));
    pointGeometry.setAttribute("color", new THREE.BufferAttribute(data.colors, 3));

    const pointMaterial = new THREE.PointsMaterial({
      size: pointSize,
      vertexColors: true,
      sizeAttenuation: true,
    });

    const points = new THREE.Points(pointGeometry, pointMaterial);
    dataGroupRef.current.add(points);
    pointsRef.current = points;

    if (data.cameraLines.length > 0) {
      const cameraGeometry = new THREE.BufferGeometry();
      cameraGeometry.setAttribute("position", new THREE.BufferAttribute(data.cameraLines, 3));
      const cameraMaterial = new THREE.LineBasicMaterial({ color: 0xff8a00, transparent: true, opacity: 0.85 });
      const lines = new THREE.LineSegments(cameraGeometry, cameraMaterial);
      lines.visible = showCameras;
      dataGroupRef.current.add(lines);
      cameraLinesRef.current = lines;
    }

    const min = new THREE.Vector3(...data.bounds.min);
    const max = new THREE.Vector3(...data.bounds.max);
    const center = new THREE.Vector3().addVectors(min, max).multiplyScalar(0.5);
    const size = new THREE.Vector3().subVectors(max, min);
    const radius = Math.max(size.length() * 0.5, 0.1);

    const camera = cameraRef.current;
    const distance = radius / Math.tan((camera.fov * Math.PI) / 360);
    camera.near = Math.max(distance / 100, 0.01);
    camera.far = distance * 200;
    camera.position.set(center.x + distance, center.y + distance * 0.6, center.z + distance);
    camera.lookAt(center);
    camera.updateProjectionMatrix();

    controlsRef.current.target.copy(center);
    controlsRef.current.update();

    if (axesRef.current) {
      const axisSize = Math.max(radius * 0.6, 0.5);
      axesRef.current.scale.set(axisSize, axisSize, axisSize);
      axesRef.current.position.copy(center);
    }
  }, [data, pointSize, showCameras]);

  return <div ref={containerRef} style={{ width: "100%", height: "100%" }} />;
};

const SupersplatPanel = ({
  label,
  description,
  defaultUrl,
  buttonLabel,
  helperText,
  inputPlaceholder,
  ensureMetaJson,
  onNormalize,
}: SupersplatPanelProps) => {
  const iframeRef = useRef<HTMLIFrameElement | null>(null);
  const [inputUrl, setInputUrl] = useState(defaultUrl);
  const [activeUrl, setActiveUrl] = useState(defaultUrl);
  const [status, setStatus] = useState("Idle");
  const [viewerState, setViewerState] = useState<"idle" | "loading" | "ready">("idle");
  const [iframeKey, setIframeKey] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const inputId = useMemo(
    () => `supersplat-${label.toLowerCase().replace(/[^a-z0-9]+/g, "-")}`,
    [label]
  );

  const normalizeForViewer = useCallback(
    (rawValue: string) => {
      const parsed = normalizeUrl(rawValue, { ensureMetaJson });
      if (!parsed) {
        return null;
      }
      return withProxyIfNeeded(parsed);
    },
    [ensureMetaJson]
  );

  const attemptLoad = useCallback(
    (rawValue: string) => {
      setError(null);
      const normalized = normalizeForViewer(rawValue);
      if (!normalized) {
        setError("Enter a valid URL pointing to a SOGS bundle or PLY file.");
        return false;
      }
      setViewerState("loading");
      setStatus("Loading viewer...");
      setActiveUrl(normalized);
      setIframeKey((prev) => prev + 1);
      if (onNormalize) {
        onNormalize(rawValue.trim() ? rawValue : null);
      }
      return true;
    },
    [normalizeForViewer, onNormalize]
  );

  useEffect(() => {
    const handleMessage = (event: MessageEvent) => {
      if (event.data?.type === "supersplat:firstFrame" && event.source === iframeRef.current?.contentWindow) {
        setViewerState("ready");
        setStatus("Viewer ready");
      }
    };
    window.addEventListener("message", handleMessage);
    return () => window.removeEventListener("message", handleMessage);
  }, []);

  useEffect(() => {
    const normalized = normalizeForViewer(defaultUrl);
    setActiveUrl(normalized ?? "");
    setInputUrl(defaultUrl);
  }, [defaultUrl, normalizeForViewer]);

  const viewerSrc = useMemo(() => {
    if (!activeUrl) {
      return `${VIEWER_BASE}?settings=/supersplat-viewer/settings.json`;
    }
    const params = new URLSearchParams({
      settings: "/supersplat-viewer/settings.json",
      content: activeUrl,
    });
    return `${VIEWER_BASE}?${params.toString()}`;
  }, [activeUrl, iframeKey]);

  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    attemptLoad(inputUrl);
  };

  return (
    <div style={overlayCardStyles}>
      <div>
        <p style={statusPillStyles}>
          {viewerState === "ready" ? "Viewer ready" : viewerState === "loading" ? "Loading" : "Idle"}
        </p>
        <h2 style={{ margin: "8px 0 6px", fontSize: "1.6rem" }}>{label}</h2>
        <p style={mutedTextStyles}>{description}</p>
      </div>
      <form onSubmit={handleSubmit} style={mobileStackStyles}>
        <div>
          <label style={labelStyles} htmlFor={inputId}>
            Source URL
          </label>
          <input
            id={inputId}
            type="url"
            value={inputUrl}
            onChange={(event) => setInputUrl(event.target.value)}
            placeholder={inputPlaceholder}
            style={inputStyles}
          />
        </div>
        <div style={{ display: "flex", gap: "10px", alignItems: "center", flexWrap: "wrap" }}>
          <button type="submit" style={buttonStyles}>
            {buttonLabel}
          </button>
          <span style={mutedTextStyles}>{helperText}</span>
        </div>
        {error && <p style={{ ...mutedTextStyles, color: "#ff7a6d" }}>{error}</p>}
      </form>
      <div style={viewerShellStyles}>
        <iframe
          key={iframeKey}
          ref={iframeRef}
          src={viewerSrc}
          title={`${label} Viewer`}
          style={{ border: "none", width: "100%", height: "100%", display: "block" }}
          allow="xr-spatial-tracking"
        />
      </div>
      <p style={mutedTextStyles}>{status}</p>
    </div>
  );
};

export default function PipelineViewerPage() {
  const [activeTab, setActiveTab] = useState<"sfm" | "gaussian" | "compressed">("compressed");
  const [compressedInput, setCompressedInput] = useState(DEFAULT_COMPRESSED_BUNDLE);
  const [derivedJobId, setDerivedJobId] = useState<string | null>(null);
  const [colmapBaseUrl, setColmapBaseUrl] = useState("");
  const [gaussianPlyUrl, setGaussianPlyUrl] = useState("");
  const [sfmSparsePath, setSfmSparsePath] = useState("sparse/0/");
  const [sfmMaxPoints, setSfmMaxPoints] = useState(150000);
  const [sfmMaxCameras, setSfmMaxCameras] = useState(600);
  const [sfmPointSize, setSfmPointSize] = useState(0.02);
  const [sfmTransform, setSfmTransform] = useState<TransformOption>("native");
  const [showAxes, setShowAxes] = useState(true);
  const [showCameras, setShowCameras] = useState(true);
  const [sfmData, setSfmData] = useState<SfmData | null>(null);
  const [sfmStatus, setSfmStatus] = useState("Awaiting data");
  const [sfmError, setSfmError] = useState<string | null>(null);

  const handleDerive = () => {
    const result = derivePipelineFromCompressed(compressedInput);
    if (!result) {
      setDerivedJobId(null);
      return;
    }
    setDerivedJobId(result.jobId);
    setColmapBaseUrl(result.colmapBase);
    setGaussianPlyUrl(result.gaussianPly);
    setCompressedInput(result.compressedBundle);
  };

  const handleLoadSfm = async () => {
    setSfmError(null);
    setSfmStatus("Loading SFM output...");

    const fileUrls = buildSfmFileUrls(colmapBaseUrl, sfmSparsePath);
    if (!fileUrls) {
      setSfmError("Enter a valid COLMAP base URL (s3:// or https).");
      setSfmStatus("Failed to load");
      return;
    }

    try {
      const imagesUrl = normalizeUrl(fileUrls.images) ?? new URL(fileUrls.images);
      const pointsUrl = normalizeUrl(fileUrls.points) ?? new URL(fileUrls.points);

      const [imagesText, pointsText] = await Promise.all([
        fetch(withProxyIfNeeded(imagesUrl)).then((res) => {
          if (!res.ok) {
            throw new Error(`images.txt fetch failed (${res.status})`);
          }
          return res.text();
        }),
        fetch(withProxyIfNeeded(pointsUrl)).then((res) => {
          if (!res.ok) {
            throw new Error(`points3D.txt fetch failed (${res.status})`);
          }
          return res.text();
        }),
      ]);

      const parsedPoints = parsePoints(pointsText, sfmMaxPoints);
      const parsedImages = parseImages(imagesText, sfmMaxCameras);
      let bounds = parsedPoints.bounds;
      if (parsedPoints.count > 0 && parsedImages.count > 0) {
        bounds = mergeBounds(parsedPoints.bounds, parsedImages.bounds);
      } else if (parsedImages.count > 0) {
        bounds = parsedImages.bounds;
      }

      setSfmData({
        points: parsedPoints.positions,
        colors: parsedPoints.colors,
        cameraLines: parsedImages.positions,
        pointCount: parsedPoints.count,
        cameraCount: parsedImages.count,
        bounds,
      });

      setSfmStatus(`Loaded ${parsedPoints.count} points and ${parsedImages.count} cameras.`);
    } catch (error) {
      const message = error instanceof Error ? error.message : "Unknown error";
      setSfmError(message);
      setSfmStatus("Failed to load");
    }
  };

  const sfmFileUrls = useMemo(() => buildSfmFileUrls(colmapBaseUrl, sfmSparsePath), [colmapBaseUrl, sfmSparsePath]);

  return (
    <main style={pageStyles}>
      <header style={headerStyles}>
        <h1 style={titleStyles}>Pipeline Viewer</h1>
        <p style={subtitleStyles}>
          Trace orientation drift across the SfM, 3DGS, and compressed SOGS stages. Start with a known-good
          compressed bundle, derive the pipeline step URLs, and inspect each output in a dedicated viewer.
        </p>
      </header>

      <section style={sectionGridStyles}>
        <div style={cardStyles}>
          <h2 style={{ margin: "0 0 12px", fontSize: "1.3rem" }}>Pipeline Source</h2>
          <p style={mutedTextStyles}>
            Paste the compressed bundle URL that renders correctly. We will infer the job ID and suggest the
            matching COLMAP + 3DGS paths so you can check rotation errors earlier in the pipeline.
          </p>
          <div style={{ marginTop: "14px", display: "grid", gap: "10px" }}>
            <label style={labelStyles} htmlFor="compressed-seed">
              Compressed bundle URL
            </label>
            <input
              id="compressed-seed"
              type="url"
              style={inputStyles}
              value={compressedInput}
              onChange={(event) => setCompressedInput(event.target.value)}
            />
            <div style={{ display: "flex", gap: "10px", flexWrap: "wrap" }}>
              <button type="button" style={buttonStyles} onClick={handleDerive}>
                Derive step URLs
              </button>
              <span style={mutedTextStyles}>Works with `s3://` or `https://` links.</span>
            </div>
          </div>
          <div style={{ marginTop: "16px" }}>
            <p style={labelStyles}>Derived links</p>
            <div style={derivedListStyles}>
              <div>Job ID: {derivedJobId ?? "Not detected"}</div>
              <div>COLMAP base: {colmapBaseUrl || "—"}</div>
              <div>3DGS PLY: {gaussianPlyUrl || "—"}</div>
            </div>
          </div>
        </div>

        <div style={{ ...cardStyles, display: "grid", gap: "12px" }}>
          <h2 style={{ margin: 0, fontSize: "1.3rem" }}>How To Use This</h2>
          <div style={calloutStyles}>
            1. Confirm the compressed bundle renders correctly in the Compressed tab.
            2. Load the COLMAP output in the SfM tab and check if the camera cloud is rotated.
            3. Load the raw 3DGS PLY output in the 3DGS tab. If rotation appears here, the issue is upstream of
            compression.
          </div>
          <p style={mutedTextStyles}>
            If the 3DGS output is still packaged as `model.tar.gz`, extract the `splat.ply` and provide its
            direct URL. Large files may take a while to load.
          </p>
        </div>
      </section>

      <section style={fullWidthSectionStyles}>
        <div style={tabListStyles}>
          <button
            type="button"
            style={activeTab === "sfm" ? activeTabButtonStyles : tabButtonStyles}
            onClick={() => setActiveTab("sfm")}
          >
            SfM (COLMAP)
          </button>
          <button
            type="button"
            style={activeTab === "gaussian" ? activeTabButtonStyles : tabButtonStyles}
            onClick={() => setActiveTab("gaussian")}
          >
            3DGS (PLY)
          </button>
          <button
            type="button"
            style={activeTab === "compressed" ? activeTabButtonStyles : tabButtonStyles}
            onClick={() => setActiveTab("compressed")}
          >
            Compressed (SOGS)
          </button>
        </div>

        <div style={cardStyles}>
          {activeTab === "sfm" && (
            <div style={overlayCardStyles}>
              <div>
                <p style={statusPillStyles}>SfM output</p>
                <h2 style={{ margin: "8px 0 6px", fontSize: "1.6rem" }}>Structure-from-Motion Viewer</h2>
                <p style={mutedTextStyles}>
                  Load COLMAP outputs and visualize the sparse point cloud plus camera frustums. Use the
                  transform dropdown to check 90-degree rotation offsets.
                </p>
              </div>
              <div style={mobileStackStyles}>
                <div>
                  <label style={labelStyles} htmlFor="sfm-base">
                    COLMAP base URL
                  </label>
                  <input
                    id="sfm-base"
                    type="url"
                    style={inputStyles}
                    value={colmapBaseUrl}
                    onChange={(event) => setColmapBaseUrl(event.target.value)}
                    placeholder="https://spaceport-ml-processing.s3.amazonaws.com/colmap/<job-id>/"
                  />
                </div>
                <div style={{ display: "flex", flexWrap: "wrap", gap: "12px" }}>
                  <div>
                    <label style={labelStyles} htmlFor="sfm-sparse">
                      Sparse path
                    </label>
                    <input
                      id="sfm-sparse"
                      type="text"
                      style={inlineInputStyles}
                      value={sfmSparsePath}
                      onChange={(event) => setSfmSparsePath(event.target.value)}
                    />
                  </div>
                  <div>
                    <label style={labelStyles} htmlFor="sfm-points">
                      Max points
                    </label>
                    <input
                      id="sfm-points"
                      type="number"
                      min={1000}
                      style={inlineInputStyles}
                      value={sfmMaxPoints}
                      onChange={(event) => setSfmMaxPoints(Number(event.target.value))}
                    />
                  </div>
                  <div>
                    <label style={labelStyles} htmlFor="sfm-cameras">
                      Max cameras
                    </label>
                    <input
                      id="sfm-cameras"
                      type="number"
                      min={10}
                      style={inlineInputStyles}
                      value={sfmMaxCameras}
                      onChange={(event) => setSfmMaxCameras(Number(event.target.value))}
                    />
                  </div>
                  <div>
                    <label style={labelStyles} htmlFor="sfm-size">
                      Point size
                    </label>
                    <input
                      id="sfm-size"
                      type="number"
                      step={0.01}
                      min={0.001}
                      style={inlineInputStyles}
                      value={sfmPointSize}
                      onChange={(event) => setSfmPointSize(Number(event.target.value))}
                    />
                  </div>
                </div>
                <div style={toggleRowStyles}>
                  <label style={{ ...labelStyles, marginBottom: 0 }}>Transform</label>
                  <select
                    value={sfmTransform}
                    onChange={(event) => setSfmTransform(event.target.value as TransformOption)}
                    style={{ ...inputStyles, maxWidth: "220px" }}
                  >
                    {transformOptions.map((option) => (
                      <option key={option.value} value={option.value}>
                        {option.label}
                      </option>
                    ))}
                  </select>
                  <label style={{ ...mutedTextStyles, display: "flex", alignItems: "center", gap: "6px" }}>
                    <input
                      type="checkbox"
                      checked={showAxes}
                      onChange={(event) => setShowAxes(event.target.checked)}
                    />
                    Show axes
                  </label>
                  <label style={{ ...mutedTextStyles, display: "flex", alignItems: "center", gap: "6px" }}>
                    <input
                      type="checkbox"
                      checked={showCameras}
                      onChange={(event) => setShowCameras(event.target.checked)}
                    />
                    Show cameras
                  </label>
                  <button type="button" style={buttonStyles} onClick={handleLoadSfm}>
                    Load SfM
                  </button>
                </div>
              </div>
              {sfmFileUrls && (
                <p style={mutedTextStyles}>
                  Using: {sfmFileUrls.points} · {sfmFileUrls.images}
                </p>
              )}
              <div style={viewerShellStyles}>
                <SfmCanvas
                  data={sfmData}
                  showAxes={showAxes}
                  showCameras={showCameras}
                  pointSize={sfmPointSize}
                  transform={sfmTransform}
                />
              </div>
              <p style={mutedTextStyles}>{sfmStatus}</p>
              {sfmError && <p style={{ ...mutedTextStyles, color: "#ff7a6d" }}>{sfmError}</p>}
            </div>
          )}

          {activeTab === "gaussian" && (
            <SupersplatPanel
              label="3D Gaussian Splatting"
              description="Load the raw PLY output from 3DGS training. Use this to confirm orientation before compression."
              defaultUrl={gaussianPlyUrl}
              buttonLabel="Load 3DGS"
              helperText="Provide a direct .ply or .splat file URL."
              inputPlaceholder="https://bucket.s3.amazonaws.com/3dgs/<job-id>/splat.ply"
              onNormalize={(value) => {
                if (value) {
                  setGaussianPlyUrl(value);
                }
              }}
            />
          )}

          {activeTab === "compressed" && (
            <SupersplatPanel
              label="Compressed SOGS"
              description="PlayCanvas SuperSplat viewer for the compressed bundle. This should match the final output."
              defaultUrl={compressedInput}
              buttonLabel="Load Compressed"
              helperText="Paste the meta.json or bundle directory URL."
              inputPlaceholder="https://bucket.s3.amazonaws.com/compressed/<job-id>/supersplat_bundle/"
              ensureMetaJson
              onNormalize={(value) => {
                if (value) {
                  setCompressedInput(value);
                }
              }}
            />
          )}
        </div>
      </section>
    </main>
  );
}
