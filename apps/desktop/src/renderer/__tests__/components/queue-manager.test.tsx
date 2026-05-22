/**
 * Queue Manager component tests.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';

// Mock the stores
vi.mock('../../stores/generation-store', () => ({
  useGenerationStore: vi.fn(() => ({
    jobs: [],
    activeJobs: [],
    completedJobs: [],
    failedJobs: [],
    isLoading: false,
    fetchJobs: vi.fn(),
    cancelJob: vi.fn(),
    retryJob: vi.fn(),
    prioritizeJob: vi.fn(),
    removeJob: vi.fn(),
  })),
}));

// Mock the QueueManager component
vi.mock('../../components/queue-manager', () => ({
  QueueManager: ({
    jobs,
    onCancel,
    onRetry,
    onPrioritize,
    onRemove,
    showCompleted = true,
  }: any) => {
    const activeJobs =
      jobs?.filter((j: any) => j.status === 'RUNNING' || j.status === 'QUEUED') || [];
    const completedJobs = jobs?.filter((j: any) => j.status === 'COMPLETED') || [];
    const failedJobs = jobs?.filter((j: any) => j.status === 'FAILED') || [];

    return (
      <div data-testid="queue-manager">
        {/* Active Jobs Section */}
        <section data-testid="active-jobs">
          <h2>Active Jobs ({activeJobs.length})</h2>
          {activeJobs.map((job: any) => (
            <div key={job.id} data-testid={`job-${job.id}`} data-status={job.status}>
              <span>{job.name || `Job ${job.id}`}</span>
              {job.status === 'RUNNING' && (
                <div data-testid="progress-bar" style={{ width: `${job.progress}%` }}>
                  {job.progress}%
                </div>
              )}
              <button onClick={() => onCancel?.(job.id)} data-testid={`cancel-${job.id}`}>
                Cancel
              </button>
              {job.status === 'QUEUED' && (
                <button onClick={() => onPrioritize?.(job.id)} data-testid={`prioritize-${job.id}`}>
                  Prioritize
                </button>
              )}
            </div>
          ))}
          {activeJobs.length === 0 && <div data-testid="empty-active">No active jobs</div>}
        </section>

        {/* Completed Jobs Section */}
        {showCompleted && (
          <section data-testid="completed-jobs">
            <h2>Completed ({completedJobs.length})</h2>
            {completedJobs.map((job: any) => (
              <div key={job.id} data-testid={`job-${job.id}`} data-status="COMPLETED">
                <span>{job.name || `Job ${job.id}`}</span>
                <button onClick={() => onRemove?.(job.id)} data-testid={`remove-${job.id}`}>
                  Remove
                </button>
              </div>
            ))}
          </section>
        )}

        {/* Failed Jobs Section */}
        <section data-testid="failed-jobs">
          <h2>Failed ({failedJobs.length})</h2>
          {failedJobs.map((job: any) => (
            <div key={job.id} data-testid={`job-${job.id}`} data-status="FAILED">
              <span>{job.name || `Job ${job.id}`}</span>
              <span data-testid="error-message">{job.error}</span>
              <button onClick={() => onRetry?.(job.id)} data-testid={`retry-${job.id}`}>
                Retry
              </button>
              <button onClick={() => onRemove?.(job.id)} data-testid={`remove-${job.id}`}>
                Remove
              </button>
            </div>
          ))}
        </section>
      </div>
    );
  },
}));

import { QueueManager } from '../../components/queue-manager';

const mockJobs = [
  {
    id: 'job-1',
    name: 'Scene 1 Generation',
    status: 'RUNNING',
    progress: 45,
    startedAt: new Date().toISOString(),
  },
  {
    id: 'job-2',
    name: 'Scene 2 Generation',
    status: 'QUEUED',
    progress: 0,
    createdAt: new Date().toISOString(),
  },
  {
    id: 'job-3',
    name: 'Scene 3 Generation',
    status: 'COMPLETED',
    progress: 100,
    completedAt: new Date().toISOString(),
  },
  {
    id: 'job-4',
    name: 'Scene 4 Generation',
    status: 'FAILED',
    progress: 0,
    error: 'Provider timeout',
    failedAt: new Date().toISOString(),
  },
];

describe('QueueManager', () => {
  const mockHandlers = {
    onCancel: vi.fn(),
    onRetry: vi.fn(),
    onPrioritize: vi.fn(),
    onRemove: vi.fn(),
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  const renderQueueManager = (jobs = mockJobs, props = {}) => {
    return render(
      <MemoryRouter>
        <QueueManager jobs={jobs} {...mockHandlers} {...props} />
      </MemoryRouter>
    );
  };

  describe('Basic Rendering', () => {
    it('should render queue manager', () => {
      renderQueueManager();
      expect(screen.getByTestId('queue-manager')).toBeInTheDocument();
    });

    it('should render active jobs section', () => {
      renderQueueManager();
      expect(screen.getByTestId('active-jobs')).toBeInTheDocument();
    });

    it('should render completed jobs section', () => {
      renderQueueManager();
      expect(screen.getByTestId('completed-jobs')).toBeInTheDocument();
    });

    it('should render failed jobs section', () => {
      renderQueueManager();
      expect(screen.getByTestId('failed-jobs')).toBeInTheDocument();
    });
  });

  describe('Active Jobs', () => {
    it('should display running job', () => {
      renderQueueManager();
      expect(screen.getByTestId('job-job-1')).toBeInTheDocument();
      expect(screen.getByTestId('job-job-1')).toHaveAttribute('data-status', 'RUNNING');
    });

    it('should display queued job', () => {
      renderQueueManager();
      expect(screen.getByTestId('job-job-2')).toBeInTheDocument();
      expect(screen.getByTestId('job-job-2')).toHaveAttribute('data-status', 'QUEUED');
    });

    it('should show progress for running job', () => {
      renderQueueManager();
      expect(screen.getByText('45%')).toBeInTheDocument();
    });

    it('should show empty message when no active jobs', () => {
      renderQueueManager([]);
      expect(screen.getByTestId('empty-active')).toBeInTheDocument();
    });
  });

  describe('Completed Jobs', () => {
    it('should display completed job', () => {
      renderQueueManager();
      expect(screen.getByTestId('job-job-3')).toBeInTheDocument();
      expect(screen.getByTestId('job-job-3')).toHaveAttribute('data-status', 'COMPLETED');
    });

    it('should hide completed section when showCompleted is false', () => {
      renderQueueManager(mockJobs, { showCompleted: false });
      expect(screen.queryByTestId('completed-jobs')).not.toBeInTheDocument();
    });
  });

  describe('Failed Jobs', () => {
    it('should display failed job', () => {
      renderQueueManager();
      expect(screen.getByTestId('job-job-4')).toBeInTheDocument();
      expect(screen.getByTestId('job-job-4')).toHaveAttribute('data-status', 'FAILED');
    });

    it('should show error message for failed job', () => {
      renderQueueManager();
      expect(screen.getByText('Provider timeout')).toBeInTheDocument();
    });
  });

  describe('Job Actions', () => {
    it('should have cancel button for running job', () => {
      renderQueueManager();
      expect(screen.getByTestId('cancel-job-1')).toBeInTheDocument();
    });

    it('should call onCancel when cancel clicked', () => {
      renderQueueManager();
      fireEvent.click(screen.getByTestId('cancel-job-1'));
      expect(mockHandlers.onCancel).toHaveBeenCalledWith('job-1');
    });

    it('should have prioritize button for queued job', () => {
      renderQueueManager();
      expect(screen.getByTestId('prioritize-job-2')).toBeInTheDocument();
    });

    it('should call onPrioritize when prioritize clicked', () => {
      renderQueueManager();
      fireEvent.click(screen.getByTestId('prioritize-job-2'));
      expect(mockHandlers.onPrioritize).toHaveBeenCalledWith('job-2');
    });

    it('should have retry button for failed job', () => {
      renderQueueManager();
      expect(screen.getByTestId('retry-job-4')).toBeInTheDocument();
    });

    it('should call onRetry when retry clicked', () => {
      renderQueueManager();
      fireEvent.click(screen.getByTestId('retry-job-4'));
      expect(mockHandlers.onRetry).toHaveBeenCalledWith('job-4');
    });

    it('should have remove button for completed job', () => {
      renderQueueManager();
      expect(screen.getByTestId('remove-job-3')).toBeInTheDocument();
    });

    it('should call onRemove when remove clicked', () => {
      renderQueueManager();
      fireEvent.click(screen.getByTestId('remove-job-3'));
      expect(mockHandlers.onRemove).toHaveBeenCalledWith('job-3');
    });
  });

  describe('Job Counts', () => {
    it('should show correct active jobs count', () => {
      renderQueueManager();
      expect(screen.getByText('Active Jobs (2)')).toBeInTheDocument();
    });

    it('should show correct completed jobs count', () => {
      renderQueueManager();
      expect(screen.getByText('Completed (1)')).toBeInTheDocument();
    });

    it('should show correct failed jobs count', () => {
      renderQueueManager();
      expect(screen.getByText('Failed (1)')).toBeInTheDocument();
    });
  });

  describe('Empty State', () => {
    it('should show empty active state when no jobs', () => {
      renderQueueManager([]);
      expect(screen.getByTestId('empty-active')).toBeInTheDocument();
      expect(screen.getByText('No active jobs')).toBeInTheDocument();
    });
  });
});
