import { NextRequest, NextResponse } from 'next/server';

export const runtime = 'edge';

const FEEDBACK_API_URL =
  process.env.FEEDBACK_API_URL || process.env.NEXT_PUBLIC_FEEDBACK_API_URL;
const FEEDBACK_API_KEY = process.env.FEEDBACK_API_KEY;

const FAILURE_MESSAGE = 'Unable to submit feedback right now. Please try again.';

const buildHeaders = () => {
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
  };

  if (FEEDBACK_API_KEY) {
    headers['x-api-key'] = FEEDBACK_API_KEY;
  }

  return headers;
};

export async function POST(request: NextRequest) {
  let payload: unknown;

  try {
    payload = await request.json();
  } catch (error) {
    return NextResponse.json(
      { success: false, error: 'Invalid request body' },
      { status: 400 },
    );
  }

  if (!payload || typeof payload !== 'object') {
    return NextResponse.json(
      { success: false, error: 'Invalid request body' },
      { status: 400 },
    );
  }

  const message = typeof (payload as any).message === 'string'
    ? (payload as any).message.trim()
    : '';
  const source = typeof (payload as any).source === 'string' && (payload as any).source.trim()
    ? (payload as any).source.trim()
    : 'web-footer';

  if (!message) {
    return NextResponse.json(
      { success: false, error: 'Feedback message is required' },
      { status: 400 },
    );
  }

  if (!FEEDBACK_API_URL) {
    console.error('[feedback] FEEDBACK_API_URL is not configured.');
    return NextResponse.json(
      {
        success: false,
        error: FAILURE_MESSAGE,
      },
      { status: 500 },
    );
  }

  try {
    const upstreamResponse = await fetch(FEEDBACK_API_URL, {
      method: 'POST',
      headers: buildHeaders(),
      body: JSON.stringify({ message, source }),
    });

    const contentType = upstreamResponse.headers.get('content-type') || '';
    const isJson = contentType.includes('application/json');

    const body = isJson
      ? await upstreamResponse.json().catch(() => null)
      : await upstreamResponse.text();

    if (!upstreamResponse.ok || (isJson && body && body.success === false)) {
      const errorMessage =
        (isJson && body?.error) || (typeof body === 'string' ? body : FAILURE_MESSAGE);
      console.error('[feedback] Upstream error:', errorMessage);
      return NextResponse.json(
        {
          success: false,
          error: typeof errorMessage === 'string' ? errorMessage : FAILURE_MESSAGE,
        },
        { status: upstreamResponse.status || 502 },
      );
    }

    return NextResponse.json(
      {
        success: true,
        message:
          (isJson && body?.message) || 'Feedback sent successfully',
      },
      { status: 200 },
    );
  } catch (error) {
    console.error('[feedback] Failed to reach upstream lambda:', error);
    return NextResponse.json(
      {
        success: false,
        error: FAILURE_MESSAGE,
      },
      { status: 502 },
    );
  }
}

export function OPTIONS() {
  return NextResponse.json({}, { status: 204 });
}
