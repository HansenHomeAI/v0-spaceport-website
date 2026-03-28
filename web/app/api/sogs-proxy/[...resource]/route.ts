import { NextRequest } from "next/server";
import { AwsClient } from "aws4fetch";

export const runtime = "edge";

const ALLOWED_HOSTS = new Set([
  "spaceport-ml-processing.s3.amazonaws.com",
  "spaceport-ml-processing.s3.us-west-2.amazonaws.com",
]);

const S3_REGION = process.env.AWS_REGION ?? "us-west-2";

/** Map global S3 hostname to regional so legacy private S3 bundle links can still be fetched with SigV4 when needed. */
function toRegionalS3HttpsUrl(url: URL): URL {
  const globalMatch = /^([^.]+)\.s3\.amazonaws\.com$/i.exec(url.host);
  if (globalMatch) {
    const bucket = globalMatch[1];
    return new URL(`https://${bucket}.s3.${S3_REGION}.amazonaws.com${url.pathname}${url.search}`);
  }
  return url;
}

function awsCredentialsAvailable(): boolean {
  return Boolean(process.env.AWS_ACCESS_KEY_ID && process.env.AWS_SECRET_ACCESS_KEY);
}

async function fetchS3Signed(url: URL): Promise<Response> {
  const regional = toRegionalS3HttpsUrl(url);
  const client = new AwsClient({
    accessKeyId: process.env.AWS_ACCESS_KEY_ID as string,
    secretAccessKey: process.env.AWS_SECRET_ACCESS_KEY as string,
    sessionToken: process.env.AWS_SESSION_TOKEN,
    region: S3_REGION,
  });
  return client.fetch(regional.toString());
}

const normalizeUpstreamUrl = (segments: string[]): URL | null => {
  if (!segments.length) {
    return null;
  }

  const joined = segments.join("/");
  let urlString = joined;
  if (urlString.startsWith("https:/") && !urlString.startsWith("https://")) {
    urlString = urlString.replace("https:/", "https://");
  }
  if (urlString.startsWith("http:/") && !urlString.startsWith("http://")) {
    urlString = urlString.replace("http:/", "http://");
  }
  urlString = urlString.replace(/^https:\/\//, "https://").replace(/^http:\/\//, "http://");
  try {
    const url = new URL(urlString);
    const isAllowedS3Host = ALLOWED_HOSTS.has(url.host);
    const isAllowedEdgeBundle =
      url.host.endsWith(".cloudfront.net") && url.pathname.startsWith("/models/");

    if (!isAllowedS3Host && !isAllowedEdgeBundle) {
      return null;
    }
    return url;
  } catch {
    return null;
  }
};

export async function GET(request: NextRequest, { params }: { params: { resource: string[] } }) {
  const upstreamUrl = normalizeUpstreamUrl(params.resource ?? []);
  if (!upstreamUrl) {
    return new Response("Invalid or disallowed upstream resource", { status: 400 });
  }

  let upstreamResponse = await fetch(upstreamUrl, {
    headers: {
      Accept: request.headers.get("accept") ?? "*/*",
    },
  });

  // Legacy direct-S3 bundle URLs may still require SigV4 depending on bucket/object policy.
  if (
    (upstreamResponse.status === 400 || upstreamResponse.status === 403) &&
    awsCredentialsAvailable()
  ) {
    try {
      upstreamResponse = await fetchS3Signed(upstreamUrl);
    } catch {
      /* keep original response */
    }
  }

  const headers = new Headers(upstreamResponse.headers);
  headers.set("Access-Control-Allow-Origin", "*");
  headers.delete("content-security-policy");

  return new Response(upstreamResponse.body, {
    status: upstreamResponse.status,
    statusText: upstreamResponse.statusText,
    headers,
  });
}
