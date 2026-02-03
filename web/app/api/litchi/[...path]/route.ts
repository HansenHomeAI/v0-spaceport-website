import { NextRequest, NextResponse } from 'next/server';

export const runtime = 'nodejs';
export const dynamic = 'force-dynamic';

function stripTrailingSlash(rawUrl: string): string {
  return rawUrl.replace(/\/+$/, '');
}

function deriveProjectsBase(rawUrl: string | undefined): string {
  if (!rawUrl) return '';
  const trimmed = stripTrailingSlash(rawUrl.trim());
  if (!trimmed) return '';
  return trimmed.replace(/\/projects$/i, '');
}

function resolveLitchiBase(hostname?: string): { base: string; usingFallback: boolean } {
  const override = (process.env.LITCHI_API_URL || '').trim();
  const overrideBase = override.startsWith('http') ? stripTrailingSlash(override) : '';
  if (overrideBase) return { base: overrideBase, usingFallback: false };

  const isLocalHost = hostname ? (/^(localhost|127\.0\.0\.1)$/).test(hostname) : false;
  if (isLocalHost) {
    return {
      base: deriveProjectsBase(process.env.NEXT_PUBLIC_PROJECTS_API_URL),
      usingFallback: true,
    };
  }

  const publicUrl = (process.env.NEXT_PUBLIC_LITCHI_API_URL || '').trim();
  const publicBase = publicUrl.startsWith('http') ? stripTrailingSlash(publicUrl) : '';
  if (publicBase) return { base: publicBase, usingFallback: false };

  return {
    base: deriveProjectsBase(process.env.NEXT_PUBLIC_PROJECTS_API_URL),
    usingFallback: true,
  };
}

async function proxyLitchi(request: NextRequest, path: string[]) {
  const { base, usingFallback } = resolveLitchiBase(request.nextUrl.hostname);
  if (!base) {
    return NextResponse.json({ error: 'Litchi API is not configured.' }, { status: 500 });
  }

  const targetPath = path.join('/');
  const search = request.nextUrl.search || '';
  const url = `${base}/litchi/${targetPath}${search}`;

  const headers: Record<string, string> = {};
  const authHeader = request.headers.get('authorization');
  if (authHeader) headers.Authorization = authHeader;
  const contentType = request.headers.get('content-type');
  if (contentType) headers['Content-Type'] = contentType;

  const init: RequestInit = {
    method: request.method,
    headers,
  };

  if (!['GET', 'HEAD'].includes(request.method)) {
    const bodyText = await request.text();
    if (bodyText) init.body = bodyText;
  }

  const response = await fetch(url, init);
  const responseText = await response.text();
  const responseContentType = response.headers.get('content-type') || 'application/json';

  if (usingFallback && (response.status === 403 || response.status === 404)) {
    const lower = responseText.toLowerCase();
    if (lower.includes('missing authentication token') || lower.includes('authorization header requires')) {
      return NextResponse.json(
        {
          error: 'Litchi API is not deployed for this environment. Set NEXT_PUBLIC_LITCHI_API_URL or deploy the Litchi API stack.',
        },
        { status: 502 },
      );
    }
  }

  return new NextResponse(responseText, {
    status: response.status,
    headers: {
      'Content-Type': responseContentType,
    },
  });
}

export async function GET(request: NextRequest, context: { params: { path: string[] } }) {
  return proxyLitchi(request, context.params.path);
}

export async function POST(request: NextRequest, context: { params: { path: string[] } }) {
  return proxyLitchi(request, context.params.path);
}
