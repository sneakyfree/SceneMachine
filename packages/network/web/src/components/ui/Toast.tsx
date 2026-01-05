/**
 * Toast Component & Provider
 *
 * Toast notification system with multiple variants.
 */

import React, { createContext, useContext, useState, useCallback } from 'react';
import clsx from 'clsx';

export type ToastVariant = 'success' | 'error' | 'warning' | 'info';

export interface Toast {
  id: string;
  message: string;
  variant: ToastVariant;
  duration?: number;
}

interface ToastContextValue {
  toasts: Toast[];
  showToast: (message: string, variant?: ToastVariant, duration?: number) => void;
  hideToast: (id: string) => void;
}

const ToastContext = createContext<ToastContextValue | null>(null);

export function useToast() {
  const context = useContext(ToastContext);
  if (!context) {
    throw new Error('useToast must be used within a ToastProvider');
  }
  return context;
}

export function ToastProvider({ children }: { children: React.ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([]);

  const hideToast = useCallback((id: string) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }, []);

  const showToast = useCallback(
    (message: string, variant: ToastVariant = 'info', duration = 5000) => {
      const id = Math.random().toString(36).slice(2);
      const toast: Toast = { id, message, variant, duration };

      setToasts((prev) => [...prev, toast]);

      if (duration > 0) {
        setTimeout(() => hideToast(id), duration);
      }
    },
    [hideToast]
  );

  return (
    <ToastContext.Provider value={{ toasts, showToast, hideToast }}>
      {children}
      <ToastContainer toasts={toasts} onDismiss={hideToast} />
    </ToastContext.Provider>
  );
}

interface ToastContainerProps {
  toasts: Toast[];
  onDismiss: (id: string) => void;
}

function ToastContainer({ toasts, onDismiss }: ToastContainerProps) {
  if (toasts.length === 0) return null;

  return (
    <>
      <div className="toast-container" role="region" aria-label="Notifications">
        {toasts.map((toast) => (
          <ToastItem key={toast.id} toast={toast} onDismiss={onDismiss} />
        ))}
      </div>

      <style jsx>{`
        .toast-container {
          position: fixed;
          bottom: 1rem;
          right: 1rem;
          z-index: 200;
          display: flex;
          flex-direction: column;
          gap: 0.5rem;
          max-width: 24rem;
          width: calc(100vw - 2rem);
        }

        @media (min-width: 640px) {
          .toast-container {
            bottom: 1.5rem;
            right: 1.5rem;
          }
        }
      `}</style>
    </>
  );
}

interface ToastItemProps {
  toast: Toast;
  onDismiss: (id: string) => void;
}

function ToastItem({ toast, onDismiss }: ToastItemProps) {
  const icons: Record<ToastVariant, React.ReactNode> = {
    success: (
      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
        <circle cx="12" cy="12" r="10" />
        <path d="M9 12l2 2 4-4" />
      </svg>
    ),
    error: (
      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
        <circle cx="12" cy="12" r="10" />
        <line x1="15" y1="9" x2="9" y2="15" />
        <line x1="9" y1="9" x2="15" y2="15" />
      </svg>
    ),
    warning: (
      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
        <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z" />
        <line x1="12" y1="9" x2="12" y2="13" />
        <line x1="12" y1="17" x2="12.01" y2="17" />
      </svg>
    ),
    info: (
      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
        <circle cx="12" cy="12" r="10" />
        <line x1="12" y1="16" x2="12" y2="12" />
        <line x1="12" y1="8" x2="12.01" y2="8" />
      </svg>
    ),
  };

  return (
    <>
      <div
        className={clsx('toast', `toast-${toast.variant}`)}
        role="alert"
        aria-live="polite"
      >
        <span className="toast-icon">{icons[toast.variant]}</span>
        <span className="toast-message">{toast.message}</span>
        <button
          className="toast-dismiss"
          onClick={() => onDismiss(toast.id)}
          aria-label="Dismiss notification"
        >
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <line x1="18" y1="6" x2="6" y2="18" />
            <line x1="6" y1="6" x2="18" y2="18" />
          </svg>
        </button>
      </div>

      <style jsx>{`
        .toast {
          display: flex;
          align-items: center;
          gap: 0.75rem;
          padding: 0.875rem 1rem;
          background: var(--color-bg-primary);
          border: 1px solid var(--color-border);
          border-radius: var(--radius-md);
          box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.3);
          animation: toast-enter 0.3s ease-out;
        }

        @keyframes toast-enter {
          from {
            opacity: 0;
            transform: translateX(100%);
          }
          to {
            opacity: 1;
            transform: translateX(0);
          }
        }

        .toast-icon {
          flex-shrink: 0;
          display: flex;
        }

        .toast-success .toast-icon {
          color: var(--color-success);
        }

        .toast-error .toast-icon {
          color: var(--color-error);
        }

        .toast-warning .toast-icon {
          color: var(--color-warning);
        }

        .toast-info .toast-icon {
          color: var(--color-accent);
        }

        .toast-message {
          flex: 1;
          font-size: var(--text-sm);
          color: var(--color-text-primary);
        }

        .toast-dismiss {
          flex-shrink: 0;
          display: flex;
          align-items: center;
          justify-content: center;
          width: 1.5rem;
          height: 1.5rem;
          background: transparent;
          border: none;
          border-radius: var(--radius-sm);
          color: var(--color-text-tertiary);
          cursor: pointer;
          transition: color var(--transition-fast),
            background-color var(--transition-fast);
        }

        .toast-dismiss:hover {
          background: var(--color-bg-secondary);
          color: var(--color-text-primary);
        }
      `}</style>
    </>
  );
}

export default ToastProvider;
