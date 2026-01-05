/**
 * Modal Component
 *
 * Accessible modal dialog with backdrop.
 */

import React, { useEffect, useCallback } from 'react';
import clsx from 'clsx';

export interface ModalProps {
  isOpen: boolean;
  onClose: () => void;
  title?: string;
  size?: 'sm' | 'md' | 'lg' | 'xl' | 'full';
  children: React.ReactNode;
  footer?: React.ReactNode;
  closeOnBackdrop?: boolean;
  closeOnEscape?: boolean;
  showCloseButton?: boolean;
}

export function Modal({
  isOpen,
  onClose,
  title,
  size = 'md',
  children,
  footer,
  closeOnBackdrop = true,
  closeOnEscape = true,
  showCloseButton = true,
}: ModalProps) {
  // Handle escape key
  const handleKeyDown = useCallback(
    (event: KeyboardEvent) => {
      if (closeOnEscape && event.key === 'Escape') {
        onClose();
      }
    },
    [closeOnEscape, onClose]
  );

  useEffect(() => {
    if (isOpen) {
      document.addEventListener('keydown', handleKeyDown);
      document.body.style.overflow = 'hidden';
    }
    return () => {
      document.removeEventListener('keydown', handleKeyDown);
      document.body.style.overflow = '';
    };
  }, [isOpen, handleKeyDown]);

  if (!isOpen) return null;

  return (
    <>
      <div className="modal-overlay" aria-hidden="true">
        <div
          className="modal-backdrop"
          onClick={closeOnBackdrop ? onClose : undefined}
        />
        <div
          className={clsx('modal-container', `modal-${size}`)}
          role="dialog"
          aria-modal="true"
          aria-labelledby={title ? 'modal-title' : undefined}
        >
          {(title || showCloseButton) && (
            <div className="modal-header">
              {title && (
                <h2 id="modal-title" className="modal-title">
                  {title}
                </h2>
              )}
              {showCloseButton && (
                <button
                  className="modal-close"
                  onClick={onClose}
                  aria-label="Close modal"
                >
                  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <line x1="18" y1="6" x2="6" y2="18" />
                    <line x1="6" y1="6" x2="18" y2="18" />
                  </svg>
                </button>
              )}
            </div>
          )}
          <div className="modal-body">{children}</div>
          {footer && <div className="modal-footer">{footer}</div>}
        </div>
      </div>

      <style jsx>{`
        .modal-overlay {
          position: fixed;
          inset: 0;
          z-index: 100;
          display: flex;
          align-items: center;
          justify-content: center;
          padding: 1rem;
        }

        .modal-backdrop {
          position: absolute;
          inset: 0;
          background: rgba(0, 0, 0, 0.75);
          backdrop-filter: blur(4px);
        }

        .modal-container {
          position: relative;
          background: var(--color-bg-primary);
          border-radius: var(--radius-lg);
          box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.5);
          max-height: calc(100vh - 2rem);
          display: flex;
          flex-direction: column;
          overflow: hidden;
          animation: modal-enter 0.2s ease-out;
        }

        @keyframes modal-enter {
          from {
            opacity: 0;
            transform: scale(0.95);
          }
          to {
            opacity: 1;
            transform: scale(1);
          }
        }

        /* Sizes */
        .modal-sm {
          width: 100%;
          max-width: 24rem;
        }

        .modal-md {
          width: 100%;
          max-width: 32rem;
        }

        .modal-lg {
          width: 100%;
          max-width: 48rem;
        }

        .modal-xl {
          width: 100%;
          max-width: 64rem;
        }

        .modal-full {
          width: calc(100vw - 2rem);
          height: calc(100vh - 2rem);
          max-width: none;
        }

        .modal-header {
          display: flex;
          align-items: center;
          justify-content: space-between;
          padding: 1rem 1.5rem;
          border-bottom: 1px solid var(--color-border);
        }

        .modal-title {
          font-size: var(--text-lg);
          font-weight: 600;
          margin: 0;
        }

        .modal-close {
          display: flex;
          align-items: center;
          justify-content: center;
          width: 2rem;
          height: 2rem;
          border-radius: var(--radius-md);
          background: transparent;
          border: none;
          color: var(--color-text-secondary);
          cursor: pointer;
          transition: background-color var(--transition-fast),
            color var(--transition-fast);
        }

        .modal-close:hover {
          background: var(--color-bg-secondary);
          color: var(--color-text-primary);
        }

        .modal-body {
          flex: 1;
          padding: 1.5rem;
          overflow-y: auto;
        }

        .modal-footer {
          display: flex;
          align-items: center;
          justify-content: flex-end;
          gap: 0.75rem;
          padding: 1rem 1.5rem;
          border-top: 1px solid var(--color-border);
        }
      `}</style>
    </>
  );
}

export default Modal;
