import type { NextRequest } from 'next/server';

export const runtime = 'edge';
export const dynamic = 'force-dynamic';

const REGION = process.env.NEXT_PUBLIC_MODEL_DELIVERY_REGION || 'us-west-2';
const BUCKET = process.env.NEXT_PUBLIC_MODEL_DELIVERY_BUCKET || '';
const BASE_URL = process.env.NEXT_PUBLIC_MODEL_DELIVERY_BASE_URL || '';
const PREFIX = (process.env.NEXT_PUBLIC_MODEL_DELIVERY_PREFIX || 'models').replace(/^\/+|\/+$/g, '');
const HTML_CACHE_SECONDS = Number(process.env.NEXT_PUBLIC_MODEL_DELIVERY_HTML_CACHE_SECONDS || '60');
const ASSET_CACHE_SECONDS = Number(process.env.NEXT_PUBLIC_MODEL_DELIVERY_ASSET_CACHE_SECONDS || String(30 * 24 * 60 * 60));

function resolveBaseUrl(): string {
  if (BASE_URL.trim()) {
    return BASE_URL.replace(/\/$/, '');
  }

  if (!BUCKET) {
    throw new Error('Model delivery bucket is not configured');
  }

  if (REGION === 'us-east-1') {
    return `https://${BUCKET}.s3.amazonaws.com`;
  }

  return `https://${BUCKET}.s3.${REGION}.amazonaws.com`;
}

function encodeSegment(segment: string): string {
  return encodeURIComponent(segment).replace(/%2F/gi, '/');
}

function deriveKey(segments: string[]): { key: string; isHtml: boolean } {
  if (!segments.length) {
    throw new Error('Missing model identifier');
  }

  const [slug, ...rest] = segments;
  const safeSegments = [slug.trim(), ...rest];
  if (!safeSegments[0]) {
    throw new Error('Invalid model identifier');
  }

  const objectSegments = safeSegments.map(encodeSegment);
  let isHtml = false;

  if (objectSegments.length === 1) {
    objectSegments.push('index.html');
    isHtml = true;
  } else {
    const last = objectSegments[objectSegments.length - 1];
    isHtml = /\.html?$/i.test(last);
  }

  const key = `${PREFIX}/${objectSegments.join('/')}`;
  return { key, isHtml };
}

function computeCacheHeader(isHtml: boolean): string {
  return isHtml
    ? `public, max-age=${HTML_CACHE_SECONDS}, must-revalidate`
    : `public, max-age=${ASSET_CACHE_SECONDS}, immutable`;
}

export async function GET(request: NextRequest, context: { params: { path?: string[] } }): Promise<Response> {
  const segments = context.params.path ?? [];
  let keyDetails: { key: string; isHtml: boolean };

  try {
    keyDetails = deriveKey(segments);
  } catch (error) {
    console.error('Invalid model delivery request', error);
    return new Response('Invalid model identifier', { status: 400, headers: { 'Content-Type': 'text/plain; charset=utf-8' } });
  }

  const { key, isHtml } = keyDetails;

  let originBase: string;
  try {
    originBase = resolveBaseUrl();
  } catch (error) {
    console.error('Model delivery misconfigured', error);
    return new Response('Model delivery unavailable', { status: 500 });
  }

  const search = request.nextUrl.search || '';
  const url = `${originBase}/${key}${search}`;
  const cacheTtl = isHtml ? HTML_CACHE_SECONDS : ASSET_CACHE_SECONDS;

  try {
    const upstream = await fetch(url, {
      method: 'GET',
      cf: { cacheEverything: true, cacheTtl },
      headers: {
        Accept: isHtml ? 'text/html,application/xhtml+xml' : '*/*',
      },
    });

    if (!upstream.ok) {
      if (upstream.status === 404) {
        return new Response('Model not found', { status: 404, headers: { 'Content-Type': 'text/plain; charset=utf-8' } });
      }

      console.error('Model delivery fetch failed', upstream.status, url);
      return new Response('Upstream error', { status: 502 });
    }

    const headers = new Headers(upstream.headers);
    const cacheHeader = headers.get('Cache-Control') ?? computeCacheHeader(isHtml);
    headers.set('Cache-Control', cacheHeader);

    const contentType = headers.get('Content-Type') || (isHtml ? 'text/html; charset=utf-8' : 'application/octet-stream');
    headers.set('Content-Type', contentType);

    return new Response(upstream.body, {
      status: upstream.status,
      headers,
    });
  } catch (error) {
    console.error('Model delivery proxy error', error);
    return new Response('Model delivery unavailable', { status: 502 });
  }
}

export async function HEAD(request: NextRequest, context: { params: { path?: string[] } }): Promise<Response> {
  const segments = context.params.path ?? [];
  let keyDetails: { key: string; isHtml: boolean };

  try {
    keyDetails = deriveKey(segments);
  } catch (error) {
    console.error('Invalid model delivery HEAD request', error);
    return new Response(null, { status: 400 });
  }

  const { key, isHtml } = keyDetails;

  let originBase: string;
  try {
    originBase = resolveBaseUrl();
  } catch (error) {
    console.error('Model delivery misconfigured (HEAD)', error);
    return new Response(null, { status: 500 });
  }

  const search = request.nextUrl.search || '';
  const url = `${originBase}/${key}${search}`;
  const cacheTtl = isHtml ? HTML_CACHE_SECONDS : ASSET_CACHE_SECONDS;

  try {
    const upstream = await fetch(url, {
      method: 'HEAD',
      cf: { cacheEverything: true, cacheTtl },
      headers: {
        Accept: isHtml ? 'text/html,application/xhtml+xml' : '*/*',
      },
    });

    const headers = new Headers(upstream.headers);
    const cacheHeader = headers.get('Cache-Control') ?? computeCacheHeader(isHtml);
    headers.set('Cache-Control', cacheHeader);
    const contentType = headers.get('Content-Type') || (isHtml ? 'text/html; charset=utf-8' : 'application/octet-stream');
    headers.set('Content-Type', contentType);

    return new Response(null, {
      status: upstream.status,
      headers,
    });
  } catch (error) {
    console.error('Model delivery HEAD proxy error', error);
    return new Response(null, { status: 502 });
  }
}

export const revalidate = 0;
