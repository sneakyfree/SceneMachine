/**
 * Skeleton loading components for better perceived performance.
 *
 * Components for consistent loading states across the application.
 */

import { memo, ReactNode } from 'react';
import { Loader2, RefreshCw, AlertCircle } from 'lucide-react';
import { cn } from '../lib/utils';

interface SkeletonProps {
  className?: string;
}

/**
 * Base skeleton element with pulse animation.
 */
export function Skeleton({ className }: SkeletonProps) {
  return (
    <div className={cn('animate-pulse bg-surface-700 rounded', className)} aria-hidden="true" />
  );
}

/**
 * Skeleton for a single line of text.
 */
export function SkeletonText({ className, width = 'w-full' }: SkeletonProps & { width?: string }) {
  return <Skeleton className={cn('h-4', width, className)} />;
}

/**
 * Skeleton for a title/heading.
 */
export function SkeletonTitle({ className }: SkeletonProps) {
  return <Skeleton className={cn('h-6 w-48', className)} />;
}

/**
 * Skeleton for a circular avatar.
 */
export function SkeletonAvatar({
  className,
  size = 'w-10 h-10',
}: SkeletonProps & { size?: string }) {
  return <Skeleton className={cn('rounded-full', size, className)} />;
}

/**
 * Skeleton for a button.
 */
export function SkeletonButton({ className }: SkeletonProps) {
  return <Skeleton className={cn('h-9 w-24 rounded-lg', className)} />;
}

/**
 * Skeleton for a shot card in the generation view.
 */
export function SkeletonShotCard({ className }: SkeletonProps) {
  return (
    <div className={cn('bg-surface-800 rounded-lg overflow-hidden', className)}>
      {/* Video preview placeholder */}
      <Skeleton className="aspect-video w-full rounded-none" />

      {/* Content */}
      <div className="p-4 space-y-3">
        <div className="flex items-center justify-between">
          <Skeleton className="h-5 w-16" />
          <Skeleton className="h-5 w-20 rounded-full" />
        </div>
        <Skeleton className="h-4 w-full" />
        <Skeleton className="h-4 w-3/4" />
      </div>
    </div>
  );
}

/**
 * Skeleton for a queue job row.
 */
export function SkeletonQueueJob({ className }: SkeletonProps) {
  return (
    <div className={cn('p-3 bg-surface-800/50 rounded-lg border border-surface-700', className)}>
      <div className="flex items-center gap-3">
        <Skeleton className="w-4 h-4" />
        <div className="flex-1 space-y-2">
          <div className="flex items-center gap-2">
            <Skeleton className="h-5 w-32" />
            <Skeleton className="h-5 w-16 rounded-full" />
          </div>
        </div>
        <Skeleton className="h-6 w-20" />
      </div>
    </div>
  );
}

/**
 * Skeleton for a timeline clip.
 */
export function SkeletonTimelineClip({
  className,
  width = 'w-32',
}: SkeletonProps & { width?: string }) {
  return (
    <div className={cn('h-16 bg-surface-800 rounded border border-surface-700', width, className)}>
      <div className="p-2 space-y-1">
        <Skeleton className="h-3 w-12" />
        <Skeleton className="h-2 w-full" />
      </div>
    </div>
  );
}

/**
 * Skeleton for a scene row.
 */
export function SkeletonScene({ className }: SkeletonProps) {
  return (
    <div className={cn('p-4 bg-surface-800 rounded-lg border border-surface-700', className)}>
      <div className="flex items-center gap-3 mb-3">
        <Skeleton className="w-8 h-8 rounded" />
        <div className="flex-1 space-y-2">
          <Skeleton className="h-5 w-48" />
          <Skeleton className="h-3 w-24" />
        </div>
      </div>
      <Skeleton className="h-4 w-full" />
      <Skeleton className="h-4 w-2/3 mt-2" />
    </div>
  );
}

/**
 * Skeleton for a project card.
 */
export function SkeletonProjectCard({ className }: SkeletonProps) {
  return (
    <div className={cn('p-4 bg-surface-800 rounded-lg border border-surface-700', className)}>
      <div className="flex items-start gap-4">
        <Skeleton className="w-16 h-12 rounded" />
        <div className="flex-1 space-y-2">
          <Skeleton className="h-5 w-32" />
          <Skeleton className="h-4 w-24" />
          <Skeleton className="h-3 w-full" />
        </div>
      </div>
    </div>
  );
}

/**
 * Loading placeholder that shows multiple skeleton items.
 */
export function SkeletonList({
  count = 3,
  children,
  className,
}: {
  count?: number;
  children: (index: number) => React.ReactNode;
  className?: string;
}) {
  return (
    <div className={cn('space-y-3', className)} aria-label="Loading content">
      {Array.from({ length: count }, (_, i) => children(i))}
    </div>
  );
}

// =============================================================================
// Enhanced Loading State Components
// =============================================================================

export type LoadingState = 'idle' | 'loading' | 'success' | 'error' | 'empty';

interface LoadingContainerProps {
  /**
   * Current loading state
   */
  state: LoadingState;

  /**
   * Content to render when state is 'success'
   */
  children: ReactNode;

  /**
   * Skeleton to show during loading
   */
  skeleton?: ReactNode;

  /**
   * Number of skeleton items to show
   */
  skeletonCount?: number;

  /**
   * Error message when state is 'error'
   */
  error?: string | null;

  /**
   * Callback for retry action
   */
  onRetry?: () => void;

  /**
   * Empty state message
   */
  emptyMessage?: string;

  /**
   * Empty state icon
   */
  emptyIcon?: ReactNode;

  /**
   * Empty state action button text
   */
  emptyAction?: string;

  /**
   * Empty state action callback
   */
  onEmptyAction?: () => void;

  /**
   * Loading message
   */
  loadingMessage?: string;

  /**
   * CSS class for container
   */
  className?: string;

  /**
   * Minimum height for the container
   */
  minHeight?: string;
}

/**
 * Unified loading container component for consistent loading states.
 */
export const LoadingContainer = memo(function LoadingContainer({
  state,
  children,
  skeleton,
  skeletonCount = 3,
  error,
  onRetry,
  emptyMessage = 'No items found',
  emptyIcon,
  emptyAction,
  onEmptyAction,
  loadingMessage,
  className,
  minHeight = 'min-h-[200px]',
}: LoadingContainerProps) {
  // Loading state
  if (state === 'loading') {
    if (skeleton) {
      return (
        <div className={cn('space-y-3', className)} aria-label="Loading content">
          {Array.from({ length: skeletonCount }, (_, i) => (
            <div key={i}>{skeleton}</div>
          ))}
        </div>
      );
    }

    return (
      <div
        className={cn('flex flex-col items-center justify-center', minHeight, className)}
        aria-label="Loading"
      >
        <Loader2 className="w-8 h-8 text-primary-400 animate-spin" />
        {loadingMessage && <p className="mt-3 text-sm text-surface-400">{loadingMessage}</p>}
      </div>
    );
  }

  // Error state
  if (state === 'error') {
    return (
      <div
        className={cn(
          'flex flex-col items-center justify-center text-center',
          minHeight,
          className
        )}
        role="alert"
      >
        <div className="p-4 bg-red-500/10 rounded-full mb-4">
          <AlertCircle className="w-8 h-8 text-red-400" />
        </div>
        <h3 className="text-lg font-medium text-surface-100 mb-2">Something went wrong</h3>
        <p className="text-sm text-surface-400 max-w-md mb-4">
          {error || 'An unexpected error occurred. Please try again.'}
        </p>
        {onRetry && (
          <button
            onClick={onRetry}
            className={cn(
              'flex items-center gap-2 px-4 py-2 rounded-lg',
              'bg-surface-700 hover:bg-surface-600 transition-colors',
              'text-surface-200'
            )}
          >
            <RefreshCw className="w-4 h-4" />
            Try again
          </button>
        )}
      </div>
    );
  }

  // Empty state
  if (state === 'empty') {
    return (
      <div
        className={cn(
          'flex flex-col items-center justify-center text-center',
          minHeight,
          className
        )}
      >
        {emptyIcon ? (
          <div className="mb-4">{emptyIcon}</div>
        ) : (
          <div className="w-16 h-16 mb-4 rounded-full bg-surface-800 flex items-center justify-center">
            <div className="w-8 h-8 border-2 border-dashed border-surface-600 rounded-lg" />
          </div>
        )}
        <p className="text-surface-400 mb-4">{emptyMessage}</p>
        {emptyAction && onEmptyAction && (
          <button
            onClick={onEmptyAction}
            className={cn(
              'px-4 py-2 rounded-lg',
              'bg-primary-500 hover:bg-primary-600 transition-colors',
              'text-white font-medium'
            )}
          >
            {emptyAction}
          </button>
        )}
      </div>
    );
  }

  // Success/idle state - render children
  return <>{children}</>;
});

/**
 * Simple inline loading spinner
 */
export const InlineLoader = memo(function InlineLoader({
  size = 'sm',
  className,
  label,
}: {
  size?: 'xs' | 'sm' | 'md' | 'lg';
  className?: string;
  label?: string;
}) {
  const sizeClasses = {
    xs: 'w-3 h-3',
    sm: 'w-4 h-4',
    md: 'w-5 h-5',
    lg: 'w-6 h-6',
  };

  return (
    <span className={cn('inline-flex items-center gap-2', className)}>
      <Loader2 className={cn('animate-spin text-primary-400', sizeClasses[size])} />
      {label && <span className="text-surface-400 text-sm">{label}</span>}
    </span>
  );
});

/**
 * Page-level loading overlay
 */
export const PageLoader = memo(function PageLoader({
  message = 'Loading...',
  className,
}: {
  message?: string;
  className?: string;
}) {
  return (
    <div
      className={cn(
        'fixed inset-0 z-50 flex flex-col items-center justify-center',
        'bg-surface-950/90 backdrop-blur-sm',
        className
      )}
    >
      <Loader2 className="w-12 h-12 text-primary-400 animate-spin" />
      <p className="mt-4 text-surface-300 font-medium">{message}</p>
    </div>
  );
});

/**
 * Content placeholder for lazy-loaded sections
 */
export const ContentPlaceholder = memo(function ContentPlaceholder({
  lines = 3,
  className,
}: {
  lines?: number;
  className?: string;
}) {
  return (
    <div className={cn('space-y-3', className)} aria-label="Loading content">
      {Array.from({ length: lines }, (_, i) => (
        <Skeleton key={i} className={cn('h-4', i === lines - 1 ? 'w-2/3' : 'w-full')} />
      ))}
    </div>
  );
});

/**
 * Grid skeleton for loading card layouts
 */
export const SkeletonGrid = memo(function SkeletonGrid({
  count = 6,
  columns = 3,
  aspectRatio = 'aspect-video',
  className,
}: {
  count?: number;
  columns?: 2 | 3 | 4;
  aspectRatio?: 'aspect-video' | 'aspect-square' | 'aspect-[4/3]';
  className?: string;
}) {
  const gridCols = {
    2: 'grid-cols-2',
    3: 'grid-cols-3',
    4: 'grid-cols-4',
  };

  return (
    <div className={cn('grid gap-4', gridCols[columns], className)}>
      {Array.from({ length: count }, (_, i) => (
        <div key={i} className="bg-surface-800 rounded-lg overflow-hidden">
          <Skeleton className={cn(aspectRatio, 'w-full rounded-none')} />
          <div className="p-3 space-y-2">
            <Skeleton className="h-4 w-3/4" />
            <Skeleton className="h-3 w-1/2" />
          </div>
        </div>
      ))}
    </div>
  );
});

/**
 * Table skeleton for loading tabular data
 */
export const SkeletonTable = memo(function SkeletonTable({
  rows = 5,
  columns = 4,
  className,
}: {
  rows?: number;
  columns?: number;
  className?: string;
}) {
  return (
    <div className={cn('space-y-2', className)}>
      {/* Header */}
      <div className="flex gap-4 p-3 bg-surface-800 rounded-lg">
        {Array.from({ length: columns }, (_, i) => (
          <Skeleton
            key={i}
            className={cn('h-4', i === 0 ? 'w-1/4' : i === columns - 1 ? 'w-20' : 'flex-1')}
          />
        ))}
      </div>

      {/* Rows */}
      {Array.from({ length: rows }, (_, rowIndex) => (
        <div key={rowIndex} className="flex gap-4 p-3 bg-surface-800/50 rounded-lg">
          {Array.from({ length: columns }, (_, colIndex) => (
            <Skeleton
              key={colIndex}
              className={cn(
                'h-4',
                colIndex === 0 ? 'w-1/4' : colIndex === columns - 1 ? 'w-20' : 'flex-1'
              )}
            />
          ))}
        </div>
      ))}
    </div>
  );
});
