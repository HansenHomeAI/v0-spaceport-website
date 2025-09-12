export const runtime = 'edge';

export async function POST(request: Request): Promise<Response> {
  try {
    // Get the subscription API URL from environment variables
    const subscriptionApiUrl = process.env.NEXT_PUBLIC_SUBSCRIPTION_API_URL;
    
    if (!subscriptionApiUrl) {
      return new Response(
        JSON.stringify({ error: 'Subscription API URL not configured' }),
        { 
          status: 500,
          headers: { 'content-type': 'application/json; charset=utf-8' }
        }
      );
    }

    // Forward the request to the AWS Lambda API
    const response = await fetch(`${subscriptionApiUrl}/cancel-subscription`, {
      method: 'POST',
      headers: {
        'Authorization': request.headers.get('Authorization') || '',
        'Content-Type': 'application/json',
      },
    });

    const data = await response.json();
    
    return new Response(JSON.stringify(data), {
      status: response.status,
      headers: {
        'content-type': 'application/json; charset=utf-8',
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Methods': 'POST, OPTIONS',
        'Access-Control-Allow-Headers': 'Content-Type, Authorization',
      }
    });

  } catch (error) {
    console.error('Error proxying cancel subscription request:', error);
    return new Response(
      JSON.stringify({ error: 'Failed to cancel subscription' }),
      { 
        status: 500,
        headers: { 'content-type': 'application/json; charset=utf-8' }
      }
    );
  }
}

export async function OPTIONS(): Promise<Response> {
  return new Response(null, {
    status: 200,
    headers: {
      'Access-Control-Allow-Origin': '*',
      'Access-Control-Allow-Methods': 'POST, OPTIONS',
      'Access-Control-Allow-Headers': 'Content-Type, Authorization',
    },
  });
}
