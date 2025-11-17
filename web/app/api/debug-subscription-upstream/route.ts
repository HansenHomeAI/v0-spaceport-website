import { resolveSubscriptionApiUrl } from 'lib/subscriptionApi';

export const runtime = 'edge';

export async function GET(): Promise<Response> {
  const target = resolveSubscriptionApiUrl('/subscription-status');
  const { diagnostics } = target;

  return new Response(
    JSON.stringify({
      configured: target.kind === 'ok',
      error: target.kind === 'error' ? target.error : undefined,
      rawBase: diagnostics.rawBase,
      normalizedBase: diagnostics.normalizedBase,
      baseWithPrefix: diagnostics.baseWithPrefix,
      resolvedUrl: diagnostics.resolvedUrl,
      hasTrailingSlash: diagnostics.hasTrailingSlash,
      hasSubscriptionSuffix: diagnostics.hasSubscriptionSuffix,
    }),
    {
      status: 200,
      headers: { 'content-type': 'application/json; charset=utf-8' }
    }
  );
}
