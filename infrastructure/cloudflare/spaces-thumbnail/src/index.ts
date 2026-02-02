import puppeteer from '@cloudflare/puppeteer';

const DEFAULT_CACHE_CONTROL = 'public, max-age=86400';
const VIEWPORT = { width: 1200, height: 900, deviceScaleFactor: 1 };
const SCREENSHOT_QUALITY = 82;

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

async function chooseLargestElement(page: any) {
  const handles = await page.$$('canvas, model-viewer, iframe');
  let best = null;
  let bestArea = 0;
  for (const handle of handles) {
    const box = await handle.boundingBox();
    if (!box) continue;
    const area = box.width * box.height;
    if (area > bestArea) {
      bestArea = area;
      best = handle;
    }
  }
  return best;
}

async function renderThumbnail(viewerUrl: string, env: Env): Promise<Uint8Array> {
  const browser = await puppeteer.launch(env.BROWSER);
  let page;
  try {
    page = await browser.newPage();
    await page.setViewport(VIEWPORT);
    await page.goto(viewerUrl, { waitUntil: 'networkidle2', timeout: 60000 });
    await page.waitForSelector('canvas, model-viewer, iframe', { timeout: 15000 }).catch(() => undefined);
    await page.waitForTimeout(2000);

    const target = await chooseLargestElement(page);
    if (target) {
      return await target.screenshot({ type: 'jpeg', quality: SCREENSHOT_QUALITY });
    }
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
