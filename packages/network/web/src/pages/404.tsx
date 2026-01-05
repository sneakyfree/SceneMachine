/**
 * 404 Page
 *
 * Custom not found page for SceneMachine Network.
 */

import React from 'react';
import Link from 'next/link';

export default function NotFoundPage() {
  return (
    <div className="error-page">
      <div className="error-content">
        <div className="error-icon">
          <svg width="120" height="120" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1">
            <circle cx="12" cy="12" r="10" />
            <path d="M16 16s-1.5-2-4-2-4 2-4 2" />
            <line x1="9" y1="9" x2="9.01" y2="9" strokeWidth="2" />
            <line x1="15" y1="9" x2="15.01" y2="9" strokeWidth="2" />
          </svg>
        </div>

        <h1>404</h1>
        <h2>Page Not Found</h2>
        <p>
          Oops! The page you're looking for doesn't exist or has been moved.
        </p>

        <div className="actions">
          <Link href="/" className="btn-primary">
            Go Home
          </Link>
          <button onClick={() => window.history.back()} className="btn-secondary">
            Go Back
          </button>
        </div>

        <div className="suggestions">
          <p>You might want to check out:</p>
          <nav>
            <Link href="/browse">Browse Videos</Link>
            <Link href="/search">Search</Link>
            <Link href="/upload">Upload a Video</Link>
          </nav>
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
          color: var(--color-text-tertiary);
          margin-bottom: var(--space-6);
        }

        h1 {
          font-size: 6rem;
          font-weight: 800;
          background: var(--gradient-primary);
          -webkit-background-clip: text;
          -webkit-text-fill-color: transparent;
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
          text-decoration: none;
        }

        .btn-primary:hover {
          opacity: 0.9;
        }

        .btn-secondary {
          background: var(--color-bg-secondary);
          border: 1px solid var(--color-border);
          color: var(--color-text-primary);
        }

        .btn-secondary:hover {
          border-color: var(--color-accent);
        }

        .suggestions {
          padding-top: var(--space-6);
          border-top: 1px solid var(--color-border);
        }

        .suggestions p {
          font-size: var(--text-sm);
          margin-bottom: var(--space-3);
        }

        .suggestions nav {
          display: flex;
          gap: var(--space-4);
          justify-content: center;
        }

        .suggestions a {
          color: var(--color-accent);
          font-weight: 500;
          font-size: var(--text-sm);
        }

        .suggestions a:hover {
          text-decoration: underline;
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

          .suggestions nav {
            flex-direction: column;
            gap: var(--space-2);
          }
        }
      `}</style>
    </div>
  );
}
