import type { Metadata } from "next";
import { Inter } from "next/font/google";

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: "sogs-viewer",
  description: "Standalone SOGS (SuperSplat) viewer",
};

export default function SogsViewerLayout({ children }: { children: React.ReactNode }) {
  return <div className={inter.className}>{children}</div>;
}
