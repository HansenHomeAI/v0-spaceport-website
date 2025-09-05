import { NextRequest, NextResponse } from 'next/server';
import { Auth } from 'aws-amplify';

export async function POST(request: NextRequest) {
  try {
    // Verify authentication
    const authHeader = request.headers.get('authorization');
    if (!authHeader || !authHeader.startsWith('Bearer ')) {
      return NextResponse.json(
        { error: 'Unauthorized' },
        { status: 401 }
      );
    }

    const token = authHeader.replace('Bearer ', '');
    
    // Verify JWT token with Cognito
    try {
      await Auth.currentSession();
    } catch (error) {
      return NextResponse.json(
        { error: 'Invalid token' },
        { status: 401 }
      );
    }

    // Forward request to Lambda function
    const lambdaResponse = await fetch(
      `${process.env.SUBSCRIPTION_API_URL}/cancel-subscription`,
      {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      }
    );

    if (!lambdaResponse.ok) {
      const errorData = await lambdaResponse.json();
      return NextResponse.json(
        { error: errorData.error || 'Failed to cancel subscription' },
        { status: lambdaResponse.status }
      );
    }

    const data = await lambdaResponse.json();
    return NextResponse.json(data);

  } catch (error) {
    console.error('Error in cancel-subscription:', error);
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    );
  }
}
