const DEFAULT_CACHE_CONTROL = 'public, max-age=300';
const MAX_UPLOAD_BYTES = 2 * 1024 * 1024;
const DISALLOWED_PATH_SEGMENTS = new Set(['..', '.']);

interface Env {
  SPACES_BUCKET: R2Bucket;
  SPACES_HOST?: string;
  SPACES_PATH_PREFIX?: string;
  ADMIN_EMAIL_DOMAIN?: string;
  ADMIN_EMAIL_ALLOWLIST?: string;
  SPACES_PUBLISH_TOKEN?: string;
  COGNITO_REGION?: string;
  COGNITO_USER_POOL_ID?: string;
}

type JwtPayload = {
  sub?: string;
  email?: string;
  exp?: number;
  iss?: string;
  token_use?: string;
  [key: string]: unknown;
};

type Jwk = {
  kid: string;
  kty: string;
  e: string;
  n: string;
  alg?: string;
  use?: string;
};

let jwksCache: { keys: Jwk[]; expiresAt: number } | null = null;

const corsHeaders = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Headers': 'Content-Type,Authorization,X-Spaces-Token',
  'Access-Control-Allow-Methods': 'GET,POST,OPTIONS',
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

function normalizeSlug(input: string): string {
  const cleaned = input
    .toLowerCase()
    .replace(/['’]/g, '')
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '')
    .slice(0, 64);
  return cleaned || 'model';
}

function randomSuffix(length = 4): string {
  const alphabet = 'abcdefghijklmnopqrstuvwxyz0123456789';
  const bytes = new Uint8Array(length);
  crypto.getRandomValues(bytes);
  let result = '';
  for (const byte of bytes) {
    result += alphabet[byte % alphabet.length];
  }
  return result;
}

async function findAvailableSlug(env: Env, baseSlug: string): Promise<string> {
  let slug = baseSlug;
  for (let attempt = 0; attempt < 5; attempt += 1) {
    const key = `models/${slug}/index.html`;
    const existing = await env.SPACES_BUCKET.head(key);
    if (!existing) {
      return slug;
    }
    slug = `${baseSlug}-${randomSuffix(4)}`;
  }
  return `${baseSlug}-${Date.now().toString(36)}`;
}

function getHost(env: Env, request: Request): string {
  if (env.SPACES_HOST) return env.SPACES_HOST;
  return new URL(request.url).host;
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

function stripPrefix(pathname: string, prefix: string): string {
  if (!prefix) return pathname;
  if (pathname === prefix) return '/';
  if (pathname.startsWith(`${prefix}/`)) {
    return pathname.slice(prefix.length);
  }
  return pathname;
}

function buildBaseUrl(env: Env, request: Request): string {
  const host = getHost(env, request);
  const prefix = normalizePrefix(env.SPACES_PATH_PREFIX);
  if (!prefix) {
    return `https://${host}`;
  }
  return `https://${host}${prefix}`;
}

function base64UrlToBytes(input: string): Uint8Array {
  const padding = '='.repeat((4 - (input.length % 4)) % 4);
  const base64 = (input + padding).replace(/-/g, '+').replace(/_/g, '/');
  const raw = atob(base64);
  const bytes = new Uint8Array(raw.length);
  for (let i = 0; i < raw.length; i += 1) {
    bytes[i] = raw.charCodeAt(i);
  }
  return bytes;
}

async function fetchJwks(env: Env): Promise<Jwk[]> {
  const now = Date.now();
  if (jwksCache && jwksCache.expiresAt > now) {
    return jwksCache.keys;
  }

  const region = env.COGNITO_REGION;
  const poolId = env.COGNITO_USER_POOL_ID;
  if (!region || !poolId) {
    throw new Error('Cognito configuration missing');
  }

  const jwksUrl = `https://cognito-idp.${region}.amazonaws.com/${poolId}/.well-known/jwks.json`;
  const response = await fetch(jwksUrl, { cf: { cacheTtl: 300, cacheEverything: true } });
  if (!response.ok) {
    throw new Error('Failed to fetch JWKS');
  }
  const data = await response.json<{ keys: Jwk[] }>();
  jwksCache = {
    keys: data.keys || [],
    expiresAt: now + 5 * 60 * 1000,
  };
  return jwksCache.keys;
}

async function verifyJwt(token: string, env: Env): Promise<JwtPayload | null> {
  const parts = token.split('.');
  if (parts.length !== 3) return null;
  const [encodedHeader, encodedPayload, encodedSignature] = parts;

  let header: { kid?: string; alg?: string };
  let payload: JwtPayload;
  try {
    header = JSON.parse(new TextDecoder().decode(base64UrlToBytes(encodedHeader)));
    payload = JSON.parse(new TextDecoder().decode(base64UrlToBytes(encodedPayload)));
  } catch {
    return null;
  }

  if (header.alg !== 'RS256' || !header.kid) return null;

  const keys = await fetchJwks(env);
  const key = keys.find((candidate) => candidate.kid === header.kid);
  if (!key) return null;

  const cryptoKey = await crypto.subtle.importKey(
    'jwk',
    key,
    { name: 'RSASSA-PKCS1-v1_5', hash: 'SHA-256' },
    false,
    ['verify']
  );

  const data = new TextEncoder().encode(`${encodedHeader}.${encodedPayload}`);
  const signature = base64UrlToBytes(encodedSignature);

  const verified = await crypto.subtle.verify('RSASSA-PKCS1-v1_5', cryptoKey, signature, data);
  if (!verified) return null;

  if (payload.exp && payload.exp * 1000 < Date.now()) return null;

  const region = env.COGNITO_REGION;
  const poolId = env.COGNITO_USER_POOL_ID;
  if (region && poolId) {
    const expectedIss = `https://cognito-idp.${region}.amazonaws.com/${poolId}`;
    if (payload.iss !== expectedIss) return null;
  }

  return payload;
}

function emailAllowed(email: string | undefined, env: Env): boolean {
  if (!email) return false;
  const allowlist = env.ADMIN_EMAIL_ALLOWLIST?.split(',').map((item) => item.trim().toLowerCase()).filter(Boolean);
  if (allowlist && allowlist.length > 0) {
    return allowlist.includes(email.toLowerCase());
  }
  if (env.ADMIN_EMAIL_DOMAIN) {
    return email.toLowerCase().endsWith(`@${env.ADMIN_EMAIL_DOMAIN.toLowerCase()}`);
  }
  return false;
}

async function authorizePublish(request: Request, env: Env): Promise<{ email?: string } | null> {
  const tokenHeader = request.headers.get('X-Spaces-Token');
  if (env.SPACES_PUBLISH_TOKEN && tokenHeader && tokenHeader === env.SPACES_PUBLISH_TOKEN) {
    return { email: 'token' };
  }

  const authHeader = request.headers.get('Authorization');
  if (!authHeader?.startsWith('Bearer ')) return null;

  try {
    const payload = await verifyJwt(authHeader.slice('Bearer '.length), env);
    if (!payload) return null;
    const email = typeof payload.email === 'string' ? payload.email : undefined;
    if (!emailAllowed(email, env)) return null;
    return { email };
  } catch {
    return null;
  }
}

async function handlePublish(request: Request, env: Env): Promise<Response> {
  const authorized = await authorizePublish(request, env);
  if (!authorized) {
    return jsonResponse(401, { error: 'Unauthorized' });
  }

  const formData = await request.formData();
  const titleRaw = formData.get('title');
  const file = formData.get('file');

  if (!file || !(file instanceof File)) {
    return jsonResponse(400, { error: 'Missing HTML file upload' });
  }

  if (file.size > MAX_UPLOAD_BYTES) {
    return jsonResponse(400, { error: 'File is too large' });
  }

  const title = typeof titleRaw === 'string' ? titleRaw.trim() : '';
  const baseSlug = normalizeSlug(title || file.name || 'model');
  const slug = await findAvailableSlug(env, baseSlug);
  const key = `models/${slug}/index.html`;
  const fileBuffer = await file.arrayBuffer();
  const hashBuffer = await crypto.subtle.digest('SHA-256', fileBuffer);
  const hashHex = Array.from(new Uint8Array(hashBuffer))
    .map((byte) => byte.toString(16).padStart(2, '0'))
    .join('');

  await env.SPACES_BUCKET.put(key, fileBuffer, {
    httpMetadata: {
      contentType: 'text/html; charset=utf-8',
      cacheControl: DEFAULT_CACHE_CONTROL,
    },
  });

  const baseUrl = buildBaseUrl(env, request);
  const viewerUrl = `${baseUrl}/${slug}`;

  return jsonResponse(200, { ok: true, slug, url: viewerUrl, hash: hashHex });
}

function resolveViewerKey(pathname: string): { slug: string; key: string } | null {
  const parts = pathname.replace(/^\/+/, '').split('/').filter(Boolean);
  if (!parts.length) return null;
  if (parts.some((segment) => DISALLOWED_PATH_SEGMENTS.has(segment) || segment.startsWith('.'))) {
    return null;
  }
  const slug = parts[0];
  const assetPath = parts.slice(1).join('/');
  const key = assetPath ? `models/${slug}/${assetPath}` : `models/${slug}/index.html`;
  return { slug, key };
}

async function handleViewer(request: Request, env: Env, pathname: string): Promise<Response> {
  const resolved = resolveViewerKey(pathname);
  const slug = resolved?.slug;
  if (!slug || slug === 'health') {
    return new Response('Not found', { status: 404 });
  }

  if (!resolved) {
    return new Response('Not found', { status: 404 });
  }

  const key = resolved.key;
  const object = await env.SPACES_BUCKET.get(key);
  if (!object) {
    return new Response('Not found', { status: 404 });
  }

  const headers = new Headers(corsHeaders);
  object.writeHttpMetadata(headers);
  headers.set('Cache-Control', object.httpMetadata?.cacheControl || DEFAULT_CACHE_CONTROL);
  headers.set('Content-Type', object.httpMetadata?.contentType || 'text/html; charset=utf-8');
  headers.set('ETag', object.httpEtag);

  return new Response(object.body, { status: 200, headers });
}

export default {
  async fetch(request: Request, env: Env): Promise<Response> {
    if (request.method === 'OPTIONS') {
      return new Response(null, { status: 204, headers: corsHeaders });
    }

    const url = new URL(request.url);
    const prefix = normalizePrefix(env.SPACES_PATH_PREFIX);
    const pathname = stripPrefix(url.pathname, prefix);

    if (pathname === '/health') {
      return new Response('ok', { status: 200, headers: corsHeaders });
    }

    if (pathname === '/publish') {
      if (request.method !== 'POST') {
        return jsonResponse(405, { error: 'Method not allowed' });
      }
      return handlePublish(request, env);
    }

    if (request.method === 'GET' || request.method === 'HEAD') {
      return handleViewer(request, env, pathname);
    }

    return jsonResponse(404, { error: 'Not found' });
  },
};
