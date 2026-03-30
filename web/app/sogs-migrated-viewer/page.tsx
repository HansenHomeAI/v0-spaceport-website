export const runtime = "edge";

import { redirect } from "next/navigation";

type SearchParams = Record<string, string | string[] | undefined>;

function buildQueryString(searchParams: SearchParams | undefined): string {
  const params = new URLSearchParams();
  for (const [key, value] of Object.entries(searchParams ?? {})) {
    if (Array.isArray(value)) {
      for (const item of value) {
        params.append(key, item);
      }
      continue;
    }
    if (typeof value === "string") {
      params.set(key, value);
    }
  }
  const query = params.toString();
  return query ? `?${query}` : "";
}

export default function SogsMigratedViewerPage({ searchParams }: { searchParams?: SearchParams }) {
  redirect(`/sogs-migrated-viewer/index.html${buildQueryString(searchParams)}`);
}
