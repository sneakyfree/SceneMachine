/**
 * 500 Page
 *
 * Custom server error page for SceneMachine Network.
 */

import React from 'react';
import Link from 'next/link';

export default function ServerErrorPage() {
  return (
    <div className="error-page">
      <div className="error-content">
        <div className="error-icon">
          <svg width="120" height="120" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1">
            <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z" />
            <line x1="12" y1="9" x2="12" y2="13" strokeWidth="2" />
            <line x1="12" y1="17" x2="12.01" y2="17" strokeWidth="2" />
          </svg>
        </div>

        <h1>500</h1>
        <h2>Server Error</h2>
        <p>
          Something went wrong on our end. We're working to fix it.
          Please try again in a few moments.
        </p>

        <div className="actions">
          <button onClick={() => window.location.reload()} className="btn-primary">
            Try Again
          </button>
          <Link href="/" className="btn-secondary">
            Go Home
          </Link>
        </div>

        <div className="status">
          <p>If this problem persists, please contact support.</p>
          <a href="mailto:support@scenemachine.com">support@scenemachine.com</a>
        </div>
      </div>

      <style jsx>{`
        .error-page {
          min-height: 100vh;
          display: flex;
          align-items: center;
          justify-content: center;
          padding: var(--space-4);
          background: var(--gradient-bg);
        }

        .error-content {
          text-align: center;
          max-width: 480px;
        }

        .error-icon {
          color: var(--color-warning);
          margin-bottom: var(--space-6);
        }

        h1 {
          font-size: 6rem;
          font-weight: 800;
          color: var(--color-warning);
          line-height: 1;
          margin-bottom: var(--space-2);
        }

        h2 {
          font-size: var(--text-2xl);
          margin-bottom: var(--space-4);
        }

        p {
          color: var(--color-text-secondary);
          margin-bottom: var(--space-8);
        }

        .actions {
          display: flex;
          gap: var(--space-3);
          justify-content: center;
          margin-bottom: var(--space-8);
        }

        .btn-primary,
        .btn-secondary {
          padding: var(--space-3) var(--space-6);
          border-radius: var(--radius-md);
          font-weight: 600;
          transition: all var(--transition-fast);
        }

        .btn-primary {
          background: var(--gradient-primary);
          color: white;
        }

        .btn-primary:hover {
          opacity: 0.9;
        }

        .btn-secondary {
          background: var(--color-bg-secondary);
          border: 1px solid var(--color-border);
          color: var(--color-text-primary);
          text-decoration: none;
        }

        .btn-secondary:hover {
          border-color: var(--color-accent);
        }

        .status {
          padding-top: var(--space-6);
          border-top: 1px solid var(--color-border);
        }

        .status p {
          font-size: var(--text-sm);
          margin-bottom: var(--space-2);
        }

        .status a {
          color: var(--color-accent);
          font-weight: 500;
        }

        @media (max-width: 640px) {
          h1 {
            font-size: 4rem;
          }

          .actions {
            flex-direction: column;
          }

          .btn-primary,
          .btn-secondary {
            width: 100%;
          }
        }
      `}</style>
    </div>
  );
}
