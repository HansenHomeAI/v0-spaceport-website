'use client';

import { useTransition } from 'react';
import { useRouter } from 'next/navigation';

export function JoinWaitlistButton(): JSX.Element {
  const router = useRouter();
  const [isPending, startTransition] = useTransition();

  const handleClick = (): void => {
    if (isPending) return;

    startTransition(() => {
      router.push('/create');
    });
  };

  return (
    <button
      type="button"
      className={`cta-button${isPending ? ' is-loading' : ''}`}
      onClick={handleClick}
      disabled={isPending}
      data-testid="join-waitlist-button"
    >
      {isPending ? (
        <>
          <span className="cta-button-spinner" aria-hidden="true" />
          Opening...
        </>
      ) : (
        'Join waitlist'
      )}
    </button>
  );
}
