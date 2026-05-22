/**
 * Enhanced Toast Notification System
 * Success/error feedback with animations and progress
 */

import React from 'react';
import { CheckCircle, XCircle, AlertTriangle, Info, X, Loader2, ChevronRight } from 'lucide-react';
import { cn } from '../../lib/utils';

// Toast types
export type ToastType = 'success' | 'error' | 'warning' | 'info' | 'loading';

// Toast position
export type ToastPosition =
  | 'top-right'
  | 'top-center'
  | 'top-left'
  | 'bottom-right'
  | 'bottom-center'
  | 'bottom-left';

// Toast interface
export interface Toast {
  id: string;
  type: ToastType;
  title: string;
  description?: string;
  duration?: number;
  action?: {
    label: string;
    onClick: () => void;
  };
  onDismiss?: () => void;
  progress?: boolean;
}

// Toast configuration
const TOAST_CONFIG: Record<ToastType, { icon: React.ReactNode; className: string }> = {
  success: {
    icon: <CheckCircle className="w-5 h-5 text-green-400" />,
    className: 'border-green-500/30 bg-green-500/10',
  },
  error: {
    icon: <XCircle className="w-5 h-5 text-red-400" />,
    className: 'border-red-500/30 bg-red-500/10',
  },
  warning: {
    icon: <AlertTriangle className="w-5 h-5 text-yellow-400" />,
    className: 'border-yellow-500/30 bg-yellow-500/10',
  },
  info: {
    icon: <Info className="w-5 h-5 text-blue-400" />,
    className: 'border-blue-500/30 bg-blue-500/10',
  },
  loading: {
    icon: <Loader2 className="w-5 h-5 text-brand-400 animate-spin" />,
    className: 'border-brand-500/30 bg-brand-500/10',
  },
};

// Single toast component
const ToastItem: React.FC<{
  toast: Toast;
  onDismiss: () => void;
}> = ({ toast, onDismiss }) => {
  const [progress, setProgress] = React.useState(100);
  const [isExiting, setIsExiting] = React.useState(false);
  const config = TOAST_CONFIG[toast.type];

  // Auto-dismiss timer
  React.useEffect(() => {
    if (toast.type === 'loading' || !toast.duration) return;

    const startTime = Date.now();
    const duration = toast.duration;

    const interval = setInterval(() => {
      const elapsed = Date.now() - startTime;
      const remaining = Math.max(0, 100 - (elapsed / duration) * 100);
      setProgress(remaining);

      if (remaining === 0) {
        clearInterval(interval);
        handleDismiss();
      }
    }, 10);

    return () => clearInterval(interval);
  }, [toast.duration, toast.type]);

  const handleDismiss = () => {
    setIsExiting(true);
    setTimeout(() => {
      onDismiss();
      toast.onDismiss?.();
    }, 200);
  };

  return (
    <div
      className={cn(
        'relative flex items-start gap-3 p-4 rounded-lg border backdrop-blur-sm shadow-lg max-w-sm',
        config.className,
        isExiting ? 'animate-slideOut' : 'animate-slideIn'
      )}
      style={{
        animation: isExiting ? 'slideOut 0.2s ease-out forwards' : 'slideIn 0.3s ease-out forwards',
      }}
    >
      {/* Icon */}
      <div className="flex-shrink-0 mt-0.5">{config.icon}</div>

      {/* Content */}
      <div className="flex-1 min-w-0">
        <p className="font-medium text-sm">{toast.title}</p>
        {toast.description && (
          <p className="text-sm text-surface-400 mt-0.5">{toast.description}</p>
        )}
        {toast.action && (
          <button
            onClick={toast.action.onClick}
            className="flex items-center gap-1 text-sm text-brand-400 hover:text-brand-300 mt-2"
          >
            {toast.action.label}
            <ChevronRight className="w-4 h-4" />
          </button>
        )}
      </div>

      {/* Close button */}
      {toast.type !== 'loading' && (
        <button
          onClick={handleDismiss}
          className="flex-shrink-0 p-1 hover:bg-surface-700/50 rounded transition-colors"
        >
          <X className="w-4 h-4 text-surface-400" />
        </button>
      )}

      {/* Progress bar */}
      {toast.progress !== false && toast.duration && toast.type !== 'loading' && (
        <div className="absolute bottom-0 left-0 right-0 h-1 bg-surface-800 rounded-b-lg overflow-hidden">
          <div
            className={cn(
              'h-full transition-all',
              toast.type === 'success' && 'bg-green-500',
              toast.type === 'error' && 'bg-red-500',
              toast.type === 'warning' && 'bg-yellow-500',
              toast.type === 'info' && 'bg-blue-500'
            )}
            style={{ width: `${progress}%` }}
          />
        </div>
      )}
    </div>
  );
};

// Toast container
export const ToastContainer: React.FC<{
  toasts: Toast[];
  position?: ToastPosition;
  onDismiss: (id: string) => void;
}> = ({ toasts, position = 'top-right', onDismiss }) => {
  const positionClasses: Record<ToastPosition, string> = {
    'top-right': 'top-4 right-4 items-end',
    'top-center': 'top-4 left-1/2 -translate-x-1/2 items-center',
    'top-left': 'top-4 left-4 items-start',
    'bottom-right': 'bottom-4 right-4 items-end',
    'bottom-center': 'bottom-4 left-1/2 -translate-x-1/2 items-center',
    'bottom-left': 'bottom-4 left-4 items-start',
  };

  return (
    <div
      className={cn(
        'fixed z-50 flex flex-col gap-2 pointer-events-none',
        positionClasses[position]
      )}
    >
      {toasts.map((toast) => (
        <div key={toast.id} className="pointer-events-auto">
          <ToastItem toast={toast} onDismiss={() => onDismiss(toast.id)} />
        </div>
      ))}
    </div>
  );
};

// Toast context
interface ToastContextValue {
  toasts: Toast[];
  addToast: (toast: Omit<Toast, 'id'>) => string;
  dismissToast: (id: string) => void;
  dismissAll: () => void;
  updateToast: (id: string, updates: Partial<Toast>) => void;
}

const ToastContext = React.createContext<ToastContextValue | null>(null);

// Toast provider
export const ToastProvider: React.FC<{
  children: React.ReactNode;
  position?: ToastPosition;
  defaultDuration?: number;
}> = ({ children, position = 'top-right', defaultDuration = 5000 }) => {
  const [toasts, setToasts] = React.useState<Toast[]>([]);

  const addToast = React.useCallback(
    (toast: Omit<Toast, 'id'>): string => {
      const id = `toast-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
      const newToast: Toast = {
        ...toast,
        id,
        duration: toast.duration ?? (toast.type === 'loading' ? undefined : defaultDuration),
      };
      setToasts((prev) => [...prev, newToast]);
      return id;
    },
    [defaultDuration]
  );

  const dismissToast = React.useCallback((id: string) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }, []);

  const dismissAll = React.useCallback(() => {
    setToasts([]);
  }, []);

  const updateToast = React.useCallback((id: string, updates: Partial<Toast>) => {
    setToasts((prev) => prev.map((t) => (t.id === id ? { ...t, ...updates } : t)));
  }, []);

  return (
    <ToastContext.Provider value={{ toasts, addToast, dismissToast, dismissAll, updateToast }}>
      {children}
      <ToastContainer toasts={toasts} position={position} onDismiss={dismissToast} />
    </ToastContext.Provider>
  );
};

// Hook to use toast
export function useToast() {
  const context = React.useContext(ToastContext);
  if (!context) {
    throw new Error('useToast must be used within a ToastProvider');
  }

  const { addToast, dismissToast, updateToast, dismissAll } = context;

  // Convenience methods
  const success = React.useCallback(
    (title: string, description?: string) => {
      return addToast({ type: 'success', title, description });
    },
    [addToast]
  );

  const error = React.useCallback(
    (title: string, description?: string) => {
      return addToast({ type: 'error', title, description });
    },
    [addToast]
  );

  const warning = React.useCallback(
    (title: string, description?: string) => {
      return addToast({ type: 'warning', title, description });
    },
    [addToast]
  );

  const info = React.useCallback(
    (title: string, description?: string) => {
      return addToast({ type: 'info', title, description });
    },
    [addToast]
  );

  const loading = React.useCallback(
    (title: string, description?: string) => {
      return addToast({ type: 'loading', title, description });
    },
    [addToast]
  );

  // Promise toast (for async operations)
  const promise = React.useCallback(
    async <T,>(
      promiseFn: Promise<T>,
      messages: {
        loading: string;
        success: string | ((data: T) => string);
        error: string | ((err: Error) => string);
      }
    ): Promise<T> => {
      const id = loading(messages.loading);

      try {
        const result = await promiseFn;
        updateToast(id, {
          type: 'success',
          title:
            typeof messages.success === 'function' ? messages.success(result) : messages.success,
          duration: 5000,
        });
        return result;
      } catch (err) {
        updateToast(id, {
          type: 'error',
          title:
            typeof messages.error === 'function' ? messages.error(err as Error) : messages.error,
          duration: 5000,
        });
        throw err;
      }
    },
    [loading, updateToast]
  );

  return {
    addToast,
    dismissToast,
    dismissAll,
    updateToast,
    success,
    error,
    warning,
    info,
    loading,
    promise,
  };
}

// Animation styles for toasts
export const toastAnimationStyles = `
@keyframes slideIn {
  from {
    opacity: 0;
    transform: translateX(100%);
  }
  to {
    opacity: 1;
    transform: translateX(0);
  }
}

@keyframes slideOut {
  from {
    opacity: 1;
    transform: translateX(0);
  }
  to {
    opacity: 0;
    transform: translateX(100%);
  }
}
`;
