export interface SubscriptionApiDiagnostics {
  rawBase: string;
  trimmedBase: string;
  normalizedBase: string;
  baseWithPrefix: string;
  normalizedPath: string;
  resolvedUrl: string;
  hasTrailingSlash: boolean;
  hasSubscriptionSuffix: boolean;
}

interface SubscriptionApiResolutionOk {
  kind: 'ok';
  url: string;
  diagnostics: SubscriptionApiDiagnostics;
}

interface SubscriptionApiResolutionError {
  kind: 'error';
  error: string;
  diagnostics: SubscriptionApiDiagnostics;
}

export type SubscriptionApiResolution =
  | SubscriptionApiResolutionOk
  | SubscriptionApiResolutionError;

const SUBSCRIPTION_SEGMENT = 'subscription';

const stripTrailingSlashes = (value: string): string => value.replace(/\/+$/, '');

const joinSegments = (base: string, segment: string): string => {
  const normalizedBase = stripTrailingSlashes(base);
  const normalizedSegment = segment.replace(/^\/+/, '');
  if (!normalizedSegment) {
    return normalizedBase;
  }
  if (!normalizedBase) {
    return normalizedSegment.startsWith('/') ? normalizedSegment : `/${normalizedSegment}`;
  }
  return `${normalizedBase}/${normalizedSegment}`;
};

export const resolveSubscriptionApiUrl = (path: string): SubscriptionApiResolution => {
  const rawBase = process.env.NEXT_PUBLIC_SUBSCRIPTION_API_URL ?? '';
  const trimmedBase = rawBase.trim();
  const normalizedBase = stripTrailingSlashes(trimmedBase);
  const normalizedPath = path.startsWith('/') ? path.slice(1) : path;
  const hasTrailingSlash = Boolean(trimmedBase) && trimmedBase !== normalizedBase;

  let hasSubscriptionSuffix = false;

  if (normalizedBase) {
    try {
      const parsed = new URL(normalizedBase);
      const segments = parsed.pathname.split('/').filter(Boolean);
      const suffix = segments[segments.length - 1];
      hasSubscriptionSuffix = (suffix ?? '').toLowerCase() === SUBSCRIPTION_SEGMENT;
    } catch {
      const segments = normalizedBase.split('/').filter(Boolean);
      const suffix = segments[segments.length - 1];
      hasSubscriptionSuffix = (suffix ?? '').toLowerCase() === SUBSCRIPTION_SEGMENT;
    }
  }

  const baseWithPrefix = normalizedBase
    ? hasSubscriptionSuffix
      ? normalizedBase
      : joinSegments(normalizedBase, SUBSCRIPTION_SEGMENT)
    : '';

  const resolvedUrl = baseWithPrefix
    ? joinSegments(baseWithPrefix, normalizedPath)
    : '';

  const diagnostics: SubscriptionApiDiagnostics = {
    rawBase,
    trimmedBase,
    normalizedBase,
    baseWithPrefix,
    normalizedPath,
    resolvedUrl,
    hasTrailingSlash,
    hasSubscriptionSuffix,
  };

  if (!trimmedBase) {
    return {
      kind: 'error',
      error: 'Subscription API URL not configured',
      diagnostics,
    };
  }

  return {
    kind: 'ok',
    url: resolvedUrl,
    diagnostics,
  };
};
