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

    const body = await request.json();
    const { planType, userId, referralCode } = body;

    if (!planType || !userId) {
      return NextResponse.json(
        { error: 'Missing planType or userId' },
        { status: 400 }
      );
    }

    // Forward request to Lambda function
    const lambdaResponse = await fetch(
      `${process.env.SUBSCRIPTION_API_URL}/create-checkout-session`,
      {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
        },
        body: JSON.stringify({
          planType,
          userId,
          referralCode,
        }),
      }
    );

    if (!lambdaResponse.ok) {
      const errorData = await lambdaResponse.json();
      return NextResponse.json(
        { error: errorData.error || 'Failed to create checkout session' },
        { status: lambdaResponse.status }
      );
    }

    const data = await lambdaResponse.json();
    return NextResponse.json(data);

  } catch (error) {
    console.error('Error in create-checkout-session:', error);
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    );
  }
}
