export const runtime = 'edge';

export async function GET(): Promise<Response> {
  const envVars = {
    SUBSCRIPTION_API_URL: process.env.NEXT_PUBLIC_SUBSCRIPTION_API_URL ? 'SET' : 'NOT SET',
    STRIPE_PUBLISHABLE_KEY: process.env.NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY ? 'SET' : 'NOT SET',
  };

  return new Response(JSON.stringify(envVars), {
    status: 200,
    headers: { 'content-type': 'application/json; charset=utf-8' }
  });
}
