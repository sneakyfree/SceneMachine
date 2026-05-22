/**
 * React application entry point.
 */

import React from 'react';
import ReactDOM from 'react-dom/client';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import * as Sentry from '@sentry/react';
import { ErrorBoundary } from './components/error-boundary';
import { App } from './App';
import { FeedbackWidget } from './components/feedback-widget';
import './styles/globals.css';

// Create React Query client
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 1000 * 60, // 1 minute
      retry: 2,
      refetchOnWindowFocus: false,
    },
  },
});

// =============================================================================
// Sentry Monitoring Initialization
// =============================================================================

function initializeSentry(): void {
  const sentryDsn = import.meta.env.VITE_SENTRY_DSN;

  if (import.meta.env.PROD && sentryDsn) {
    Sentry.init({
      dsn: sentryDsn,
      environment: import.meta.env.MODE,
      release: import.meta.env.VITE_APP_VERSION || '0.1.0',
      tracesSampleRate: 0.1,
      integrations: [
        Sentry.browserTracingIntegration(),
        Sentry.replayIntegration({
          maskAllText: false,
          blockAllMedia: false,
        }),
      ],
      replaysSessionSampleRate: 0.1,
      replaysOnErrorSampleRate: 1.0,
    });
    console.log('[App] Sentry monitoring initialized');
  }
}

// =============================================================================
// PWA Service Worker Registration (via vite-plugin-pwa)
// =============================================================================

async function registerPWA(): Promise<void> {
  if (import.meta.env.PROD) {
    try {
      const { registerSW } = await import('virtual:pwa-register');

      const updateSW = registerSW({
        onNeedRefresh() {
          // Show update notification to user
          if (confirm('New version available. Reload to update?')) {
            updateSW(true);
          }
        },
        onOfflineReady() {
          console.log('[PWA] App is ready for offline use');
        },
        onRegistered(registration) {
          console.log('[PWA] Service Worker registered:', registration?.scope);
        },
        onRegisterError(error) {
          console.error('[PWA] Service Worker registration failed:', error);
        },
      });
    } catch (error) {
      console.debug('[PWA] PWA registration not available:', error);
    }
  }
}

// =============================================================================
// Application Initialization
// =============================================================================

function initializeApp(): void {
  console.log('[App] SceneMachine starting...', {
    version: import.meta.env.VITE_APP_VERSION || 'dev',
    mode: import.meta.env.MODE,
  });

  initializeSentry();
  registerPWA();
}

// Initialize
initializeApp();

// =============================================================================
// Render Application
// =============================================================================

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <Sentry.ErrorBoundary
      fallback={
        <ErrorBoundary>
          <div>An error has occurred.</div>
        </ErrorBoundary>
      }
      showDialog
    >
      <ErrorBoundary>
        <QueryClientProvider client={queryClient}>
          <App />
          {/* Global feedback widget - Shift+F to toggle */}
          <FeedbackWidget sessionId={crypto.randomUUID()} position="bottom-right" />
        </QueryClientProvider>
      </ErrorBoundary>
    </Sentry.ErrorBoundary>
  </React.StrictMode>
);
