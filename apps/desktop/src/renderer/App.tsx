/**
 * Main App component with onboarding and global providers.
 */

import { useEffect } from 'react';
import { RouterProvider, createHashRouter } from 'react-router-dom';
import { routes } from './routes';
import { ToastContainer } from './components/toast';
import { Onboarding, useOnboardingStatus } from './components/onboarding';
import { ErrorBoundary, setupGlobalErrorHandlers } from './components/error-boundary';
import { useSettingsStore } from './stores/settings-store';
import { Loader2 } from 'lucide-react';

// Import accessibility styles
import './styles/accessibility.css';

// Create router (hash router for Electron)
const router = createHashRouter(routes);

export function App() {
  // Set up global error handlers on mount
  useEffect(() => {
    setupGlobalErrorHandlers();
  }, []);

  const { shouldShowOnboarding, isChecking, completeOnboarding, skipOnboarding } =
    useOnboardingStatus();
  const settings = useSettingsStore((state) => state.settings);

  // Apply accessibility settings to document root
  useEffect(() => {
    if (!settings) return;

    const root = document.documentElement;

    // Apply font scale
    const fontScaleClass = `font-scale-${settings.fontSizeScale || 'medium'}`;
    root.classList.remove(
      'font-scale-small',
      'font-scale-medium',
      'font-scale-large',
      'font-scale-extra-large'
    );
    root.classList.add(fontScaleClass);

    // Apply high contrast mode
    root.classList.toggle('high-contrast', settings.highContrastEnabled || false);

    // Apply reduced motion
    root.classList.toggle('reduce-motion', settings.reduceMotionEnabled || false);

    // Apply large click targets
    root.classList.toggle('large-targets', settings.largeClickTargetsEnabled || false);
  }, [
    settings?.fontSizeScale,
    settings?.highContrastEnabled,
    settings?.reduceMotionEnabled,
    settings?.largeClickTargetsEnabled,
  ]);

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

  // Regular app - StevenAssistant is now inside MainLayout (within router context)
  return (
    <ErrorBoundary>
      <RouterProvider router={router} />
      <ToastContainer />
    </ErrorBoundary>
  );
}
