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

    if (!parsed.pathname.endsWith(".json") && !parsed.pathname.endsWith(".ply")) {
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
  return PROXY_HOSTS.has(url.host);
}

function toViewerAssetUrl(url: URL): string {
  return shouldProxyBundleUrl(url) ? convertToProxyPath(url) : url.toString();
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
