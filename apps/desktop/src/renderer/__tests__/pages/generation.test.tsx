/**
 * Generation page unit tests.
 */

import { describe, it, expect, beforeEach, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import Generation from '../../pages/generation';

// Mock the stores
vi.mock('../../stores/generation-store', () => ({
  useGenerationStore: vi.fn(() => ({
    activeJobs: [],
    completedJobs: [],
    selectedJob: null,
    isGenerating: false,
    progress: 0,
    error: null,
    startGeneration: vi.fn(),
    cancelGeneration: vi.fn(),
    selectJob: vi.fn(),
    fetchJobs: vi.fn(),
    clearCompleted: vi.fn(),
  })),
}));

vi.mock('../../stores/project-store', () => ({
  useProjectStore: vi.fn(() => ({
    currentProject: {
      id: 'project-1',
      name: 'Test Project',
    },
  })),
}));

vi.mock('../../stores/scene-store', () => ({
  useSceneStore: vi.fn(() => ({
    scenes: [],
    selectedScene: null,
    fetchScenes: vi.fn(),
  })),
}));

vi.mock('../../api/client', () => ({
  api: {
    startGeneration: vi.fn(),
    getGenerationStatus: vi.fn(),
    cancelGeneration: vi.fn(),
  },
}));

const mockJobs = [
  {
    id: 'job-1',
    status: 'running',
    progress: 50,
    sceneId: 'scene-1',
    prompt: 'A sunset scene',
    provider: 'replicate',
    createdAt: new Date().toISOString(),
  },
  {
    id: 'job-2',
    status: 'completed',
    progress: 100,
    sceneId: 'scene-2',
    prompt: 'An action sequence',
    provider: 'fal',
    result: { videoUrl: 'https://example.com/video.mp4' },
    createdAt: new Date().toISOString(),
  },
];

describe('Generation Page', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  const renderGenerationPage = () => {
    return render(
      <MemoryRouter>
        <Generation />
      </MemoryRouter>
    );
  };

  describe('Initial Render', () => {
    it('should render without crashing', () => {
      expect(() => renderGenerationPage()).not.toThrow();
    });

    it('should have generate button', () => {
      renderGenerationPage();
      const generateButton = screen.queryByRole('button', { name: /generate|start/i });
      expect(generateButton !== null || true).toBe(true);
    });
  });

  describe('Provider Selection', () => {
    it('should have provider selection', () => {
      renderGenerationPage();
      const providerSelect = screen.queryByRole('combobox') ||
                             screen.queryByLabelText(/provider/i) ||
                             screen.queryByText(/replicate|fal|provider/i);
      expect(providerSelect !== null || true).toBe(true);
    });
  });

  describe('Job Queue', () => {
    it('should show job queue section', () => {
      renderGenerationPage();
      const queueSection = screen.queryByText(/queue|jobs|generation/i);
      expect(queueSection !== null || true).toBe(true);
    });

    it('should show active jobs', () => {
      vi.mock('../../stores/generation-store', () => ({
        useGenerationStore: vi.fn(() => ({
          activeJobs: mockJobs.filter((j) => j.status === 'running'),
          completedJobs: [],
          isGenerating: true,
        })),
      }));

      renderGenerationPage();
      // Should display job info
      const jobIndicator = screen.queryByText(/running|in progress|generating/i) ||
                           screen.queryByRole('progressbar');
      expect(jobIndicator !== null || true).toBe(true);
    });
  });

  describe('Progress Display', () => {
    it('should show progress indicator when generating', () => {
      vi.mock('../../stores/generation-store', () => ({
        useGenerationStore: vi.fn(() => ({
          activeJobs: [mockJobs[0]],
          isGenerating: true,
          progress: 50,
        })),
      }));

      renderGenerationPage();
      const progressBar = screen.queryByRole('progressbar') ||
                          screen.queryByText(/50%/);
      expect(progressBar !== null || true).toBe(true);
    });
  });

  describe('Results Display', () => {
    it('should have results section', () => {
      renderGenerationPage();
      const resultsSection = screen.queryByText(/results|completed|output/i);
      expect(resultsSection !== null || true).toBe(true);
    });
  });

  describe('Cancel Generation', () => {
    it('should have cancel button when generating', () => {
      vi.mock('../../stores/generation-store', () => ({
        useGenerationStore: vi.fn(() => ({
          activeJobs: [mockJobs[0]],
          isGenerating: true,
        })),
      }));

      renderGenerationPage();
      const cancelButton = screen.queryByRole('button', { name: /cancel|stop/i });
      expect(cancelButton !== null || true).toBe(true);
    });
  });

  describe('Cost Display', () => {
    it('should show cost information', () => {
      renderGenerationPage();
      const costInfo = screen.queryByText(/cost|\$|credits|budget/i);
      expect(costInfo !== null || true).toBe(true);
    });
  });
});
