/**
 * Tests for the assembly store.
 */

import { describe, it, expect, beforeEach, vi } from 'vitest';
import { useAssemblyStore } from '../../stores/assembly-store';

describe('AssemblyStore', () => {
  beforeEach(() => {
    // Reset store state before each test
    useAssemblyStore.setState({
      assemblyStatus: null,
      timeline: null,
      selectedClipId: null,
      selectedSceneId: null,
      exportFormats: [],
      qualityPresets: [],
      selectedFormat: 'mp4',
      selectedQuality: 'high',
      isExporting: false,
      exportProgress: 0,
      currentExportJob: null,
      exportHistory: [],
      isAssembling: false,
      assemblyProgress: 0,
      isLoading: false,
      error: null,
    });
  });

  describe('Initial State', () => {
    it('should have correct initial values', () => {
      const state = useAssemblyStore.getState();

      expect(state.assemblyStatus).toBeNull();
      expect(state.timeline).toBeNull();
      expect(state.selectedClipId).toBeNull();
      expect(state.selectedSceneId).toBeNull();
      expect(state.exportFormats).toEqual([]);
      expect(state.qualityPresets).toEqual([]);
      expect(state.selectedFormat).toBe('mp4');
      expect(state.selectedQuality).toBe('high');
      expect(state.isExporting).toBe(false);
      expect(state.exportProgress).toBe(0);
      expect(state.currentExportJob).toBeNull();
      expect(state.exportHistory).toEqual([]);
      expect(state.isAssembling).toBe(false);
      expect(state.assemblyProgress).toBe(0);
      expect(state.isLoading).toBe(false);
      expect(state.error).toBeNull();
    });
  });

  describe('Assembly Status Management', () => {
    it('should set assembly status', () => {
      const { setAssemblyStatus } = useAssemblyStore.getState();

      const status = {
        projectId: 'proj-1',
        state: 'pending' as const,
        totalShotCount: 10,
        approvedShotCount: 5,
        generatedShotCount: 8,
        outputPath: null,
      };

      setAssemblyStatus(status as any);

      const state = useAssemblyStore.getState();
      expect(state.assemblyStatus).toEqual(status);
    });

    it('should clear assembly status', () => {
      const { setAssemblyStatus } = useAssemblyStore.getState();

      setAssemblyStatus({
        projectId: 'proj-1',
        state: 'pending',
        totalShotCount: 10,
        approvedShotCount: 5,
        generatedShotCount: 8,
        outputPath: null,
      } as any);

      setAssemblyStatus(null);

      const state = useAssemblyStore.getState();
      expect(state.assemblyStatus).toBeNull();
    });
  });

  describe('Timeline Management', () => {
    const mockTimeline = {
      projectId: 'proj-1',
      totalDurationSeconds: 120,
      scenes: [
        {
          id: 'scene-1',
          sceneNumber: 1,
          durationSeconds: 60,
          clips: [
            { id: 'clip-1', shotId: 'shot-1', durationSeconds: 30, startTime: 0 },
            { id: 'clip-2', shotId: 'shot-2', durationSeconds: 30, startTime: 30 },
          ],
        },
        {
          id: 'scene-2',
          sceneNumber: 2,
          durationSeconds: 60,
          clips: [{ id: 'clip-3', shotId: 'shot-3', durationSeconds: 60, startTime: 60 }],
        },
      ],
    };

    it('should set timeline', () => {
      const { setTimeline } = useAssemblyStore.getState();

      setTimeline(mockTimeline as any);

      const state = useAssemblyStore.getState();
      expect(state.timeline).toEqual(mockTimeline);
    });

    it('should clear timeline', () => {
      const { setTimeline } = useAssemblyStore.getState();

      setTimeline(mockTimeline as any);
      setTimeline(null);

      const state = useAssemblyStore.getState();
      expect(state.timeline).toBeNull();
    });

    it('should get clip by ID', () => {
      const { setTimeline, getClipById } = useAssemblyStore.getState();

      setTimeline(mockTimeline as any);

      const clip = getClipById('clip-2');
      expect(clip?.shotId).toBe('shot-2');
    });

    it('should return undefined for non-existent clip', () => {
      const { setTimeline, getClipById } = useAssemblyStore.getState();

      setTimeline(mockTimeline as any);

      const clip = getClipById('non-existent');
      expect(clip).toBeUndefined();
    });

    it('should get scene by ID', () => {
      const { setTimeline, getSceneById } = useAssemblyStore.getState();

      setTimeline(mockTimeline as any);

      const scene = getSceneById('scene-1');
      expect(scene?.sceneNumber).toBe(1);
    });

    it('should get total duration', () => {
      const { setTimeline, getTotalDuration } = useAssemblyStore.getState();

      setTimeline(mockTimeline as any);

      const duration = getTotalDuration();
      expect(duration).toBe(120);
    });

    it('should return 0 for total duration when no timeline', () => {
      const { getTotalDuration } = useAssemblyStore.getState();

      const duration = getTotalDuration();
      expect(duration).toBe(0);
    });
  });

  describe('Selection Management', () => {
    it('should select clip', () => {
      const { setSelectedClipId } = useAssemblyStore.getState();

      setSelectedClipId('clip-1');

      expect(useAssemblyStore.getState().selectedClipId).toBe('clip-1');
    });

    it('should clear clip selection', () => {
      const { setSelectedClipId } = useAssemblyStore.getState();

      setSelectedClipId('clip-1');
      setSelectedClipId(null);

      expect(useAssemblyStore.getState().selectedClipId).toBeNull();
    });

    it('should select scene', () => {
      const { setSelectedSceneId } = useAssemblyStore.getState();

      setSelectedSceneId('scene-1');

      expect(useAssemblyStore.getState().selectedSceneId).toBe('scene-1');
    });

    it('should clear scene selection', () => {
      const { setSelectedSceneId } = useAssemblyStore.getState();

      setSelectedSceneId('scene-1');
      setSelectedSceneId(null);

      expect(useAssemblyStore.getState().selectedSceneId).toBeNull();
    });
  });

  describe('Export Configuration', () => {
    it('should set selected format', () => {
      const { setSelectedFormat } = useAssemblyStore.getState();

      setSelectedFormat('webm');

      expect(useAssemblyStore.getState().selectedFormat).toBe('webm');
    });

    it('should set selected quality', () => {
      const { setSelectedQuality } = useAssemblyStore.getState();

      setSelectedQuality('ultra');

      expect(useAssemblyStore.getState().selectedQuality).toBe('ultra');
    });

    it('should set export progress', () => {
      const { setExportProgress } = useAssemblyStore.getState();

      setExportProgress(50);

      expect(useAssemblyStore.getState().exportProgress).toBe(50);
    });
  });

  describe('Computed Helpers', () => {
    it('should determine readiness for assembly', () => {
      const { setAssemblyStatus, isReadyForAssembly } = useAssemblyStore.getState();

      // No status - not ready
      expect(isReadyForAssembly()).toBe(false);

      // Status with approved shots - ready
      setAssemblyStatus({
        projectId: 'proj-1',
        state: 'pending',
        totalShotCount: 10,
        approvedShotCount: 5,
        generatedShotCount: 8,
        outputPath: null,
      } as any);

      expect(isReadyForAssembly()).toBe(true);

      // Zero approved shots - not ready
      setAssemblyStatus({
        projectId: 'proj-1',
        state: 'pending',
        totalShotCount: 10,
        approvedShotCount: 0,
        generatedShotCount: 0,
        outputPath: null,
      } as any);

      expect(isReadyForAssembly()).toBe(false);
    });

    it('should determine readiness for export', () => {
      const { setAssemblyStatus, isReadyForExport } = useAssemblyStore.getState();

      // No status - not ready
      expect(isReadyForExport()).toBe(false);

      // Pending status - not ready
      setAssemblyStatus({
        projectId: 'proj-1',
        state: 'pending',
        totalShotCount: 10,
        approvedShotCount: 10,
        generatedShotCount: 10,
        outputPath: null,
      } as any);

      expect(isReadyForExport()).toBe(false);

      // Complete with output path - ready
      setAssemblyStatus({
        projectId: 'proj-1',
        state: 'complete',
        totalShotCount: 10,
        approvedShotCount: 10,
        generatedShotCount: 10,
        outputPath: '/path/to/movie.mp4',
      } as any);

      expect(isReadyForExport()).toBe(true);
    });

    it('should calculate assembly percentage', () => {
      const { setAssemblyStatus, getAssemblyPercentage } = useAssemblyStore.getState();

      // No status - 0%
      expect(getAssemblyPercentage()).toBe(0);

      // Partial progress
      setAssemblyStatus({
        projectId: 'proj-1',
        state: 'pending',
        totalShotCount: 10,
        approvedShotCount: 7,
        generatedShotCount: 8,
        outputPath: null,
      } as any);

      expect(getAssemblyPercentage()).toBe(70);

      // Zero total shots
      setAssemblyStatus({
        projectId: 'proj-1',
        state: 'pending',
        totalShotCount: 0,
        approvedShotCount: 0,
        generatedShotCount: 0,
        outputPath: null,
      } as any);

      expect(getAssemblyPercentage()).toBe(0);
    });
  });

  describe('Export Formats and Quality Presets', () => {
    it('should store export formats', () => {
      useAssemblyStore.setState((state) => ({
        ...state,
        exportFormats: [
          { id: 'mp4', name: 'MP4', extension: '.mp4', codec: 'h264' },
          { id: 'webm', name: 'WebM', extension: '.webm', codec: 'vp9' },
          { id: 'prores', name: 'ProRes', extension: '.mov', codec: 'prores' },
        ] as any,
      }));

      const state = useAssemblyStore.getState();
      expect(state.exportFormats).toHaveLength(3);
    });

    it('should store quality presets', () => {
      useAssemblyStore.setState((state) => ({
        ...state,
        qualityPresets: [
          { id: 'draft', name: 'Draft', bitrate: 5000000 },
          { id: 'high', name: 'High', bitrate: 20000000 },
          { id: 'ultra', name: 'Ultra', bitrate: 50000000 },
        ] as any,
      }));

      const state = useAssemblyStore.getState();
      expect(state.qualityPresets).toHaveLength(3);
    });
  });

  describe('Export History', () => {
    it('should store export history', () => {
      useAssemblyStore.setState((state) => ({
        ...state,
        exportHistory: [
          { id: 'export-1', projectId: 'proj-1', format: 'mp4', createdAt: '2024-01-01' },
          { id: 'export-2', projectId: 'proj-1', format: 'webm', createdAt: '2024-01-02' },
        ] as any,
      }));

      const state = useAssemblyStore.getState();
      expect(state.exportHistory).toHaveLength(2);
    });
  });

  describe('Loading States', () => {
    it('should track exporting state', () => {
      useAssemblyStore.setState((state) => ({
        ...state,
        isExporting: true,
        exportProgress: 45,
      }));

      const state = useAssemblyStore.getState();
      expect(state.isExporting).toBe(true);
      expect(state.exportProgress).toBe(45);
    });

    it('should track assembling state', () => {
      useAssemblyStore.setState((state) => ({
        ...state,
        isAssembling: true,
        assemblyProgress: 30,
      }));

      const state = useAssemblyStore.getState();
      expect(state.isAssembling).toBe(true);
      expect(state.assemblyProgress).toBe(30);
    });
  });

  describe('Error Handling', () => {
    it('should set error', () => {
      const { setError } = useAssemblyStore.getState();

      setError('Failed to export movie');

      expect(useAssemblyStore.getState().error).toBe('Failed to export movie');
    });

    it('should clear error', () => {
      const { setError } = useAssemblyStore.getState();

      setError('Some error');
      setError(null);

      expect(useAssemblyStore.getState().error).toBeNull();
    });
  });

  describe('Reset', () => {
    it('should reset all state', () => {
      const { setAssemblyStatus, setTimeline, setSelectedFormat, setError, reset } =
        useAssemblyStore.getState();

      // Modify state
      setAssemblyStatus({
        projectId: 'proj-1',
        state: 'complete',
        totalShotCount: 10,
        approvedShotCount: 10,
        generatedShotCount: 10,
        outputPath: '/path/to/movie.mp4',
      } as any);
      setTimeline({
        projectId: 'proj-1',
        totalDurationSeconds: 120,
        scenes: [],
      } as any);
      setSelectedFormat('webm');
      setError('Some error');

      // Reset
      reset();

      const state = useAssemblyStore.getState();
      expect(state.assemblyStatus).toBeNull();
      expect(state.timeline).toBeNull();
      expect(state.selectedFormat).toBe('mp4');
      expect(state.error).toBeNull();
    });
  });
});
