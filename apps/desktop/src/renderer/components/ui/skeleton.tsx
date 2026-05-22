/**
 * Skeleton Loading Components
 * Content-aware skeleton loaders with shimmer effects
 */

import React from 'react';
import { cn } from '../../lib/utils';

// Base skeleton with shimmer animation
export const Skeleton: React.FC<{
  className?: string;
  variant?: 'default' | 'circular' | 'text' | 'rectangular';
  width?: string | number;
  height?: string | number;
  animation?: 'shimmer' | 'pulse' | 'none';
}> = ({ className, variant = 'default', width, height, animation = 'shimmer' }) => {
  const variantStyles = {
    default: 'rounded',
    circular: 'rounded-full',
    text: 'rounded h-4',
    rectangular: 'rounded-lg',
  };

  const animationStyles = {
    shimmer:
      'animate-shimmer bg-gradient-to-r from-surface-800 via-surface-700 to-surface-800 bg-[length:200%_100%]',
    pulse: 'animate-pulse bg-surface-700',
    none: 'bg-surface-700',
  };

  return (
    <div
      className={cn('skeleton', variantStyles[variant], animationStyles[animation], className)}
      style={{
        width: typeof width === 'number' ? `${width}px` : width,
        height: typeof height === 'number' ? `${height}px` : height,
      }}
    />
  );
};

// Text skeleton
export const SkeletonText: React.FC<{
  lines?: number;
  className?: string;
}> = ({ lines = 3, className }) => (
  <div className={cn('space-y-2', className)}>
    {Array.from({ length: lines }).map((_, i) => (
      <Skeleton key={i} variant="text" width={i === lines - 1 ? '75%' : '100%'} />
    ))}
  </div>
);

// Avatar skeleton
export const SkeletonAvatar: React.FC<{
  size?: 'sm' | 'md' | 'lg';
  className?: string;
}> = ({ size = 'md', className }) => {
  const sizes = { sm: 32, md: 40, lg: 56 };
  return (
    <Skeleton variant="circular" width={sizes[size]} height={sizes[size]} className={className} />
  );
};

// Card skeleton
export const SkeletonCard: React.FC<{
  hasImage?: boolean;
  hasTitle?: boolean;
  hasDescription?: boolean;
  hasActions?: boolean;
  className?: string;
}> = ({
  hasImage = true,
  hasTitle = true,
  hasDescription = true,
  hasActions = false,
  className,
}) => (
  <div className={cn('bg-surface-800 rounded-xl overflow-hidden', className)}>
    {hasImage && <Skeleton variant="rectangular" height={160} className="w-full" />}
    <div className="p-4 space-y-3">
      {hasTitle && <Skeleton variant="text" width="60%" height={20} />}
      {hasDescription && <SkeletonText lines={2} />}
      {hasActions && (
        <div className="flex gap-2 pt-2">
          <Skeleton variant="rectangular" width={80} height={32} />
          <Skeleton variant="rectangular" width={80} height={32} />
        </div>
      )}
    </div>
  </div>
);

// List item skeleton
export const SkeletonListItem: React.FC<{
  hasAvatar?: boolean;
  hasSecondaryText?: boolean;
  className?: string;
}> = ({ hasAvatar = true, hasSecondaryText = true, className }) => (
  <div className={cn('flex items-center gap-3 p-3', className)}>
    {hasAvatar && <SkeletonAvatar size="md" />}
    <div className="flex-1 space-y-2">
      <Skeleton variant="text" width="40%" height={16} />
      {hasSecondaryText && <Skeleton variant="text" width="60%" height={12} />}
    </div>
    <Skeleton variant="rectangular" width={24} height={24} />
  </div>
);

// Table skeleton
export const SkeletonTable: React.FC<{
  rows?: number;
  columns?: number;
  className?: string;
}> = ({ rows = 5, columns = 4, className }) => (
  <div className={cn('border border-surface-700 rounded-lg overflow-hidden', className)}>
    {/* Header */}
    <div className="flex gap-4 p-3 bg-surface-800 border-b border-surface-700">
      {Array.from({ length: columns }).map((_, i) => (
        <Skeleton key={i} variant="text" className="flex-1" height={16} />
      ))}
    </div>
    {/* Rows */}
    {Array.from({ length: rows }).map((_, rowIdx) => (
      <div key={rowIdx} className="flex gap-4 p-3 border-b border-surface-700 last:border-b-0">
        {Array.from({ length: columns }).map((_, colIdx) => (
          <Skeleton
            key={colIdx}
            variant="text"
            className="flex-1"
            height={14}
            width={colIdx === 0 ? '80%' : '60%'}
          />
        ))}
      </div>
    ))}
  </div>
);

// Timeline skeleton
export const SkeletonTimeline: React.FC<{
  clips?: number;
  tracks?: number;
  className?: string;
}> = ({ clips = 5, tracks = 3, className }) => (
  <div className={cn('space-y-2', className)}>
    {Array.from({ length: tracks }).map((_, trackIdx) => (
      <div key={trackIdx} className="flex items-center gap-2">
        <Skeleton variant="rectangular" width={120} height={40} />
        <div className="flex-1 flex gap-1">
          {Array.from({ length: clips }).map((_, clipIdx) => (
            <Skeleton
              key={clipIdx}
              variant="rectangular"
              width={`${Math.random() * 15 + 10}%`}
              height={40}
            />
          ))}
        </div>
      </div>
    ))}
  </div>
);

// Calendar skeleton
export const SkeletonCalendar: React.FC<{ className?: string }> = ({ className }) => (
  <div className={cn('space-y-3', className)}>
    <div className="flex justify-between items-center">
      <Skeleton variant="rectangular" width={32} height={32} />
      <Skeleton variant="text" width={150} height={24} />
      <Skeleton variant="rectangular" width={32} height={32} />
    </div>
    <div className="grid grid-cols-7 gap-1">
      {Array.from({ length: 7 }).map((_, i) => (
        <Skeleton key={i} variant="text" height={20} className="w-full" />
      ))}
    </div>
    <div className="grid grid-cols-7 gap-1">
      {Array.from({ length: 35 }).map((_, i) => (
        <Skeleton key={i} variant="rectangular" height={40} className="w-full" />
      ))}
    </div>
  </div>
);

// Form skeleton
export const SkeletonForm: React.FC<{
  fields?: number;
  hasSubmit?: boolean;
  className?: string;
}> = ({ fields = 4, hasSubmit = true, className }) => (
  <div className={cn('space-y-4', className)}>
    {Array.from({ length: fields }).map((_, i) => (
      <div key={i} className="space-y-1">
        <Skeleton variant="text" width={100} height={14} />
        <Skeleton variant="rectangular" height={40} className="w-full" />
      </div>
    ))}
    {hasSubmit && <Skeleton variant="rectangular" width={120} height={40} className="mt-4" />}
  </div>
);

// Asset grid skeleton
export const SkeletonAssetGrid: React.FC<{
  count?: number;
  className?: string;
}> = ({ count = 8, className }) => (
  <div className={cn('grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-3', className)}>
    {Array.from({ length: count }).map((_, i) => (
      <div key={i} className="bg-surface-800 rounded-lg overflow-hidden">
        <Skeleton variant="rectangular" className="aspect-square w-full" />
        <div className="p-2 space-y-1">
          <Skeleton variant="text" width="70%" height={14} />
          <Skeleton variant="text" width="40%" height={12} />
        </div>
      </div>
    ))}
  </div>
);

// Add CSS for shimmer animation
export const skeletonStyles = `
@keyframes shimmer {
  0% { background-position: -200% 0; }
  100% { background-position: 200% 0; }
}

.animate-shimmer {
  animation: shimmer 1.5s ease-in-out infinite;
}
`;
