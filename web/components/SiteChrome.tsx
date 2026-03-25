import { headers } from "next/headers";
import AnalyticsProvider from "./AnalyticsProvider";
import Footer from "./Footer";
import Header from "./Header";

function isStandalonePath(pathname: string): boolean {
  return pathname === "/sogs-viewer" || pathname.startsWith("/sogs-viewer/");
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
