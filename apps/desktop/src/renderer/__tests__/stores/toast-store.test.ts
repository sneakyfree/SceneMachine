/**
 * Toast store unit tests.
 */

import { describe, it, expect, beforeEach, vi, afterEach } from 'vitest';
import { act } from '@testing-library/react';
import { useToastStore } from '../../stores/toast-store';

describe('ToastStore', () => {
  beforeEach(() => {
    // Reset store state before each test
    useToastStore.setState({ toasts: [] });
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  describe('addToast', () => {
    it('should add a toast to the store', () => {
      const { addToast, toasts } = useToastStore.getState();

      act(() => {
        addToast({ type: 'success', title: 'Test Toast' });
      });

      const state = useToastStore.getState();
      expect(state.toasts).toHaveLength(1);
      expect(state.toasts[0].title).toBe('Test Toast');
      expect(state.toasts[0].type).toBe('success');
    });

    it('should generate unique IDs for toasts', () => {
      const { addToast } = useToastStore.getState();

      act(() => {
        addToast({ type: 'info', title: 'Toast 1' });
        addToast({ type: 'info', title: 'Toast 2' });
      });

      const state = useToastStore.getState();
      expect(state.toasts[0].id).not.toBe(state.toasts[1].id);
    });

    it('should respect maxToasts limit', () => {
      useToastStore.setState({ maxToasts: 3 });
      const { addToast } = useToastStore.getState();

      act(() => {
        for (let i = 0; i < 5; i++) {
          addToast({ type: 'info', title: `Toast ${i}` });
        }
      });

      const state = useToastStore.getState();
      expect(state.toasts).toHaveLength(3);
      // Should keep the most recent toasts
      expect(state.toasts[0].title).toBe('Toast 2');
      expect(state.toasts[2].title).toBe('Toast 4');
    });

    it('should set default duration based on type', () => {
      const { addToast } = useToastStore.getState();

      act(() => {
        addToast({ type: 'success', title: 'Success' });
        addToast({ type: 'error', title: 'Error' });
        addToast({ type: 'warning', title: 'Warning' });
        addToast({ type: 'info', title: 'Info' });
      });

      const state = useToastStore.getState();
      expect(state.toasts.find((t) => t.type === 'success')?.duration).toBe(3000);
      expect(state.toasts.find((t) => t.type === 'error')?.duration).toBe(6000);
      expect(state.toasts.find((t) => t.type === 'warning')?.duration).toBe(5000);
      expect(state.toasts.find((t) => t.type === 'info')?.duration).toBe(4000);
    });

    it('should allow custom duration', () => {
      const { addToast } = useToastStore.getState();

      act(() => {
        addToast({ type: 'info', title: 'Custom', duration: 10000 });
      });

      const state = useToastStore.getState();
      expect(state.toasts[0].duration).toBe(10000);
    });
  });

  describe('removeToast', () => {
    it('should remove a toast by ID', () => {
      const { addToast, removeToast } = useToastStore.getState();

      let toastId: string;
      act(() => {
        toastId = addToast({ type: 'info', title: 'To Remove' });
        addToast({ type: 'info', title: 'To Keep' });
      });

      expect(useToastStore.getState().toasts).toHaveLength(2);

      act(() => {
        removeToast(toastId);
      });

      const state = useToastStore.getState();
      expect(state.toasts).toHaveLength(1);
      expect(state.toasts[0].title).toBe('To Keep');
    });

    it('should handle removing non-existent toast gracefully', () => {
      const { addToast, removeToast } = useToastStore.getState();

      act(() => {
        addToast({ type: 'info', title: 'Existing' });
      });

      act(() => {
        removeToast('non-existent-id');
      });

      const state = useToastStore.getState();
      expect(state.toasts).toHaveLength(1);
    });
  });

  describe('clearAllToasts', () => {
    it('should clear all toasts', () => {
      const { addToast, clearAllToasts } = useToastStore.getState();

      act(() => {
        addToast({ type: 'info', title: 'Toast 1' });
        addToast({ type: 'info', title: 'Toast 2' });
        addToast({ type: 'info', title: 'Toast 3' });
      });

      expect(useToastStore.getState().toasts).toHaveLength(3);

      act(() => {
        clearAllToasts();
      });

      expect(useToastStore.getState().toasts).toHaveLength(0);
    });
  });

  describe('convenience methods', () => {
    it('success() should create success toast', () => {
      const { success } = useToastStore.getState();

      act(() => {
        success('Success!', 'Operation completed');
      });

      const state = useToastStore.getState();
      expect(state.toasts[0].type).toBe('success');
      expect(state.toasts[0].title).toBe('Success!');
      expect(state.toasts[0].message).toBe('Operation completed');
    });

    it('error() should create error toast', () => {
      const { error } = useToastStore.getState();

      act(() => {
        error('Error!', 'Something went wrong');
      });

      const state = useToastStore.getState();
      expect(state.toasts[0].type).toBe('error');
      expect(state.toasts[0].title).toBe('Error!');
    });

    it('warning() should create warning toast', () => {
      const { warning } = useToastStore.getState();

      act(() => {
        warning('Warning!');
      });

      const state = useToastStore.getState();
      expect(state.toasts[0].type).toBe('warning');
    });

    it('info() should create info toast', () => {
      const { info } = useToastStore.getState();

      act(() => {
        info('Info', 'FYI message');
      });

      const state = useToastStore.getState();
      expect(state.toasts[0].type).toBe('info');
    });
  });

  describe('auto-dismiss', () => {
    it('should auto-dismiss toast after duration', () => {
      const { success } = useToastStore.getState();

      act(() => {
        success('Auto dismiss');
      });

      expect(useToastStore.getState().toasts).toHaveLength(1);

      // Fast-forward past default success duration (3000ms)
      act(() => {
        vi.advanceTimersByTime(3500);
      });

      expect(useToastStore.getState().toasts).toHaveLength(0);
    });

    it('should not auto-dismiss if duration is 0', () => {
      const { addToast } = useToastStore.getState();

      act(() => {
        addToast({ type: 'info', title: 'Persistent', duration: 0 });
      });

      act(() => {
        vi.advanceTimersByTime(10000);
      });

      expect(useToastStore.getState().toasts).toHaveLength(1);
    });
  });

  describe('toast options', () => {
    it('should support action callback', () => {
      const { addToast } = useToastStore.getState();
      const actionFn = vi.fn();

      act(() => {
        addToast({
          type: 'info',
          title: 'With Action',
          action: { label: 'Undo', onClick: actionFn },
        });
      });

      const state = useToastStore.getState();
      expect(state.toasts[0].action).toBeDefined();
      expect(state.toasts[0].action?.label).toBe('Undo');

      state.toasts[0].action?.onClick();
      expect(actionFn).toHaveBeenCalled();
    });

    it('should support dismissible option', () => {
      const { addToast } = useToastStore.getState();

      act(() => {
        addToast({ type: 'error', title: 'Not dismissible', dismissible: false });
      });

      const state = useToastStore.getState();
      expect(state.toasts[0].dismissible).toBe(false);
    });

    it('should default dismissible to true', () => {
      const { addToast } = useToastStore.getState();

      act(() => {
        addToast({ type: 'info', title: 'Default dismissible' });
      });

      const state = useToastStore.getState();
      expect(state.toasts[0].dismissible).toBe(true);
    });
  });
});
