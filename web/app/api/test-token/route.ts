export const runtime = 'edge';

export async function GET(request: Request): Promise<Response> {
  try {
    const authHeader = request.headers.get('Authorization');
    
    if (!authHeader) {
      return new Response(JSON.stringify({
        error: 'No Authorization header',
        received: false
      }), {
        status: 200,
        headers: {
          'Content-Type': 'application/json',
          'Access-Control-Allow-Origin': '*',
        },
      });
    }

    // Extract token
    const token = authHeader.replace('Bearer ', '');
    
    // Basic token structure check
    const parts = token.split('.');
    const isValidJWT = parts.length === 3;
    
    // Try to decode the header (without verification)
    let header;
    let payload;
    try {
      header = JSON.parse(atob(parts[0]));
      payload = JSON.parse(atob(parts[1]));
    } catch (e) {
      header = null;
      payload = null;
    }

    return new Response(JSON.stringify({
      received: true,
      isValidJWT,
      tokenLength: token.length,
      header,
      payload: payload ? {
        iss: payload.iss,
        aud: payload.aud,
        token_use: payload.token_use,
        sub: payload.sub,
        client_id: payload.client_id
      } : null
    }), {
      status: 200,
      headers: {
        'Content-Type': 'application/json',
        'Access-Control-Allow-Origin': '*',
      },
    });
  } catch (error: any) {
    return new Response(JSON.stringify({
      error: error.message,
    }), {
      status: 500,
      headers: {
        'Content-Type': 'application/json',
        'Access-Control-Allow-Origin': '*',
      },
    });
  }
}
