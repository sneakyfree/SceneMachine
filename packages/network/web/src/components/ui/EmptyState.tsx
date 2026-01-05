/**
 * EmptyState Component
 *
 * Placeholder for empty lists and sections.
 */

import React from 'react';
import clsx from 'clsx';
import { Button } from './Button';

export interface EmptyStateProps {
  icon?: React.ReactNode;
  title: string;
  description?: string;
  action?: {
    label: string;
    onClick: () => void;
  };
  className?: string;
}

export function EmptyState({
  icon,
  title,
  description,
  action,
  className,
}: EmptyStateProps) {
  return (
    <>
      <div className={clsx('empty-state', className)}>
        {icon && <div className="empty-icon">{icon}</div>}
        <h3 className="empty-title">{title}</h3>
        {description && <p className="empty-description">{description}</p>}
        {action && (
          <Button onClick={action.onClick} variant="primary" size="sm">
            {action.label}
          </Button>
        )}
      </div>

      <style jsx>{`
        .empty-state {
          display: flex;
          flex-direction: column;
          align-items: center;
          justify-content: center;
          padding: 3rem 1.5rem;
          text-align: center;
        }

        .empty-icon {
          margin-bottom: 1rem;
          color: var(--color-text-tertiary);
        }

        .empty-title {
          font-size: var(--text-lg);
          font-weight: 600;
          margin: 0 0 0.5rem;
        }

        .empty-description {
          color: var(--color-text-secondary);
          margin: 0 0 1.5rem;
          max-width: 24rem;
        }
      `}</style>
    </>
  );
}

export default EmptyState;
