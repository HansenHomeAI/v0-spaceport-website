import type { ViewerManifest } from "../manifest-viewer/manifest";
import { meadowLaneManifest } from "./meadowLaneManifest";

const VIEWER_MANIFESTS = [meadowLaneManifest] as const;

const manifestBySlug = new Map<string, ViewerManifest>(VIEWER_MANIFESTS.map((manifest) => [manifest.slug, manifest]));

export function getViewerManifest(slug: string): ViewerManifest | null {
  return manifestBySlug.get(slug) ?? null;
}

export function listViewerManifestSlugs(): string[] {
  return VIEWER_MANIFESTS.map((manifest) => manifest.slug);
}
