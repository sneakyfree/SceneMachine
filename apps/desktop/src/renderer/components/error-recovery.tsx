/**
 * Error Recovery Components
 *
 * Provides user-friendly error display with actionable recovery options.
 * Works with the enhanced error system (lib/errors.ts).
 */

import { memo, useState, useCallback, useEffect, ReactNode } from 'react';
import {
  AlertCircle,
  RefreshCw,
  WifiOff,
  Clock,
  ShieldAlert,
  HardDrive,
  Zap,
  Server,
  HelpCircle,
  ChevronDown,
  ChevronUp,
  ExternalLink,
  Copy,
  Check,
} from 'lucide-react';
import { cn } from '../lib/utils';
import {
  AppError,
  ErrorCategory,
  ErrorCode,
  formatErrorForDisplay,
  classifyError,
} from '../lib/errors';
import { useTranslation } from '../i18n/use-translation';

// =============================================================================
// Error Icon Mapping
// =============================================================================

function getErrorIcon(category: ErrorCategory) {
  switch (category) {
    case ErrorCategory.NETWORK:
      return WifiOff;
    case ErrorCategory.AUTH:
    case ErrorCategory.PERMISSION:
      return ShieldAlert;
    case ErrorCategory.TIMEOUT:
    case ErrorCategory.RATE_LIMIT:
      return Clock;
    case ErrorCategory.STORAGE:
      return HardDrive;
    case ErrorCategory.PROVIDER:
    case ErrorCategory.GENERATION:
      return Zap;
    case ErrorCategory.SERVER:
      return Server;
    default:
      return AlertCircle;
  }
}

function getErrorColor(category: ErrorCategory): string {
  switch (category) {
    case ErrorCategory.NETWORK:
    case ErrorCategory.TIMEOUT:
      return 'text-orange-400';
    case ErrorCategory.AUTH:
    case ErrorCategory.PERMISSION:
      return 'text-yellow-400';
    case ErrorCategory.RATE_LIMIT:
      return 'text-blue-400';
    case ErrorCategory.SERVER:
    case ErrorCategory.STORAGE:
      return 'text-red-400';
    case ErrorCategory.PROVIDER:
    case ErrorCategory.GENERATION:
      return 'text-purple-400';
    default:
      return 'text-red-400';
  }
}

function getErrorBgColor(category: ErrorCategory): string {
  switch (category) {
    case ErrorCategory.NETWORK:
    case ErrorCategory.TIMEOUT:
      return 'bg-orange-500/10';
    case ErrorCategory.AUTH:
    case ErrorCategory.PERMISSION:
      return 'bg-yellow-500/10';
    case ErrorCategory.RATE_LIMIT:
      return 'bg-blue-500/10';
    case ErrorCategory.SERVER:
    case ErrorCategory.STORAGE:
      return 'bg-red-500/10';
    case ErrorCategory.PROVIDER:
    case ErrorCategory.GENERATION:
      return 'bg-purple-500/10';
    default:
      return 'bg-red-500/10';
  }
}

// =============================================================================
// Error Alert Component
// =============================================================================

interface ErrorAlertProps {
  /**
   * The error to display (can be AppError or any Error)
   */
  error: unknown;

  /**
   * Called when retry button is clicked
   */
  onRetry?: () => void;

  /**
   * Called when dismiss button is clicked
   */
  onDismiss?: () => void;

  /**
   * Whether a retry is currently in progress
   */
  isRetrying?: boolean;

  /**
   * Show compact version
   */
  compact?: boolean;

  /**
   * Additional CSS classes
   */
  className?: string;
}

/**
 * Inline error alert with recovery options
 */
export const ErrorAlert = memo(function ErrorAlert({
  error,
  onRetry,
  onDismiss,
  isRetrying = false,
  compact = false,
  className,
}: ErrorAlertProps) {
  const { t } = useTranslation();
  const appError = error instanceof AppError ? error : classifyError(error);
  const { title, message, hint, canRetry, helpLink } = formatErrorForDisplay(appError);
  const Icon = getErrorIcon(appError.category);
  const color = getErrorColor(appError.category);
  const bgColor = getErrorBgColor(appError.category);

  if (compact) {
    return (
      <div
        className={cn(
          'flex items-center gap-3 px-3 py-2 rounded-lg',
          bgColor,
          'border border-current/20',
          className
        )}
        role="alert"
      >
        <Icon className={cn('w-4 h-4 flex-shrink-0', color)} />
        <span className={cn('text-sm flex-1', color)}>{message}</span>
        {canRetry && onRetry && (
          <button
            onClick={onRetry}
            disabled={isRetrying}
            className={cn(
              'p-1.5 rounded hover:bg-white/10 transition-colors',
              isRetrying && 'opacity-50 cursor-not-allowed'
            )}
          >
            <RefreshCw className={cn('w-4 h-4', color, isRetrying && 'animate-spin')} />
          </button>
        )}
      </div>
    );
  }

  return (
    <div
      className={cn('rounded-lg border overflow-hidden', bgColor, 'border-current/20', className)}
      role="alert"
    >
      {/* Header */}
      <div className="flex items-start gap-3 p-4">
        <div className={cn('p-2 rounded-lg', bgColor)}>
          <Icon className={cn('w-5 h-5', color)} />
        </div>
        <div className="flex-1 min-w-0">
          <h4 className="font-medium text-surface-100">{title}</h4>
          <p className="text-sm text-surface-300 mt-1">{message}</p>
          <p className="text-sm text-surface-400 mt-2">{hint}</p>
        </div>
        {onDismiss && (
          <button
            onClick={onDismiss}
            className="p-1 rounded hover:bg-white/10 transition-colors text-surface-400"
            aria-label={t('errRecovery.dismiss', 'Dismiss')}
          >
            ×
          </button>
        )}
      </div>

      {/* Actions */}
      {(canRetry || helpLink) && (
        <div className="flex items-center gap-2 px-4 pb-4">
          {canRetry && onRetry && (
            <button
              onClick={onRetry}
              disabled={isRetrying}
              className={cn(
                'flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm font-medium',
                'bg-surface-700 hover:bg-surface-600 transition-colors',
                'text-surface-200',
                isRetrying && 'opacity-50 cursor-not-allowed'
              )}
            >
              <RefreshCw className={cn('w-4 h-4', isRetrying && 'animate-spin')} />
              {isRetrying
                ? t('errRecovery.retrying', 'Retrying...')
                : t('errRecovery.tryAgain', 'Try again')}
            </button>
          )}
          {helpLink && (
            <a
              href={helpLink}
              className={cn(
                'flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm',
                'text-surface-400 hover:text-surface-200 transition-colors'
              )}
            >
              <HelpCircle className="w-4 h-4" />
              {t('errRecovery.learnMore', 'Learn more')}
            </a>
          )}
        </div>
      )}
    </div>
  );
});

// =============================================================================
// Error Details Component (Expandable)
// =============================================================================

interface ErrorDetailsProps {
  /**
   * The error to display
   */
  error: AppError;

  /**
   * Additional CSS classes
   */
  className?: string;
}

/**
 * Expandable technical error details for debugging
 */
export const ErrorDetails = memo(function ErrorDetails({ error, className }: ErrorDetailsProps) {
  const { t } = useTranslation();
  const [isExpanded, setIsExpanded] = useState(false);
  const [copied, setCopied] = useState(false);

  const errorJson = JSON.stringify(
    {
      code: error.code,
      category: error.category,
      message: error.message,
      timestamp: error.timestamp.toISOString(),
      context: error.context,
      stack: error.stack,
    },
    null,
    2
  );

  const handleCopy = useCallback(async () => {
    try {
      await navigator.clipboard.writeText(errorJson);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (e) {
      console.error('Failed to copy:', e);
    }
  }, [errorJson]);

  return (
    <div className={cn('border-t border-surface-700', className)}>
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="w-full flex items-center justify-between px-4 py-2 text-xs text-surface-500 hover:text-surface-400 transition-colors"
      >
        <span>{t('errRecovery.technicalDetails', 'Technical Details')}</span>
        {isExpanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
      </button>

      {isExpanded && (
        <div className="px-4 pb-4">
          <div className="relative">
            <pre className="text-xs bg-surface-900 p-3 rounded-lg overflow-x-auto text-surface-400 max-h-48">
              {errorJson}
            </pre>
            <button
              onClick={handleCopy}
              className="absolute top-2 right-2 p-1.5 rounded bg-surface-800 hover:bg-surface-700 transition-colors"
              title={t('errRecovery.copyErrorDetails', 'Copy error details')}
            >
              {copied ? (
                <Check className="w-3.5 h-3.5 text-green-400" />
              ) : (
                <Copy className="w-3.5 h-3.5 text-surface-400" />
              )}
            </button>
          </div>

          <div className="mt-2 text-xs text-surface-500">
            {t('errRecovery.errorCode', 'Error Code:')}{' '}
            <code className="bg-surface-800 px-1 py-0.5 rounded">{error.code}</code>
          </div>
        </div>
      )}
    </div>
  );
});

// =============================================================================
// Retry Countdown Component
// =============================================================================

interface RetryCountdownProps {
  /**
   * Seconds until retry
   */
  seconds: number;

  /**
   * Called when countdown completes
   */
  onComplete: () => void;

  /**
   * Called to cancel countdown
   */
  onCancel?: () => void;

  /**
   * Additional CSS classes
   */
  className?: string;
}

/**
 * Countdown timer for automatic retry
 */
export const RetryCountdown = memo(function RetryCountdown({
  seconds,
  onComplete,
  onCancel,
  className,
}: RetryCountdownProps) {
  const { t } = useTranslation();
  const [remaining, setRemaining] = useState(seconds);

  useEffect(() => {
    if (remaining <= 0) {
      onComplete();
      return;
    }

    const timer = setTimeout(() => {
      setRemaining(remaining - 1);
    }, 1000);

    return () => clearTimeout(timer);
  }, [remaining, onComplete]);

  return (
    <div className={cn('flex items-center gap-3 text-sm text-surface-400', className)}>
      <RefreshCw className="w-4 h-4 animate-spin" />
      <span>
        {t('errRecovery.retryingIn', 'Retrying in')} {remaining}
        {t('errRecovery.secondsSuffix', 's...')}
      </span>
      {onCancel && (
        <button onClick={onCancel} className="text-surface-500 hover:text-surface-300 underline">
          {t('errRecovery.cancel', 'Cancel')}
        </button>
      )}
    </div>
  );
});

// =============================================================================
// Error Recovery Card Component
// =============================================================================

interface ErrorRecoveryCardProps {
  /**
   * The error to display
   */
  error: unknown;

  /**
   * Called when retry button is clicked
   */
  onRetry?: () => void;

  /**
   * Whether a retry is currently in progress
   */
  isRetrying?: boolean;

  /**
   * Enable auto-retry with countdown
   */
  autoRetry?: boolean;

  /**
   * Auto-retry delay in seconds
   */
  autoRetryDelay?: number;

  /**
   * Show technical details section
   */
  showDetails?: boolean;

  /**
   * Additional CSS classes
   */
  className?: string;
}

/**
 * Full error recovery card with all options
 */
export const ErrorRecoveryCard = memo(function ErrorRecoveryCard({
  error,
  onRetry,
  isRetrying = false,
  autoRetry = false,
  autoRetryDelay = 5,
  showDetails = true,
  className,
}: ErrorRecoveryCardProps) {
  const { t } = useTranslation();
  const appError = error instanceof AppError ? error : classifyError(error);
  const [showCountdown, setShowCountdown] = useState(autoRetry && appError.canRetry);

  const handleAutoRetry = useCallback(() => {
    setShowCountdown(false);
    onRetry?.();
  }, [onRetry]);

  const handleCancelAutoRetry = useCallback(() => {
    setShowCountdown(false);
  }, []);

  const { title, message, hint, canRetry, helpLink } = formatErrorForDisplay(appError);
  const Icon = getErrorIcon(appError.category);
  const color = getErrorColor(appError.category);
  const bgColor = getErrorBgColor(appError.category);

  return (
    <div
      className={cn(
        'rounded-xl bg-surface-800 border border-surface-700 overflow-hidden',
        className
      )}
      role="alert"
    >
      {/* Main content */}
      <div className="p-6">
        <div className="flex items-start gap-4">
          <div className={cn('p-3 rounded-xl', bgColor)}>
            <Icon className={cn('w-6 h-6', color)} />
          </div>
          <div className="flex-1">
            <h3 className="text-lg font-semibold text-surface-100">{title}</h3>
            <p className="text-surface-300 mt-1">{message}</p>
            <p className="text-sm text-surface-400 mt-3">{hint}</p>
          </div>
        </div>

        {/* Actions */}
        <div className="mt-6 flex items-center gap-3">
          {canRetry && onRetry && !showCountdown && (
            <button
              onClick={onRetry}
              disabled={isRetrying}
              className={cn(
                'flex items-center gap-2 px-4 py-2 rounded-lg font-medium',
                'bg-primary-500 hover:bg-primary-600 text-white transition-colors',
                isRetrying && 'opacity-50 cursor-not-allowed'
              )}
            >
              <RefreshCw className={cn('w-4 h-4', isRetrying && 'animate-spin')} />
              {isRetrying
                ? t('errRecovery.retrying', 'Retrying...')
                : t('errRecovery.tryAgain', 'Try again')}
            </button>
          )}

          {showCountdown && (
            <RetryCountdown
              seconds={autoRetryDelay}
              onComplete={handleAutoRetry}
              onCancel={handleCancelAutoRetry}
            />
          )}

          {helpLink && (
            <a
              href={helpLink}
              className={cn(
                'flex items-center gap-2 px-4 py-2 rounded-lg',
                'bg-surface-700 hover:bg-surface-600 transition-colors',
                'text-surface-200'
              )}
            >
              <ExternalLink className="w-4 h-4" />
              {t('errRecovery.getHelp', 'Get help')}
            </a>
          )}
        </div>
      </div>

      {/* Technical details */}
      {showDetails && <ErrorDetails error={appError} />}
    </div>
  );
});

// =============================================================================
// Hook for Error Recovery State
// =============================================================================

interface UseErrorRecoveryOptions {
  /**
   * Maximum number of automatic retries
   */
  maxRetries?: number;

  /**
   * Delay between retries in milliseconds
   */
  retryDelay?: number;

  /**
   * Called on each retry attempt
   */
  onRetry?: (attempt: number) => void;

  /**
   * Called when all retries are exhausted
   */
  onExhausted?: (error: AppError) => void;
}

interface ErrorRecoveryState {
  error: AppError | null;
  isRetrying: boolean;
  retryCount: number;
  setError: (error: unknown) => void;
  clearError: () => void;
  retry: (fn: () => Promise<void>) => Promise<void>;
}

/**
 * Hook for managing error recovery state
 */
export function useErrorRecovery(options: UseErrorRecoveryOptions = {}): ErrorRecoveryState {
  const { maxRetries = 3, retryDelay = 2000, onRetry, onExhausted } = options;

  const [error, setErrorState] = useState<AppError | null>(null);
  const [isRetrying, setIsRetrying] = useState(false);
  const [retryCount, setRetryCount] = useState(0);

  const setError = useCallback((err: unknown) => {
    const appError = err instanceof AppError ? err : classifyError(err);
    setErrorState(appError);
    setRetryCount(0);
  }, []);

  const clearError = useCallback(() => {
    setErrorState(null);
    setRetryCount(0);
  }, []);

  const retry = useCallback(
    async (fn: () => Promise<void>) => {
      if (!error?.canRetry || retryCount >= maxRetries) {
        if (error && retryCount >= maxRetries) {
          onExhausted?.(error);
        }
        return;
      }

      setIsRetrying(true);
      const attempt = retryCount + 1;
      onRetry?.(attempt);

      try {
        await new Promise((resolve) => setTimeout(resolve, retryDelay));
        await fn();
        clearError();
      } catch (err) {
        const newError = err instanceof AppError ? err : classifyError(err);
        setErrorState(newError);
        setRetryCount(attempt);

        if (attempt >= maxRetries) {
          onExhausted?.(newError);
        }
      } finally {
        setIsRetrying(false);
      }
    },
    [error, retryCount, maxRetries, retryDelay, onRetry, onExhausted, clearError]
  );

  return {
    error,
    isRetrying,
    retryCount,
    setError,
    clearError,
    retry,
  };
}

export default ErrorRecoveryCard;
