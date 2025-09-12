import { NextRequest, NextResponse } from 'next/server';

export async function POST(request: NextRequest) {
  try {
    // Get the subscription API URL from environment variables
    const subscriptionApiUrl = process.env.NEXT_PUBLIC_SUBSCRIPTION_API_URL;
    
    if (!subscriptionApiUrl) {
      return NextResponse.json(
        { error: 'Subscription API URL not configured' },
        { status: 500 }
      );
    }

    // Get the request body
    const body = await request.json();

    // Forward the request to the AWS Lambda API
    const response = await fetch(`${subscriptionApiUrl}/create-checkout-session`, {
      method: 'POST',
      headers: {
        'Authorization': request.headers.get('Authorization') || '',
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(body),
    });

    const data = await response.json();
    
    return NextResponse.json(data, { 
      status: response.status,
      headers: {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Methods': 'POST, OPTIONS',
        'Access-Control-Allow-Headers': 'Content-Type, Authorization',
      }
    });

  } catch (error) {
    console.error('Error proxying checkout session request:', error);
    return NextResponse.json(
      { error: 'Failed to create checkout session' },
      { status: 500 }
    );
  }
}

export async function OPTIONS() {
  return new NextResponse(null, {
    status: 200,
    headers: {
      'Access-Control-Allow-Origin': '*',
      'Access-Control-Allow-Methods': 'POST, OPTIONS',
      'Access-Control-Allow-Headers': 'Content-Type, Authorization',
    },
  });
}
