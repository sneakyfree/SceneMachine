/**
 * Skeleton Component
 *
 * Loading placeholder for content.
 */

import React from 'react';
import clsx from 'clsx';

export interface SkeletonProps {
  variant?: 'text' | 'circular' | 'rectangular';
  width?: string | number;
  height?: string | number;
  className?: string;
  animation?: 'pulse' | 'wave' | 'none';
}

export function Skeleton({
  variant = 'text',
  width,
  height,
  className,
  animation = 'pulse',
}: SkeletonProps) {
  const style: React.CSSProperties = {};

  if (width) style.width = typeof width === 'number' ? `${width}px` : width;
  if (height) style.height = typeof height === 'number' ? `${height}px` : height;

  return (
    <>
      <span
        className={clsx(
          'skeleton',
          `skeleton-${variant}`,
          `animation-${animation}`,
          className
        )}
        style={style}
        aria-hidden="true"
      />

      <style jsx>{`
        .skeleton {
          display: block;
          background: var(--color-bg-secondary);
        }

        .skeleton-text {
          height: 1em;
          border-radius: var(--radius-sm);
          transform-origin: 0 55%;
          transform: scale(1, 0.6);
        }

        .skeleton-circular {
          border-radius: 50%;
        }

        .skeleton-rectangular {
          border-radius: var(--radius-md);
        }

        .animation-pulse {
          animation: skeleton-pulse 2s ease-in-out infinite;
        }

        @keyframes skeleton-pulse {
          0% {
            opacity: 1;
          }
          50% {
            opacity: 0.4;
          }
          100% {
            opacity: 1;
          }
        }

        .animation-wave {
          position: relative;
          overflow: hidden;
        }

        .animation-wave::after {
          content: '';
          position: absolute;
          inset: 0;
          transform: translateX(-100%);
          background: linear-gradient(
            90deg,
            transparent,
            rgba(255, 255, 255, 0.1),
            transparent
          );
          animation: skeleton-wave 1.6s linear infinite;
        }

        @keyframes skeleton-wave {
          100% {
            transform: translateX(100%);
          }
        }

        .animation-none {
          animation: none;
        }
      `}</style>
    </>
  );
}

// Preset skeleton components for common patterns
export function SkeletonText({
  lines = 3,
  className,
}: {
  lines?: number;
  className?: string;
}) {
  return (
    <>
      <div className={clsx('skeleton-text-block', className)}>
        {Array.from({ length: lines }).map((_, i) => (
          <Skeleton
            key={i}
            variant="text"
            width={i === lines - 1 ? '60%' : '100%'}
          />
        ))}
      </div>

      <style jsx>{`
        .skeleton-text-block {
          display: flex;
          flex-direction: column;
          gap: 0.5rem;
        }
      `}</style>
    </>
  );
}

export function SkeletonCard({ className }: { className?: string }) {
  return (
    <>
      <div className={clsx('skeleton-card', className)}>
        <Skeleton variant="rectangular" height={180} />
        <div className="skeleton-card-content">
          <div className="skeleton-card-header">
            <Skeleton variant="circular" width={40} height={40} />
            <div className="skeleton-card-meta">
              <Skeleton variant="text" width="80%" />
              <Skeleton variant="text" width="50%" />
            </div>
          </div>
        </div>
      </div>

      <style jsx>{`
        .skeleton-card {
          border-radius: var(--radius-lg);
          overflow: hidden;
          background: var(--color-bg-primary);
        }

        .skeleton-card-content {
          padding: 1rem;
        }

        .skeleton-card-header {
          display: flex;
          gap: 0.75rem;
        }

        .skeleton-card-meta {
          flex: 1;
          display: flex;
          flex-direction: column;
          gap: 0.375rem;
        }
      `}</style>
    </>
  );
}

export function SkeletonVideoGrid({
  count = 6,
  className,
}: {
  count?: number;
  className?: string;
}) {
  return (
    <>
      <div className={clsx('skeleton-video-grid', className)}>
        {Array.from({ length: count }).map((_, i) => (
          <SkeletonCard key={i} />
        ))}
      </div>

      <style jsx>{`
        .skeleton-video-grid {
          display: grid;
          grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
          gap: 1.5rem;
        }
      `}</style>
    </>
  );
}

export default Skeleton;
