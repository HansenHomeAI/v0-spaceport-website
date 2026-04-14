import {
  resolveBundleAssetUrlForTransport,
  resolveSogsViewerBundle,
  type ResolvedSogsViewerBundle,
} from "../sogsViewerBundle";
import type { ViewerBundleManifest, ViewerPreviewManifest, ViewerSkyboxManifest } from "./manifest";

const DEFAULT_SPACEPORT_CONFIG_NAME = "spaceport_bundle.json";

type SpaceportBundleConfig = {
  skybox?:
    | string
    | {
        path?: string;
        url?: string;
      };
  preview?:
    | string
    | {
        path?: string;
        url?: string;
      };
};

export type ResolvedViewerPreview = {
  metaUrl: string;
};

export type ResolvedViewerBundle = {
  contentUrl: string;
  skyboxUrl: string | null;
  skyboxPitch: number;
  skyboxVOffset: number;
  preview: ResolvedViewerPreview | null;
  bundleKind: ResolvedSogsViewerBundle["bundleKind"];
  summary: ResolvedSogsViewerBundle["summary"];
};

function skyboxSettings(skybox: ViewerSkyboxManifest | undefined): { pitch: number; vOffset: number } {
  return {
    pitch: skybox?.pitch ?? 0,
    vOffset: skybox?.vOffset ?? 0,
  };
}

async function resolveSkyboxUrl(
  bundleManifest: ViewerBundleManifest,
  rawBundleValue: string,
  resolvedBundle: ResolvedSogsViewerBundle,
): Promise<string | null> {
  const skybox = bundleManifest.skybox;
  if (!skybox) return resolvedBundle.skyboxUrl;

  if (!skybox) return null;

  if (skybox.type === "explicit") {
    if (skybox.url === null) return null;
    return (
      resolveBundleAssetUrlForTransport(rawBundleValue, skybox.url, resolvedBundle.summary.transport) ?? skybox.url
    );
  }

  if (skybox.type === "adjacent-file") {
    return resolveBundleAssetUrlForTransport(rawBundleValue, skybox.fileName, resolvedBundle.summary.transport);
  }

  if (
    (skybox.configFileName == null || skybox.configFileName === DEFAULT_SPACEPORT_CONFIG_NAME) &&
    skybox.fallbackUrl === undefined
  ) {
    return resolvedBundle.skyboxUrl;
  }

  const configUrl = resolveBundleAssetUrlForTransport(
    rawBundleValue,
    skybox.configFileName ?? DEFAULT_SPACEPORT_CONFIG_NAME,
    resolvedBundle.summary.transport,
  );
  if (configUrl) {
    try {
      const response = await fetch(configUrl, {
        headers: { Accept: "application/json" },
      });
      if (response.ok) {
        const config = (await response.json()) as SpaceportBundleConfig;
        const configuredSkybox =
          typeof config.skybox === "string"
            ? config.skybox
            : typeof config.skybox?.path === "string"
              ? config.skybox.path
              : typeof config.skybox?.url === "string"
                ? config.skybox.url
                : null;
        if (configuredSkybox) {
          return resolveBundleAssetUrlForTransport(
            rawBundleValue,
            configuredSkybox,
            resolvedBundle.summary.transport,
          );
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
    return (
      resolveBundleAssetUrlForTransport(rawBundleValue, skybox.fallbackUrl, resolvedBundle.summary.transport) ??
      skybox.fallbackUrl
    );
  }
  return resolvedBundle.skyboxUrl;
}

function readPreviewPath(config: SpaceportBundleConfig): string | null {
  if (typeof config.preview === "string") {
    return config.preview;
  }
  if (typeof config.preview?.path === "string") {
    return config.preview.path;
  }
  if (typeof config.preview?.url === "string") {
    return config.preview.url;
  }
  return null;
}

async function resolvePreviewUrl(
  previewManifest: ViewerPreviewManifest | undefined,
  rawBundleValue: string,
  resolvedBundle: ResolvedSogsViewerBundle,
): Promise<string | null> {
  if (previewManifest?.metaUrl === null) {
    return null;
  }
  if (typeof previewManifest?.metaUrl === "string") {
    return (
      resolveBundleAssetUrlForTransport(rawBundleValue, previewManifest.metaUrl, resolvedBundle.summary.transport) ??
      previewManifest.metaUrl
    );
  }

  const configUrl = resolveBundleAssetUrlForTransport(
    rawBundleValue,
    previewManifest?.configFileName ?? DEFAULT_SPACEPORT_CONFIG_NAME,
    resolvedBundle.summary.transport,
  );

  if (configUrl) {
    try {
      const response = await fetch(configUrl, {
        headers: { Accept: "application/json" },
      });
      if (response.ok) {
        const config = (await response.json()) as SpaceportBundleConfig;
        const previewPath = readPreviewPath(config);
        if (previewPath) {
          return resolveBundleAssetUrlForTransport(rawBundleValue, previewPath, resolvedBundle.summary.transport);
        }
      }
    } catch {
      /* fall back below */
    }
  }

  if (previewManifest?.fallbackUrl === null) {
    return null;
  }
  if (typeof previewManifest?.fallbackUrl === "string") {
    return (
      resolveBundleAssetUrlForTransport(rawBundleValue, previewManifest.fallbackUrl, resolvedBundle.summary.transport) ??
      previewManifest.fallbackUrl
    );
  }
  return null;
}

export async function resolveViewerBundle(
  bundleManifest: ViewerBundleManifest,
  rawBundleValue: string,
): Promise<ResolvedViewerBundle | null> {
  const resolvedBundle = await resolveSogsViewerBundle(rawBundleValue);
  if (!resolvedBundle) return null;

  const skybox = await resolveSkyboxUrl(bundleManifest, rawBundleValue, resolvedBundle);
  const previewUrl = await resolvePreviewUrl(bundleManifest.preview, rawBundleValue, resolvedBundle);
  const { pitch, vOffset } = skyboxSettings(bundleManifest.skybox);

  return {
    contentUrl: resolvedBundle.contentUrl,
    skyboxUrl: skybox,
    skyboxPitch: pitch,
    skyboxVOffset: vOffset,
    preview: previewUrl ? { metaUrl: previewUrl } : null,
    bundleKind: resolvedBundle.bundleKind,
    summary: resolvedBundle.summary,
  };
}
