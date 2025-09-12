export const runtime = 'edge';

export async function GET(): Promise<Response> {
  // Test if we can import and use Auth
  try {
    const { Auth } = await import('aws-amplify');
    
    // Test if we can configure Amplify
    const { configureAmplify } = await import('../amplifyClient');
    const configured = configureAmplify();
    
    return new Response(JSON.stringify({
      amplifyConfigured: configured,
      cognitoRegion: process.env.NEXT_PUBLIC_COGNITO_REGION,
      cognitoUserPoolId: process.env.NEXT_PUBLIC_COGNITO_USER_POOL_ID,
      cognitoUserPoolClientId: process.env.NEXT_PUBLIC_COGNITO_USER_POOL_CLIENT_ID,
      authAvailable: configured,
    }), {
      status: 200,
      headers: { 'content-type': 'application/json; charset=utf-8' },
    });
  } catch (error) {
    return new Response(JSON.stringify({
      error: error instanceof Error ? error.message : 'Unknown error',
      amplifyConfigured: false,
    }), {
      status: 200,
      headers: { 'content-type': 'application/json; charset=utf-8' },
    });
  }
}
