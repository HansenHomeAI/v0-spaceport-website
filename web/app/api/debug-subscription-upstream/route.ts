export const runtime = 'edge';

export async function GET(): Promise<Response> {
  const base = process.env.NEXT_PUBLIC_SUBSCRIPTION_API_URL || '';
  const hasProdSuffix = base.endsWith('/prod');
  const hasTrailingSlash = base.endsWith('/');
  const hasSubscriptionTwice = base.includes('/subscription/subscription');
  const samplePath = `${base}/subscription/subscription-status`;
  const hasDoubleSlash = samplePath.includes('//subscription');

  return new Response(
    JSON.stringify({
      configured: Boolean(base),
      hasProdSuffix,
      hasTrailingSlash,
      hasSubscriptionTwice,
      hasDoubleSlash
    }),
    {
      status: 200,
      headers: { 'content-type': 'application/json; charset=utf-8' }
    }
  );
}


