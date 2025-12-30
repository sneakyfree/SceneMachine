/**
 * Main App component with onboarding and global providers.
 */

import { useEffect } from 'react';
import { RouterProvider, createHashRouter } from 'react-router-dom';
import { routes } from './routes';
import { ToastContainer } from './components/toast';
import { Onboarding, useOnboardingStatus } from './components/onboarding';
import { ErrorBoundary, setupGlobalErrorHandlers } from './components/error-boundary';
import { Loader2 } from 'lucide-react';

// Create router (hash router for Electron)
const router = createHashRouter(routes);

export function App() {
  // Set up global error handlers on mount
  useEffect(() => {
    setupGlobalErrorHandlers();
  }, []);
  const { shouldShowOnboarding, isChecking, completeOnboarding, skipOnboarding } =
    useOnboardingStatus();

  // Show loading while checking onboarding status
  if (isChecking) {
    return (
      <div className="h-screen flex items-center justify-center bg-surface-950">
        <Loader2 className="w-8 h-8 text-brand-400 animate-spin" />
      </div>
    );
  }

  // Show onboarding for new users
  if (shouldShowOnboarding) {
    return <Onboarding onComplete={completeOnboarding} onSkip={skipOnboarding} />;
  }

  // Regular app
  return (
    <ErrorBoundary>
      <RouterProvider router={router} />
      <ToastContainer />
    </ErrorBoundary>
  );
}
