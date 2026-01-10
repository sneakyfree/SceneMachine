/**
 * Screenplay store unit tests.
 */

import { describe, it, expect, beforeEach, vi } from 'vitest';
import { act } from '@testing-library/react';
import { useScreenplayStore } from '../../stores/screenplay-store';

// Mock the API client
vi.mock('../../api/client', () => ({
  api: {
    getScreenplay: vi.fn(),
    getProjectScreenplay: vi.fn(),
    uploadScreenplay: vi.fn(),
    parseScreenplay: vi.fn(),
    deleteScreenplay: vi.fn(),
    getMoviePlan: vi.fn(),
    generateMoviePlan: vi.fn(),
    approveMoviePlan: vi.fn(),
  },
}));

const mockScreenplay = {
  id: 'screenplay-1',
  projectId: 'project-1',
  filename: 'test-script.pdf',
  status: 'parsed',
  title: 'Test Script',
  pageCount: 120,
  createdAt: new Date().toISOString(),
};

const mockMoviePlan = {
  id: 'plan-1',
  screenplayId: 'screenplay-1',
  title: 'Test Script',
  scenes: [],
  characters: [],
  estimatedDuration: 120,
  createdAt: new Date().toISOString(),
};

describe('ScreenplayStore', () => {
  beforeEach(() => {
    // Reset store state before each test
    useScreenplayStore.setState({
      currentScreenplay: null,
      screenplaySummary: null,
      moviePlan: null,
      moviePlanApproved: false,
      uploadProgress: 0,
      isUploading: false,
      isParsing: false,
      parseProgress: 0,
      isGeneratingPlan: false,
      isLoading: false,
      error: null,
    });
    vi.clearAllMocks();
  });

  describe('setCurrentScreenplay', () => {
    it('should set the current screenplay', () => {
      const { setCurrentScreenplay } = useScreenplayStore.getState();

      act(() => {
        setCurrentScreenplay(mockScreenplay);
      });

      expect(useScreenplayStore.getState().currentScreenplay).toEqual(mockScreenplay);
    });

    it('should allow clearing the screenplay', () => {
      useScreenplayStore.setState({ currentScreenplay: mockScreenplay });

      const { setCurrentScreenplay } = useScreenplayStore.getState();

      act(() => {
        setCurrentScreenplay(null);
      });

      expect(useScreenplayStore.getState().currentScreenplay).toBeNull();
    });
  });

  describe('setScreenplaySummary', () => {
    it('should set the screenplay summary', () => {
      const summary = { id: 'sp-1', title: 'Test', pageCount: 100 };
      const { setScreenplaySummary } = useScreenplayStore.getState();

      act(() => {
        setScreenplaySummary(summary);
      });

      expect(useScreenplayStore.getState().screenplaySummary).toEqual(summary);
    });
  });

  describe('setMoviePlan', () => {
    it('should set the movie plan', () => {
      const { setMoviePlan } = useScreenplayStore.getState();

      act(() => {
        setMoviePlan(mockMoviePlan);
      });

      expect(useScreenplayStore.getState().moviePlan).toEqual(mockMoviePlan);
    });
  });

  describe('setMoviePlanApproved', () => {
    it('should set movie plan approved state', () => {
      const { setMoviePlanApproved } = useScreenplayStore.getState();

      act(() => {
        setMoviePlanApproved(true);
      });

      expect(useScreenplayStore.getState().moviePlanApproved).toBe(true);
    });
  });

  describe('setUploadProgress', () => {
    it('should set upload progress', () => {
      const { setUploadProgress } = useScreenplayStore.getState();

      act(() => {
        setUploadProgress(50);
      });

      expect(useScreenplayStore.getState().uploadProgress).toBe(50);
    });
  });

  describe('setParseProgress', () => {
    it('should set parse progress', () => {
      const { setParseProgress } = useScreenplayStore.getState();

      act(() => {
        setParseProgress(75);
      });

      expect(useScreenplayStore.getState().parseProgress).toBe(75);
    });
  });

  describe('setError', () => {
    it('should set error message', () => {
      const { setError } = useScreenplayStore.getState();

      act(() => {
        setError('Test error');
      });

      expect(useScreenplayStore.getState().error).toBe('Test error');
    });

    it('should allow clearing error', () => {
      useScreenplayStore.setState({ error: 'Previous error' });

      const { setError } = useScreenplayStore.getState();

      act(() => {
        setError(null);
      });

      expect(useScreenplayStore.getState().error).toBeNull();
    });
  });

  describe('isReadyForParsing', () => {
    it('should return false when no screenplay', () => {
      const { isReadyForParsing } = useScreenplayStore.getState();

      expect(isReadyForParsing()).toBe(false);
    });

    it('should return true when screenplay is uploaded', () => {
      useScreenplayStore.setState({
        currentScreenplay: { ...mockScreenplay, status: 'uploaded' },
      });

      const { isReadyForParsing } = useScreenplayStore.getState();

      expect(isReadyForParsing()).toBe(true);
    });
  });

  describe('isReadyForPlanGeneration', () => {
    it('should return false when screenplay not parsed', () => {
      useScreenplayStore.setState({
        currentScreenplay: { ...mockScreenplay, status: 'uploaded' },
      });

      const { isReadyForPlanGeneration } = useScreenplayStore.getState();

      expect(isReadyForPlanGeneration()).toBe(false);
    });

    it('should return true when screenplay is parsed', () => {
      useScreenplayStore.setState({
        currentScreenplay: { ...mockScreenplay, status: 'parsed' },
      });

      const { isReadyForPlanGeneration } = useScreenplayStore.getState();

      expect(isReadyForPlanGeneration()).toBe(true);
    });
  });

  describe('isReadyForSceneBreakdown', () => {
    it('should return false when no movie plan', () => {
      const { isReadyForSceneBreakdown } = useScreenplayStore.getState();

      expect(isReadyForSceneBreakdown()).toBe(false);
    });

    it('should return false when plan not approved', () => {
      useScreenplayStore.setState({
        moviePlan: mockMoviePlan,
        moviePlanApproved: false,
      });

      const { isReadyForSceneBreakdown } = useScreenplayStore.getState();

      expect(isReadyForSceneBreakdown()).toBe(false);
    });

    it('should return true when plan is approved', () => {
      useScreenplayStore.setState({
        moviePlan: mockMoviePlan,
        moviePlanApproved: true,
      });

      const { isReadyForSceneBreakdown } = useScreenplayStore.getState();

      expect(isReadyForSceneBreakdown()).toBe(true);
    });
  });

  describe('reset', () => {
    it('should reset store to initial state', () => {
      useScreenplayStore.setState({
        currentScreenplay: mockScreenplay,
        moviePlan: mockMoviePlan,
        moviePlanApproved: true,
        uploadProgress: 100,
        error: 'Some error',
      });

      const { reset } = useScreenplayStore.getState();

      act(() => {
        reset();
      });

      const state = useScreenplayStore.getState();
      expect(state.currentScreenplay).toBeNull();
      expect(state.moviePlan).toBeNull();
      expect(state.moviePlanApproved).toBe(false);
      expect(state.uploadProgress).toBe(0);
      expect(state.error).toBeNull();
    });
  });
});
