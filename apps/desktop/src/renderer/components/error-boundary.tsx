/**
 * Error boundary component for catching React errors.
 * Provides error logging, user feedback, and recovery options.
 */

import React, { Component, ErrorInfo, ReactNode, useCallback } from 'react';
import { AlertTriangle, RefreshCw, Home, Bug, Copy, CheckCircle, ChevronDown, ChevronUp } from 'lucide-react';

interface Props {
  children: ReactNode;
  fallback?: ReactNode;
  onError?: (error: Error, errorInfo: ErrorInfo) => void;
}

interface State {
  hasError: boolean;
  error: Error | null;
  errorInfo: ErrorInfo | null;
  showDetails: boolean;
  copied: boolean;
}

export class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = {
      hasError: false,
      error: null,
      errorInfo: null,
      showDetails: false,
      copied: false,
    };
  }

  static getDerivedStateFromError(error: Error): Partial<State> {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    this.setState({ errorInfo });

    // Log error to console
    console.error('Error caught by ErrorBoundary:', error, errorInfo);

    // Call optional error handler
    this.props.onError?.(error, errorInfo);

    // Log to backend for error tracking
    this.logErrorToBackend(error, errorInfo);
  }

  private async logErrorToBackend(error: Error, errorInfo: ErrorInfo) {
    try {
      if (window.electronAPI?.backendRequest) {
        await window.electronAPI.backendRequest('system.logError', {
          type: 'react_error_boundary',
          message: error.message,
          stack: error.stack,
          componentStack: errorInfo.componentStack,
          timestamp: new Date().toISOString(),
          url: window.location.href,
          userAgent: navigator.userAgent,
        });
      }
    } catch {
      // Silently fail - don't compound the error
    }
  }

  handleReload = () => {
    window.location.reload();
  };

  handleGoHome = () => {
    window.location.hash = '#/';
    this.setState({ hasError: false, error: null, errorInfo: null, showDetails: false, copied: false });
  };

  handleRetry = () => {
    this.setState({ hasError: false, error: null, errorInfo: null, showDetails: false, copied: false });
  };

  toggleDetails = () => {
    this.setState((prev) => ({ showDetails: !prev.showDetails }));
  };

  copyErrorDetails = async () => {
    const { error, errorInfo } = this.state;
    const details = `Error: ${error?.message}\n\nStack Trace:\n${error?.stack}\n\nComponent Stack:${errorInfo?.componentStack}`;

    try {
      await navigator.clipboard.writeText(details);
      this.setState({ copied: true });
      setTimeout(() => this.setState({ copied: false }), 2000);
    } catch {
      // Fallback for older browsers
      console.log(details);
    }
  };

  handleReportBug = () => {
    const { error, errorInfo } = this.state;
    const title = encodeURIComponent(`[Bug] ${error?.message?.slice(0, 50) || 'Unknown error'}`);
    const body = encodeURIComponent(
      `## Error Report\n\n**Error Message:** ${error?.message}\n\n**Stack Trace:**\n\`\`\`\n${error?.stack?.slice(0, 1500)}\n\`\`\`\n\n**Component Stack:**\n\`\`\`${errorInfo?.componentStack?.slice(0, 1000)}\n\`\`\`\n\n**Environment:**\n- URL: ${window.location.href}\n- User Agent: ${navigator.userAgent}\n- Timestamp: ${new Date().toISOString()}`
    );
    window.open(`https://github.com/scenemachine/scenemachine/issues/new?title=${title}&body=${body}`, '_blank');
  };

  render() {
    if (this.state.hasError) {
      // Custom fallback UI
      if (this.props.fallback) {
        return this.props.fallback;
      }

      const { error, errorInfo, showDetails, copied } = this.state;

      return (
        <div className="min-h-screen bg-surface-950 flex items-center justify-center p-8">
          <div className="max-w-lg w-full">
            {/* Error icon */}
            <div className="text-center mb-8">
              <div className="w-20 h-20 bg-red-500/10 rounded-full flex items-center justify-center mx-auto mb-4">
                <AlertTriangle className="w-10 h-10 text-red-400" />
              </div>
              <h1 className="text-2xl font-bold text-white mb-2">
                Something went wrong
              </h1>
              <p className="text-surface-400">
                An unexpected error occurred. You can try again or go back to the home screen.
              </p>
            </div>

            {/* Error message summary */}
            <div className="mb-6 bg-surface-900 border border-surface-800 rounded-lg p-4">
              <p className="text-red-400 font-mono text-sm break-all">
                {error?.message || 'Unknown error'}
              </p>
            </div>

            {/* Action buttons */}
            <div className="flex flex-col sm:flex-row gap-3 mb-6">
              <button
                onClick={this.handleRetry}
                className="flex-1 px-4 py-3 bg-brand-500 hover:bg-brand-600 text-white rounded-lg font-medium flex items-center justify-center gap-2 transition-colors"
              >
                <RefreshCw className="w-4 h-4" />
                Try Again
              </button>
              <button
                onClick={this.handleGoHome}
                className="flex-1 px-4 py-3 bg-surface-700 hover:bg-surface-600 text-white rounded-lg font-medium flex items-center justify-center gap-2 transition-colors"
              >
                <Home className="w-4 h-4" />
                Go Home
              </button>
            </div>

            {/* Technical details toggle */}
            <button
              onClick={this.toggleDetails}
              className="w-full flex items-center justify-center gap-2 py-2 text-surface-400 hover:text-surface-200 transition-colors"
            >
              {showDetails ? (
                <ChevronUp className="w-4 h-4" />
              ) : (
                <ChevronDown className="w-4 h-4" />
              )}
              {showDetails ? 'Hide' : 'Show'} Technical Details
            </button>

            {/* Technical details */}
            {showDetails && (
              <div className="mt-4 space-y-4">
                {/* Stack trace */}
                <div className="bg-surface-900 border border-surface-800 rounded-lg p-4">
                  <div className="flex items-center justify-between mb-2">
                    <h3 className="text-sm font-medium text-surface-300">
                      Stack Trace
                    </h3>
                    <button
                      onClick={this.copyErrorDetails}
                      className="flex items-center gap-1 text-xs text-surface-400 hover:text-surface-200"
                    >
                      {copied ? (
                        <>
                          <CheckCircle className="w-3 h-3 text-green-400" />
                          Copied!
                        </>
                      ) : (
                        <>
                          <Copy className="w-3 h-3" />
                          Copy
                        </>
                      )}
                    </button>
                  </div>
                  <pre className="text-xs text-surface-400 font-mono overflow-x-auto whitespace-pre-wrap max-h-40 overflow-y-auto">
                    {error?.stack || 'No stack trace available'}
                  </pre>
                </div>

                {/* Component stack */}
                {errorInfo?.componentStack && (
                  <div className="bg-surface-900 border border-surface-800 rounded-lg p-4">
                    <h3 className="text-sm font-medium text-surface-300 mb-2">
                      Component Stack
                    </h3>
                    <pre className="text-xs text-surface-400 font-mono overflow-x-auto whitespace-pre-wrap max-h-32 overflow-y-auto">
                      {errorInfo.componentStack}
                    </pre>
                  </div>
                )}

                {/* Report bug button */}
                <button
                  onClick={this.handleReportBug}
                  className="w-full px-4 py-2 bg-surface-800 hover:bg-surface-700 border border-surface-700 rounded-lg text-sm flex items-center justify-center gap-2 transition-colors"
                >
                  <Bug className="w-4 h-4" />
                  Report This Bug
                </button>
              </div>
            )}

            {/* Additional help */}
            <p className="text-center text-sm text-surface-500 mt-6">
              If this problem persists,{' '}
              <button
                onClick={this.handleReload}
                className="text-brand-400 hover:text-brand-300 underline"
              >
                reload the application
              </button>
              .
            </p>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}

// Functional wrapper for use with hooks
export function withErrorBoundary<P extends object>(
  WrappedComponent: React.ComponentType<P>,
  fallback?: ReactNode
) {
  return function WithErrorBoundary(props: P) {
    return (
      <ErrorBoundary fallback={fallback}>
        <WrappedComponent {...props} />
      </ErrorBoundary>
    );
  };
}

// Page-level error boundary with simpler UI
export function PageErrorBoundary({ children }: { children: ReactNode }) {
  return (
    <ErrorBoundary
      fallback={
        <div className="flex flex-col items-center justify-center h-full p-8">
          <AlertTriangle className="w-12 h-12 text-red-400 mb-4" />
          <h2 className="text-xl font-bold mb-2">Page Error</h2>
          <p className="text-surface-400 text-center mb-4">
            This page encountered an error and couldn't be displayed.
          </p>
          <button
            onClick={() => window.location.reload()}
            className="px-4 py-2 bg-brand-500 hover:bg-brand-600 rounded-lg flex items-center gap-2"
          >
            <RefreshCw className="w-4 h-4" />
            Reload Page
          </button>
        </div>
      }
    >
      {children}
    </ErrorBoundary>
  );
}

/**
 * Hook for programmatic error handling.
 * Use this for catching and logging errors in async operations.
 */
export function useErrorHandler() {
  const logError = useCallback(async (error: Error, context?: string) => {
    console.error(`Error${context ? ` in ${context}` : ''}:`, error);

    // Log to backend
    try {
      if (window.electronAPI?.backendRequest) {
        await window.electronAPI.backendRequest('system.logError', {
          type: 'programmatic',
          message: error.message,
          stack: error.stack,
          context,
          timestamp: new Date().toISOString(),
          url: window.location.href,
        });
      }
    } catch {
      // Silently fail
    }
  }, []);

  const wrapAsync = useCallback(<T extends (...args: any[]) => Promise<any>>(
    fn: T,
    context?: string
  ): T => {
    return (async (...args: Parameters<T>) => {
      try {
        return await fn(...args);
      } catch (error) {
        logError(error as Error, context);
        throw error;
      }
    }) as T;
  }, [logError]);

  return { logError, wrapAsync };
}

/**
 * Global error handler setup for unhandled errors.
 * Call this once at app initialization.
 */
export function setupGlobalErrorHandlers() {
  // Handle unhandled promise rejections
  window.addEventListener('unhandledrejection', (event) => {
    console.error('Unhandled promise rejection:', event.reason);

    if (window.electronAPI?.backendRequest) {
      window.electronAPI.backendRequest('system.logError', {
        type: 'unhandled_rejection',
        message: event.reason?.message || String(event.reason),
        stack: event.reason?.stack,
        timestamp: new Date().toISOString(),
        url: window.location.href,
      }).catch(() => {});
    }
  });

  // Handle uncaught errors
  window.addEventListener('error', (event) => {
    console.error('Uncaught error:', event.error);

    if (window.electronAPI?.backendRequest) {
      window.electronAPI.backendRequest('system.logError', {
        type: 'uncaught_error',
        message: event.error?.message || event.message,
        stack: event.error?.stack,
        filename: event.filename,
        lineno: event.lineno,
        colno: event.colno,
        timestamp: new Date().toISOString(),
        url: window.location.href,
      }).catch(() => {});
    }
  });
}
