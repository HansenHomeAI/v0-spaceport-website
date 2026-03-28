const PROXY_HOSTS = new Set([
  "spaceport-ml-processing.s3.amazonaws.com",
  "spaceport-ml-processing.s3.us-west-2.amazonaws.com",
]);

const CONFIGURED_DEFAULT_SOGS_BUNDLE_URL =
  process.env.NEXT_PUBLIC_DEFAULT_SOGS_BUNDLE_URL?.trim() || "";

/** Prefer edge-hosted bundle URLs; keep S3 proxying only for legacy direct-bucket links. */
export const DEFAULT_SOGS_BUNDLE_URL =
  CONFIGURED_DEFAULT_SOGS_BUNDLE_URL ||
  "https://spaceport-ml-processing.s3.amazonaws.com/compressed/manual-3dgs-1774642514/supersplat_bundle/meta.json";

export function getBaseOrigin(): string {
  return typeof window !== "undefined" ? window.location.origin : "https://spcprt.com";
}

function convertToProxyPath(url: URL): string {
  const base = `${url.protocol}//${url.host}`;
  const encodedBase = base.replace("://", ":/");
  return `/api/sogs-proxy/${encodedBase}${url.pathname}${url.search}`;
}

function shouldProxyBundleUrl(url: URL): boolean {
  if (PROXY_HOSTS.has(url.host)) {
    return true;
  }

  // Route edge-delivered bundle assets through the same-origin proxy to avoid
  // browser-only access discrepancies when preview environments fetch CloudFront.
  return url.host.endsWith(".cloudfront.net") && url.pathname.startsWith("/models/");
}

export function normalizeBundleUrl(rawValue: string): string | null {
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

    if (!parsed.pathname.endsWith(".json")) {
      parsed.pathname = parsed.pathname.replace(/\/?$/, "/meta.json");
    }

    if (shouldProxyBundleUrl(parsed)) {
      return convertToProxyPath(parsed);
    }

    return parsed.toString();
  } catch {
    return null;
  }
}
