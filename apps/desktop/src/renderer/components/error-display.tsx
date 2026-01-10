/**
 * Error Display Components
 *
 * Provides consistent error UI with retry functionality,
 * timeout indicators, and recovery hints.
 */

import React, { useState, useEffect, useCallback } from 'react';
import {
  AlertTriangle,
  AlertCircle,
  WifiOff,
  Clock,
  RefreshCw,
  X,
  ChevronDown,
  ChevronUp,
  ExternalLink,
  Info,
  ServerCrash,
  KeyRound,
  HardDrive,
  Gauge,
  Zap,
} from 'lucide-react';
import { cn } from '../lib/utils';
import {
  AppError,
  ErrorCategory,
  ErrorCode,
  classifyError,
  formatErrorForDisplay,
} from '../lib/errors';

// ============================================================================
// Types
// ============================================================================

interface ErrorDisplayProps {
  error: unknown;
  onRetry?: () => void;
  onDismiss?: () => void;
  className?: string;
  variant?: 'inline' | 'banner' | 'card' | 'toast';
  showDetails?: boolean;
  showRetryCountdown?: boolean;
  autoRetry?: boolean;
  compact?: boolean;
}

interface RetryState {
  isRetrying: boolean;
  countdown: number;
  attemptsMade: number;
}

// ============================================================================
// Icon Mapping
// ============================================================================

function getCategoryIcon(category: ErrorCategory): React.ReactNode {
  switch (category) {
    case ErrorCategory.NETWORK:
      return <WifiOff className="w-5 h-5" />;
    case ErrorCategory.AUTH:
      return <KeyRound className="w-5 h-5" />;
    case ErrorCategory.TIMEOUT:
      return <Clock className="w-5 h-5" />;
    case ErrorCategory.RATE_LIMIT:
      return <Gauge className="w-5 h-5" />;
    case ErrorCategory.SERVER:
      return <ServerCrash className="w-5 h-5" />;
    case ErrorCategory.STORAGE:
      return <HardDrive className="w-5 h-5" />;
    case ErrorCategory.PROVIDER:
    case ErrorCategory.GENERATION:
      return <Zap className="w-5 h-5" />;
    case ErrorCategory.NOT_FOUND:
    case ErrorCategory.VALIDATION:
    case ErrorCategory.PERMISSION:
      return <AlertCircle className="w-5 h-5" />;
    default:
      return <AlertTriangle className="w-5 h-5" />;
  }
}

function getCategoryColor(category: ErrorCategory): string {
  switch (category) {
    case ErrorCategory.NETWORK:
    case ErrorCategory.TIMEOUT:
      return 'text-amber-400 bg-amber-400/10 border-amber-400/30';
    case ErrorCategory.AUTH:
    case ErrorCategory.PERMISSION:
      return 'text-orange-400 bg-orange-400/10 border-orange-400/30';
    case ErrorCategory.RATE_LIMIT:
      return 'text-yellow-400 bg-yellow-400/10 border-yellow-400/30';
    case ErrorCategory.SERVER:
    case ErrorCategory.PROVIDER:
    case ErrorCategory.GENERATION:
      return 'text-red-400 bg-red-400/10 border-red-400/30';
    case ErrorCategory.STORAGE:
      return 'text-purple-400 bg-purple-400/10 border-purple-400/30';
    case ErrorCategory.VALIDATION:
    case ErrorCategory.NOT_FOUND:
      return 'text-blue-400 bg-blue-400/10 border-blue-400/30';
    default:
      return 'text-red-400 bg-red-400/10 border-red-400/30';
  }
}

// ============================================================================
// Main Error Display Component
// ============================================================================

export function ErrorDisplay({
  error,
  onRetry,
  onDismiss,
  className,
  variant = 'card',
  showDetails = false,
  showRetryCountdown = true,
  autoRetry = false,
  compact = false,
}: ErrorDisplayProps) {
  const [appError] = useState(() => classifyError(error));
  const [isExpanded, setIsExpanded] = useState(showDetails);
  const [retryState, setRetryState] = useState<RetryState>({
    isRetrying: false,
    countdown: 0,
    attemptsMade: 0,
  });

  const formatted = formatErrorForDisplay(error);
  const colorClass = getCategoryColor(appError.category);
  const icon = getCategoryIcon(appError.category);

  // Auto-retry countdown
  useEffect(() => {
    if (autoRetry && appError.canRetry && retryState.attemptsMade < appError.retryCount) {
      const countdownStart = Math.ceil(appError.retryDelay / 1000);
      setRetryState((prev) => ({ ...prev, countdown: countdownStart }));

      const interval = setInterval(() => {
        setRetryState((prev) => {
          if (prev.countdown <= 1) {
            clearInterval(interval);
            return { ...prev, countdown: 0, isRetrying: true };
          }
          return { ...prev, countdown: prev.countdown - 1 };
        });
      }, 1000);

      return () => clearInterval(interval);
    }
  }, [autoRetry, appError, retryState.attemptsMade]);

  // Handle auto-retry trigger
  useEffect(() => {
    if (retryState.isRetrying && onRetry) {
      onRetry();
      setRetryState((prev) => ({
        ...prev,
        isRetrying: false,
        attemptsMade: prev.attemptsMade + 1,
      }));
    }
  }, [retryState.isRetrying, onRetry]);

  const handleRetry = useCallback(() => {
    setRetryState((prev) => ({
      ...prev,
      attemptsMade: prev.attemptsMade + 1,
    }));
    onRetry?.();
  }, [onRetry]);

  const handleHelpClick = useCallback(() => {
    if (appError.helpLink) {
      window.location.hash = appError.helpLink;
    }
  }, [appError.helpLink]);

  // Render based on variant
  switch (variant) {
    case 'inline':
      return (
        <InlineError
          icon={icon}
          message={formatted.message}
          hint={formatted.hint}
          canRetry={formatted.canRetry}
          onRetry={handleRetry}
          colorClass={colorClass}
          className={className}
          compact={compact}
        />
      );

    case 'banner':
      return (
        <BannerError
          icon={icon}
          message={formatted.message}
          hint={formatted.hint}
          canRetry={formatted.canRetry}
          onRetry={handleRetry}
          onDismiss={onDismiss}
          colorClass={colorClass}
          className={className}
          countdown={showRetryCountdown ? retryState.countdown : 0}
        />
      );

    case 'toast':
      return (
        <ToastError
          icon={icon}
          message={formatted.message}
          onDismiss={onDismiss}
          colorClass={colorClass}
          className={className}
        />
      );

    case 'card':
    default:
      return (
        <CardError
          appError={appError}
          icon={icon}
          title={formatted.title}
          message={formatted.message}
          hint={formatted.hint}
          canRetry={formatted.canRetry}
          onRetry={handleRetry}
          onDismiss={onDismiss}
          onHelpClick={appError.helpLink ? handleHelpClick : undefined}
          colorClass={colorClass}
          className={className}
          isExpanded={isExpanded}
          onToggleExpand={() => setIsExpanded(!isExpanded)}
          retryState={retryState}
          showRetryCountdown={showRetryCountdown}
        />
      );
  }
}

// ============================================================================
// Inline Error Component
// ============================================================================

interface InlineErrorProps {
  icon: React.ReactNode;
  message: string;
  hint: string;
  canRetry: boolean;
  onRetry?: () => void;
  colorClass: string;
  className?: string;
  compact?: boolean;
}

function InlineError({
  icon,
  message,
  hint,
  canRetry,
  onRetry,
  colorClass,
  className,
  compact,
}: InlineErrorProps) {
  return (
    <div
      className={cn(
        'flex items-center gap-2 px-3 py-2 rounded-lg border',
        colorClass,
        className
      )}
      role="alert"
    >
      {icon}
      <div className="flex-1 min-w-0">
        <p className={cn('font-medium', compact ? 'text-xs' : 'text-sm')}>
          {message}
        </p>
        {!compact && hint && (
          <p className="text-xs opacity-80 truncate">{hint}</p>
        )}
      </div>
      {canRetry && onRetry && (
        <button
          onClick={onRetry}
          className="p-1 hover:bg-white/10 rounded transition-colors"
          aria-label="Retry"
        >
          <RefreshCw className="w-4 h-4" />
        </button>
      )}
    </div>
  );
}

// ============================================================================
// Banner Error Component
// ============================================================================

interface BannerErrorProps {
  icon: React.ReactNode;
  message: string;
  hint: string;
  canRetry: boolean;
  onRetry?: () => void;
  onDismiss?: () => void;
  colorClass: string;
  className?: string;
  countdown?: number;
}

function BannerError({
  icon,
  message,
  hint,
  canRetry,
  onRetry,
  onDismiss,
  colorClass,
  className,
  countdown = 0,
}: BannerErrorProps) {
  return (
    <div
      className={cn(
        'flex items-center gap-3 px-4 py-3 border-b',
        colorClass.replace('rounded-lg', ''),
        className
      )}
      role="alert"
    >
      {icon}
      <div className="flex-1 min-w-0">
        <p className="font-medium text-sm">{message}</p>
        <p className="text-xs opacity-80">{hint}</p>
      </div>
      <div className="flex items-center gap-2">
        {countdown > 0 && (
          <span className="text-xs opacity-70">Retrying in {countdown}s...</span>
        )}
        {canRetry && onRetry && !countdown && (
          <button
            onClick={onRetry}
            className="px-3 py-1 text-sm bg-white/10 hover:bg-white/20 rounded transition-colors flex items-center gap-1"
          >
            <RefreshCw className="w-3 h-3" />
            Retry
          </button>
        )}
        {onDismiss && (
          <button
            onClick={onDismiss}
            className="p-1 hover:bg-white/10 rounded transition-colors"
            aria-label="Dismiss"
          >
            <X className="w-4 h-4" />
          </button>
        )}
      </div>
    </div>
  );
}

// ============================================================================
// Toast Error Component
// ============================================================================

interface ToastErrorProps {
  icon: React.ReactNode;
  message: string;
  onDismiss?: () => void;
  colorClass: string;
  className?: string;
}

function ToastError({
  icon,
  message,
  onDismiss,
  colorClass,
  className,
}: ToastErrorProps) {
  return (
    <div
      className={cn(
        'flex items-center gap-2 px-4 py-3 rounded-lg border shadow-lg',
        colorClass,
        className
      )}
      role="alert"
    >
      {icon}
      <p className="text-sm font-medium flex-1">{message}</p>
      {onDismiss && (
        <button
          onClick={onDismiss}
          className="p-1 hover:bg-white/10 rounded transition-colors"
          aria-label="Dismiss"
        >
          <X className="w-4 h-4" />
        </button>
      )}
    </div>
  );
}

// ============================================================================
// Card Error Component
// ============================================================================

interface CardErrorProps {
  appError: AppError;
  icon: React.ReactNode;
  title: string;
  message: string;
  hint: string;
  canRetry: boolean;
  onRetry?: () => void;
  onDismiss?: () => void;
  onHelpClick?: () => void;
  colorClass: string;
  className?: string;
  isExpanded: boolean;
  onToggleExpand: () => void;
  retryState: RetryState;
  showRetryCountdown: boolean;
}

function CardError({
  appError,
  icon,
  title,
  message,
  hint,
  canRetry,
  onRetry,
  onDismiss,
  onHelpClick,
  colorClass,
  className,
  isExpanded,
  onToggleExpand,
  retryState,
  showRetryCountdown,
}: CardErrorProps) {
  return (
    <div
      className={cn(
        'rounded-lg border overflow-hidden',
        colorClass,
        className
      )}
      role="alert"
      aria-live="polite"
    >
      {/* Header */}
      <div className="flex items-start gap-3 p-4">
        <div className="mt-0.5">{icon}</div>
        <div className="flex-1 min-w-0">
          <h3 className="font-semibold text-sm">{title}</h3>
          <p className="mt-1 text-sm">{message}</p>

          {/* Recovery hint */}
          <div className="mt-3 flex items-start gap-2 text-xs opacity-80">
            <Info className="w-3.5 h-3.5 mt-0.5 flex-shrink-0" />
            <p>{hint}</p>
          </div>

          {/* Timeout indicator */}
          {appError.showTimeout && (
            <div className="mt-2 flex items-center gap-2 text-xs">
              <Clock className="w-3.5 h-3.5" />
              <span>Expected wait: ~{appError.timeoutSeconds}s</span>
            </div>
          )}

          {/* Retry countdown */}
          {showRetryCountdown && retryState.countdown > 0 && (
            <div className="mt-2 flex items-center gap-2 text-xs">
              <RefreshCw className="w-3.5 h-3.5 animate-spin" />
              <span>
                Retrying automatically in {retryState.countdown}s
                {retryState.attemptsMade > 0 &&
                  ` (attempt ${retryState.attemptsMade + 1}/${appError.retryCount + 1})`}
              </span>
            </div>
          )}
        </div>

        {/* Dismiss button */}
        {onDismiss && (
          <button
            onClick={onDismiss}
            className="p-1 hover:bg-white/10 rounded transition-colors"
            aria-label="Dismiss error"
          >
            <X className="w-4 h-4" />
          </button>
        )}
      </div>

      {/* Actions */}
      <div className="flex items-center gap-2 px-4 pb-4">
        {canRetry && onRetry && retryState.countdown === 0 && (
          <button
            onClick={onRetry}
            disabled={retryState.isRetrying}
            className={cn(
              'px-3 py-1.5 text-sm bg-white/10 hover:bg-white/20 rounded-md',
              'transition-colors flex items-center gap-2',
              'disabled:opacity-50 disabled:cursor-not-allowed'
            )}
          >
            <RefreshCw
              className={cn('w-3.5 h-3.5', retryState.isRetrying && 'animate-spin')}
            />
            {retryState.isRetrying ? 'Retrying...' : 'Try Again'}
          </button>
        )}

        {onHelpClick && (
          <button
            onClick={onHelpClick}
            className="px-3 py-1.5 text-sm hover:bg-white/10 rounded-md transition-colors flex items-center gap-2"
          >
            <ExternalLink className="w-3.5 h-3.5" />
            Get Help
          </button>
        )}

        {/* Technical details toggle */}
        <button
          onClick={onToggleExpand}
          className="ml-auto px-2 py-1.5 text-xs hover:bg-white/10 rounded-md transition-colors flex items-center gap-1"
        >
          {isExpanded ? (
            <>
              <ChevronUp className="w-3 h-3" />
              Hide Details
            </>
          ) : (
            <>
              <ChevronDown className="w-3 h-3" />
              Show Details
            </>
          )}
        </button>
      </div>

      {/* Technical details */}
      {isExpanded && (
        <div className="px-4 pb-4 pt-0">
          <div className="p-3 bg-black/20 rounded-md text-xs font-mono space-y-1">
            <p>
              <span className="opacity-60">Code:</span> {appError.code}
            </p>
            <p>
              <span className="opacity-60">Category:</span> {appError.category}
            </p>
            <p>
              <span className="opacity-60">Timestamp:</span>{' '}
              {appError.timestamp.toISOString()}
            </p>
            {appError.context && (
              <p>
                <span className="opacity-60">Context:</span>{' '}
                {JSON.stringify(appError.context)}
              </p>
            )}
            {appError.originalError && (
              <p className="break-all">
                <span className="opacity-60">Original:</span>{' '}
                {appError.originalError.message}
              </p>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

// ============================================================================
// Specialized Error Components
// ============================================================================

/**
 * Error display for empty states when data fails to load.
 */
export function DataLoadError({
  entity,
  error,
  onRetry,
  className,
}: {
  entity: string;
  error: unknown;
  onRetry?: () => void;
  className?: string;
}) {
  const formatted = formatErrorForDisplay(error);

  return (
    <div
      className={cn(
        'flex flex-col items-center justify-center py-12 px-4 text-center',
        className
      )}
      role="alert"
    >
      <div className="w-16 h-16 bg-red-500/10 rounded-full flex items-center justify-center mb-4">
        <AlertTriangle className="w-8 h-8 text-red-400" />
      </div>
      <h3 className="text-lg font-semibold text-surface-100 mb-2">
        Unable to load {entity}
      </h3>
      <p className="text-surface-400 text-sm max-w-md mb-2">
        {formatted.message}
      </p>
      <p className="text-surface-500 text-xs max-w-md mb-6">
        {formatted.hint}
      </p>
      {formatted.canRetry && onRetry && (
        <button
          onClick={onRetry}
          className="px-4 py-2 bg-brand-500 hover:bg-brand-600 text-white rounded-lg flex items-center gap-2 transition-colors"
        >
          <RefreshCw className="w-4 h-4" />
          Try Again
        </button>
      )}
    </div>
  );
}

/**
 * Compact error for form fields.
 */
export function FieldError({
  error,
  className,
}: {
  error: string | unknown;
  className?: string;
}) {
  const message =
    typeof error === 'string'
      ? error
      : formatErrorForDisplay(error).message;

  return (
    <p
      className={cn('text-xs text-red-400 mt-1 flex items-center gap-1', className)}
      role="alert"
    >
      <AlertCircle className="w-3 h-3" />
      {message}
    </p>
  );
}

/**
 * Connection error banner for backend issues.
 */
export function ConnectionError({
  onRetry,
  className,
}: {
  onRetry?: () => void;
  className?: string;
}) {
  return (
    <div
      className={cn(
        'flex items-center gap-3 px-4 py-3 bg-amber-500/10 border-b border-amber-500/30 text-amber-400',
        className
      )}
      role="alert"
    >
      <WifiOff className="w-5 h-5" />
      <div className="flex-1">
        <p className="font-medium text-sm">Cannot connect to server</p>
        <p className="text-xs opacity-80">
          Make sure the backend is running and try again.
        </p>
      </div>
      {onRetry && (
        <button
          onClick={onRetry}
          className="px-3 py-1.5 text-sm bg-amber-500/20 hover:bg-amber-500/30 rounded transition-colors flex items-center gap-2"
        >
          <RefreshCw className="w-4 h-4" />
          Retry
        </button>
      )}
    </div>
  );
}

// ============================================================================
// Hook for Error Management
// ============================================================================

export interface UseErrorReturn {
  error: AppError | null;
  setError: (error: unknown) => void;
  clearError: () => void;
  isError: boolean;
}

export function useError(): UseErrorReturn {
  const [error, setErrorState] = useState<AppError | null>(null);

  const setError = useCallback((err: unknown) => {
    if (err) {
      setErrorState(classifyError(err));
    }
  }, []);

  const clearError = useCallback(() => {
    setErrorState(null);
  }, []);

  return {
    error,
    setError,
    clearError,
    isError: error !== null,
  };
}

// ============================================================================
// Exports
// ============================================================================

export default ErrorDisplay;
