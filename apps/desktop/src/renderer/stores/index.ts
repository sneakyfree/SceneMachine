/**
 * Central export for all Zustand stores.
 */

// Core stores
export { useProjectStore } from './project-store';
export {
  useSettingsStore,
  type UserSettings,
  type FontSizeScale,
  type ProviderStatus,
  type StorageStats,
  type ProviderOption,
} from './settings-store';
export {
  useToastStore,
  useToast,
  type Toast,
  type ToastType,
} from './toast-store';

// Workflow stores
export {
  useScreenplayStore,
  useScreenplayStage,
  useScreenplayProcessing,
} from './screenplay-store';
export {
  useCharacterStore,
  useLockedCharacterCount,
  useAllCharactersLocked,
  useCharacterCompletion,
} from './character-store';
export {
  useSceneStore,
  useSceneProgress,
  useAllScenesGenerated,
  useSceneByNumber,
} from './scene-store';
export {
  useShotStore,
  useShotStats,
  useSceneShotsApproved,
  useNextShotToReview,
} from './shot-store';

// Generation & Assembly stores
export {
  useGenerationStore,
  useCurrentModel,
  useGenerationReady,
} from './generation-store';
export {
  useAssemblyStore,
  useAssemblyReadiness,
  useExportConfig,
  useIsExporting,
} from './assembly-store';

// Audio store
export {
  useAudioStore,
  type Voice,
  type TTSProvider,
  type CharacterVoice,
  type SpeechResult,
} from './audio-store';

// Feature stores
export {
  useSharingStore,
  useShareCount,
  useUnresolvedCommentCount,
} from './sharing-store';
export {
  useExperienceStore,
  useExperienceMode,
  type ExperienceMode,
  type FeatureArea,
  MODE_INFO,
  FRIENDLY_TERMS,
  STEVEN_MESSAGES,
} from './experience-store';
export {
  useCopilotStore,
  useHasPendingSuggestions,
  useAnalysisScorePercentage,
  useCopilotReady,
  useHighConfidenceSuggestions,
  useWeakestArea,
} from './copilot-store';

// ActForge stores
export {
  useActForgeStore,
  useACIBadgeColor,
  useRevenueTierLabel,
  useBookingModeInfo,
} from './actforge-store';

// GPU Exchange store
export {
  useGPUExchangeStore,
  useCheapestProvider,
  useFastestProvider,
  useHasAvailableProviders,
  useGPUTypeOptions,
} from './gpu-exchange-store';

// Auth store (wired to backend)
export {
  useAuthStore,
  useUser,
  useIsAuthenticated,
  useAuthLoading,
  useAuthError,
} from './auth-store';

// Asset store (wired to backend)
export { useAssetStore } from './asset-store';
export type { Asset } from './asset-store';

// Timeline store (wired to backend)
export { useTimelineStore } from './timeline-store';
export type { Track, Clip } from './timeline-store';
