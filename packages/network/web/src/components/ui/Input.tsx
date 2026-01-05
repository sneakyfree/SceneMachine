/**
 * Input Component
 *
 * Styled form input with label and error states.
 */

import React, { forwardRef } from 'react';
import clsx from 'clsx';

export interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  error?: string;
  hint?: string;
  leftIcon?: React.ReactNode;
  rightIcon?: React.ReactNode;
}

export const Input = forwardRef<HTMLInputElement, InputProps>(
  ({ label, error, hint, leftIcon, rightIcon, className, id, ...props }, ref) => {
    const inputId = id || `input-${Math.random().toString(36).slice(2)}`;

    return (
      <>
        <div className={clsx('input-wrapper', { 'has-error': !!error }, className)}>
          {label && (
            <label htmlFor={inputId} className="input-label">
              {label}
            </label>
          )}
          <div className="input-container">
            {leftIcon && <span className="input-icon left">{leftIcon}</span>}
            <input
              ref={ref}
              id={inputId}
              className={clsx('input', {
                'has-left-icon': !!leftIcon,
                'has-right-icon': !!rightIcon,
              })}
              aria-invalid={!!error}
              aria-describedby={error ? `${inputId}-error` : hint ? `${inputId}-hint` : undefined}
              {...props}
            />
            {rightIcon && <span className="input-icon right">{rightIcon}</span>}
          </div>
          {error && (
            <span id={`${inputId}-error`} className="input-error" role="alert">
              {error}
            </span>
          )}
          {!error && hint && (
            <span id={`${inputId}-hint`} className="input-hint">
              {hint}
            </span>
          )}
        </div>

        <style jsx>{`
          .input-wrapper {
            display: flex;
            flex-direction: column;
            gap: 0.375rem;
          }

          .input-label {
            font-size: var(--text-sm);
            font-weight: 500;
            color: var(--color-text-secondary);
          }

          .input-container {
            position: relative;
            display: flex;
            align-items: center;
          }

          .input {
            width: 100%;
            padding: 0.75rem 1rem;
            background: var(--color-bg-secondary);
            border: 1px solid var(--color-border);
            border-radius: var(--radius-md);
            color: var(--color-text-primary);
            font-size: var(--text-base);
            transition: border-color var(--transition-fast),
              box-shadow var(--transition-fast);
          }

          .input:focus {
            outline: none;
            border-color: var(--color-accent);
            box-shadow: 0 0 0 3px rgba(139, 92, 246, 0.1);
          }

          .input::placeholder {
            color: var(--color-text-tertiary);
          }

          .input:disabled {
            opacity: 0.5;
            cursor: not-allowed;
          }

          .input.has-left-icon {
            padding-left: 2.75rem;
          }

          .input.has-right-icon {
            padding-right: 2.75rem;
          }

          .input-icon {
            position: absolute;
            display: flex;
            align-items: center;
            justify-content: center;
            width: 2.5rem;
            height: 100%;
            color: var(--color-text-tertiary);
            pointer-events: none;
          }

          .input-icon.left {
            left: 0;
          }

          .input-icon.right {
            right: 0;
          }

          .has-error .input {
            border-color: var(--color-error);
          }

          .has-error .input:focus {
            box-shadow: 0 0 0 3px rgba(239, 68, 68, 0.1);
          }

          .input-error {
            font-size: var(--text-sm);
            color: var(--color-error);
          }

          .input-hint {
            font-size: var(--text-sm);
            color: var(--color-text-tertiary);
          }
        `}</style>
      </>
    );
  }
);

Input.displayName = 'Input';

export default Input;
