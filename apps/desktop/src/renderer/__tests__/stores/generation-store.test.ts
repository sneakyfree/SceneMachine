/**
 * Tests for the generation store.
 */

import { describe, it, expect, beforeEach, vi } from 'vitest';
import { useGenerationStore } from '../../stores/generation-store';

describe('GenerationStore', () => {
  beforeEach(() => {
    // Reset store state before each test
    useGenerationStore.setState({
      selectedProvider: 'replicate',
      selectedModel: null,
      availableModels: {},
      providersHealth: [],
      workerStatus: null,
      lastCostEstimate: null,
      isLoadingModels: false,
      isLoadingHealth: false,
    });
  });

  describe('Initial State', () => {
    it('should have correct initial values', () => {
      const state = useGenerationStore.getState();

      expect(state.selectedProvider).toBe('replicate');
      expect(state.selectedModel).toBeNull();
      expect(state.availableModels).toEqual({});
      expect(state.providersHealth).toEqual([]);
      expect(state.workerStatus).toBeNull();
      expect(state.lastCostEstimate).toBeNull();
      expect(state.isLoadingModels).toBe(false);
      expect(state.isLoadingHealth).toBe(false);
    });
  });

  describe('Provider Selection', () => {
    it('should update selected provider', () => {
      const { setSelectedProvider } = useGenerationStore.getState();

      setSelectedProvider('fal');

      expect(useGenerationStore.getState().selectedProvider).toBe('fal');
    });

    it('should set model from available models when provider changes', () => {
      const { setAvailableModels, setSelectedProvider } = useGenerationStore.getState();

      // Set up models for fal
      setAvailableModels('fal', [
        { id: 'cogvideo', name: 'CogVideoX', description: 'Fast video gen' } as any,
        { id: 'hunyuan', name: 'Hunyuan', description: 'High quality' } as any,
      ]);

      // Change provider to fal
      setSelectedProvider('fal');

      const state = useGenerationStore.getState();
      expect(state.selectedProvider).toBe('fal');
      expect(state.selectedModel).toBe('cogvideo'); // First model auto-selected
    });

    it('should reset model to null when no models available', () => {
      const { setSelectedProvider, setSelectedModel } = useGenerationStore.getState();

      setSelectedModel('some-model');
      setSelectedProvider('comfyui'); // No models set for this provider

      expect(useGenerationStore.getState().selectedModel).toBeNull();
    });
  });

  describe('Model Selection', () => {
    it('should update selected model', () => {
      const { setSelectedModel } = useGenerationStore.getState();

      setSelectedModel('minimax');

      expect(useGenerationStore.getState().selectedModel).toBe('minimax');
    });

    it('should clear model selection', () => {
      const { setSelectedModel } = useGenerationStore.getState();

      setSelectedModel('minimax');
      setSelectedModel(null);

      expect(useGenerationStore.getState().selectedModel).toBeNull();
    });

    it('should use setModel alias', () => {
      const { setModel } = useGenerationStore.getState();

      setModel('luma');

      expect(useGenerationStore.getState().selectedModel).toBe('luma');
    });

    it('should use setProvider alias', () => {
      const { setProvider } = useGenerationStore.getState();

      setProvider('fal');

      expect(useGenerationStore.getState().selectedProvider).toBe('fal');
    });
  });

  describe('Available Models', () => {
    it('should set available models for provider', () => {
      const { setAvailableModels } = useGenerationStore.getState();

      const models = [
        { id: 'minimax', name: 'MiniMax', description: 'Fast generation' },
        { id: 'luma', name: 'Luma AI', description: 'High quality' },
      ] as any;

      setAvailableModels('replicate', models);

      const state = useGenerationStore.getState();
      expect(state.availableModels['replicate']).toEqual(models);
    });

    it('should auto-select first model for current provider', () => {
      const { setAvailableModels } = useGenerationStore.getState();

      const models = [
        { id: 'minimax', name: 'MiniMax', description: 'Fast generation' },
        { id: 'luma', name: 'Luma AI', description: 'High quality' },
      ] as any;

      // Current provider is replicate
      setAvailableModels('replicate', models);

      const state = useGenerationStore.getState();
      expect(state.selectedModel).toBe('minimax');
    });

    it('should not auto-select if model already selected', () => {
      const { setAvailableModels, setSelectedModel } = useGenerationStore.getState();

      // Pre-select a model
      setSelectedModel('luma');

      const models = [
        { id: 'minimax', name: 'MiniMax', description: 'Fast generation' },
        { id: 'luma', name: 'Luma AI', description: 'High quality' },
      ] as any;

      setAvailableModels('replicate', models);

      // Should keep existing selection
      expect(useGenerationStore.getState().selectedModel).toBe('luma');
    });

    it('should not auto-select for different provider', () => {
      const { setAvailableModels } = useGenerationStore.getState();

      const models = [{ id: 'cogvideo', name: 'CogVideoX', description: 'Fast generation' }] as any;

      // Current provider is replicate, setting models for fal
      setAvailableModels('fal', models);

      // Should not change selection for different provider
      expect(useGenerationStore.getState().selectedModel).toBeNull();
    });
  });

  describe('Providers Health', () => {
    it('should set providers health', () => {
      const { setProvidersHealth } = useGenerationStore.getState();

      const health = [
        { provider: 'replicate', available: true, configured: true, latencyMs: 100 },
        { provider: 'fal', available: true, configured: false, latencyMs: 150 },
      ] as any;

      setProvidersHealth(health);

      const state = useGenerationStore.getState();
      expect(state.providersHealth).toHaveLength(2);
      expect(state.providersHealth[0].provider).toBe('replicate');
    });
  });

  describe('Worker Status', () => {
    it('should set worker status', () => {
      const { setWorkerStatus } = useGenerationStore.getState();

      const status = {
        is_running: true,
        is_paused: false,
        pending_jobs: 5,
        active_jobs: 2,
      } as any;

      setWorkerStatus(status);

      const state = useGenerationStore.getState();
      expect(state.workerStatus?.is_running).toBe(true);
      expect(state.workerStatus?.pending_jobs).toBe(5);
    });

    it('should clear worker status', () => {
      const { setWorkerStatus } = useGenerationStore.getState();

      setWorkerStatus({ is_running: true, is_paused: false } as any);
      setWorkerStatus(null);

      expect(useGenerationStore.getState().workerStatus).toBeNull();
    });
  });

  describe('Cost Estimation', () => {
    it('should set last cost estimate', () => {
      const { setLastCostEstimate } = useGenerationStore.getState();

      const estimate = {
        provider: 'replicate',
        model: 'minimax',
        durationSeconds: 10,
        costPerShot: 0.15,
        totalCost: 1.5,
      };

      setLastCostEstimate(estimate);

      expect(useGenerationStore.getState().lastCostEstimate).toEqual(estimate);
    });

    it('should clear cost estimate', () => {
      const { setLastCostEstimate } = useGenerationStore.getState();

      setLastCostEstimate({
        provider: 'replicate',
        model: 'minimax',
        durationSeconds: 10,
        costPerShot: 0.15,
        totalCost: 1.5,
      });

      setLastCostEstimate(null);

      expect(useGenerationStore.getState().lastCostEstimate).toBeNull();
    });
  });

  describe('Loading States', () => {
    it('should set loading models state', () => {
      const { setLoadingModels } = useGenerationStore.getState();

      setLoadingModels(true);
      expect(useGenerationStore.getState().isLoadingModels).toBe(true);

      setLoadingModels(false);
      expect(useGenerationStore.getState().isLoadingModels).toBe(false);
    });

    it('should set loading health state', () => {
      const { setLoadingHealth } = useGenerationStore.getState();

      setLoadingHealth(true);
      expect(useGenerationStore.getState().isLoadingHealth).toBe(true);

      setLoadingHealth(false);
      expect(useGenerationStore.getState().isLoadingHealth).toBe(false);
    });
  });

  describe('Computed Helpers', () => {
    it('should get current model', () => {
      const { setAvailableModels, setSelectedModel, getCurrentModel } =
        useGenerationStore.getState();

      const models = [
        { id: 'minimax', name: 'MiniMax', description: 'Fast generation' },
        { id: 'luma', name: 'Luma AI', description: 'High quality' },
      ] as any;

      setAvailableModels('replicate', models);
      setSelectedModel('luma');

      const currentModel = getCurrentModel();
      expect(currentModel?.id).toBe('luma');
      expect(currentModel?.name).toBe('Luma AI');
    });

    it('should return null when no model selected', () => {
      const { getCurrentModel } = useGenerationStore.getState();

      expect(getCurrentModel()).toBeNull();
    });

    it('should return null when model not found', () => {
      const { setSelectedModel, getCurrentModel } = useGenerationStore.getState();

      setSelectedModel('non-existent');

      expect(getCurrentModel()).toBeNull();
    });

    it('should get models for provider', () => {
      const { setAvailableModels, getModelsForProvider } = useGenerationStore.getState();

      const models = [{ id: 'minimax', name: 'MiniMax', description: 'Fast generation' }] as any;

      setAvailableModels('replicate', models);

      expect(getModelsForProvider('replicate')).toEqual(models);
      expect(getModelsForProvider('fal')).toEqual([]);
    });
  });
});
