/**
 * Tests for the scene store.
 */

import { describe, it, expect, beforeEach, vi } from 'vitest';
import { useSceneStore } from '../../stores/scene-store';

describe('SceneStore', () => {
  beforeEach(() => {
    // Reset store state before each test
    useSceneStore.setState({
      scenes: [],
      sceneMap: {},
      selectedSceneId: null,
      selectedScene: null,
      analysisCache: {},
      shotTypes: [],
      cameraMovements: [],
      isLoading: false,
      isAnalyzing: null,
      isGeneratingBreakdown: null,
      error: null,
    });
  });

  describe('Initial State', () => {
    it('should have correct initial values', () => {
      const state = useSceneStore.getState();

      expect(state.scenes).toEqual([]);
      expect(state.sceneMap).toEqual({});
      expect(state.selectedSceneId).toBeNull();
      expect(state.selectedScene).toBeNull();
      expect(state.analysisCache).toEqual({});
      expect(state.shotTypes).toEqual([]);
      expect(state.cameraMovements).toEqual([]);
      expect(state.isLoading).toBe(false);
      expect(state.isAnalyzing).toBeNull();
      expect(state.isGeneratingBreakdown).toBeNull();
      expect(state.error).toBeNull();
    });
  });

  describe('Scene List Management', () => {
    it('should set scenes and create scene map', () => {
      const { setScenes } = useSceneStore.getState();

      const scenes = [
        { id: 'scene-1', sceneNumber: 1, state: 'draft' as const, shotCount: 5, projectId: 'proj-1' },
        { id: 'scene-2', sceneNumber: 2, state: 'analyzed' as const, shotCount: 3, projectId: 'proj-1' },
      ];

      setScenes(scenes as any);

      const state = useSceneStore.getState();
      expect(state.scenes).toHaveLength(2);
      expect(state.sceneMap['scene-1']).toBeDefined();
      expect(state.sceneMap['scene-2']).toBeDefined();
      expect(state.sceneMap['scene-1'].sceneNumber).toBe(1);
    });

    it('should update sceneMap when setting scenes', () => {
      const { setScenes } = useSceneStore.getState();

      setScenes([
        { id: 'scene-1', sceneNumber: 1, state: 'draft' as const, shotCount: 5 },
      ] as any);

      setScenes([
        { id: 'scene-2', sceneNumber: 2, state: 'analyzed' as const, shotCount: 3 },
      ] as any);

      const state = useSceneStore.getState();
      expect(state.scenes).toHaveLength(1);
      expect(state.sceneMap['scene-1']).toBeUndefined();
      expect(state.sceneMap['scene-2']).toBeDefined();
    });
  });

  describe('Scene Selection', () => {
    it('should select a scene', () => {
      const { setScenes, setSelectedSceneId } = useSceneStore.getState();

      const scenes = [
        { id: 'scene-1', sceneNumber: 1, state: 'draft' as const, shotCount: 5 },
        { id: 'scene-2', sceneNumber: 2, state: 'analyzed' as const, shotCount: 3 },
      ];

      setScenes(scenes as any);
      setSelectedSceneId('scene-1');

      const state = useSceneStore.getState();
      expect(state.selectedSceneId).toBe('scene-1');
      expect(state.selectedScene?.id).toBe('scene-1');
    });

    it('should clear selection when null is passed', () => {
      const { setScenes, setSelectedSceneId } = useSceneStore.getState();

      setScenes([
        { id: 'scene-1', sceneNumber: 1, state: 'draft' as const, shotCount: 5 },
      ] as any);

      setSelectedSceneId('scene-1');
      setSelectedSceneId(null);

      const state = useSceneStore.getState();
      expect(state.selectedSceneId).toBeNull();
      expect(state.selectedScene).toBeNull();
    });

    it('should return null for non-existent scene selection', () => {
      const { setSelectedSceneId } = useSceneStore.getState();

      setSelectedSceneId('non-existent');

      const state = useSceneStore.getState();
      expect(state.selectedSceneId).toBe('non-existent');
      expect(state.selectedScene).toBeNull();
    });
  });

  describe('Error Handling', () => {
    it('should set error', () => {
      const { setError } = useSceneStore.getState();

      setError('Failed to load scenes');

      expect(useSceneStore.getState().error).toBe('Failed to load scenes');
    });

    it('should clear error', () => {
      const { setError } = useSceneStore.getState();

      setError('Some error');
      setError(null);

      expect(useSceneStore.getState().error).toBeNull();
    });
  });

  describe('Computed Helpers', () => {
    beforeEach(() => {
      const { setScenes } = useSceneStore.getState();
      setScenes([
        { id: 'scene-1', sceneNumber: 1, state: 'draft' as const, shotCount: 5 },
        { id: 'scene-2', sceneNumber: 2, state: 'analyzed' as const, shotCount: 3 },
        { id: 'scene-3', sceneNumber: 3, state: 'breakdown_approved' as const, shotCount: 4 },
        { id: 'scene-4', sceneNumber: 4, state: 'generating' as const, shotCount: 2 },
        { id: 'scene-5', sceneNumber: 5, state: 'generated' as const, shotCount: 6 },
      ] as any);
    });

    it('should get scene by ID', () => {
      const { getSceneById } = useSceneStore.getState();

      const scene = getSceneById('scene-2');
      expect(scene?.sceneNumber).toBe(2);
    });

    it('should return undefined for non-existent scene ID', () => {
      const { getSceneById } = useSceneStore.getState();

      const scene = getSceneById('non-existent');
      expect(scene).toBeUndefined();
    });

    it('should get scenes by state', () => {
      const { getScenesByState } = useSceneStore.getState();

      const draftScenes = getScenesByState('draft');
      expect(draftScenes).toHaveLength(1);
      expect(draftScenes[0].id).toBe('scene-1');
    });

    it('should get scenes ready for generation', () => {
      const { getScenesReadyForGeneration } = useSceneStore.getState();

      const readyScenes = getScenesReadyForGeneration();
      expect(readyScenes).toHaveLength(3);
      expect(readyScenes.map(s => s.id)).toContain('scene-3');
      expect(readyScenes.map(s => s.id)).toContain('scene-4');
      expect(readyScenes.map(s => s.id)).toContain('scene-5');
    });

    it('should get scenes needing breakdown', () => {
      const { getScenesNeedingBreakdown } = useSceneStore.getState();

      const needingBreakdown = getScenesNeedingBreakdown();
      expect(needingBreakdown).toHaveLength(2);
      expect(needingBreakdown.map(s => s.id)).toContain('scene-1');
      expect(needingBreakdown.map(s => s.id)).toContain('scene-2');
    });

    it('should get total shot count', () => {
      const { getTotalShotCount } = useSceneStore.getState();

      const total = getTotalShotCount();
      expect(total).toBe(20); // 5 + 3 + 4 + 2 + 6
    });
  });

  describe('Analysis Cache', () => {
    it('should get scene analysis from cache', () => {
      const { getSceneAnalysis } = useSceneStore.getState();

      // Set analysis cache directly
      useSceneStore.setState((state) => ({
        ...state,
        analysisCache: {
          'scene-1': {
            sceneId: 'scene-1',
            mood: 'tense',
            pacing: 'fast',
            visualStyle: 'noir',
            suggestedShotCount: 5,
          } as any,
        },
      }));

      const analysis = getSceneAnalysis('scene-1');
      expect(analysis?.mood).toBe('tense');
    });

    it('should return undefined for uncached scene', () => {
      const { getSceneAnalysis } = useSceneStore.getState();

      const analysis = getSceneAnalysis('non-existent');
      expect(analysis).toBeUndefined();
    });
  });

  describe('Loading States', () => {
    it('should track analyzing state', () => {
      useSceneStore.setState((state) => ({
        ...state,
        isAnalyzing: 'scene-1',
      }));

      const state = useSceneStore.getState();
      expect(state.isAnalyzing).toBe('scene-1');
    });

    it('should track generating breakdown state', () => {
      useSceneStore.setState((state) => ({
        ...state,
        isGeneratingBreakdown: 'scene-2',
      }));

      const state = useSceneStore.getState();
      expect(state.isGeneratingBreakdown).toBe('scene-2');
    });
  });

  describe('Reference Data', () => {
    it('should store shot types', () => {
      useSceneStore.setState((state) => ({
        ...state,
        shotTypes: [
          { id: 'wide', name: 'Wide Shot', description: 'Full scene view' },
          { id: 'close', name: 'Close-up', description: 'Detailed view' },
        ] as any,
      }));

      const state = useSceneStore.getState();
      expect(state.shotTypes).toHaveLength(2);
    });

    it('should store camera movements', () => {
      useSceneStore.setState((state) => ({
        ...state,
        cameraMovements: [
          { id: 'pan', name: 'Pan', description: 'Horizontal rotation' },
          { id: 'tilt', name: 'Tilt', description: 'Vertical rotation' },
        ] as any,
      }));

      const state = useSceneStore.getState();
      expect(state.cameraMovements).toHaveLength(2);
    });
  });

  describe('Reset', () => {
    it('should reset all state', () => {
      const { setScenes, setSelectedSceneId, setError, reset } = useSceneStore.getState();

      // Modify state
      setScenes([
        { id: 'scene-1', sceneNumber: 1, state: 'draft' as const, shotCount: 5 },
      ] as any);
      setSelectedSceneId('scene-1');
      setError('Some error');

      // Reset
      reset();

      const state = useSceneStore.getState();
      expect(state.scenes).toEqual([]);
      expect(state.sceneMap).toEqual({});
      expect(state.selectedSceneId).toBeNull();
      expect(state.selectedScene).toBeNull();
      expect(state.error).toBeNull();
    });
  });
});
