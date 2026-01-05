/**
 * Badge Component
 *
 * Status badges and labels.
 */

import React from 'react';
import clsx from 'clsx';

export interface BadgeProps {
  variant?: 'default' | 'success' | 'warning' | 'error' | 'info' | 'accent';
  size?: 'sm' | 'md';
  children: React.ReactNode;
  className?: string;
  dot?: boolean;
}

export function Badge({
  variant = 'default',
  size = 'md',
  children,
  className,
  dot = false,
}: BadgeProps) {
  return (
    <>
      <span className={clsx('badge', `badge-${variant}`, `badge-${size}`, className)}>
        {dot && <span className="badge-dot" />}
        {children}
      </span>

      <style jsx>{`
        .badge {
          display: inline-flex;
          align-items: center;
          gap: 0.375rem;
          font-weight: 500;
          border-radius: var(--radius-full);
        }

        .badge-sm {
          padding: 0.125rem 0.5rem;
          font-size: var(--text-xs);
        }

        .badge-md {
          padding: 0.25rem 0.625rem;
          font-size: var(--text-sm);
        }

        .badge-default {
          background: var(--color-bg-secondary);
          color: var(--color-text-secondary);
        }

        .badge-success {
          background: rgba(34, 197, 94, 0.1);
          color: var(--color-success);
        }

        .badge-warning {
          background: rgba(234, 179, 8, 0.1);
          color: var(--color-warning);
        }

        .badge-error {
          background: rgba(239, 68, 68, 0.1);
          color: var(--color-error);
        }

        .badge-info {
          background: rgba(59, 130, 246, 0.1);
          color: #3b82f6;
        }

        .badge-accent {
          background: rgba(139, 92, 246, 0.1);
          color: var(--color-accent);
        }

        .badge-dot {
          width: 0.5rem;
          height: 0.5rem;
          border-radius: 50%;
          background: currentColor;
        }
      `}</style>
    </>
  );
}

export default Badge;
