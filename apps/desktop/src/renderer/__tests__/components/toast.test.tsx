/**
 * Toast component tests.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, act } from '@testing-library/react';
import { ToastContainer, ProgressToast, useToast } from '../../components/toast';
import { useToastStore } from '../../stores/toast-store';

// Mock the toast store
vi.mock('../../stores/toast-store', () => ({
  useToastStore: vi.fn(),
}));

const mockToastStore = {
  toasts: [],
  addToast: vi.fn(),
  removeToast: vi.fn(),
  clearAllToasts: vi.fn(),
  success: vi.fn(),
  error: vi.fn(),
  warning: vi.fn(),
  info: vi.fn(),
};

describe('ToastContainer', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    (useToastStore as any).mockReturnValue(mockToastStore);
  });

  it('should return null when no toasts', () => {
    (useToastStore as any).mockReturnValue({ ...mockToastStore, toasts: [] });
    const { container } = render(<ToastContainer />);
    expect(container.firstChild).toBeNull();
  });

  it('should render toasts when available', () => {
    const toasts = [
      {
        id: 'toast-1',
        type: 'success' as const,
        title: 'Success!',
        message: 'Operation completed',
        dismissible: true,
      },
    ];
    (useToastStore as any).mockReturnValue({ ...mockToastStore, toasts });

    render(<ToastContainer />);
    expect(screen.getByText('Success!')).toBeInTheDocument();
    expect(screen.getByText('Operation completed')).toBeInTheDocument();
  });

  it('should render multiple toasts', () => {
    const toasts = [
      { id: 'toast-1', type: 'success' as const, title: 'First', dismissible: true },
      { id: 'toast-2', type: 'error' as const, title: 'Second', dismissible: true },
      { id: 'toast-3', type: 'warning' as const, title: 'Third', dismissible: true },
    ];
    (useToastStore as any).mockReturnValue({ ...mockToastStore, toasts });

    render(<ToastContainer />);
    expect(screen.getByText('First')).toBeInTheDocument();
    expect(screen.getByText('Second')).toBeInTheDocument();
    expect(screen.getByText('Third')).toBeInTheDocument();
  });

  it('should have aria-live for accessibility', () => {
    const toasts = [{ id: 'toast-1', type: 'info' as const, title: 'Info', dismissible: true }];
    (useToastStore as any).mockReturnValue({ ...mockToastStore, toasts });

    render(<ToastContainer />);
    const container =
      screen.getByRole('generic', { hidden: true }) || document.querySelector('[aria-live]');
    // Container should have aria-live attribute
    expect(document.querySelector('[aria-live="polite"]')).toBeInTheDocument();
  });

  describe('Toast Types', () => {
    it('should render success toast with correct styling', () => {
      const toasts = [
        { id: 'toast-1', type: 'success' as const, title: 'Success', dismissible: true },
      ];
      (useToastStore as any).mockReturnValue({ ...mockToastStore, toasts });

      render(<ToastContainer />);
      const alert = screen.getByRole('alert');
      expect(alert).toHaveClass('bg-green-500/10');
    });

    it('should render error toast with correct styling', () => {
      const toasts = [{ id: 'toast-1', type: 'error' as const, title: 'Error', dismissible: true }];
      (useToastStore as any).mockReturnValue({ ...mockToastStore, toasts });

      render(<ToastContainer />);
      const alert = screen.getByRole('alert');
      expect(alert).toHaveClass('bg-red-500/10');
    });

    it('should render warning toast with correct styling', () => {
      const toasts = [
        { id: 'toast-1', type: 'warning' as const, title: 'Warning', dismissible: true },
      ];
      (useToastStore as any).mockReturnValue({ ...mockToastStore, toasts });

      render(<ToastContainer />);
      const alert = screen.getByRole('alert');
      expect(alert).toHaveClass('bg-yellow-500/10');
    });

    it('should render info toast with correct styling', () => {
      const toasts = [{ id: 'toast-1', type: 'info' as const, title: 'Info', dismissible: true }];
      (useToastStore as any).mockReturnValue({ ...mockToastStore, toasts });

      render(<ToastContainer />);
      const alert = screen.getByRole('alert');
      expect(alert).toHaveClass('bg-blue-500/10');
    });
  });

  describe('Toast Dismissal', () => {
    it('should show dismiss button when dismissible', () => {
      const toasts = [
        { id: 'toast-1', type: 'info' as const, title: 'Dismissible', dismissible: true },
      ];
      (useToastStore as any).mockReturnValue({ ...mockToastStore, toasts });

      render(<ToastContainer />);
      expect(screen.getByLabelText('Dismiss notification')).toBeInTheDocument();
    });

    it('should not show dismiss button when not dismissible', () => {
      const toasts = [
        { id: 'toast-1', type: 'info' as const, title: 'Not Dismissible', dismissible: false },
      ];
      (useToastStore as any).mockReturnValue({ ...mockToastStore, toasts });

      render(<ToastContainer />);
      expect(screen.queryByLabelText('Dismiss notification')).not.toBeInTheDocument();
    });

    it('should call removeToast when dismiss clicked', async () => {
      const toasts = [
        { id: 'toast-1', type: 'info' as const, title: 'Dismissible', dismissible: true },
      ];
      (useToastStore as any).mockReturnValue({ ...mockToastStore, toasts });

      render(<ToastContainer />);
      fireEvent.click(screen.getByLabelText('Dismiss notification'));

      // Wait for animation
      await act(async () => {
        await new Promise((resolve) => setTimeout(resolve, 250));
      });

      expect(mockToastStore.removeToast).toHaveBeenCalledWith('toast-1');
    });
  });

  describe('Toast Action', () => {
    it('should render action button when provided', () => {
      const actionHandler = vi.fn();
      const toasts = [
        {
          id: 'toast-1',
          type: 'info' as const,
          title: 'With Action',
          dismissible: true,
          action: { label: 'Undo', onClick: actionHandler },
        },
      ];
      (useToastStore as any).mockReturnValue({ ...mockToastStore, toasts });

      render(<ToastContainer />);
      expect(screen.getByText('Undo')).toBeInTheDocument();
    });

    it('should call action handler when clicked', () => {
      const actionHandler = vi.fn();
      const toasts = [
        {
          id: 'toast-1',
          type: 'info' as const,
          title: 'With Action',
          dismissible: true,
          action: { label: 'Undo', onClick: actionHandler },
        },
      ];
      (useToastStore as any).mockReturnValue({ ...mockToastStore, toasts });

      render(<ToastContainer />);
      fireEvent.click(screen.getByText('Undo'));

      expect(actionHandler).toHaveBeenCalled();
    });
  });

  describe('Toast Message', () => {
    it('should render message when provided', () => {
      const toasts = [
        {
          id: 'toast-1',
          type: 'info' as const,
          title: 'Title',
          message: 'Detailed message here',
          dismissible: true,
        },
      ];
      (useToastStore as any).mockReturnValue({ ...mockToastStore, toasts });

      render(<ToastContainer />);
      expect(screen.getByText('Detailed message here')).toBeInTheDocument();
    });

    it('should not render message section when not provided', () => {
      const toasts = [
        { id: 'toast-1', type: 'info' as const, title: 'Title Only', dismissible: true },
      ];
      (useToastStore as any).mockReturnValue({ ...mockToastStore, toasts });

      render(<ToastContainer />);
      expect(screen.queryByText('Detailed message here')).not.toBeInTheDocument();
    });
  });
});

describe('ProgressToast', () => {
  it('should render title', () => {
    render(<ProgressToast title="Uploading" progress={50} />);
    expect(screen.getByText('Uploading')).toBeInTheDocument();
  });

  it('should render progress percentage', () => {
    render(<ProgressToast title="Processing" progress={75} />);
    expect(screen.getByText('75%')).toBeInTheDocument();
  });

  it('should render progress bar', () => {
    const { container } = render(<ProgressToast title="Loading" progress={50} />);
    const progressBar = container.querySelector('.bg-brand-500');
    expect(progressBar).toBeInTheDocument();
    expect(progressBar).toHaveStyle({ width: '50%' });
  });

  it('should render message when provided', () => {
    render(<ProgressToast title="Exporting" progress={30} message="Processing frame 150/500" />);
    expect(screen.getByText('Processing frame 150/500')).toBeInTheDocument();
  });

  it('should not render message when not provided', () => {
    render(<ProgressToast title="Working" progress={50} />);
    expect(screen.queryByText('Processing')).not.toBeInTheDocument();
  });

  it('should render cancel button when onCancel provided', () => {
    render(<ProgressToast title="Uploading" progress={50} onCancel={() => {}} />);
    expect(screen.getByText('Cancel')).toBeInTheDocument();
  });

  it('should not render cancel button when onCancel not provided', () => {
    render(<ProgressToast title="Uploading" progress={50} />);
    expect(screen.queryByText('Cancel')).not.toBeInTheDocument();
  });

  it('should call onCancel when cancel clicked', () => {
    const onCancel = vi.fn();
    render(<ProgressToast title="Uploading" progress={50} onCancel={onCancel} />);

    fireEvent.click(screen.getByText('Cancel'));
    expect(onCancel).toHaveBeenCalled();
  });

  it('should round progress percentage', () => {
    render(<ProgressToast title="Loading" progress={33.7} />);
    expect(screen.getByText('34%')).toBeInTheDocument();
  });
});

describe('useToast hook', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    (useToastStore as any).mockReturnValue(mockToastStore);
  });

  it('should return toast functions', () => {
    let hookResult: any;

    function TestComponent() {
      hookResult = useToast();
      return null;
    }

    render(<TestComponent />);

    expect(hookResult).toHaveProperty('toast');
    expect(hookResult).toHaveProperty('dismiss');
    expect(hookResult).toHaveProperty('clear');
    expect(hookResult).toHaveProperty('toasts');
    expect(hookResult).toHaveProperty('showToast');
  });

  it('should call store.success for success type', () => {
    let hookResult: any;

    function TestComponent() {
      hookResult = useToast();
      return null;
    }

    render(<TestComponent />);
    hookResult.showToast('Success message', 'success');

    expect(mockToastStore.success).toHaveBeenCalledWith('Success message');
  });

  it('should call store.error for error type', () => {
    let hookResult: any;

    function TestComponent() {
      hookResult = useToast();
      return null;
    }

    render(<TestComponent />);
    hookResult.showToast('Error message', 'error');

    expect(mockToastStore.error).toHaveBeenCalledWith('Error message');
  });

  it('should call store.warning for warning type', () => {
    let hookResult: any;

    function TestComponent() {
      hookResult = useToast();
      return null;
    }

    render(<TestComponent />);
    hookResult.showToast('Warning message', 'warning');

    expect(mockToastStore.warning).toHaveBeenCalledWith('Warning message');
  });

  it('should default to info type', () => {
    let hookResult: any;

    function TestComponent() {
      hookResult = useToast();
      return null;
    }

    render(<TestComponent />);
    hookResult.showToast('Info message');

    expect(mockToastStore.info).toHaveBeenCalledWith('Info message');
  });
});
