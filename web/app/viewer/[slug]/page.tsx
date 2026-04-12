export const runtime = "edge";

import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { ManifestViewer } from "../../../components/manifest-viewer/ManifestViewer";
import { getViewerManifest, listViewerManifestSlugs } from "../../../lib/viewer-manifests";

type PageProps = {
  params: {
    slug: string;
  };
};

export function generateStaticParams() {
  return listViewerManifestSlugs().map((slug) => ({ slug }));
}

export function generateMetadata({ params }: PageProps): Metadata {
  const manifest = getViewerManifest(params.slug);
  if (!manifest) {
    return {
      title: "Viewer",
      description: "Standalone property viewer",
    };
  }

  return {
    title: manifest.text.pageTitle,
    description: manifest.text.pageDescription,
  };
}

export default function ViewerManifestPage({ params }: PageProps) {
  const manifest = getViewerManifest(params.slug);
  if (!manifest) {
    notFound();
  }

  return <ManifestViewer manifest={manifest} />;
}
