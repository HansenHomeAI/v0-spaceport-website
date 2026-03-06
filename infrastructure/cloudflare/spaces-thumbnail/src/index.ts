import puppeteer from '@cloudflare/puppeteer';

const DEFAULT_CACHE_CONTROL = 'public, max-age=86400';
const VIEWPORT = { width: 1200, height: 900, deviceScaleFactor: 1 };
const SCREENSHOT_QUALITY = 82;
const RENDER_SETTLE_MS = 16000;
const HTML_FETCH_HEADERS = {
  'User-Agent':
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
  Accept: 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
};
const IMAGE_FETCH_HEADERS = {
  'User-Agent':
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
  Accept: 'image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8',
};

interface Env {
  SPACES_BUCKET: R2Bucket;
  SPACES_HOST?: string;
  SPACES_PATH_PREFIX?: string;
  THUMBNAIL_TOKEN?: string;
  BROWSER: Fetcher;
}

const corsHeaders = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Headers': 'Content-Type,Authorization,X-Spaces-Token',
  'Access-Control-Allow-Methods': 'POST,OPTIONS,GET',
};

function jsonResponse(status: number, body: Record<string, unknown>) {
  return new Response(JSON.stringify(body), {
    status,
    headers: {
      ...corsHeaders,
      'Content-Type': 'application/json',
    },
  });
}

function normalizePrefix(prefix?: string): string {
  if (!prefix) return '';
  let normalized = prefix.trim();
  if (!normalized) return '';
  if (!normalized.startsWith('/')) {
    normalized = `/${normalized}`;
  }
  normalized = normalized.replace(/\/+$/, '');
  return normalized === '/' ? '' : normalized;
}

function getHost(env: Env, request: Request): string {
  if (env.SPACES_HOST) return env.SPACES_HOST;
  return new URL(request.url).host;
}

function buildViewerUrl(env: Env, request: Request, slug: string): string {
  const prefix = normalizePrefix(env.SPACES_PATH_PREFIX || '/spaces');
  const host = getHost(env, request);
  const base = prefix ? `https://${host}${prefix}` : `https://${host}`;
  return `${base.replace(/\/$/, '')}/${slug}`;
}

function authorizeRequest(request: Request, env: Env): boolean {
  const token = env.THUMBNAIL_TOKEN;
  if (!token) return true;
  const header = request.headers.get('X-Spaces-Token');
  return Boolean(header && header === token);
}

function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function decodeEscapedUrl(value: string): string {
  return value.replace(/&amp;/g, '&').replace(/\\u0026/g, '&').replace(/\\\//g, '/');
}

async function fetchText(url: string): Promise<string> {
  const response = await fetch(url, { headers: HTML_FETCH_HEADERS });
  if (!response.ok) {
    throw new Error(`Failed to fetch ${url}: ${response.status}`);
  }
  return response.text();
}

async function fetchImage(url: string): Promise<Uint8Array> {
  const response = await fetch(url, { headers: IMAGE_FETCH_HEADERS });
  if (!response.ok) {
    throw new Error(`Failed to fetch preview image ${url}: ${response.status}`);
  }
  return new Uint8Array(await response.arrayBuffer());
}

function extractMatches(text: string, pattern: RegExp): string[] {
  const matches = Array.from(text.matchAll(pattern), (match) => decodeEscapedUrl(match[1] || match[0]));
  return Array.from(new Set(matches.filter(Boolean)));
}

function extractLumaEmbedUrls(viewerHtml: string): string[] {
  return extractMatches(viewerHtml, /https:\/\/lumalabs\.ai\/embed\/[^"'\\s<]+/g);
}

function extractLumaPreviewUrl(embedHtml: string): string | null {
  const candidates = [
    ...extractMatches(embedHtml, /"with_background_preview":"(https:\/\/cdn-luma\.com\/[^"]+)"/g),
    ...extractMatches(embedHtml, /"(?:thumb|skybox)":"(https:\/\/cdn-luma\.com\/[^"]+)"/g),
    ...extractMatches(embedHtml, /<meta[^>]+property="og:image"[^>]+content="([^"]+)"/gi),
  ];
  return candidates.find(Boolean) || null;
}

async function fetchLumaPreview(viewerUrl: string): Promise<Uint8Array | null> {
  const viewerHtml = await fetchText(viewerUrl);
  const embedUrls = extractLumaEmbedUrls(viewerHtml);
  for (const embedUrl of embedUrls) {
    try {
      const embedHtml = await fetchText(embedUrl);
      const previewUrl = extractLumaPreviewUrl(embedHtml);
      if (!previewUrl) continue;
      return await fetchImage(previewUrl);
    } catch {
      continue;
    }
  }
  return null;
}

async function renderThumbnail(viewerUrl: string, env: Env): Promise<Uint8Array> {
  const lumaPreview = await fetchLumaPreview(viewerUrl).catch(() => null);
  if (lumaPreview) {
    return lumaPreview;
  }

  const browser = await puppeteer.launch(env.BROWSER);
  let page;
  try {
    page = await browser.newPage();
    await page.setViewport(VIEWPORT);
    await page.goto(viewerUrl, { waitUntil: 'domcontentloaded', timeout: 60000 });
    await page
      .waitForFunction(
        () => {
          const target = document.querySelector('canvas, model-viewer, iframe') as HTMLElement | null;
          if (!target) return false;
          const rect = target.getBoundingClientRect();
          return rect.width >= 200 && rect.height >= 150;
        },
        { timeout: 30000 }
      )
      .catch(() => undefined);
    // The 3D viewer paints the primary geometry before the distant skybox finishes loading.
    await sleep(RENDER_SETTLE_MS);
    return await page.screenshot({ type: 'jpeg', quality: SCREENSHOT_QUALITY });
  } finally {
    if (page) {
      await page.close().catch(() => undefined);
    }
    await browser.close().catch(() => undefined);
  }
}

export default {
  async fetch(request: Request, env: Env): Promise<Response> {
    if (request.method === 'OPTIONS') {
      return new Response(null, { status: 204, headers: corsHeaders });
    }

    const url = new URL(request.url);
    if (url.pathname.endsWith('/health')) {
      return new Response('ok', { status: 200, headers: corsHeaders });
    }

    if (request.method !== 'POST') {
      return jsonResponse(405, { error: 'Method not allowed' });
    }

    if (!authorizeRequest(request, env)) {
      return jsonResponse(401, { error: 'Unauthorized' });
    }

    let payload: { slug?: string; viewerUrl?: string; force?: boolean } = {};
    try {
      payload = await request.json();
    } catch {
      return jsonResponse(400, { error: 'Invalid JSON payload' });
    }

    const slug = (payload.slug || '').trim();
    if (!slug) {
      return jsonResponse(400, { error: 'slug is required' });
    }

    const viewerUrl = payload.viewerUrl?.trim() || buildViewerUrl(env, request, slug);
    try {
      const screenshot = await renderThumbnail(viewerUrl, env);
      const key = `models/${slug}/thumb.jpg`;
      await env.SPACES_BUCKET.put(key, screenshot, {
        httpMetadata: {
          contentType: 'image/jpeg',
          cacheControl: DEFAULT_CACHE_CONTROL,
        },
      });

      return jsonResponse(200, {
        ok: true,
        slug,
        url: `${viewerUrl.replace(/\/$/, '')}/thumb.jpg`,
      });
    } catch (error: any) {
      return jsonResponse(500, { error: error?.message || 'Thumbnail generation failed' });
    }
  },
};
