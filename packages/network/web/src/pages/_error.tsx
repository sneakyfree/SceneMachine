/**
 * Custom Error Page
 *
 * Handles all error states with appropriate messaging.
 */

import React from 'react';
import { NextPageContext } from 'next';
import Link from 'next/link';

interface ErrorProps {
  statusCode: number;
}

const ERROR_MESSAGES: Record<number, { title: string; description: string }> = {
  400: {
    title: 'Bad Request',
    description: 'The request could not be understood by the server.',
  },
  401: {
    title: 'Unauthorized',
    description: 'You need to sign in to access this page.',
  },
  403: {
    title: 'Forbidden',
    description: "You don't have permission to access this resource.",
  },
  404: {
    title: 'Not Found',
    description: "The page you're looking for doesn't exist or has been moved.",
  },
  500: {
    title: 'Server Error',
    description: "Something went wrong on our end. We're working to fix it.",
  },
  502: {
    title: 'Bad Gateway',
    description: 'The server received an invalid response.',
  },
  503: {
    title: 'Service Unavailable',
    description: 'The service is temporarily unavailable. Please try again later.',
  },
};

function ErrorPage({ statusCode }: ErrorProps) {
  const error = ERROR_MESSAGES[statusCode] || {
    title: 'Error',
    description: 'An unexpected error occurred.',
  };

  const isClientError = statusCode >= 400 && statusCode < 500;

  return (
    <div className="error-page">
      <div className="error-content">
        <div className="error-icon">
          {isClientError ? (
            <svg width="100" height="100" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
              <circle cx="12" cy="12" r="10" />
              <line x1="15" y1="9" x2="9" y2="15" />
              <line x1="9" y1="9" x2="15" y2="15" />
            </svg>
          ) : (
            <svg width="100" height="100" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
              <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z" />
              <line x1="12" y1="9" x2="12" y2="13" />
              <line x1="12" y1="17" x2="12.01" y2="17" />
            </svg>
          )}
        </div>

        <h1>{statusCode}</h1>
        <h2>{error.title}</h2>
        <p>{error.description}</p>

        <div className="actions">
          {statusCode === 401 ? (
            <Link href="/login" className="btn-primary">
              Sign In
            </Link>
          ) : (
            <button onClick={() => window.location.reload()} className="btn-primary">
              Try Again
            </button>
          )}
          <Link href="/" className="btn-secondary">
            Go Home
          </Link>
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
          color: ${isClientError ? 'var(--color-text-tertiary)' : 'var(--color-warning)'};
          margin-bottom: var(--space-6);
        }

        h1 {
          font-size: 5rem;
          font-weight: 800;
          background: var(--gradient-primary);
          -webkit-background-clip: text;
          -webkit-text-fill-color: transparent;
          line-height: 1;
          margin-bottom: var(--space-2);
        }

        h2 {
          font-size: var(--text-xl);
          margin-bottom: var(--space-4);
        }

        p {
          color: var(--color-text-secondary);
          margin-bottom: var(--space-6);
        }

        .actions {
          display: flex;
          gap: var(--space-3);
          justify-content: center;
        }

        .btn-primary,
        .btn-secondary {
          padding: var(--space-3) var(--space-5);
          border-radius: var(--radius-md);
          font-weight: 600;
          transition: all var(--transition-fast);
          text-decoration: none;
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
        }

        .btn-secondary:hover {
          border-color: var(--color-accent);
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

ErrorPage.getInitialProps = ({ res, err }: NextPageContext): ErrorProps => {
  const statusCode = res ? res.statusCode : err ? err.statusCode ?? 500 : 404;
  return { statusCode };
};

export default ErrorPage;
