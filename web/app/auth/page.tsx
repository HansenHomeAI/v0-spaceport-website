'use client';

import { useEffect } from 'react';
import { useSearchParams, useRouter } from 'next/navigation';
import AuthGate from './AuthGate';

export default function AuthPage(): JSX.Element {
  const searchParams = useSearchParams();
  const router = useRouter();
  
  const redirect = searchParams.get('redirect');
  const plan = searchParams.get('plan');
  const referral = searchParams.get('referral');

  useEffect(() => {
    // This effect will run after successful authentication
    // AuthGate will handle the authentication flow
  }, []);

  const handleAuthSuccess = () => {
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
  };

  return (
    <div className="auth-page">
      <AuthGate>
        <div className="auth-success">
          <h2>Authentication Successful!</h2>
          <p>Redirecting you now...</p>
          {handleAuthSuccess()}
        </div>
      </AuthGate>
    </div>
  );
}
