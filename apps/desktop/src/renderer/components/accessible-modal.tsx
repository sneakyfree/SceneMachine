/**
 * Accessible Modal Component
 *
 * A fully accessible modal/dialog component with:
 * - Focus trapping
 * - Keyboard navigation (Escape to close)
 * - ARIA attributes
 * - Screen reader announcements
 * - Focus restoration on close
 */

import React, { useEffect, useId, useCallback } from 'react';
import { createPortal } from 'react-dom';
import { X } from 'lucide-react';
import { cn } from '../lib/utils';
import {
  useFocusTrap,
  announce,
  ariaDialog,
  usePrefersReducedMotion,
} from '../lib/accessibility';

// ============================================================================
// Types
// ============================================================================

export interface ModalProps {
  /**
   * Whether the modal is open.
   */
  isOpen: boolean;
  /**
   * Callback to close the modal.
   */
  onClose: () => void;
  /**
   * Modal title (required for accessibility).
   */
  title: string;
  /**
   * Optional description for screen readers.
   */
  description?: string;
  /**
   * Modal content.
   */
  children: React.ReactNode;
  /**
   * Optional footer content (e.g., action buttons).
   */
  footer?: React.ReactNode;
  /**
   * Size variant.
   */
  size?: 'sm' | 'md' | 'lg' | 'xl' | 'full';
  /**
   * Whether clicking the backdrop closes the modal.
   */
  closeOnBackdrop?: boolean;
  /**
   * Whether pressing Escape closes the modal.
   */
  closeOnEscape?: boolean;
  /**
   * Whether to show the close button.
   */
  showCloseButton?: boolean;
  /**
   * Additional CSS classes for the modal container.
   */
  className?: string;
  /**
   * Initial element to focus (selector or element).
   */
  initialFocus?: string | HTMLElement | null;
  /**
   * Role override (dialog, alertdialog).
   */
  role?: 'dialog' | 'alertdialog';
}

// ============================================================================
// Size Classes
// ============================================================================

const sizeClasses: Record<string, string> = {
  sm: 'max-w-sm',
  md: 'max-w-md',
  lg: 'max-w-lg',
  xl: 'max-w-xl',
  full: 'max-w-[90vw] max-h-[90vh]',
};

// ============================================================================
// Modal Component
// ============================================================================

export function Modal({
  isOpen,
  onClose,
  title,
  description,
  children,
  footer,
  size = 'md',
  closeOnBackdrop = true,
  closeOnEscape = true,
  showCloseButton = true,
  className,
  initialFocus,
  role = 'dialog',
}: ModalProps) {
  // Generate unique IDs for ARIA
  const titleId = useId();
  const descriptionId = useId();

  // Detect reduced motion preference
  const prefersReducedMotion = usePrefersReducedMotion();

  // Focus trap
  const containerRef = useFocusTrap<HTMLDivElement>({
    active: isOpen,
    autoFocus: true,
    restoreFocus: true,
    initialFocus,
    onEscape: closeOnEscape ? onClose : undefined,
  });

  // Prevent body scroll when modal is open
  useEffect(() => {
    if (isOpen) {
      const originalOverflow = document.body.style.overflow;
      document.body.style.overflow = 'hidden';
      return () => {
        document.body.style.overflow = originalOverflow;
      };
    }
  }, [isOpen]);

  // Announce modal to screen readers
  useEffect(() => {
    if (isOpen) {
      announce(`${title} dialog opened`, 'polite');
    }
  }, [isOpen, title]);

  // Handle backdrop click
  const handleBackdropClick = useCallback(
    (event: React.MouseEvent) => {
      if (closeOnBackdrop && event.target === event.currentTarget) {
        onClose();
      }
    },
    [closeOnBackdrop, onClose]
  );

  // Handle close button click
  const handleCloseClick = useCallback(() => {
    announce(`${title} dialog closed`, 'polite');
    onClose();
  }, [onClose, title]);

  // Don't render if not open
  if (!isOpen) return null;

  // Get ARIA attributes
  const ariaAttrs = ariaDialog({
    labelledBy: titleId,
    describedBy: description ? descriptionId : undefined,
    modal: true,
  });

  // Build modal content
  const modalContent = (
    <div
      className={cn(
        'fixed inset-0 z-50 flex items-center justify-center p-4',
        // Backdrop
        'bg-black/60 backdrop-blur-sm',
        // Animation
        !prefersReducedMotion && 'animate-fade-in'
      )}
      onClick={handleBackdropClick}
      aria-hidden="false"
    >
      {/* Modal container */}
      <div
        ref={containerRef}
        role={role}
        {...ariaAttrs}
        className={cn(
          'relative w-full',
          sizeClasses[size],
          'bg-surface-900 rounded-lg shadow-2xl',
          'border border-surface-700',
          'flex flex-col max-h-[90vh]',
          // Animation
          !prefersReducedMotion && 'animate-scale-in',
          className
        )}
      >
        {/* Header */}
        <div className="flex items-start justify-between p-4 border-b border-surface-700">
          <div>
            <h2
              id={titleId}
              className="text-lg font-semibold text-surface-100"
            >
              {title}
            </h2>
            {description && (
              <p
                id={descriptionId}
                className="mt-1 text-sm text-surface-400"
              >
                {description}
              </p>
            )}
          </div>
          {showCloseButton && (
            <button
              type="button"
              onClick={handleCloseClick}
              className={cn(
                'p-2 -mr-2 -mt-1',
                'text-surface-400 hover:text-surface-200',
                'rounded-lg hover:bg-surface-800',
                'transition-colors',
                'focus:outline-none focus:ring-2 focus:ring-brand-500'
              )}
              aria-label="Close dialog"
            >
              <X className="w-5 h-5" />
            </button>
          )}
        </div>

        {/* Body */}
        <div className="flex-1 overflow-y-auto p-4">
          {children}
        </div>

        {/* Footer */}
        {footer && (
          <div className="p-4 border-t border-surface-700 bg-surface-800/50">
            {footer}
          </div>
        )}
      </div>
    </div>
  );

  // Render using portal
  return createPortal(modalContent, document.body);
}

// ============================================================================
// Confirm Dialog Component
// ============================================================================

export interface ConfirmDialogProps {
  isOpen: boolean;
  onConfirm: () => void;
  onCancel: () => void;
  title: string;
  message: string | React.ReactNode;
  confirmText?: string;
  cancelText?: string;
  variant?: 'default' | 'danger';
  isLoading?: boolean;
}

export function ConfirmDialog({
  isOpen,
  onConfirm,
  onCancel,
  title,
  message,
  confirmText = 'Confirm',
  cancelText = 'Cancel',
  variant = 'default',
  isLoading = false,
}: ConfirmDialogProps) {
  return (
    <Modal
      isOpen={isOpen}
      onClose={onCancel}
      title={title}
      size="sm"
      role="alertdialog"
      closeOnBackdrop={!isLoading}
      closeOnEscape={!isLoading}
      showCloseButton={!isLoading}
      footer={
        <div className="flex justify-end gap-3">
          <button
            type="button"
            onClick={onCancel}
            disabled={isLoading}
            className={cn(
              'px-4 py-2 text-sm font-medium rounded-lg',
              'bg-surface-700 text-surface-200 hover:bg-surface-600',
              'transition-colors',
              'focus:outline-none focus:ring-2 focus:ring-surface-500',
              'disabled:opacity-50 disabled:cursor-not-allowed'
            )}
          >
            {cancelText}
          </button>
          <button
            type="button"
            onClick={onConfirm}
            disabled={isLoading}
            className={cn(
              'px-4 py-2 text-sm font-medium rounded-lg',
              'transition-colors',
              'focus:outline-none focus:ring-2',
              'disabled:opacity-50 disabled:cursor-not-allowed',
              variant === 'danger'
                ? 'bg-red-600 text-white hover:bg-red-700 focus:ring-red-500'
                : 'bg-brand-500 text-white hover:bg-brand-600 focus:ring-brand-400'
            )}
          >
            {isLoading ? 'Processing...' : confirmText}
          </button>
        </div>
      }
    >
      <div className="text-surface-300">
        {typeof message === 'string' ? <p>{message}</p> : message}
      </div>
    </Modal>
  );
}

// ============================================================================
// Alert Dialog Component
// ============================================================================

export interface AlertDialogProps {
  isOpen: boolean;
  onClose: () => void;
  title: string;
  message: string | React.ReactNode;
  buttonText?: string;
  variant?: 'info' | 'success' | 'warning' | 'error';
}

export function AlertDialog({
  isOpen,
  onClose,
  title,
  message,
  buttonText = 'OK',
  variant = 'info',
}: AlertDialogProps) {
  const variantClasses = {
    info: 'bg-blue-500',
    success: 'bg-green-500',
    warning: 'bg-amber-500',
    error: 'bg-red-500',
  };

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title={title}
      size="sm"
      role="alertdialog"
      footer={
        <div className="flex justify-end">
          <button
            type="button"
            onClick={onClose}
            className={cn(
              'px-4 py-2 text-sm font-medium rounded-lg',
              'text-white transition-colors',
              'focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-offset-surface-900',
              variantClasses[variant],
              'hover:opacity-90'
            )}
          >
            {buttonText}
          </button>
        </div>
      }
    >
      <div className="text-surface-300">
        {typeof message === 'string' ? <p>{message}</p> : message}
      </div>
    </Modal>
  );
}

// ============================================================================
// useModal Hook
// ============================================================================

export interface UseModalReturn {
  isOpen: boolean;
  open: () => void;
  close: () => void;
  toggle: () => void;
}

export function useModal(initialState = false): UseModalReturn {
  const [isOpen, setIsOpen] = React.useState(initialState);

  const open = useCallback(() => setIsOpen(true), []);
  const close = useCallback(() => setIsOpen(false), []);
  const toggle = useCallback(() => setIsOpen((prev) => !prev), []);

  return { isOpen, open, close, toggle };
}

// ============================================================================
// Exports
// ============================================================================

export default Modal;
