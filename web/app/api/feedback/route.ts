export const runtime = 'edge';

type FeedbackPayload = {
  message?: unknown;
  source?: unknown;
};

const normalizeUrl = (value: string | undefined): string => {
  if (!value) return '';
  let normalized = value;
  while (normalized.endsWith('/')) {
    normalized = normalized.slice(0, -1);
  }
  return normalized;
};

const jsonHeaders = {
  'content-type': 'application/json; charset=utf-8',
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Methods': 'POST, OPTIONS',
  'Access-Control-Allow-Headers': 'Content-Type',
};

export async function POST(request: Request): Promise<Response> {
  try {
    const upstreamUrl =
      normalizeUrl(process.env.FEEDBACK_FUNCTION_URL) ||
      normalizeUrl(process.env.NEXT_PUBLIC_FEEDBACK_API_URL);

    if (!upstreamUrl) {
      return new Response(
        JSON.stringify({ success: false, error: 'Feedback endpoint not configured' }),
        { status: 500, headers: jsonHeaders }
      );
    }

    let body: FeedbackPayload = {};
    try {
      body = await request.json();
    } catch {
      return new Response(
        JSON.stringify({ success: false, error: 'Invalid JSON body' }),
        { status: 400, headers: jsonHeaders }
      );
    }

    const message = typeof body.message === 'string' ? body.message.trim() : '';
    if (!message) {
      return new Response(
        JSON.stringify({ success: false, error: 'Feedback message is required' }),
        { status: 400, headers: jsonHeaders }
      );
    }

    const source = typeof body.source === 'string' && body.source.trim()
      ? body.source.trim()
      : 'website-footer';

    const upstreamResponse = await fetch(upstreamUrl, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        message,
        source,
      }),
    });

    let upstreamBody = await upstreamResponse.text();
    if (!upstreamBody) {
      upstreamBody = JSON.stringify({ success: upstreamResponse.ok });
    } else {
      try {
        JSON.parse(upstreamBody);
      } catch {
        upstreamBody = JSON.stringify({ success: upstreamResponse.ok });
      }
    }

    return new Response(upstreamBody, {
      status: upstreamResponse.status,
      headers: jsonHeaders,
    });
  } catch (error) {
    console.error('Failed to proxy feedback submission', error);
    return new Response(
      JSON.stringify({ success: false, error: 'Failed to submit feedback' }),
      { status: 500, headers: jsonHeaders }
    );
  }
}

export async function OPTIONS(): Promise<Response> {
  return new Response(null, {
    status: 200,
    headers: jsonHeaders,
  });
}
