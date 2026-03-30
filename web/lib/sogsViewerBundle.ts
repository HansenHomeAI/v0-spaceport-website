const PROXY_HOSTS = new Set([
  "spaceport-ml-processing.s3.amazonaws.com",
  "spaceport-ml-processing.s3.us-west-2.amazonaws.com",
]);

/** Latest pipeline compression output (SSE-KMS); /api/sogs-proxy signs GETs when AWS_* creds are set. */
export const DEFAULT_SOGS_BUNDLE_URL =
  "https://spaceport-ml-processing.s3.amazonaws.com/compressed/manual-3dgs-1774642514/supersplat_bundle/meta.json";

export function getBaseOrigin(): string {
  return typeof window !== "undefined" ? window.location.origin : "https://spcprt.com";
}

export type NormalizeBundleUrlOptions = {
  useProxy?: boolean;
  baseOrigin?: string;
};

function convertToProxyPath(url: URL): string {
  const base = `${url.protocol}//${url.host}`;
  const encodedBase = base.replace("://", ":/");
  return `/api/sogs-proxy/${encodedBase}${url.pathname}${url.search}`;
}

export function normalizeBundleUrl(
  rawValue: string,
  options: NormalizeBundleUrlOptions = {},
): string | null {
  const trimmed = rawValue.trim();
  if (!trimmed) {
    return null;
  }

  try {
    const baseOrigin = options.baseOrigin ?? getBaseOrigin();
    const parsed =
      trimmed.startsWith("http://") || trimmed.startsWith("https://")
        ? new URL(trimmed)
        : new URL(trimmed, baseOrigin);

    if (!parsed.protocol.startsWith("http")) {
      return null;
    }

    if (!parsed.pathname.endsWith(".json")) {
      parsed.pathname = parsed.pathname.replace(/\/?$/, "/meta.json");
    }

    if (options.useProxy !== false && PROXY_HOSTS.has(parsed.host)) {
      return convertToProxyPath(parsed);
    }

    return parsed.toString();
  } catch {
    return null;
  }
}
