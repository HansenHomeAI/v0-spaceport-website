import {
  DEFAULT_SFM_PREVIEW_ARTIFACT,
  fetchSignedS3,
  getSfmPreviewDownloadDefinition,
} from "../../../../lib/sfmPreview";

export const runtime = "edge";
export const dynamic = "force-dynamic";

type RouteContext = {
  params: {
    id: string;
  };
};

function buildProxyHeaders(response: Response, fileName: string) {
  const headers = new Headers();
  const headerNames = [
    "accept-ranges",
    "content-length",
    "content-range",
    "content-type",
    "etag",
    "last-modified",
  ];

  for (const headerName of headerNames) {
    const value = response.headers.get(headerName);
    if (value) {
      headers.set(headerName, value);
    }
  }

  headers.set("Cache-Control", "no-store");
  headers.set("Content-Disposition", `inline; filename="${fileName}"`);
  return headers;
}

async function proxyObject(method: "GET" | "HEAD", id: string, request: Request) {
  const definition = getSfmPreviewDownloadDefinition(id, DEFAULT_SFM_PREVIEW_ARTIFACT);
  if (!definition) {
    return Response.json({ error: "Unknown SfM preview artifact download." }, { status: 404 });
  }

  const range = request.headers.get("range");
  const upstream = await fetchSignedS3(definition.bucket, definition.key, {
    method,
    headers: range ? { Range: range } : undefined,
  });

  return new Response(method === "HEAD" ? null : upstream.body, {
    status: upstream.status,
    headers: buildProxyHeaders(upstream, definition.fileName),
  });
}

export async function GET(request: Request, context: RouteContext) {
  try {
    return await proxyObject("GET", context.params.id, request);
  } catch (error) {
    const message = error instanceof Error ? error.message : "Unknown SfM preview download error";
    return Response.json({ error: message }, { status: 500 });
  }
}

export async function HEAD(request: Request, context: RouteContext) {
  try {
    return await proxyObject("HEAD", context.params.id, request);
  } catch (error) {
    const message = error instanceof Error ? error.message : "Unknown SfM preview download error";
    return Response.json({ error: message }, { status: 500 });
  }
}
