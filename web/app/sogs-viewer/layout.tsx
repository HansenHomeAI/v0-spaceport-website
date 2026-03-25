import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "sogs-viewer",
  description: "Standalone SOGS (SuperSplat) viewer",
};

export default function SogsViewerLayout({ children }: { children: React.ReactNode }) {
  return children;
}
