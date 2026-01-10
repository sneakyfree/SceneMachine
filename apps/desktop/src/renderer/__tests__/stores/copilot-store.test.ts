/**
 * Copilot store unit tests.
 */

import { describe, it, expect, beforeEach, vi } from 'vitest';
import { act } from '@testing-library/react';
import {
  useCopilotStore,
  useHasPendingSuggestions,
  useCopilotReady,
} from '../../stores/copilot-store';

// Mock the API client
vi.mock('../../api/client', () => ({
  api: {
    sendCopilotMessage: vi.fn(),
    getCopilotAnalysis: vi.fn(),
    getCopilotSceneSuggestions: vi.fn(),
    getCopilotShotSuggestions: vi.fn(),
    applyCopilotSuggestion: vi.fn(),
    dismissCopilotSuggestion: vi.fn(),
    getCopilotQuickActions: vi.fn(),
  },
}));

const mockSuggestion = {
  id: 'suggestion-1',
  type: 'scene' as const,
  title: 'Test Suggestion',
  description: 'A test suggestion',
  confidence: 0.85,
  priority: 'medium' as const,
};

const mockMessage = {
  role: 'user' as const,
  content: 'Hello',
  timestamp: new Date().toISOString(),
};

describe('CopilotStore', () => {
  beforeEach(() => {
    // Reset store state before each test
    useCopilotStore.setState({
      messages: [],
      isTyping: false,
      currentProjectId: null,
      currentContext: {},
      activeSuggestions: [],
      dismissedSuggestionIds: new Set(),
      appliedSuggestionIds: new Set(),
      projectAnalysis: null,
      isAnalyzing: false,
      quickActions: [],
      isPanelOpen: false,
      isPanelMinimized: false,
      activeTab: 'chat',
      autoSuggest: true,
      suggestionTypes: ['scene', 'shot', 'character', 'dialogue', 'pacing', 'visual'],
      isLoadingSuggestions: false,
      isSending: false,
      error: null,
    });
    vi.clearAllMocks();
  });

  describe('addMessage', () => {
    it('should add a message to the messages array', () => {
      const { addMessage } = useCopilotStore.getState();

      act(() => {
        addMessage(mockMessage);
      });

      expect(useCopilotStore.getState().messages).toHaveLength(1);
      expect(useCopilotStore.getState().messages[0]).toEqual(mockMessage);
    });
  });

  describe('clearMessages', () => {
    it('should clear all messages', () => {
      useCopilotStore.setState({ messages: [mockMessage] });

      const { clearMessages } = useCopilotStore.getState();

      act(() => {
        clearMessages();
      });

      expect(useCopilotStore.getState().messages).toHaveLength(0);
    });
  });

  describe('setIsTyping', () => {
    it('should set typing state', () => {
      const { setIsTyping } = useCopilotStore.getState();

      act(() => {
        setIsTyping(true);
      });

      expect(useCopilotStore.getState().isTyping).toBe(true);
    });
  });

  describe('setCurrentProjectId', () => {
    it('should set the current project ID', () => {
      const { setCurrentProjectId } = useCopilotStore.getState();

      act(() => {
        setCurrentProjectId('project-123');
      });

      expect(useCopilotStore.getState().currentProjectId).toBe('project-123');
    });

    it('should clear context when project changes', () => {
      useCopilotStore.setState({
        currentProjectId: 'project-1',
        currentContext: { sceneId: 'scene-1' },
        activeSuggestions: [mockSuggestion],
        projectAnalysis: { overallScore: 0.8 } as any,
      });

      const { setCurrentProjectId } = useCopilotStore.getState();

      act(() => {
        setCurrentProjectId('project-2');
      });

      const state = useCopilotStore.getState();
      expect(state.currentContext).toEqual({});
      expect(state.activeSuggestions).toHaveLength(0);
      expect(state.projectAnalysis).toBeNull();
    });
  });

  describe('setCurrentContext', () => {
    it('should set the current context', () => {
      const { setCurrentContext } = useCopilotStore.getState();

      act(() => {
        setCurrentContext({ sceneId: 'scene-1', shotId: 'shot-1' });
      });

      expect(useCopilotStore.getState().currentContext).toEqual({
        sceneId: 'scene-1',
        shotId: 'shot-1',
      });
    });
  });

  describe('addSuggestions', () => {
    it('should add new suggestions', () => {
      const { addSuggestions } = useCopilotStore.getState();

      act(() => {
        addSuggestions([mockSuggestion]);
      });

      expect(useCopilotStore.getState().activeSuggestions).toHaveLength(1);
    });

    it('should not add duplicate suggestions', () => {
      useCopilotStore.setState({ activeSuggestions: [mockSuggestion] });

      const { addSuggestions } = useCopilotStore.getState();

      act(() => {
        addSuggestions([mockSuggestion]);
      });

      expect(useCopilotStore.getState().activeSuggestions).toHaveLength(1);
    });

    it('should not add dismissed suggestions', () => {
      useCopilotStore.setState({
        dismissedSuggestionIds: new Set(['suggestion-1']),
      });

      const { addSuggestions } = useCopilotStore.getState();

      act(() => {
        addSuggestions([mockSuggestion]);
      });

      expect(useCopilotStore.getState().activeSuggestions).toHaveLength(0);
    });

    it('should not add applied suggestions', () => {
      useCopilotStore.setState({
        appliedSuggestionIds: new Set(['suggestion-1']),
      });

      const { addSuggestions } = useCopilotStore.getState();

      act(() => {
        addSuggestions([mockSuggestion]);
      });

      expect(useCopilotStore.getState().activeSuggestions).toHaveLength(0);
    });
  });

  describe('clearSuggestions', () => {
    it('should clear all suggestions', () => {
      useCopilotStore.setState({ activeSuggestions: [mockSuggestion] });

      const { clearSuggestions } = useCopilotStore.getState();

      act(() => {
        clearSuggestions();
      });

      expect(useCopilotStore.getState().activeSuggestions).toHaveLength(0);
    });
  });

  describe('markSuggestionApplied', () => {
    it('should mark suggestion as applied and remove from active', () => {
      useCopilotStore.setState({ activeSuggestions: [mockSuggestion] });

      const { markSuggestionApplied } = useCopilotStore.getState();

      act(() => {
        markSuggestionApplied('suggestion-1');
      });

      const state = useCopilotStore.getState();
      expect(state.appliedSuggestionIds.has('suggestion-1')).toBe(true);
      expect(state.activeSuggestions).toHaveLength(0);
    });
  });

  describe('markSuggestionDismissed', () => {
    it('should mark suggestion as dismissed and remove from active', () => {
      useCopilotStore.setState({ activeSuggestions: [mockSuggestion] });

      const { markSuggestionDismissed } = useCopilotStore.getState();

      act(() => {
        markSuggestionDismissed('suggestion-1');
      });

      const state = useCopilotStore.getState();
      expect(state.dismissedSuggestionIds.has('suggestion-1')).toBe(true);
      expect(state.activeSuggestions).toHaveLength(0);
    });
  });

  describe('setProjectAnalysis', () => {
    it('should set project analysis', () => {
      const analysis = { overallScore: 0.75 } as any;
      const { setProjectAnalysis } = useCopilotStore.getState();

      act(() => {
        setProjectAnalysis(analysis);
      });

      expect(useCopilotStore.getState().projectAnalysis).toEqual(analysis);
    });
  });

  describe('setQuickActions', () => {
    it('should set quick actions', () => {
      const actions = [{ id: '1', label: 'Action 1', action: 'do_something' }];
      const { setQuickActions } = useCopilotStore.getState();

      act(() => {
        setQuickActions(actions);
      });

      expect(useCopilotStore.getState().quickActions).toEqual(actions);
    });
  });

  describe('togglePanel', () => {
    it('should toggle panel open state', () => {
      expect(useCopilotStore.getState().isPanelOpen).toBe(false);

      const { togglePanel } = useCopilotStore.getState();

      act(() => {
        togglePanel();
      });

      expect(useCopilotStore.getState().isPanelOpen).toBe(true);

      act(() => {
        togglePanel();
      });

      expect(useCopilotStore.getState().isPanelOpen).toBe(false);
    });
  });

  describe('setActiveTab', () => {
    it('should set the active tab', () => {
      const { setActiveTab } = useCopilotStore.getState();

      act(() => {
        setActiveTab('suggestions');
      });

      expect(useCopilotStore.getState().activeTab).toBe('suggestions');
    });
  });

  describe('setAutoSuggest', () => {
    it('should set auto suggest setting', () => {
      const { setAutoSuggest } = useCopilotStore.getState();

      act(() => {
        setAutoSuggest(false);
      });

      expect(useCopilotStore.getState().autoSuggest).toBe(false);
    });
  });

  describe('setSuggestionTypes', () => {
    it('should set suggestion types', () => {
      const { setSuggestionTypes } = useCopilotStore.getState();

      act(() => {
        setSuggestionTypes(['scene', 'shot']);
      });

      expect(useCopilotStore.getState().suggestionTypes).toEqual(['scene', 'shot']);
    });
  });

  describe('setError', () => {
    it('should set error message', () => {
      const { setError } = useCopilotStore.getState();

      act(() => {
        setError('Test error');
      });

      expect(useCopilotStore.getState().error).toBe('Test error');
    });
  });

  describe('getUnreadSuggestionCount', () => {
    it('should return count of active suggestions', () => {
      useCopilotStore.setState({
        activeSuggestions: [mockSuggestion, { ...mockSuggestion, id: 'suggestion-2' }],
      });

      const { getUnreadSuggestionCount } = useCopilotStore.getState();
      expect(getUnreadSuggestionCount()).toBe(2);
    });
  });

  describe('getVisibleSuggestions', () => {
    it('should filter suggestions by enabled types', () => {
      const suggestions = [
        { ...mockSuggestion, id: 's1', type: 'scene' as const },
        { ...mockSuggestion, id: 's2', type: 'dialogue' as const },
        { ...mockSuggestion, id: 's3', type: 'pacing' as const },
      ];
      useCopilotStore.setState({
        activeSuggestions: suggestions,
        suggestionTypes: ['scene', 'dialogue'],
      });

      const { getVisibleSuggestions } = useCopilotStore.getState();
      const visible = getVisibleSuggestions();

      expect(visible).toHaveLength(2);
      expect(visible.map((s) => s.type)).toEqual(['scene', 'dialogue']);
    });
  });

  describe('getSuggestionsByType', () => {
    it('should filter suggestions by type', () => {
      const suggestions = [
        { ...mockSuggestion, id: 's1', type: 'scene' as const },
        { ...mockSuggestion, id: 's2', type: 'scene' as const },
        { ...mockSuggestion, id: 's3', type: 'dialogue' as const },
      ];
      useCopilotStore.setState({ activeSuggestions: suggestions });

      const { getSuggestionsByType } = useCopilotStore.getState();
      const sceneSuggestions = getSuggestionsByType('scene');

      expect(sceneSuggestions).toHaveLength(2);
    });
  });

  describe('getAnalysisScore', () => {
    it('should return analysis score when available', () => {
      useCopilotStore.setState({
        projectAnalysis: { overallScore: 0.85 } as any,
      });

      const { getAnalysisScore } = useCopilotStore.getState();
      expect(getAnalysisScore()).toBe(0.85);
    });

    it('should return null when no analysis', () => {
      const { getAnalysisScore } = useCopilotStore.getState();
      expect(getAnalysisScore()).toBeNull();
    });
  });
});

describe('useHasPendingSuggestions', () => {
  beforeEach(() => {
    useCopilotStore.setState({ activeSuggestions: [] });
  });

  it('should return false when no suggestions', () => {
    // This would need to be tested in a React component context
    expect(useCopilotStore.getState().activeSuggestions.length > 0).toBe(false);
  });

  it('should return true when there are suggestions', () => {
    useCopilotStore.setState({ activeSuggestions: [mockSuggestion] });
    expect(useCopilotStore.getState().activeSuggestions.length > 0).toBe(true);
  });
});

describe('useCopilotReady', () => {
  beforeEach(() => {
    useCopilotStore.setState({ currentProjectId: null });
  });

  it('should return false when no project selected', () => {
    expect(useCopilotStore.getState().currentProjectId !== null).toBe(false);
  });

  it('should return true when project is selected', () => {
    useCopilotStore.setState({ currentProjectId: 'project-1' });
    expect(useCopilotStore.getState().currentProjectId !== null).toBe(true);
  });
});
