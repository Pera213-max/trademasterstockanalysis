'use client';

import React from 'react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { PersistQueryClientProvider } from '@tanstack/react-query-persist-client';
import { createSyncStoragePersister } from '@tanstack/query-sync-storage-persister';
import { ThemeProvider } from '@/lib/theme-context';

// Create a client
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 1000 * 60 * 5, // 5 minutes
      gcTime: 1000 * 60 * 30, // 30 minutes (formerly cacheTime)
      refetchOnWindowFocus: false,
      retry: 2,
    },
  },
});

const createPersister = () => {
  if (typeof window === 'undefined') {
    return undefined;
  }
  return createSyncStoragePersister({
    storage: window.localStorage,
    key: 'tm_query_cache',
    throttleTime: 1000,
  });
};

export function Providers({ children }: { children: React.ReactNode }) {
  const persister = React.useMemo(() => createPersister(), []);

  if (!persister) {
    return (
      <QueryClientProvider client={queryClient}>
        <ThemeProvider>
          {children}
        </ThemeProvider>
      </QueryClientProvider>
    );
  }

  return (
    <PersistQueryClientProvider
      client={queryClient}
      persistOptions={{
        persister,
        maxAge: 1000 * 60 * 30,
        buster: 'v1',
      }}
    >
      <ThemeProvider>
        {children}
      </ThemeProvider>
    </PersistQueryClientProvider>
  );
}
