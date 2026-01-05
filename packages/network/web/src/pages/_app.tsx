/**
 * App Component
 *
 * Global app wrapper that includes providers and global styles.
 */

import type { AppProps } from 'next/app';
import Head from 'next/head';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { useState } from 'react';

// Import global styles
import '../styles/globals.css';

export default function App({ Component, pageProps }: AppProps) {
  // Create a client for each request to avoid sharing state
  const [queryClient] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: {
            staleTime: 60 * 1000, // 1 minute
            refetchOnWindowFocus: false,
          },
        },
      })
  );

  return (
    <>
      <Head>
        <meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover" />
        <meta name="theme-color" content="#0a0a0f" />
        <title>SceneMachine Network</title>
        <meta
          name="description"
          content="Discover and share indie films, series, and creative content on SceneMachine Network."
        />
        <link rel="icon" href="/favicon.ico" />
      </Head>
      <QueryClientProvider client={queryClient}>
        <Component {...pageProps} />
      </QueryClientProvider>
    </>
  );
}
