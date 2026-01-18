"use client";

import { useEffect } from 'react';
import { useParams, useRouter } from 'next/navigation';

/**
 * Redirect /stocks/[ticker] to /us/stocks/[ticker] for backwards compatibility
 */
export default function StockRedirect() {
  const router = useRouter();
  const params = useParams();
  const ticker = params.ticker as string;

  useEffect(() => {
    router.replace(`/us/stocks/${ticker}`);
  }, [router, ticker]);

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-950 via-slate-900 to-slate-950 flex items-center justify-center">
      <div className="text-center">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-400 mx-auto mb-4"></div>
        <p className="text-slate-400">Redirecting to {ticker?.toUpperCase()}...</p>
      </div>
    </div>
  );
}
