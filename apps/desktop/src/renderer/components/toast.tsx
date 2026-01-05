/**
 * Toast notification component.
 */

import { useState } from 'react';
import {
  CheckCircle,
  XCircle,
  AlertTriangle,
  Info,
  X,
} from 'lucide-react';
import { cn } from '../lib/utils';
import { Toast as ToastType, useToastStore } from '../stores/toast-store';

export function useToast() {
  const store = useToastStore();

  // Helper function for showToast(message, type) pattern
  const showToast = (message: string, type: 'success' | 'error' | 'warning' | 'info' = 'info') => {
    switch (type) {
      case 'success':
        return store.success(message);
      case 'error':
        return store.error(message);
      case 'warning':
        return store.warning(message);
      case 'info':
      default:
        return store.info(message);
    }
  };

  return {
    toast: store.addToast,
    dismiss: store.removeToast,
    clear: store.clearAllToasts,
    toasts: store.toasts,
    showToast,
  };
}

// Individual toast item
function ToastItem({ toast, onDismiss }: { toast: ToastType; onDismiss: () => void }) {
  const [isExiting, setIsExiting] = useState(false);

  const handleDismiss = () => {
    setIsExiting(true);
    setTimeout(onDismiss, 200); // Match animation duration
  };

  const icons = {
    success: CheckCircle,
    error: XCircle,
    warning: AlertTriangle,
    info: Info,
  };

  const Icon = icons[toast.type];

  const colors = {
    success: {
      bg: 'bg-green-500/10',
      border: 'border-green-500/30',
      icon: 'text-green-400',
      title: 'text-green-300',
    },
    error: {
      bg: 'bg-red-500/10',
      border: 'border-red-500/30',
      icon: 'text-red-400',
      title: 'text-red-300',
    },
    warning: {
      bg: 'bg-yellow-500/10',
      border: 'border-yellow-500/30',
      icon: 'text-yellow-400',
      title: 'text-yellow-300',
    },
    info: {
      bg: 'bg-blue-500/10',
      border: 'border-blue-500/30',
      icon: 'text-blue-400',
      title: 'text-blue-300',
    },
  };

  const colorSet = colors[toast.type];

  return (
    <div
      className={cn(
        'flex items-start gap-3 p-4 rounded-lg border shadow-lg backdrop-blur-sm',
        'transform transition-all duration-200 ease-out',
        colorSet.bg,
        colorSet.border,
        isExiting ? 'opacity-0 translate-x-4' : 'opacity-100 translate-x-0'
      )}
      role="alert"
    >
      <Icon className={cn('w-5 h-5 flex-shrink-0 mt-0.5', colorSet.icon)} />

      <div className="flex-1 min-w-0">
        <p className={cn('font-medium', colorSet.title)}>{toast.title}</p>
        {toast.message && (
          <p className="text-sm text-surface-400 mt-1">{toast.message}</p>
        )}
        {toast.action && (
          <button
            onClick={toast.action.onClick}
            className="mt-2 text-sm text-brand-400 hover:text-brand-300 font-medium"
          >
            {toast.action.label}
          </button>
        )}
      </div>

      {toast.dismissible && (
        <button
          onClick={handleDismiss}
          className="icon-btn flex-shrink-0 p-2 text-surface-400 hover:text-surface-300 transition-colors rounded"
          aria-label="Dismiss notification"
        >
          <X className="w-5 h-5" />
        </button>
      )}
    </div>
  );
}

// Toast container that renders all toasts
export function ToastContainer() {
  const { toasts, removeToast } = useToastStore();

  if (toasts.length === 0) return null;

  return (
    <div
      className="fixed bottom-4 right-4 z-50 flex flex-col gap-2 max-w-sm w-full pointer-events-none"
      aria-live="polite"
      aria-label="Notifications"
    >
      {toasts.map((toast) => (
        <div key={toast.id} className="pointer-events-auto">
          <ToastItem toast={toast} onDismiss={() => removeToast(toast.id)} />
        </div>
      ))}
    </div>
  );
}

// Progress toast for long-running operations
export function ProgressToast({
  title,
  progress,
  message,
  onCancel,
}: {
  title: string;
  progress: number;
  message?: string;
  onCancel?: () => void;
}) {
  return (
    <div className="flex flex-col gap-2 p-4 rounded-lg border bg-surface-800/90 border-surface-700 shadow-lg backdrop-blur-sm">
      <div className="flex items-center justify-between">
        <span className="font-medium">{title}</span>
        <span className="text-sm text-surface-400">{Math.round(progress)}%</span>
      </div>

      <div className="w-full h-2 bg-surface-700 rounded-full overflow-hidden">
        <div
          className="h-full bg-brand-500 transition-all duration-300"
          style={{ width: `${progress}%` }}
        />
      </div>

      {message && <p className="text-sm text-surface-400">{message}</p>}

      {onCancel && (
        <button
          onClick={onCancel}
          className="self-end text-sm text-surface-400 hover:text-surface-300"
        >
          Cancel
        </button>
      )}
    </div>
  );
}
