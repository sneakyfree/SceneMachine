/**
 * Co-pilot (Steven) state store using Zustand.
 *
 * Manages AI co-pilot chat, suggestions, and project analysis
 * for intelligent filmmaking assistance.
 */

import { create } from 'zustand';
import { devtools, persist } from 'zustand/middleware';
import { immer } from 'zustand/middleware/immer';
import {
  api,
  type CopilotMessage,
  type CopilotSuggestion,
  type CopilotAnalysis,
  type CopilotChatResponse,
} from '../api/client';

interface QuickAction {
  id: string;
  label: string;
  action: string;
}

interface CopilotStoreState {
  // Chat state
  messages: CopilotMessage[];
  isTyping: boolean;
  currentProjectId: string | null;

  // Context for chat
  currentContext: {
    sceneId?: string;
    shotId?: string;
    characterId?: string;
  };

  // Suggestions
  activeSuggestions: CopilotSuggestion[];
  dismissedSuggestionIds: Set<string>;
  appliedSuggestionIds: Set<string>;

  // Analysis
  projectAnalysis: CopilotAnalysis | null;
  isAnalyzing: boolean;

  // Quick actions
  quickActions: QuickAction[];

  // UI state
  isPanelOpen: boolean;
  isPanelMinimized: boolean;
  activeTab: 'chat' | 'suggestions' | 'analysis';

  // Settings
  autoSuggest: boolean;
  suggestionTypes: Array<CopilotSuggestion['type']>;

  // Loading states
  isLoadingSuggestions: boolean;
  isSending: boolean;

  // Error state
  error: string | null;

  // Actions - Chat
  addMessage: (message: CopilotMessage) => void;
  clearMessages: () => void;
  setIsTyping: (typing: boolean) => void;
  setCurrentProjectId: (projectId: string | null) => void;
  setCurrentContext: (context: CopilotStoreState['currentContext']) => void;

  // Actions - Suggestions
  addSuggestions: (suggestions: CopilotSuggestion[]) => void;
  clearSuggestions: () => void;
  markSuggestionApplied: (suggestionId: string) => void;
  markSuggestionDismissed: (suggestionId: string) => void;

  // Actions - Analysis
  setProjectAnalysis: (analysis: CopilotAnalysis | null) => void;
  setIsAnalyzing: (analyzing: boolean) => void;

  // Actions - Quick actions
  setQuickActions: (actions: QuickAction[]) => void;

  // Actions - UI
  setIsPanelOpen: (open: boolean) => void;
  setIsPanelMinimized: (minimized: boolean) => void;
  setActiveTab: (tab: 'chat' | 'suggestions' | 'analysis') => void;
  togglePanel: () => void;

  // Actions - Settings
  setAutoSuggest: (auto: boolean) => void;
  setSuggestionTypes: (types: Array<CopilotSuggestion['type']>) => void;

  // Actions - Loading states
  setLoadingSuggestions: (loading: boolean) => void;
  setIsSending: (sending: boolean) => void;
  setError: (error: string | null) => void;

  // Async actions
  sendMessage: (message: string) => Promise<CopilotChatResponse | null>;
  analyzeProject: (projectId: string) => Promise<void>;
  fetchSceneSuggestions: (projectId: string, sceneId: string) => Promise<void>;
  fetchShotSuggestions: (projectId: string, shotId: string) => Promise<void>;
  applySuggestion: (projectId: string, suggestionId: string) => Promise<boolean>;
  dismissSuggestion: (projectId: string, suggestionId: string) => Promise<boolean>;
  fetchQuickActions: () => Promise<void>;

  // Computed helpers
  getUnreadSuggestionCount: () => number;
  getVisibleSuggestions: () => CopilotSuggestion[];
  getSuggestionsByType: (type: CopilotSuggestion['type']) => CopilotSuggestion[];
  getAnalysisScore: () => number | null;
}

const initialState = {
  messages: [],
  isTyping: false,
  currentProjectId: null,
  currentContext: {},
  activeSuggestions: [],
  dismissedSuggestionIds: new Set<string>(),
  appliedSuggestionIds: new Set<string>(),
  projectAnalysis: null,
  isAnalyzing: false,
  quickActions: [],
  isPanelOpen: false,
  isPanelMinimized: false,
  activeTab: 'chat' as const,
  autoSuggest: true,
  suggestionTypes: ['scene', 'shot', 'character', 'dialogue', 'pacing', 'visual'] as Array<
    CopilotSuggestion['type']
  >,
  isLoadingSuggestions: false,
  isSending: false,
  error: null,
};

export const useCopilotStore = create<CopilotStoreState>()(
  devtools(
    persist(
      immer((set, get) => ({
        ...initialState,

        // Chat actions
        addMessage: (message) =>
          set((state) => {
            state.messages.push(message);
          }),

        clearMessages: () =>
          set((state) => {
            state.messages = [];
          }),

        setIsTyping: (typing) =>
          set((state) => {
            state.isTyping = typing;
          }),

        setCurrentProjectId: (projectId) =>
          set((state) => {
            state.currentProjectId = projectId;
            // Clear context when project changes
            if (state.currentProjectId !== projectId) {
              state.currentContext = {};
              state.activeSuggestions = [];
              state.projectAnalysis = null;
            }
          }),

        setCurrentContext: (context) =>
          set((state) => {
            state.currentContext = context;
          }),

        // Suggestion actions
        addSuggestions: (suggestions) =>
          set((state) => {
            // Filter out already applied or dismissed suggestions
            const newSuggestions = suggestions.filter(
              (s) =>
                !state.appliedSuggestionIds.has(s.id) && !state.dismissedSuggestionIds.has(s.id)
            );
            // Merge with existing, avoiding duplicates
            const existingIds = new Set(state.activeSuggestions.map((s) => s.id));
            for (const suggestion of newSuggestions) {
              if (!existingIds.has(suggestion.id)) {
                state.activeSuggestions.push(suggestion);
              }
            }
          }),

        clearSuggestions: () =>
          set((state) => {
            state.activeSuggestions = [];
          }),

        markSuggestionApplied: (suggestionId) =>
          set((state) => {
            state.appliedSuggestionIds.add(suggestionId);
            state.activeSuggestions = state.activeSuggestions.filter((s) => s.id !== suggestionId);
          }),

        markSuggestionDismissed: (suggestionId) =>
          set((state) => {
            state.dismissedSuggestionIds.add(suggestionId);
            state.activeSuggestions = state.activeSuggestions.filter((s) => s.id !== suggestionId);
          }),

        // Analysis actions
        setProjectAnalysis: (analysis) =>
          set((state) => {
            state.projectAnalysis = analysis;
          }),

        setIsAnalyzing: (analyzing) =>
          set((state) => {
            state.isAnalyzing = analyzing;
          }),

        // Quick actions
        setQuickActions: (actions) =>
          set((state) => {
            state.quickActions = actions;
          }),

        // UI actions
        setIsPanelOpen: (open) =>
          set((state) => {
            state.isPanelOpen = open;
          }),

        setIsPanelMinimized: (minimized) =>
          set((state) => {
            state.isPanelMinimized = minimized;
          }),

        setActiveTab: (tab) =>
          set((state) => {
            state.activeTab = tab;
          }),

        togglePanel: () =>
          set((state) => {
            state.isPanelOpen = !state.isPanelOpen;
          }),

        // Settings actions
        setAutoSuggest: (auto) =>
          set((state) => {
            state.autoSuggest = auto;
          }),

        setSuggestionTypes: (types) =>
          set((state) => {
            state.suggestionTypes = types;
          }),

        // Loading state actions
        setLoadingSuggestions: (loading) =>
          set((state) => {
            state.isLoadingSuggestions = loading;
          }),

        setIsSending: (sending) =>
          set((state) => {
            state.isSending = sending;
          }),

        setError: (error) =>
          set((state) => {
            state.error = error;
          }),

        // Async actions
        sendMessage: async (message) => {
          const state = get();
          if (!state.currentProjectId) {
            console.error('No project selected for co-pilot chat');
            return null;
          }

          // Add user message
          const userMessage: CopilotMessage = {
            role: 'user',
            content: message,
            timestamp: new Date().toISOString(),
          };
          set((s) => {
            s.messages.push(userMessage);
            s.isSending = true;
            s.isTyping = true;
            s.error = null;
          });

          try {
            const response = await api.sendCopilotMessage({
              projectId: state.currentProjectId,
              message,
              context: state.currentContext,
            });

            // Add assistant response
            const assistantMessage: CopilotMessage = {
              role: 'assistant',
              content: response.message,
              timestamp: new Date().toISOString(),
            };

            set((s) => {
              s.messages.push(assistantMessage);
              s.isTyping = false;
              s.isSending = false;

              // Add any suggestions from the response
              if (response.suggestions && response.suggestions.length > 0) {
                const existingIds = new Set(s.activeSuggestions.map((sg) => sg.id));
                for (const suggestion of response.suggestions) {
                  if (
                    !existingIds.has(suggestion.id) &&
                    !s.appliedSuggestionIds.has(suggestion.id) &&
                    !s.dismissedSuggestionIds.has(suggestion.id)
                  ) {
                    s.activeSuggestions.push(suggestion);
                  }
                }
              }
            });

            return response;
          } catch (error) {
            console.error('Failed to send co-pilot message:', error);
            set((s) => {
              s.isTyping = false;
              s.isSending = false;
              s.error = 'Failed to send message';
            });
            return null;
          }
        },

        analyzeProject: async (projectId) => {
          set((state) => {
            state.isAnalyzing = true;
            state.error = null;
          });
          try {
            const analysis = await api.getCopilotAnalysis(projectId);
            set((state) => {
              state.projectAnalysis = analysis;
              state.isAnalyzing = false;

              // Add suggestions from analysis
              if (analysis.suggestions && analysis.suggestions.length > 0) {
                const existingIds = new Set(state.activeSuggestions.map((s) => s.id));
                for (const suggestion of analysis.suggestions) {
                  if (
                    !existingIds.has(suggestion.id) &&
                    !state.appliedSuggestionIds.has(suggestion.id) &&
                    !state.dismissedSuggestionIds.has(suggestion.id)
                  ) {
                    state.activeSuggestions.push(suggestion);
                  }
                }
              }
            });
          } catch (error) {
            console.error('Failed to analyze project:', error);
            set((state) => {
              state.isAnalyzing = false;
              state.error = 'Failed to analyze project';
            });
          }
        },

        fetchSceneSuggestions: async (projectId, sceneId) => {
          set((state) => {
            state.isLoadingSuggestions = true;
          });
          try {
            const suggestions = await api.getCopilotSceneSuggestions(projectId, sceneId);
            set((state) => {
              state.isLoadingSuggestions = false;
              const existingIds = new Set(state.activeSuggestions.map((s) => s.id));
              for (const suggestion of suggestions) {
                if (
                  !existingIds.has(suggestion.id) &&
                  !state.appliedSuggestionIds.has(suggestion.id) &&
                  !state.dismissedSuggestionIds.has(suggestion.id)
                ) {
                  state.activeSuggestions.push(suggestion);
                }
              }
            });
          } catch (error) {
            console.error('Failed to fetch scene suggestions:', error);
            set((state) => {
              state.isLoadingSuggestions = false;
            });
          }
        },

        fetchShotSuggestions: async (projectId, shotId) => {
          set((state) => {
            state.isLoadingSuggestions = true;
          });
          try {
            const suggestions = await api.getCopilotShotSuggestions(projectId, shotId);
            set((state) => {
              state.isLoadingSuggestions = false;
              const existingIds = new Set(state.activeSuggestions.map((s) => s.id));
              for (const suggestion of suggestions) {
                if (
                  !existingIds.has(suggestion.id) &&
                  !state.appliedSuggestionIds.has(suggestion.id) &&
                  !state.dismissedSuggestionIds.has(suggestion.id)
                ) {
                  state.activeSuggestions.push(suggestion);
                }
              }
            });
          } catch (error) {
            console.error('Failed to fetch shot suggestions:', error);
            set((state) => {
              state.isLoadingSuggestions = false;
            });
          }
        },

        applySuggestion: async (projectId, suggestionId) => {
          try {
            const result = await api.applyCopilotSuggestion(projectId, suggestionId);
            if (result.success) {
              set((state) => {
                state.appliedSuggestionIds.add(suggestionId);
                state.activeSuggestions = state.activeSuggestions.filter(
                  (s) => s.id !== suggestionId
                );
              });
            }
            return result.success;
          } catch (error) {
            console.error('Failed to apply suggestion:', error);
            return false;
          }
        },

        dismissSuggestion: async (projectId, suggestionId) => {
          try {
            const result = await api.dismissCopilotSuggestion(projectId, suggestionId);
            if (result.success) {
              set((state) => {
                state.dismissedSuggestionIds.add(suggestionId);
                state.activeSuggestions = state.activeSuggestions.filter(
                  (s) => s.id !== suggestionId
                );
              });
            }
            return result.success;
          } catch (error) {
            console.error('Failed to dismiss suggestion:', error);
            return false;
          }
        },

        fetchQuickActions: async () => {
          const state = get();
          if (!state.currentProjectId) return;

          try {
            const actions = await api.getCopilotQuickActions({
              projectId: state.currentProjectId,
              sceneId: state.currentContext.sceneId,
              shotId: state.currentContext.shotId,
            });
            set((s) => {
              s.quickActions = actions;
            });
          } catch (error) {
            console.error('Failed to fetch quick actions:', error);
          }
        },

        // Computed helpers
        getUnreadSuggestionCount: () => {
          return get().activeSuggestions.length;
        },

        getVisibleSuggestions: () => {
          const state = get();
          return state.activeSuggestions.filter((s) => state.suggestionTypes.includes(s.type));
        },

        getSuggestionsByType: (type) => {
          return get().activeSuggestions.filter((s) => s.type === type);
        },

        getAnalysisScore: () => {
          return get().projectAnalysis?.overallScore ?? null;
        },
      })),
      {
        name: 'scenemachine-copilot-store',
        partialize: (state) => ({
          // Persist UI preferences and settings
          isPanelOpen: state.isPanelOpen,
          isPanelMinimized: state.isPanelMinimized,
          activeTab: state.activeTab,
          autoSuggest: state.autoSuggest,
          suggestionTypes: state.suggestionTypes,
          // Persist dismissed suggestions to avoid re-showing them
          dismissedSuggestionIds: Array.from(state.dismissedSuggestionIds),
          appliedSuggestionIds: Array.from(state.appliedSuggestionIds),
        }),
        // Custom merge to handle Set conversion
        merge: (persisted, current) => {
          const persistedState = persisted as Partial<CopilotStoreState> & {
            dismissedSuggestionIds?: string[];
            appliedSuggestionIds?: string[];
          };
          return {
            ...current,
            ...persistedState,
            dismissedSuggestionIds: new Set(persistedState.dismissedSuggestionIds || []),
            appliedSuggestionIds: new Set(persistedState.appliedSuggestionIds || []),
          };
        },
      }
    ),
    { name: 'CopilotStore' }
  )
);

/**
 * Hook to check if the co-pilot has pending suggestions.
 */
export function useHasPendingSuggestions(): boolean {
  return useCopilotStore((state) => state.activeSuggestions.length > 0);
}

/**
 * Hook to get the project analysis score as a percentage.
 */
export function useAnalysisScorePercentage(): number | null {
  return useCopilotStore((state) =>
    state.projectAnalysis ? Math.round(state.projectAnalysis.overallScore * 100) : null
  );
}

/**
 * Hook to check if co-pilot is ready (has a project selected).
 */
export function useCopilotReady(): boolean {
  return useCopilotStore((state) => state.currentProjectId !== null);
}

/**
 * Hook to get high-confidence suggestions only.
 */
export function useHighConfidenceSuggestions(): CopilotSuggestion[] {
  return useCopilotStore((state) => state.activeSuggestions.filter((s) => s.confidence >= 0.8));
}

/**
 * Hook to get the weakest area from analysis.
 */
export function useWeakestArea(): { area: string; score: number } | null {
  return useCopilotStore((state) => {
    const analysis = state.projectAnalysis;
    if (!analysis) return null;

    const areas = [
      { area: 'pacing', score: analysis.pacing.score },
      { area: 'characterDevelopment', score: analysis.characterDevelopment.score },
      { area: 'visualStorytelling', score: analysis.visualStorytelling.score },
      { area: 'dialogue', score: analysis.dialogue.score },
    ];

    return areas.reduce((min, current) => (current.score < min.score ? current : min));
  });
}
