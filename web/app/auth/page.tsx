'use client';

export const runtime = 'edge';

import { useCallback, useEffect, useMemo } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import AuthGate from './AuthGate';

const ALLOWED_REDIRECTS = new Set(['pricing', 'create']);
const VALID_PLANS = new Set(['single', 'starter', 'growth']);

export default function AuthPage(): JSX.Element {
  const router = useRouter();
  const searchParams = useSearchParams();

  const planParam = (searchParams.get('plan') || '').toLowerCase();
  const referralParamRaw = searchParams.get('ref') || searchParams.get('referral') || '';
  const referralParam = referralParamRaw.trim() || undefined;
  const redirectParam = (searchParams.get('redirect') || '').toLowerCase();

  const plan = VALID_PLANS.has(planParam) ? (planParam as 'single' | 'starter' | 'growth') : null;

  const redirectTarget = useMemo(() => {
    if (ALLOWED_REDIRECTS.has(redirectParam)) {
      return redirectParam;
    }
    return plan ? 'pricing' : 'create';
  }, [plan, redirectParam]);

  useEffect(() => {
    if (!plan) return;
    if (typeof window === 'undefined') return;

    window.sessionStorage.setItem(
      'selectedPlan',
      JSON.stringify({ plan, referral: referralParam || null })
    );
  }, [plan, referralParam]);

  const handleAuthenticated = useCallback(() => {
    const destination = redirectTarget.startsWith('/') ? redirectTarget : `/${redirectTarget}`;
    router.replace(destination);
  }, [redirectTarget, router]);

  return (
    <AuthGate onAuthenticated={handleAuthenticated}>
      <div style={{ padding: '48px 24px', textAlign: 'center' }}>
        <h2 style={{ marginBottom: 12 }}>Signed in successfully</h2>
        <p style={{ color: '#bbb' }}>Redirecting you now…</p>
      </div>
    </AuthGate>
  );
}
