'use client';

import { useEffect } from 'react';
import { useSearchParams, useRouter } from 'next/navigation';
import AuthGate from './AuthGate';

// Component that handles redirect after authentication
function AuthSuccessRedirect() {
  const searchParams = useSearchParams();
  const router = useRouter();
  
  const redirect = searchParams.get('redirect');
  const plan = searchParams.get('plan');
  const referral = searchParams.get('referral');

  useEffect(() => {
    // This will run when the component mounts (after AuthGate renders children)
    // Determine where to redirect after successful authentication
    if (redirect === 'pricing' && plan) {
      // Store plan selection and redirect to pricing
      sessionStorage.setItem('selectedPlan', JSON.stringify({ plan, referral }));
      router.push('/pricing');
    } else if (redirect === 'create') {
      router.push('/create');
    } else {
      // Default redirect to dashboard/create
      router.push('/create');
    }
  }, [redirect, plan, referral, router]);

  return (
    <div className="auth-success">
      <h2>Authentication Successful!</h2>
      <p>Redirecting you now...</p>
    </div>
  );
}

export default function AuthPage(): JSX.Element {
  return (
    <div className="auth-page">
      <AuthGate>
        <AuthSuccessRedirect />
      </AuthGate>
    </div>
  );
}
