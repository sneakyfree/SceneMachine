/**
 * Toast notification store using Zustand.
 */

import { create } from 'zustand';
import { devtools } from 'zustand/middleware';
import { immer } from 'zustand/middleware/immer';

export type ToastType = 'success' | 'error' | 'warning' | 'info';

export interface Toast {
  id: string;
  type: ToastType;
  title: string;
  message?: string;
  duration?: number;
  action?: {
    label: string;
    onClick: () => void;
  };
  dismissible?: boolean;
  createdAt: number;
}

interface ToastStoreState {
  toasts: Toast[];
  maxToasts: number;

  // Actions
  addToast: (toast: Omit<Toast, 'id' | 'createdAt'>) => string;
  removeToast: (id: string) => void;
  clearAllToasts: () => void;

  // Convenience methods
  success: (title: string, message?: string, options?: Partial<Toast>) => string;
  error: (title: string, message?: string, options?: Partial<Toast>) => string;
  warning: (title: string, message?: string, options?: Partial<Toast>) => string;
  info: (title: string, message?: string, options?: Partial<Toast>) => string;
}

let toastIdCounter = 0;

const generateId = () => {
  toastIdCounter += 1;
  return `toast-${toastIdCounter}-${Date.now()}`;
};

export const useToastStore = create<ToastStoreState>()(
  devtools(
    immer((set, get) => ({
      toasts: [],
      maxToasts: 5,

      addToast: (toast) => {
        const id = generateId();
        const newToast: Toast = {
          ...toast,
          id,
          createdAt: Date.now(),
          duration: toast.duration ?? getDefaultDuration(toast.type),
          dismissible: toast.dismissible ?? true,
        };

        set((state) => {
          // Add new toast
          state.toasts.push(newToast);

          // Remove oldest if exceeding max
          if (state.toasts.length > state.maxToasts) {
            state.toasts = state.toasts.slice(-state.maxToasts);
          }
        });

        // Auto-dismiss after duration
        if (newToast.duration && newToast.duration > 0) {
          setTimeout(() => {
            get().removeToast(id);
          }, newToast.duration);
        }

        return id;
      },

      removeToast: (id) => {
        set((state) => {
          state.toasts = state.toasts.filter((t) => t.id !== id);
        });
      },

      clearAllToasts: () => {
        set((state) => {
          state.toasts = [];
        });
      },

      success: (title, message, options) => {
        return get().addToast({ type: 'success', title, message, ...options });
      },

      error: (title, message, options) => {
        return get().addToast({ type: 'error', title, message, ...options });
      },

      warning: (title, message, options) => {
        return get().addToast({ type: 'warning', title, message, ...options });
      },

      info: (title, message, options) => {
        return get().addToast({ type: 'info', title, message, ...options });
      },
    })),
    { name: 'ToastStore' }
  )
);

// Default durations based on toast type
function getDefaultDuration(type: ToastType): number {
  switch (type) {
    case 'success':
      return 3000;
    case 'info':
      return 4000;
    case 'warning':
      return 5000;
    case 'error':
      return 6000;
    default:
      return 4000;
  }
}

// Hook for easy toast access
export function useToast() {
  const { success, error, warning, info, removeToast, clearAllToasts } = useToastStore();

  return {
    success,
    error,
    warning,
    info,
    dismiss: removeToast,
    dismissAll: clearAllToasts,
  };
}
