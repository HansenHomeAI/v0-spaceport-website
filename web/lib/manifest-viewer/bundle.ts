import type { ViewerBundleManifest, ViewerSkyboxManifest } from "./manifest";

const PROXY_HOSTS = new Set([
  "spaceport-ml-processing.s3.amazonaws.com",
  "spaceport-ml-processing.s3.us-west-2.amazonaws.com",
]);

const DEFAULT_SPACEPORT_CONFIG_NAME = "spaceport_bundle.json";

export type ResolvedViewerBundle = {
  contentUrl: string;
  skyboxUrl: string | null;
  skyboxPitch: number;
  skyboxVOffset: number;
};

function getBaseOrigin(): string {
  return typeof window !== "undefined" ? window.location.origin : "https://spcprt.com";
}

function parseBundleUrl(rawValue: string): URL | null {
  const trimmed = rawValue.trim();
  if (!trimmed) return null;

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

function toAssetUrl(url: URL, useProxy: boolean): string {
  if (useProxy && PROXY_HOSTS.has(url.host)) {
    return convertToProxyPath(url);
  }
  return url.toString();
}

function resolveAssetUrl(rawBundleValue: string, assetPath: string, useProxy: boolean): string | null {
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

    return toAssetUrl(absolute, useProxy);
  } catch {
    return null;
  }
}

function skyboxSettings(skybox: ViewerSkyboxManifest | undefined): { pitch: number; vOffset: number } {
  return {
    pitch: skybox?.pitch ?? 0,
    vOffset: skybox?.vOffset ?? 0,
  };
}

async function resolveSkyboxUrl(
  rawBundleValue: string,
  skybox: ViewerSkyboxManifest | undefined,
  useProxy: boolean,
): Promise<string | null> {
  if (!skybox) return null;

  if (skybox.type === "explicit") {
    if (skybox.url === null) return null;
    return resolveAssetUrl(rawBundleValue, skybox.url, useProxy) ?? skybox.url;
  }

  if (skybox.type === "adjacent-file") {
    return resolveAssetUrl(rawBundleValue, skybox.fileName, useProxy);
  }

  const configUrl = resolveAssetUrl(rawBundleValue, skybox.configFileName ?? DEFAULT_SPACEPORT_CONFIG_NAME, useProxy);
  if (configUrl) {
    try {
      const response = await fetch(configUrl, {
        headers: { Accept: "application/json" },
      });
      if (response.ok) {
        const config = (await response.json()) as { skybox?: string | { path?: string; url?: string } };
        const configuredSkybox =
          typeof config.skybox === "string"
            ? config.skybox
            : typeof config.skybox?.path === "string"
              ? config.skybox.path
              : typeof config.skybox?.url === "string"
                ? config.skybox.url
                : null;
        if (configuredSkybox) {
          return resolveAssetUrl(rawBundleValue, configuredSkybox, useProxy);
        }
      }
    } catch {
      /* fall back below */
    }
  }

  if (skybox.fallbackUrl === null) {
    return null;
  }
  if (typeof skybox.fallbackUrl === "string") {
    return resolveAssetUrl(rawBundleValue, skybox.fallbackUrl, useProxy) ?? skybox.fallbackUrl;
  }
  return null;
}

export async function resolveViewerBundle(
  bundleManifest: ViewerBundleManifest,
  rawBundleValue: string,
): Promise<ResolvedViewerBundle | null> {
  const parsed = parseBundleUrl(rawBundleValue);
  if (!parsed) return null;

  const useProxy = bundleManifest.useProxy ?? false;
  const contentUrl = toAssetUrl(parsed, useProxy);
  const skybox = await resolveSkyboxUrl(rawBundleValue, bundleManifest.skybox, useProxy);
  const { pitch, vOffset } = skyboxSettings(bundleManifest.skybox);

  return {
    contentUrl,
    skyboxUrl: skybox,
    skyboxPitch: pitch,
    skyboxVOffset: vOffset,
  };
}
