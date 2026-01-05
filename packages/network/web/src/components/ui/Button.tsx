/**
 * Button Component
 *
 * Reusable button with multiple variants and sizes.
 */

import React from 'react';
import clsx from 'clsx';

export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'ghost' | 'danger';
  size?: 'sm' | 'md' | 'lg';
  loading?: boolean;
  fullWidth?: boolean;
  leftIcon?: React.ReactNode;
  rightIcon?: React.ReactNode;
}

export function Button({
  children,
  variant = 'primary',
  size = 'md',
  loading = false,
  fullWidth = false,
  leftIcon,
  rightIcon,
  disabled,
  className,
  ...props
}: ButtonProps) {
  return (
    <>
      <button
        className={clsx('btn', `btn-${variant}`, `btn-${size}`, {
          'btn-loading': loading,
          'btn-full': fullWidth,
        }, className)}
        disabled={disabled || loading}
        {...props}
      >
        {loading && (
          <span className="spinner" aria-hidden="true" />
        )}
        {!loading && leftIcon && <span className="btn-icon-left">{leftIcon}</span>}
        <span className="btn-text">{children}</span>
        {!loading && rightIcon && <span className="btn-icon-right">{rightIcon}</span>}
      </button>

      <style jsx>{`
        .btn {
          display: inline-flex;
          align-items: center;
          justify-content: center;
          gap: 0.5rem;
          border-radius: var(--radius-md);
          font-weight: 600;
          cursor: pointer;
          transition: all var(--transition-fast);
          border: none;
          text-decoration: none;
        }

        .btn:disabled {
          opacity: 0.5;
          cursor: not-allowed;
        }

        /* Variants */
        .btn-primary {
          background: var(--gradient-primary);
          color: white;
        }

        .btn-primary:hover:not(:disabled) {
          opacity: 0.9;
        }

        .btn-secondary {
          background: var(--color-bg-secondary);
          color: var(--color-text-primary);
          border: 1px solid var(--color-border);
        }

        .btn-secondary:hover:not(:disabled) {
          border-color: var(--color-accent);
        }

        .btn-ghost {
          background: transparent;
          color: var(--color-text-secondary);
        }

        .btn-ghost:hover:not(:disabled) {
          background: var(--color-bg-secondary);
          color: var(--color-text-primary);
        }

        .btn-danger {
          background: var(--color-error);
          color: white;
        }

        .btn-danger:hover:not(:disabled) {
          opacity: 0.9;
        }

        /* Sizes */
        .btn-sm {
          padding: 0.375rem 0.75rem;
          font-size: var(--text-sm);
        }

        .btn-md {
          padding: 0.625rem 1.25rem;
          font-size: var(--text-base);
        }

        .btn-lg {
          padding: 0.875rem 1.75rem;
          font-size: var(--text-lg);
        }

        .btn-full {
          width: 100%;
        }

        /* Loading */
        .btn-loading {
          position: relative;
        }

        .spinner {
          width: 1em;
          height: 1em;
          border: 2px solid currentColor;
          border-right-color: transparent;
          border-radius: 50%;
          animation: spin 0.75s linear infinite;
        }

        @keyframes spin {
          to {
            transform: rotate(360deg);
          }
        }

        .btn-icon-left,
        .btn-icon-right {
          display: flex;
          align-items: center;
        }
      `}</style>
    </>
  );
}

export default Button;
