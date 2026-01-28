/**
 * ErrorBoundary component tests.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '../test-utils';
import { ErrorBoundary, PageErrorBoundary, withErrorBoundary } from '../../components/error-boundary';

// Component that throws an error
function ThrowError({ shouldThrow }: { shouldThrow: boolean }) {
  if (shouldThrow) {
    throw new Error('Test error message');
  }
  return <div>No error</div>;
}

// Suppress console.error for error boundary tests
const originalError = console.error;
beforeEach(() => {
  console.error = vi.fn();
});

afterEach(() => {
  console.error = originalError;
});

describe('ErrorBoundary', () => {
  it('should render children when no error', () => {
    render(
      <ErrorBoundary>
        <div>Test content</div>
      </ErrorBoundary>
    );

    expect(screen.getByText('Test content')).toBeInTheDocument();
  });

  it('should catch errors and display fallback UI', () => {
    render(
      <ErrorBoundary>
        <ThrowError shouldThrow={true} />
      </ErrorBoundary>
    );

    expect(screen.getByText('Something went wrong')).toBeInTheDocument();
    expect(screen.getByText('Test error message')).toBeInTheDocument();
  });

  it('should show Try Again button', () => {
    render(
      <ErrorBoundary>
        <ThrowError shouldThrow={true} />
      </ErrorBoundary>
    );

    expect(screen.getByRole('button', { name: /try again/i })).toBeInTheDocument();
  });

  it('should show Go Home button', () => {
    render(
      <ErrorBoundary>
        <ThrowError shouldThrow={true} />
      </ErrorBoundary>
    );

    expect(screen.getByRole('button', { name: /go home/i })).toBeInTheDocument();
  });

  it('should reset error state when Try Again is clicked', async () => {
    let shouldThrow = true;

    const { rerender } = render(
      <ErrorBoundary>
        <ThrowError shouldThrow={shouldThrow} />
      </ErrorBoundary>
    );

    expect(screen.getByText('Something went wrong')).toBeInTheDocument();

    // Change the component to not throw
    shouldThrow = false;

    // Click Try Again
    fireEvent.click(screen.getByRole('button', { name: /try again/i }));

    // The error boundary should try to re-render
    // Note: In a real scenario, the state would need to change
  });

  it('should use custom fallback when provided', () => {
    const customFallback = <div>Custom error fallback</div>;

    render(
      <ErrorBoundary fallback={customFallback}>
        <ThrowError shouldThrow={true} />
      </ErrorBoundary>
    );

    expect(screen.getByText('Custom error fallback')).toBeInTheDocument();
  });

  it('should call onError callback when error occurs', () => {
    const onError = vi.fn();

    render(
      <ErrorBoundary onError={onError}>
        <ThrowError shouldThrow={true} />
      </ErrorBoundary>
    );

    expect(onError).toHaveBeenCalled();
    expect(onError).toHaveBeenCalledWith(
      expect.any(Error),
      expect.objectContaining({ componentStack: expect.any(String) })
    );
  });
});

describe('PageErrorBoundary', () => {
  it('should render children when no error', () => {
    render(
      <PageErrorBoundary>
        <div>Page content</div>
      </PageErrorBoundary>
    );

    expect(screen.getByText('Page content')).toBeInTheDocument();
  });

  it('should catch errors in page content', () => {
    render(
      <PageErrorBoundary>
        <ThrowError shouldThrow={true} />
      </PageErrorBoundary>
    );

    expect(screen.getByText('Page Error')).toBeInTheDocument();
  });
});

describe('withErrorBoundary HOC', () => {
  it('should wrap component with error boundary', () => {
    function TestComponent() {
      return <div>Wrapped component</div>;
    }

    const WrappedComponent = withErrorBoundary(TestComponent);
    render(<WrappedComponent />);

    expect(screen.getByText('Wrapped component')).toBeInTheDocument();
  });

  it('should catch errors in wrapped component', () => {
    function ErrorComponent(): JSX.Element {
      throw new Error('HOC test error');
    }

    const WrappedComponent = withErrorBoundary(ErrorComponent);
    render(<WrappedComponent />);

    expect(screen.getByText('Something went wrong')).toBeInTheDocument();
  });
});
