/**
 * ProgressBar Component
 *
 * Progress indicator with variants and animation.
 */

import React from 'react';
import clsx from 'clsx';

export interface ProgressBarProps {
  value: number;
  max?: number;
  variant?: 'default' | 'success' | 'warning' | 'error' | 'gradient';
  size?: 'sm' | 'md' | 'lg';
  showLabel?: boolean;
  label?: string;
  animated?: boolean;
  className?: string;
}

export function ProgressBar({
  value,
  max = 100,
  variant = 'default',
  size = 'md',
  showLabel = false,
  label,
  animated = false,
  className,
}: ProgressBarProps) {
  const percentage = Math.min(Math.max((value / max) * 100, 0), 100);

  return (
    <>
      <div className={clsx('progress-container', className)}>
        {(showLabel || label) && (
          <div className="progress-header">
            {label && <span className="progress-label">{label}</span>}
            {showLabel && (
              <span className="progress-value">{Math.round(percentage)}%</span>
            )}
          </div>
        )}
        <div
          className={clsx('progress-bar', `progress-${size}`)}
          role="progressbar"
          aria-valuenow={value}
          aria-valuemin={0}
          aria-valuemax={max}
        >
          <div
            className={clsx('progress-fill', `fill-${variant}`, {
              'fill-animated': animated,
            })}
            style={{ width: `${percentage}%` }}
          />
        </div>
      </div>

      <style jsx>{`
        .progress-container {
          width: 100%;
        }

        .progress-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          margin-bottom: 0.375rem;
        }

        .progress-label {
          font-size: var(--text-sm);
          color: var(--color-text-secondary);
        }

        .progress-value {
          font-size: var(--text-sm);
          font-weight: 500;
          color: var(--color-text-primary);
        }

        .progress-bar {
          width: 100%;
          background: var(--color-bg-secondary);
          border-radius: var(--radius-full);
          overflow: hidden;
        }

        .progress-sm {
          height: 0.25rem;
        }

        .progress-md {
          height: 0.5rem;
        }

        .progress-lg {
          height: 0.75rem;
        }

        .progress-fill {
          height: 100%;
          border-radius: var(--radius-full);
          transition: width 0.3s ease-out;
        }

        .fill-default {
          background: var(--color-accent);
        }

        .fill-success {
          background: var(--color-success);
        }

        .fill-warning {
          background: var(--color-warning);
        }

        .fill-error {
          background: var(--color-error);
        }

        .fill-gradient {
          background: var(--gradient-primary);
        }

        .fill-animated {
          position: relative;
          overflow: hidden;
        }

        .fill-animated::after {
          content: '';
          position: absolute;
          inset: 0;
          background: linear-gradient(
            90deg,
            transparent,
            rgba(255, 255, 255, 0.3),
            transparent
          );
          animation: progress-shine 1.5s ease-in-out infinite;
        }

        @keyframes progress-shine {
          0% {
            transform: translateX(-100%);
          }
          100% {
            transform: translateX(100%);
          }
        }
      `}</style>
    </>
  );
}

export default ProgressBar;
