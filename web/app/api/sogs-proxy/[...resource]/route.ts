import { NextRequest } from "next/server";
import { AwsClient } from "aws4fetch";
import { XMLParser } from "fast-xml-parser";

export const runtime = "edge";

const ALLOWED_HOSTS = new Set([
  "spaceport-ml-processing.s3.amazonaws.com",
  "spaceport-ml-processing.s3.us-west-2.amazonaws.com",
]);

const S3_REGION = process.env.AWS_REGION ?? "us-west-2";
const DELIVERY_BUCKET = process.env.ML_DELIVERY_BUCKET_NAME?.trim() ?? "";
const CLOUDFRONT_REGION = "us-east-1";
const CLOUDFRONT_DISTRIBUTIONS_URL = "https://cloudfront.amazonaws.com/2020-05-31/distribution";
const xmlParser = new XMLParser();
const cloudFrontBucketCache = new Map<string, string | null>();
let cloudFrontBucketCacheLoad: Promise<void> | null = null;

function isAllowedEdgeBundleUrl(url: URL): boolean {
  return url.host.endsWith(".cloudfront.net") && url.pathname.startsWith("/models/");
}

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

function getS3BucketFromDomainName(domainName: string): string | null {
  const regionalMatch = /^([^.]+)\.s3\.[^.]+\.amazonaws\.com$/i.exec(domainName);
  if (regionalMatch) {
    return regionalMatch[1];
  }

  const globalMatch = /^([^.]+)\.s3\.amazonaws\.com$/i.exec(domainName);
  if (globalMatch) {
    return globalMatch[1];
  }

  return null;
}

function toArray<T>(value: T | T[] | undefined): T[] {
  if (Array.isArray(value)) {
    return value;
  }
  return value == null ? [] : [value];
}

async function populateCloudFrontBucketCache(): Promise<void> {
  if (cloudFrontBucketCacheLoad) {
    return cloudFrontBucketCacheLoad;
  }

  cloudFrontBucketCacheLoad = (async () => {
    if (!awsCredentialsAvailable()) {
      return;
    }

    const client = new AwsClient({
      accessKeyId: process.env.AWS_ACCESS_KEY_ID as string,
      secretAccessKey: process.env.AWS_SECRET_ACCESS_KEY as string,
      sessionToken: process.env.AWS_SESSION_TOKEN,
      region: CLOUDFRONT_REGION,
      service: "cloudfront",
    });

    const response = await client.fetch(CLOUDFRONT_DISTRIBUTIONS_URL, {
      headers: { Accept: "application/xml" },
    });
    if (!response.ok) {
      throw new Error(`CloudFront distribution lookup failed with ${response.status}`);
    }

    const body = await response.text();
    const parsed = xmlParser.parse(body) as {
      DistributionList?: {
        Items?: {
          DistributionSummary?: Array<{
            DomainName?: string;
            Origins?: {
              Items?: {
                Origin?: Array<{ DomainName?: string }> | { DomainName?: string };
              };
            };
          }> | {
            DomainName?: string;
            Origins?: {
              Items?: {
                Origin?: Array<{ DomainName?: string }> | { DomainName?: string };
              };
            };
          };
        };
      };
    };

    const distributions = toArray(parsed.DistributionList?.Items?.DistributionSummary);
    for (const distribution of distributions) {
      const host = distribution?.DomainName?.trim();
      if (!host) {
        continue;
      }

      const origins = toArray(distribution.Origins?.Items?.Origin);
      const bucket =
        origins
          .map((origin) => origin?.DomainName?.trim())
          .map((domainName) => (domainName ? getS3BucketFromDomainName(domainName) : null))
          .find((candidate) => Boolean(candidate)) ?? null;
      cloudFrontBucketCache.set(host, bucket);
    }
  })();

  try {
    await cloudFrontBucketCacheLoad;
  } finally {
    cloudFrontBucketCacheLoad = null;
  }
}

async function resolveDeliveryBucket(url: URL): Promise<string | null> {
  if (!isAllowedEdgeBundleUrl(url)) {
    return null;
  }

  if (DELIVERY_BUCKET) {
    return DELIVERY_BUCKET;
  }

  if (cloudFrontBucketCache.has(url.host)) {
    return cloudFrontBucketCache.get(url.host) ?? null;
  }

  try {
    await populateCloudFrontBucketCache();
  } catch {
    return null;
  }

  return cloudFrontBucketCache.get(url.host) ?? null;
}

async function toSignedS3HttpsUrl(url: URL): Promise<URL | null> {
  if (isAllowedEdgeBundleUrl(url)) {
    const bucket = await resolveDeliveryBucket(url);
    if (!bucket) {
      return null;
    }
    return new URL(`https://${bucket}.s3.${S3_REGION}.amazonaws.com${url.pathname}${url.search}`);
  }

  return toRegionalS3HttpsUrl(url);
}

async function fetchS3Signed(url: URL, accept: string): Promise<Response> {
  const regional = await toSignedS3HttpsUrl(url);
  if (!regional) {
    return fetch(url, {
      headers: { Accept: accept },
    });
  }
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
    const isAllowedEdgeBundle = isAllowedEdgeBundleUrl(url);

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

  const shouldUseSignedS3First = isAllowedEdgeBundleUrl(upstreamUrl) && awsCredentialsAvailable();
  const accept = request.headers.get("accept") ?? "*/*";

  let upstreamResponse = shouldUseSignedS3First
    ? await fetchS3Signed(upstreamUrl, accept)
    : await fetch(upstreamUrl, {
        headers: {
          Accept: accept,
        },
      });

  // Legacy direct-S3 bundle URLs may still require SigV4 depending on bucket/object policy.
  if (
    (upstreamResponse.status === 400 || upstreamResponse.status === 403) &&
    awsCredentialsAvailable()
  ) {
    try {
      upstreamResponse = await fetchS3Signed(upstreamUrl, accept);
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
