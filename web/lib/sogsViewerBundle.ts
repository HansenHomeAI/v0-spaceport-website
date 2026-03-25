const PROXY_HOSTS = new Set([
  "spaceport-ml-processing.s3.amazonaws.com",
  "spaceport-ml-processing.s3.us-west-2.amazonaws.com",
]);

export const DEFAULT_SOGS_BUNDLE_URL =
  "https://spaceport-ml-processing.s3.amazonaws.com/compressed/sogs-test-1763664401/supersplat_bundle/meta.json";

export function getBaseOrigin(): string {
  return typeof window !== "undefined" ? window.location.origin : "https://spcprt.com";
}

function convertToProxyPath(url: URL): string {
  const base = `${url.protocol}//${url.host}`;
  const encodedBase = base.replace("://", ":/");
  return `/api/sogs-proxy/${encodedBase}${url.pathname}${url.search}`;
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

    if (PROXY_HOSTS.has(parsed.host)) {
      return convertToProxyPath(parsed);
    }

    return parsed.toString();
  } catch {
    return null;
  }
}
