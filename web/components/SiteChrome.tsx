import { headers } from "next/headers";
import AnalyticsProvider from "./AnalyticsProvider";
import Footer from "./Footer";
import Header from "./Header";

function isStandalonePath(pathname: string): boolean {
  return (
    pathname === "/sogs-viewer" ||
    pathname.startsWith("/sogs-viewer/") ||
    pathname === "/sogs-migrated-viewer" ||
    pathname.startsWith("/sogs-migrated-viewer/") ||
    pathname === "/pipeline-viewer" ||
    pathname.startsWith("/pipeline-viewer/") ||
    pathname === "/md1-viewer" ||
    pathname.startsWith("/md1-viewer/") ||
    pathname === "/sfm-output-viewer" ||
    pathname.startsWith("/sfm-output-viewer/")
  );
}

export default function SiteChrome({ children }: { children: React.ReactNode }) {
  const pathname = headers().get("x-pathname") ?? "";
  if (isStandalonePath(pathname)) {
    return <>{children}</>;
  }

  return (
    <AnalyticsProvider>
      <Header />
      {children}
      <Footer />
    </AnalyticsProvider>
  );
}
