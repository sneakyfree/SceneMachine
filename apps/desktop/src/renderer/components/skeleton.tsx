/**
 * Skeleton loading components for better perceived performance.
 */

import { cn } from '../lib/utils';

interface SkeletonProps {
  className?: string;
}

/**
 * Base skeleton element with pulse animation.
 */
export function Skeleton({ className }: SkeletonProps) {
  return (
    <div
      className={cn(
        'animate-pulse bg-surface-700 rounded',
        className
      )}
      aria-hidden="true"
    />
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
export function SkeletonAvatar({ className, size = 'w-10 h-10' }: SkeletonProps & { size?: string }) {
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
export function SkeletonTimelineClip({ className, width = 'w-32' }: SkeletonProps & { width?: string }) {
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
