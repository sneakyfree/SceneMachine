/**
 * Select Component
 *
 * Custom select dropdown with styling.
 */

import React, { forwardRef } from 'react';
import clsx from 'clsx';

export interface SelectOption {
  value: string;
  label: string;
  disabled?: boolean;
}

export interface SelectProps extends Omit<React.SelectHTMLAttributes<HTMLSelectElement>, 'children'> {
  label?: string;
  error?: string;
  hint?: string;
  options: SelectOption[];
  placeholder?: string;
}

export const Select = forwardRef<HTMLSelectElement, SelectProps>(
  ({ label, error, hint, options, placeholder, className, id, ...props }, ref) => {
    const selectId = id || `select-${Math.random().toString(36).slice(2)}`;

    return (
      <>
        <div className={clsx('select-wrapper', { 'has-error': !!error }, className)}>
          {label && (
            <label htmlFor={selectId} className="select-label">
              {label}
            </label>
          )}
          <div className="select-container">
            <select
              ref={ref}
              id={selectId}
              className="select"
              aria-invalid={!!error}
              aria-describedby={
                error ? `${selectId}-error` : hint ? `${selectId}-hint` : undefined
              }
              {...props}
            >
              {placeholder && (
                <option value="" disabled>
                  {placeholder}
                </option>
              )}
              {options.map((option) => (
                <option
                  key={option.value}
                  value={option.value}
                  disabled={option.disabled}
                >
                  {option.label}
                </option>
              ))}
            </select>
            <span className="select-icon" aria-hidden="true">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <polyline points="6 9 12 15 18 9" />
              </svg>
            </span>
          </div>
          {error && (
            <span id={`${selectId}-error`} className="select-error" role="alert">
              {error}
            </span>
          )}
          {!error && hint && (
            <span id={`${selectId}-hint`} className="select-hint">
              {hint}
            </span>
          )}
        </div>

        <style jsx>{`
          .select-wrapper {
            display: flex;
            flex-direction: column;
            gap: 0.375rem;
          }

          .select-label {
            font-size: var(--text-sm);
            font-weight: 500;
            color: var(--color-text-secondary);
          }

          .select-container {
            position: relative;
          }

          .select {
            width: 100%;
            padding: 0.75rem 2.5rem 0.75rem 1rem;
            background: var(--color-bg-secondary);
            border: 1px solid var(--color-border);
            border-radius: var(--radius-md);
            color: var(--color-text-primary);
            font-size: var(--text-base);
            appearance: none;
            cursor: pointer;
            transition: border-color var(--transition-fast),
              box-shadow var(--transition-fast);
          }

          .select:focus {
            outline: none;
            border-color: var(--color-accent);
            box-shadow: 0 0 0 3px rgba(139, 92, 246, 0.1);
          }

          .select:disabled {
            opacity: 0.5;
            cursor: not-allowed;
          }

          .select option {
            background: var(--color-bg-primary);
            color: var(--color-text-primary);
          }

          .select-icon {
            position: absolute;
            right: 0.75rem;
            top: 50%;
            transform: translateY(-50%);
            color: var(--color-text-tertiary);
            pointer-events: none;
          }

          .has-error .select {
            border-color: var(--color-error);
          }

          .has-error .select:focus {
            box-shadow: 0 0 0 3px rgba(239, 68, 68, 0.1);
          }

          .select-error {
            font-size: var(--text-sm);
            color: var(--color-error);
          }

          .select-hint {
            font-size: var(--text-sm);
            color: var(--color-text-tertiary);
          }
        `}</style>
      </>
    );
  }
);

Select.displayName = 'Select';

export default Select;
