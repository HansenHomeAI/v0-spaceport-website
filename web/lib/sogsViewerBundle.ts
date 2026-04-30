const PROXY_HOSTS = new Set([
  "spaceport-ml-processing.s3.amazonaws.com",
  "spaceport-ml-processing.s3.us-west-2.amazonaws.com",
]);

const CONFIGURED_DEFAULT_SOGS_BUNDLE_URL =
  process.env.NEXT_PUBLIC_DEFAULT_SOGS_BUNDLE_URL?.trim() || "";

const SPACEPORT_BUNDLE_CONFIG_NAME = "spaceport_bundle.json";
const DEFAULT_SOGS_SKYBOX_FILE_NAME = "kloppenheim_06_puresky_equirect.png";

/** Latest pipeline compression output (SSE-KMS); /api/sogs-proxy signs GETs when AWS_* creds are set. */
export const DEFAULT_SOGS_BUNDLE_URL =
  CONFIGURED_DEFAULT_SOGS_BUNDLE_URL ||
  "https://spaceport-ml-processing.s3.amazonaws.com/compressed/manual-3dgs-1774642514/supersplat_bundle/meta.json";

/** Equirect sky (Poly Haven Kloppenheim-style pure sky), baked from HDR for repo size; override with ?skybox=. */
export const DEFAULT_SOGS_SKYBOX_PATH = `/supersplat-viewer/skybox/${DEFAULT_SOGS_SKYBOX_FILE_NAME}`;

type SpaceportBundleConfig = {
  skybox?:
    | string
    | {
        path?: string;
        url?: string;
      };
};

export type ResolvedSogsViewerBundle = {
  contentUrl: string;
  skyboxUrl: string | null;
  bundleKind?: SogsBundleKind;
  summary?: SogsBundleSummary;
};

export type SogsBundleKind = "single" | "lod-streaming" | "asset";
export type SogsBundleTransport = "direct" | "proxy";

export type SogsBundleSummary = {
  bundleKind: SogsBundleKind;
  rootFile: "meta.json" | "lod-meta.json" | "asset";
  transport: SogsBundleTransport;
  sourceUrl: string;
  viewerUrl: string;
  sourceBundleRootUrl: string;
  viewerBundleRootUrl: string;
  splatCount: number | null;
  lodLevels: number | null;
  chunkFiles: number;
  lodTreeNodes: number;
  bounds:
    | {
        min: [number, number, number];
        max: [number, number, number];
      }
    | null;
};

type ManifestCandidate = {
  sourceManifestUrl: URL;
  sourceBundleRootUrl: URL;
  rootFile: "meta.json" | "lod-meta.json";
};

export function getBaseOrigin(): string {
  return typeof window !== "undefined" ? window.location.origin : "https://spcprt.com";
}

function parseBundleUrl(rawValue: string): URL | null {
  const trimmed = rawValue.trim();
  if (!trimmed) {
    return null;
  }

  try {
    const parsed =
      trimmed.startsWith("http://") || trimmed.startsWith("https://")
        ? new URL(trimmed)
        : new URL(trimmed, getBaseOrigin());

    if (!parsed.protocol.startsWith("http")) {
      return null;
    }

    if (
      !parsed.pathname.endsWith(".json") &&
      !parsed.pathname.endsWith(".ply") &&
      !parsed.pathname.endsWith(".sog")
    ) {
      parsed.pathname = parsed.pathname.replace(/\/?$/, "/meta.json");
    }

    return parsed;
  } catch {
    return null;
  }
}

function convertToProxyPath(url: URL): string {
  const base = `${url.protocol}//${url.host}`;
  const encodedBase = base.replace("://", ":/");
  return `/api/sogs-proxy/${encodedBase}${url.pathname}${url.search}`;
}

function shouldProxyBundleUrl(url: URL): boolean {
  if (url.pathname.endsWith(".ply") || url.pathname.endsWith(".sog")) {
    return false;
  }
  return PROXY_HOSTS.has(url.host);
}

function toViewerAssetUrl(url: URL): string {
  return shouldProxyBundleUrl(url) ? convertToProxyPath(url) : url.toString();
}

function toViewerUrl(url: URL, transport: SogsBundleTransport): string {
  return transport === "proxy" ? convertToProxyPath(url) : url.toString();
}

export function toSogsProxyUrl(rawValue: string): string | null {
  const parsed = parseInputUrl(rawValue);
  if (!parsed || !shouldProxyBundleUrl(parsed)) {
    return null;
  }
  return convertToProxyPath(parsed);
}

function parseInputUrl(rawValue: string): URL | null {
  const trimmed = rawValue.trim();
  if (!trimmed) {
    return null;
  }

  try {
    const parsed =
      trimmed.startsWith("http://") || trimmed.startsWith("https://")
        ? new URL(trimmed)
        : new URL(trimmed, getBaseOrigin());
    if (!parsed.protocol.startsWith("http")) {
      return null;
    }

    const leaf = parsed.pathname.split("/").pop() ?? "";
    if (!leaf.includes(".") && !parsed.pathname.endsWith("/")) {
      parsed.pathname = `${parsed.pathname}/`;
    }

    return parsed;
  } catch {
    return null;
  }
}

function buildManifestCandidates(inputUrl: URL): ManifestCandidate[] {
  const leaf = (inputUrl.pathname.split("/").pop() ?? "").toLowerCase();
  const sourceBundleRootUrl = new URL("./", inputUrl);

  if (leaf === "lod-meta.json") {
    return [{ sourceManifestUrl: new URL(inputUrl.toString()), sourceBundleRootUrl, rootFile: "lod-meta.json" }];
  }

  if (leaf.endsWith(".json")) {
    return [{ sourceManifestUrl: new URL(inputUrl.toString()), sourceBundleRootUrl, rootFile: "meta.json" }];
  }

  const bundleRoot = new URL(inputUrl.toString());
  if (!bundleRoot.pathname.endsWith("/")) {
    bundleRoot.pathname = `${bundleRoot.pathname}/`;
  }

  return [
    { sourceManifestUrl: new URL(`lod-meta.json${bundleRoot.search}`, bundleRoot), sourceBundleRootUrl: bundleRoot, rootFile: "lod-meta.json" },
    { sourceManifestUrl: new URL(`meta.json${bundleRoot.search}`, bundleRoot), sourceBundleRootUrl: bundleRoot, rootFile: "meta.json" },
  ];
}

function transportOptions(url: URL): SogsBundleTransport[] {
  return shouldProxyBundleUrl(url) ? ["direct", "proxy"] : ["direct"];
}

function readSkyboxPath(config: unknown): string | null {
  if (!config || typeof config !== "object") {
    return null;
  }

  const skybox = (config as SpaceportBundleConfig).skybox;
  if (typeof skybox === "string" && skybox.trim()) {
    return skybox.trim();
  }
  if (skybox && typeof skybox === "object") {
    const candidate = skybox.path ?? skybox.url;
    if (typeof candidate === "string" && candidate.trim()) {
      return candidate.trim();
    }
  }

  return null;
}

function countTreeNodes(node: unknown): number {
  if (!node || typeof node !== "object") {
    return 0;
  }

  const candidate = node as { lods?: unknown; children?: unknown[] };
  if (Array.isArray(candidate.children) && candidate.children.length > 0) {
    return candidate.children.reduce<number>((sum, child) => sum + countTreeNodes(child), 0);
  }

  return candidate.lods && typeof candidate.lods === "object" ? 1 : 0;
}

function parseBounds(
  bound: unknown,
): { min: [number, number, number]; max: [number, number, number] } | null {
  if (!bound || typeof bound !== "object") {
    return null;
  }

  const min = (bound as { min?: unknown }).min;
  const max = (bound as { max?: unknown }).max;
  if (
    !Array.isArray(min) ||
    !Array.isArray(max) ||
    min.length !== 3 ||
    max.length !== 3 ||
    !min.every((value) => typeof value === "number") ||
    !max.every((value) => typeof value === "number")
  ) {
    return null;
  }

  return { min: [min[0], min[1], min[2]], max: [max[0], max[1], max[2]] };
}

function summarizeManifest(
  manifest: unknown,
  candidate: ManifestCandidate,
  transport: SogsBundleTransport,
): SogsBundleSummary {
  const manifestObject = manifest && typeof manifest === "object" ? (manifest as Record<string, unknown>) : {};
  const isLod =
    candidate.rootFile === "lod-meta.json" ||
    typeof (manifestObject as { lodLevels?: unknown }).lodLevels === "number";
  const means = manifestObject.means;
  const splatCount =
    typeof means === "object" &&
    means &&
    Array.isArray((means as { shape?: unknown }).shape) &&
    typeof ((means as { shape: unknown[] }).shape[0]) === "number"
      ? ((means as { shape: number[] }).shape[0] ?? null)
      : null;
  const filenames = Array.isArray(manifestObject.filenames) ? manifestObject.filenames : [];
  const tree = manifestObject.tree;

  return {
    bundleKind: isLod ? "lod-streaming" : "single",
    rootFile: isLod ? "lod-meta.json" : "meta.json",
    transport,
    sourceUrl: candidate.sourceManifestUrl.toString(),
    viewerUrl: toViewerUrl(candidate.sourceManifestUrl, transport),
    sourceBundleRootUrl: candidate.sourceBundleRootUrl.toString(),
    viewerBundleRootUrl: toViewerUrl(candidate.sourceBundleRootUrl, transport),
    splatCount,
    lodLevels: typeof manifestObject.lodLevels === "number" ? manifestObject.lodLevels : null,
    chunkFiles: isLod ? filenames.length : 0,
    lodTreeNodes: isLod ? countTreeNodes(tree) : 0,
    bounds: parseBounds(tree && typeof tree === "object" ? (tree as { bound?: unknown }).bound : null),
  };
}

async function fetchJson(url: string): Promise<unknown | null> {
  try {
    const response = await fetch(url, {
      headers: { Accept: "application/json" },
      cache: "no-store",
    });
    if (!response.ok) {
      return null;
    }
    return (await response.json()) as unknown;
  } catch {
    return null;
  }
}

function resolveAssetUrlFromSource(
  sourceBundleRootUrl: URL,
  assetPath: string,
  transport: SogsBundleTransport,
): string | null {
  const trimmed = assetPath.trim();
  if (!trimmed) {
    return null;
  }

  try {
    const absolute =
      trimmed.startsWith("http://") || trimmed.startsWith("https://")
        ? new URL(trimmed)
        : trimmed.startsWith("/")
          ? new URL(trimmed, getBaseOrigin())
          : new URL(trimmed, sourceBundleRootUrl);

    if (!absolute.protocol.startsWith("http")) {
      return null;
    }

    return toViewerUrl(absolute, transport);
  } catch {
    return null;
  }
}

export function normalizeBundleUrl(rawValue: string): string | null {
  const parsed = parseBundleUrl(rawValue);
  if (!parsed) {
    return null;
  }

  try {
    return toViewerAssetUrl(parsed);
  } catch {
    return null;
  }
}

export function resolveBundleAssetUrl(rawBundleValue: string, assetPath: string): string | null {
  const parsedBundleUrl = parseBundleUrl(rawBundleValue);
  const trimmed = assetPath.trim();
  if (!parsedBundleUrl || !trimmed) {
    return null;
  }

  try {
    const absolute =
      trimmed.startsWith("http://") || trimmed.startsWith("https://")
        ? new URL(trimmed)
        : trimmed.startsWith("/")
          ? new URL(trimmed, getBaseOrigin())
          : new URL(trimmed, parsedBundleUrl);

    if (!absolute.protocol.startsWith("http")) {
      return null;
    }

    return toViewerAssetUrl(absolute);
  } catch {
    return null;
  }
}

export async function resolveSogsViewerBundle(
  rawBundleValue: string,
  explicitSkybox?: string | null,
): Promise<ResolvedSogsViewerBundle | null> {
  const parsed = parseInputUrl(rawBundleValue);
  if (!parsed) {
    return null;
  }

  if (parsed.pathname.endsWith(".ply") || parsed.pathname.endsWith(".sog")) {
    return {
      contentUrl: toViewerAssetUrl(parsed),
      skyboxUrl: explicitSkybox === null ? null : DEFAULT_SOGS_SKYBOX_PATH,
      bundleKind: "asset",
      summary: {
        bundleKind: "asset",
        rootFile: "asset",
        transport: "direct",
        sourceUrl: parsed.toString(),
        viewerUrl: toViewerAssetUrl(parsed),
        sourceBundleRootUrl: new URL("./", parsed).toString(),
        viewerBundleRootUrl: new URL("./", parsed).toString(),
        splatCount: null,
        lodLevels: null,
        chunkFiles: 0,
        lodTreeNodes: 0,
        bounds: null,
      },
    };
  }

  for (const candidate of buildManifestCandidates(parsed)) {
    for (const transport of transportOptions(candidate.sourceManifestUrl)) {
      const contentUrl = toViewerUrl(candidate.sourceManifestUrl, transport);
      const manifest = await fetchJson(contentUrl);
      if (!manifest) {
        continue;
      }

      const summary = summarizeManifest(manifest, candidate, transport);
      let skyboxUrl: string | null = DEFAULT_SOGS_SKYBOX_PATH;

      if (explicitSkybox === null) {
        skyboxUrl = null;
      } else if (typeof explicitSkybox === "string" && explicitSkybox.trim()) {
        skyboxUrl =
          resolveAssetUrlFromSource(candidate.sourceBundleRootUrl, explicitSkybox, transport) ??
          explicitSkybox.trim();
      } else {
        const configUrl = resolveAssetUrlFromSource(
          candidate.sourceBundleRootUrl,
          SPACEPORT_BUNDLE_CONFIG_NAME,
          transport,
        );
        if (configUrl) {
          const config = await fetchJson(configUrl);
          const configuredSkybox = readSkyboxPath(config);
          if (configuredSkybox) {
            skyboxUrl =
              resolveAssetUrlFromSource(candidate.sourceBundleRootUrl, configuredSkybox, transport) ??
              DEFAULT_SOGS_SKYBOX_PATH;
          }
        }
      }

      return {
        contentUrl,
        skyboxUrl,
        bundleKind: summary.bundleKind,
        summary,
      };
    }
  }

  const contentUrl = normalizeBundleUrl(rawBundleValue);
  if (!contentUrl) {
    return null;
  }

  if (explicitSkybox === null) {
    return { contentUrl, skyboxUrl: null };
  }

  if (typeof explicitSkybox === "string" && explicitSkybox.trim()) {
    return {
      contentUrl,
      skyboxUrl: resolveBundleAssetUrl(rawBundleValue, explicitSkybox) ?? explicitSkybox.trim(),
    };
  }

  const configUrl = resolveBundleAssetUrl(rawBundleValue, SPACEPORT_BUNDLE_CONFIG_NAME);
  if (configUrl) {
    try {
      const response = await fetch(configUrl, {
        headers: { Accept: "application/json" },
      });
      if (response.ok) {
        const config = (await response.json()) as SpaceportBundleConfig;
        const configuredSkybox = readSkyboxPath(config);
        if (configuredSkybox) {
          const resolvedSkybox = resolveBundleAssetUrl(rawBundleValue, configuredSkybox);
          if (resolvedSkybox) {
            return { contentUrl, skyboxUrl: resolvedSkybox };
          }
        }
      }
    } catch {
      /* fall back to the site-hosted default skybox */
    }
  }

  return { contentUrl, skyboxUrl: DEFAULT_SOGS_SKYBOX_PATH };
}
