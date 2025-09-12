export const runtime = 'edge';
export async function GET(request: Request): Promise<Response> {
  const authHeader = request.headers.get('authorization');
  const token = authHeader?.replace('Bearer ', '');
  
  return new Response(JSON.stringify({
    hasAuthHeader: !!authHeader,
    tokenLength: token?.length || 0,
    tokenPrefix: token?.substring(0, 20) + '...',
    fullToken: token, // For debugging - remove in production
  }), {
    status: 200,
    headers: { 'content-type': 'application/json; charset=utf-8' },
  });
}
