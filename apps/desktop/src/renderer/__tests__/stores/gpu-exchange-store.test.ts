/**
 * GPU Exchange store unit tests.
 */

import { describe, it, expect, beforeEach, vi } from 'vitest';
import { act } from '@testing-library/react';
import { useGPUExchangeStore } from '../../stores/gpu-exchange-store';

// Mock the API client
vi.mock('../../api/client', () => ({
  api: {
    getGPUProviders: vi.fn(),
    getGPUPricing: vi.fn(),
    submitGPUJob: vi.fn(),
    getGPUJobStatus: vi.fn(),
    cancelGPUJob: vi.fn(),
    getGPUUsage: vi.fn(),
    setGPUBudget: vi.fn(),
  },
}));

const mockProvider = {
  id: 'provider-1',
  name: 'Test GPU Provider',
  type: 'cloud' as const,
  status: 'online' as const,
  gpuModels: ['A100', 'V100'],
  pricePerHour: 2.5,
  latency: 50,
};

const mockJob = {
  id: 'job-1',
  providerId: 'provider-1',
  status: 'running' as const,
  progress: 50,
  cost: 1.25,
  startedAt: new Date().toISOString(),
};

describe('GPUExchangeStore', () => {
  beforeEach(() => {
    // Reset store state before each test
    useGPUExchangeStore.setState({
      providers: [],
      selectedProvider: null,
      activeJobs: [],
      completedJobs: [],
      usage: null,
      budget: null,
      isLoadingProviders: false,
      isSubmittingJob: false,
      error: null,
    });
    vi.clearAllMocks();
  });

  describe('setProviders', () => {
    it('should set providers', () => {
      const { setProviders } = useGPUExchangeStore.getState();

      act(() => {
        setProviders([mockProvider]);
      });

      expect(useGPUExchangeStore.getState().providers).toHaveLength(1);
    });
  });

  describe('setSelectedProvider', () => {
    it('should set the selected provider', () => {
      const { setSelectedProvider } = useGPUExchangeStore.getState();

      act(() => {
        setSelectedProvider(mockProvider);
      });

      expect(useGPUExchangeStore.getState().selectedProvider).toEqual(mockProvider);
    });

    it('should allow clearing the selection', () => {
      useGPUExchangeStore.setState({ selectedProvider: mockProvider });

      const { setSelectedProvider } = useGPUExchangeStore.getState();

      act(() => {
        setSelectedProvider(null);
      });

      expect(useGPUExchangeStore.getState().selectedProvider).toBeNull();
    });
  });

  describe('addActiveJob', () => {
    it('should add a job to active jobs', () => {
      const { addActiveJob } = useGPUExchangeStore.getState();

      act(() => {
        addActiveJob(mockJob);
      });

      expect(useGPUExchangeStore.getState().activeJobs).toHaveLength(1);
    });
  });

  describe('updateJob', () => {
    it('should update an existing job', () => {
      useGPUExchangeStore.setState({ activeJobs: [mockJob] });

      const { updateJob } = useGPUExchangeStore.getState();

      act(() => {
        updateJob('job-1', { progress: 75 });
      });

      expect(useGPUExchangeStore.getState().activeJobs[0].progress).toBe(75);
    });

    it('should not fail for non-existent job', () => {
      const { updateJob } = useGPUExchangeStore.getState();

      expect(() => {
        act(() => {
          updateJob('nonexistent', { progress: 50 });
        });
      }).not.toThrow();
    });
  });

  describe('moveJobToCompleted', () => {
    it('should move job from active to completed', () => {
      useGPUExchangeStore.setState({ activeJobs: [mockJob] });

      const { moveJobToCompleted } = useGPUExchangeStore.getState();

      act(() => {
        moveJobToCompleted('job-1');
      });

      const state = useGPUExchangeStore.getState();
      expect(state.activeJobs).toHaveLength(0);
      expect(state.completedJobs).toHaveLength(1);
    });
  });

  describe('removeJob', () => {
    it('should remove job from active jobs', () => {
      useGPUExchangeStore.setState({
        activeJobs: [mockJob, { ...mockJob, id: 'job-2' }],
      });

      const { removeJob } = useGPUExchangeStore.getState();

      act(() => {
        removeJob('job-1');
      });

      expect(useGPUExchangeStore.getState().activeJobs).toHaveLength(1);
    });
  });

  describe('setUsage', () => {
    it('should set usage data', () => {
      const usage = { totalCost: 100, totalHours: 40, jobCount: 25 };
      const { setUsage } = useGPUExchangeStore.getState();

      act(() => {
        setUsage(usage);
      });

      expect(useGPUExchangeStore.getState().usage).toEqual(usage);
    });
  });

  describe('setBudget', () => {
    it('should set budget', () => {
      const budget = { limit: 500, spent: 100, remaining: 400 };
      const { setBudget } = useGPUExchangeStore.getState();

      act(() => {
        setBudget(budget);
      });

      expect(useGPUExchangeStore.getState().budget).toEqual(budget);
    });
  });

  describe('setError', () => {
    it('should set error message', () => {
      const { setError } = useGPUExchangeStore.getState();

      act(() => {
        setError('GPU unavailable');
      });

      expect(useGPUExchangeStore.getState().error).toBe('GPU unavailable');
    });
  });

  describe('clearError', () => {
    it('should clear the error', () => {
      useGPUExchangeStore.setState({ error: 'Previous error' });

      const { clearError } = useGPUExchangeStore.getState();

      act(() => {
        clearError();
      });

      expect(useGPUExchangeStore.getState().error).toBeNull();
    });
  });

  describe('getOnlineProviders', () => {
    it('should return only online providers', () => {
      const offlineProvider = { ...mockProvider, id: 'offline', status: 'offline' as const };
      useGPUExchangeStore.setState({
        providers: [mockProvider, offlineProvider],
      });

      const { getOnlineProviders } = useGPUExchangeStore.getState();
      const online = getOnlineProviders();

      expect(online).toHaveLength(1);
      expect(online[0].status).toBe('online');
    });
  });

  describe('getProvidersByType', () => {
    it('should filter providers by type', () => {
      const localProvider = { ...mockProvider, id: 'local', type: 'local' as const };
      useGPUExchangeStore.setState({
        providers: [mockProvider, localProvider],
      });

      const { getProvidersByType } = useGPUExchangeStore.getState();
      const cloudProviders = getProvidersByType('cloud');

      expect(cloudProviders).toHaveLength(1);
      expect(cloudProviders[0].type).toBe('cloud');
    });
  });

  describe('getCheapestProvider', () => {
    it('should return the cheapest online provider', () => {
      const cheapProvider = { ...mockProvider, id: 'cheap', pricePerHour: 1.0 };
      useGPUExchangeStore.setState({
        providers: [mockProvider, cheapProvider],
      });

      const { getCheapestProvider } = useGPUExchangeStore.getState();
      const cheapest = getCheapestProvider();

      expect(cheapest?.id).toBe('cheap');
    });

    it('should return null if no providers', () => {
      const { getCheapestProvider } = useGPUExchangeStore.getState();
      expect(getCheapestProvider()).toBeNull();
    });
  });

  describe('getBudgetRemaining', () => {
    it('should return remaining budget', () => {
      useGPUExchangeStore.setState({
        budget: { limit: 500, spent: 100, remaining: 400 },
      });

      const { getBudgetRemaining } = useGPUExchangeStore.getState();
      expect(getBudgetRemaining()).toBe(400);
    });

    it('should return null if no budget set', () => {
      const { getBudgetRemaining } = useGPUExchangeStore.getState();
      expect(getBudgetRemaining()).toBeNull();
    });
  });

  describe('getActiveJobCount', () => {
    it('should return count of active jobs', () => {
      useGPUExchangeStore.setState({
        activeJobs: [mockJob, { ...mockJob, id: 'job-2' }],
      });

      const { getActiveJobCount } = useGPUExchangeStore.getState();
      expect(getActiveJobCount()).toBe(2);
    });
  });

  describe('reset', () => {
    it('should reset store to initial state', () => {
      useGPUExchangeStore.setState({
        providers: [mockProvider],
        selectedProvider: mockProvider,
        activeJobs: [mockJob],
        error: 'Some error',
      });

      const { reset } = useGPUExchangeStore.getState();

      act(() => {
        reset();
      });

      const state = useGPUExchangeStore.getState();
      expect(state.providers).toHaveLength(0);
      expect(state.selectedProvider).toBeNull();
      expect(state.activeJobs).toHaveLength(0);
      expect(state.error).toBeNull();
    });
  });
});
