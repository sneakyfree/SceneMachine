/**
 * Tests for the shot store.
 */

import { describe, it, expect, beforeEach, vi } from 'vitest';
import { useShotStore } from '../../stores/shot-store';

describe('ShotStore', () => {
  beforeEach(() => {
    // Reset store state before each test
    useShotStore.setState({
      shotMap: {},
      shotsByScene: {},
      selectedShotId: null,
      selectedShot: null,
      shotJobs: {},
      isLoading: false,
      isUpdating: null,
      isQueuing: null,
      error: null,
    });
  });

  describe('Initial State', () => {
    it('should have correct initial values', () => {
      const state = useShotStore.getState();

      expect(state.shotMap).toEqual({});
      expect(state.shotsByScene).toEqual({});
      expect(state.selectedShotId).toBeNull();
      expect(state.selectedShot).toBeNull();
      expect(state.shotJobs).toEqual({});
      expect(state.isLoading).toBe(false);
      expect(state.isUpdating).toBeNull();
      expect(state.isQueuing).toBeNull();
      expect(state.error).toBeNull();
    });
  });

  describe('Shot List Management', () => {
    it('should set shots and organize by scene', () => {
      const { setShots } = useShotStore.getState();

      const shots = [
        { id: 'shot-1', sceneId: 'scene-1', shotNumber: 1, state: 'planned' as const },
        { id: 'shot-2', sceneId: 'scene-1', shotNumber: 2, state: 'queued' as const },
        { id: 'shot-3', sceneId: 'scene-2', shotNumber: 1, state: 'generated' as const },
      ];

      setShots(shots as any);

      const state = useShotStore.getState();
      expect(Object.keys(state.shotMap)).toHaveLength(3);
      expect(state.shotsByScene['scene-1']).toHaveLength(2);
      expect(state.shotsByScene['scene-2']).toHaveLength(1);
    });

    it('should sort shots by number within each scene', () => {
      const { setShots } = useShotStore.getState();

      const shots = [
        { id: 'shot-2', sceneId: 'scene-1', shotNumber: 2, state: 'planned' as const },
        { id: 'shot-1', sceneId: 'scene-1', shotNumber: 1, state: 'planned' as const },
        { id: 'shot-3', sceneId: 'scene-1', shotNumber: 3, state: 'planned' as const },
      ];

      setShots(shots as any);

      const state = useShotStore.getState();
      expect(state.shotsByScene['scene-1'][0].shotNumber).toBe(1);
      expect(state.shotsByScene['scene-1'][1].shotNumber).toBe(2);
      expect(state.shotsByScene['scene-1'][2].shotNumber).toBe(3);
    });

    it('should update shot in state', () => {
      const { setShots, updateShotInState } = useShotStore.getState();

      setShots([
        { id: 'shot-1', sceneId: 'scene-1', shotNumber: 1, state: 'planned' as const },
      ] as any);

      updateShotInState({
        id: 'shot-1',
        sceneId: 'scene-1',
        shotNumber: 1,
        state: 'generated' as const,
      } as any);

      const state = useShotStore.getState();
      expect(state.shotMap['shot-1'].state).toBe('generated');
    });

    it('should add new shot in updateShotInState if not exists', () => {
      const { setShots, updateShotInState } = useShotStore.getState();

      setShots([
        { id: 'shot-1', sceneId: 'scene-1', shotNumber: 1, state: 'planned' as const },
      ] as any);

      updateShotInState({
        id: 'shot-2',
        sceneId: 'scene-1',
        shotNumber: 2,
        state: 'planned' as const,
      } as any);

      const state = useShotStore.getState();
      expect(state.shotsByScene['scene-1']).toHaveLength(2);
    });

    it('should remove shot from state', () => {
      const { setShots, removeShotFromState } = useShotStore.getState();

      setShots([
        { id: 'shot-1', sceneId: 'scene-1', shotNumber: 1, state: 'planned' as const },
        { id: 'shot-2', sceneId: 'scene-1', shotNumber: 2, state: 'planned' as const },
      ] as any);

      removeShotFromState('shot-1');

      const state = useShotStore.getState();
      expect(state.shotMap['shot-1']).toBeUndefined();
      expect(state.shotsByScene['scene-1']).toHaveLength(1);
    });

    it('should clear selection when removing selected shot', () => {
      const { setShots, setSelectedShotId, removeShotFromState } = useShotStore.getState();

      setShots([
        { id: 'shot-1', sceneId: 'scene-1', shotNumber: 1, state: 'planned' as const },
      ] as any);

      setSelectedShotId('shot-1');
      removeShotFromState('shot-1');

      const state = useShotStore.getState();
      expect(state.selectedShotId).toBeNull();
      expect(state.selectedShot).toBeNull();
    });
  });

  describe('Shot Selection', () => {
    it('should select a shot', () => {
      const { setShots, setSelectedShotId } = useShotStore.getState();

      setShots([
        { id: 'shot-1', sceneId: 'scene-1', shotNumber: 1, state: 'planned' as const },
      ] as any);

      setSelectedShotId('shot-1');

      const state = useShotStore.getState();
      expect(state.selectedShotId).toBe('shot-1');
      expect(state.selectedShot?.id).toBe('shot-1');
    });

    it('should clear selection', () => {
      const { setShots, setSelectedShotId } = useShotStore.getState();

      setShots([
        { id: 'shot-1', sceneId: 'scene-1', shotNumber: 1, state: 'planned' as const },
      ] as any);

      setSelectedShotId('shot-1');
      setSelectedShotId(null);

      const state = useShotStore.getState();
      expect(state.selectedShotId).toBeNull();
      expect(state.selectedShot).toBeNull();
    });
  });

  describe('Error Handling', () => {
    it('should set error', () => {
      const { setError } = useShotStore.getState();

      setError('Failed to load shots');

      expect(useShotStore.getState().error).toBe('Failed to load shots');
    });

    it('should clear error', () => {
      const { setError } = useShotStore.getState();

      setError('Some error');
      setError(null);

      expect(useShotStore.getState().error).toBeNull();
    });
  });

  describe('Computed Helpers', () => {
    beforeEach(() => {
      const { setShots } = useShotStore.getState();
      setShots([
        { id: 'shot-1', sceneId: 'scene-1', shotNumber: 1, state: 'planned' as const },
        { id: 'shot-2', sceneId: 'scene-1', shotNumber: 2, state: 'queued' as const },
        { id: 'shot-3', sceneId: 'scene-1', shotNumber: 3, state: 'generating' as const },
        { id: 'shot-4', sceneId: 'scene-2', shotNumber: 1, state: 'generated' as const },
        { id: 'shot-5', sceneId: 'scene-2', shotNumber: 2, state: 'approved' as const },
        { id: 'shot-6', sceneId: 'scene-2', shotNumber: 3, state: 'rejected' as const },
      ] as any);
    });

    it('should get shot by ID', () => {
      const { getShotById } = useShotStore.getState();

      const shot = getShotById('shot-2');
      expect(shot?.shotNumber).toBe(2);
    });

    it('should return undefined for non-existent shot ID', () => {
      const { getShotById } = useShotStore.getState();

      const shot = getShotById('non-existent');
      expect(shot).toBeUndefined();
    });

    it('should get shots for scene', () => {
      const { getShotsForScene } = useShotStore.getState();

      const scene1Shots = getShotsForScene('scene-1');
      expect(scene1Shots).toHaveLength(3);

      const scene2Shots = getShotsForScene('scene-2');
      expect(scene2Shots).toHaveLength(3);
    });

    it('should return empty array for non-existent scene', () => {
      const { getShotsForScene } = useShotStore.getState();

      const shots = getShotsForScene('non-existent');
      expect(shots).toEqual([]);
    });

    it('should get shots by state', () => {
      const { getShotsByState } = useShotStore.getState();

      const plannedShots = getShotsByState('planned');
      expect(plannedShots).toHaveLength(1);

      const approvedShots = getShotsByState('approved');
      expect(approvedShots).toHaveLength(1);
    });

    it('should get pending shots', () => {
      const { getPendingShots } = useShotStore.getState();

      const pendingShots = getPendingShots();
      expect(pendingShots).toHaveLength(3); // planned, queued, generating
    });

    it('should get approved shots', () => {
      const { getApprovedShots } = useShotStore.getState();

      const approvedShots = getApprovedShots();
      expect(approvedShots).toHaveLength(1);
    });
  });

  describe('Shot Generation Progress', () => {
    it('should get shot generation progress from jobs', () => {
      const { getShotGenerationProgress } = useShotStore.getState();

      useShotStore.setState((state) => ({
        ...state,
        shotJobs: {
          'shot-1': [{ id: 'job-1', progress: 75, status: 'generating' }] as any,
        },
      }));

      const progress = getShotGenerationProgress('shot-1');
      expect(progress).toBe(75);
    });

    it('should return 0 for shot without jobs', () => {
      const { getShotGenerationProgress } = useShotStore.getState();

      const progress = getShotGenerationProgress('shot-no-jobs');
      expect(progress).toBe(0);
    });

    it('should return 0 for shot with empty jobs', () => {
      const { getShotGenerationProgress } = useShotStore.getState();

      useShotStore.setState((state) => ({
        ...state,
        shotJobs: {
          'shot-1': [],
        },
      }));

      const progress = getShotGenerationProgress('shot-1');
      expect(progress).toBe(0);
    });
  });

  describe('Loading States', () => {
    it('should track updating state', () => {
      useShotStore.setState((state) => ({
        ...state,
        isUpdating: 'shot-1',
      }));

      const state = useShotStore.getState();
      expect(state.isUpdating).toBe('shot-1');
    });

    it('should track queuing state', () => {
      useShotStore.setState((state) => ({
        ...state,
        isQueuing: 'shot-2',
      }));

      const state = useShotStore.getState();
      expect(state.isQueuing).toBe('shot-2');
    });
  });

  describe('Reset', () => {
    it('should reset all state', () => {
      const { setShots, setSelectedShotId, setError, reset } = useShotStore.getState();

      // Modify state
      setShots([
        { id: 'shot-1', sceneId: 'scene-1', shotNumber: 1, state: 'planned' as const },
      ] as any);
      setSelectedShotId('shot-1');
      setError('Some error');

      // Reset
      reset();

      const state = useShotStore.getState();
      expect(state.shotMap).toEqual({});
      expect(state.shotsByScene).toEqual({});
      expect(state.selectedShotId).toBeNull();
      expect(state.selectedShot).toBeNull();
      expect(state.error).toBeNull();
    });
  });
});
