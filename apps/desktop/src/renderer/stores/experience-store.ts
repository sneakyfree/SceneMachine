/**
 * Experience Mode Store
 *
 * Manages the user's experience level preference across the application.
 * Supports three modes: Story (beginner), Creator (intermediate), Pro (advanced)
 * with per-feature overrides capability.
 */

import { create } from 'zustand';
import { devtools, persist } from 'zustand/middleware';
import { immer } from 'zustand/middleware/immer';

// Experience mode levels
export type ExperienceMode = 'story' | 'creator' | 'pro';

// Features that can have mode overrides
export type FeatureArea =
  | 'screenplay'
  | 'characters'
  | 'scenes'
  | 'generation'
  | 'timeline'
  | 'export'
  | 'settings';

// Mode descriptions for UI
export const MODE_INFO: Record<ExperienceMode, {
  name: string;
  shortName: string;
  description: string;
  icon: string;
  color: string;
}> = {
  story: {
    name: 'Story Mode',
    shortName: 'Story',
    description: 'Guided experience with maximum AI assistance. Perfect for first-time users.',
    icon: 'wand-2',
    color: 'green',
  },
  creator: {
    name: 'Creator Mode',
    shortName: 'Creator',
    description: 'Balanced controls with helpful tooltips. Great for hobbyists and YouTubers.',
    icon: 'palette',
    color: 'blue',
  },
  pro: {
    name: 'Pro Mode',
    shortName: 'Pro',
    description: 'Full technical controls for industry professionals. Maximum customization.',
    icon: 'settings-2',
    color: 'purple',
  },
};

// Plain English translations for technical terms
export const FRIENDLY_TERMS: Record<string, Record<ExperienceMode, string>> = {
  // Resolution
  '720p': {
    story: 'Good Quality',
    creator: 'HD (720p)',
    pro: '1280×720 (720p)',
  },
  '1080p': {
    story: 'Great Quality (Looks great on any TV)',
    creator: 'Full HD (1080p)',
    pro: '1920×1080 (1080p)',
  },
  '1440p': {
    story: 'Excellent Quality',
    creator: '2K (1440p)',
    pro: '2560×1440 (1440p)',
  },
  '2160p': {
    story: 'Best Quality (Perfect for big screens)',
    creator: '4K Ultra HD',
    pro: '3840×2160 (4K UHD)',
  },

  // Frame rates
  '24fps': {
    story: 'Cinematic (Movie-like)',
    creator: '24 fps (Cinematic)',
    pro: '24 fps (23.976)',
  },
  '30fps': {
    story: 'Standard (Smooth)',
    creator: '30 fps (Standard)',
    pro: '30 fps (29.97)',
  },
  '60fps': {
    story: 'Ultra Smooth',
    creator: '60 fps (Smooth)',
    pro: '60 fps (59.94)',
  },

  // Formats
  'h264': {
    story: 'Universal (Plays everywhere)',
    creator: 'MP4 (H.264)',
    pro: 'H.264/AVC MP4',
  },
  'h265': {
    story: 'Compact (Same quality, smaller file)',
    creator: 'MP4 (H.265)',
    pro: 'H.265/HEVC MP4',
  },
  'prores': {
    story: 'Professional (For editing)',
    creator: 'ProRes (Professional)',
    pro: 'Apple ProRes 422',
  },
  'webm': {
    story: 'Web-Ready (For websites)',
    creator: 'WebM (Web)',
    pro: 'VP9 WebM',
  },

  // Queue/Generation statuses
  'queued': {
    story: 'Waiting in line',
    creator: 'Queued',
    pro: 'Queued (pending)',
  },
  'pending': {
    story: 'Waiting in line',
    creator: 'Pending',
    pro: 'Pending',
  },
  'preparing': {
    story: 'Getting ready...',
    creator: 'Preparing',
    pro: 'Preparing',
  },
  'running': {
    story: 'Creating your video...',
    creator: 'Generating',
    pro: 'Running',
  },
  'processing': {
    story: 'Creating your video...',
    creator: 'Generating',
    pro: 'Processing',
  },
  'post_processing': {
    story: 'Almost done...',
    creator: 'Finishing up',
    pro: 'Post-processing',
  },
  'completed': {
    story: 'Done!',
    creator: 'Completed',
    pro: 'Completed',
  },
  'failed': {
    story: 'Something went wrong',
    creator: 'Failed',
    pro: 'Failed',
  },
  'timeout': {
    story: 'Took too long, will try again',
    creator: 'Timed out',
    pro: 'Timeout',
  },
  'cancelled': {
    story: 'Stopped',
    creator: 'Cancelled',
    pro: 'Cancelled',
  },

  // Provider names
  'replicate': {
    story: 'Cloud Processing',
    creator: 'Replicate',
    pro: 'Replicate API',
  },
  'fal': {
    story: 'Fast Cloud',
    creator: 'Fal.ai',
    pro: 'Fal.ai API',
  },
  'comfyui-local': {
    story: 'Your Computer',
    creator: 'Local (ComfyUI)',
    pro: 'ComfyUI Local',
  },
  'comfyui_local': {
    story: 'Your Computer',
    creator: 'Local (ComfyUI)',
    pro: 'ComfyUI Local',
  },
  'runpod-serverless': {
    story: 'GPU Cloud',
    creator: 'RunPod',
    pro: 'RunPod Serverless',
  },
  'runpod_serverless': {
    story: 'GPU Cloud',
    creator: 'RunPod',
    pro: 'RunPod Serverless',
  },
  'local': {
    story: 'Your Computer',
    creator: 'Local',
    pro: 'Local',
  },
  'mock': {
    story: 'Preview Mode',
    creator: 'Mock (Testing)',
    pro: 'Mock Provider',
  },

  // Provider status / Circuit breaker
  'circuit_open': {
    story: 'Taking a short break, will try again soon',
    creator: 'Temporarily unavailable',
    pro: 'Circuit breaker: OPEN',
  },
  'circuit_closed': {
    story: 'Ready to go!',
    creator: 'Available',
    pro: 'Circuit breaker: CLOSED',
  },
  'circuit_half_open': {
    story: 'Testing connection...',
    creator: 'Recovering',
    pro: 'Circuit breaker: HALF_OPEN',
  },

  // Character workflow
  'lock': {
    story: 'Save Look',
    creator: 'Lock Appearance',
    pro: 'Lock Character',
  },
  'locked': {
    story: 'Look Saved',
    creator: 'Locked',
    pro: 'Locked',
  },
  'unlock': {
    story: 'Change Look',
    creator: 'Unlock',
    pro: 'Unlock',
  },
  'unlocked': {
    story: 'Ready to Edit',
    creator: 'Unlocked',
    pro: 'Unlocked',
  },
  'finalize': {
    story: 'Save Appearance',
    creator: 'Finalize',
    pro: 'Finalize',
  },

  // Shot types
  'wide': {
    story: 'Full Scene View',
    creator: 'Wide Shot',
    pro: 'Wide',
  },
  'medium': {
    story: 'Good Quality',
    creator: 'Medium Quality',
    pro: 'Medium (balanced)',
  },
  'medium_shot': {
    story: 'Character View',
    creator: 'Medium Shot',
    pro: 'Medium Shot',
  },
  'close_up': {
    story: 'Face Close-Up',
    creator: 'Close-Up',
    pro: 'CU',
  },
  'extreme_close_up': {
    story: 'Detail Shot',
    creator: 'Extreme Close-Up',
    pro: 'ECU',
  },
  'ots': {
    story: 'Over Shoulder',
    creator: 'Over-the-Shoulder',
    pro: 'OTS',
  },
  'over_the_shoulder': {
    story: 'Over Shoulder',
    creator: 'Over-the-Shoulder',
    pro: 'OTS',
  },
  'pov': {
    story: 'First Person View',
    creator: 'Point of View',
    pro: 'POV',
  },
  'point_of_view': {
    story: 'First Person View',
    creator: 'Point of View',
    pro: 'POV',
  },
  'dutch_angle': {
    story: 'Tilted Camera',
    creator: 'Dutch Angle',
    pro: 'Dutch Angle',
  },
  'establishing': {
    story: 'Scene Opener',
    creator: 'Establishing Shot',
    pro: 'Establishing',
  },
  'two_shot': {
    story: 'Two People',
    creator: 'Two Shot',
    pro: '2-Shot',
  },
  'group_shot': {
    story: 'Group View',
    creator: 'Group Shot',
    pro: 'Group Shot',
  },
  'insert': {
    story: 'Detail Close-Up',
    creator: 'Insert Shot',
    pro: 'Insert',
  },
  'aerial': {
    story: 'Bird\'s Eye View',
    creator: 'Aerial Shot',
    pro: 'Aerial',
  },
  'tracking': {
    story: 'Moving Camera',
    creator: 'Tracking Shot',
    pro: 'Tracking',
  },
  'dolly': {
    story: 'Smooth Move',
    creator: 'Dolly Shot',
    pro: 'Dolly',
  },
  'crane': {
    story: 'Rising Shot',
    creator: 'Crane Shot',
    pro: 'Crane',
  },
  'handheld': {
    story: 'Natural Feel',
    creator: 'Handheld',
    pro: 'Handheld',
  },
  'static': {
    story: 'Still Camera',
    creator: 'Static Shot',
    pro: 'Static',
  },

  // Camera movements
  'pan': {
    story: 'Camera Looks Left/Right',
    creator: 'Pan',
    pro: 'Pan',
  },
  'tilt': {
    story: 'Camera Looks Up/Down',
    creator: 'Tilt',
    pro: 'Tilt',
  },
  'zoom': {
    story: 'Zoom In/Out',
    creator: 'Zoom',
    pro: 'Zoom',
  },
  'push_in': {
    story: 'Camera Moves Closer',
    creator: 'Push In',
    pro: 'Push In',
  },
  'pull_out': {
    story: 'Camera Moves Away',
    creator: 'Pull Out',
    pro: 'Pull Out',
  },

  // Quality
  'low': {
    story: 'Quick Preview',
    creator: 'Low Quality',
    pro: 'Low (faster)',
  },
  'high': {
    story: 'Great Quality',
    creator: 'High Quality',
    pro: 'High (slower)',
  },
  'cinema': {
    story: 'Best Quality (Movie theater ready)',
    creator: 'Cinema Quality',
    pro: 'Cinema (maximum)',
  },

  // Priority levels
  'urgent': {
    story: 'Do First!',
    creator: 'Urgent',
    pro: 'Urgent (P0)',
  },
  'priority_high': {
    story: 'Important',
    creator: 'High Priority',
    pro: 'High (P1)',
  },
  'priority_normal': {
    story: 'Normal',
    creator: 'Normal Priority',
    pro: 'Normal (P2)',
  },
  'priority_low': {
    story: 'Can Wait',
    creator: 'Low Priority',
    pro: 'Low (P3)',
  },

  // Workflow steps
  'screenplay_upload': {
    story: 'Add Your Script',
    creator: 'Upload Screenplay',
    pro: 'Upload Screenplay',
  },
  'movie_plan': {
    story: 'AI Plans Your Movie',
    creator: 'Movie Plan',
    pro: 'Movie Plan Generation',
  },
  'character_lab': {
    story: 'Design Characters',
    creator: 'Character Lab',
    pro: 'Character Lab',
  },
  'scene_planning': {
    story: 'Plan Each Scene',
    creator: 'Scene Planning',
    pro: 'Scene Breakdown',
  },
  'generation': {
    story: 'Create Videos',
    creator: 'Generation',
    pro: 'Video Generation',
  },
  'export': {
    story: 'Save Your Movie',
    creator: 'Export',
    pro: 'Export',
  },

  // Misc UI terms
  'approve': {
    story: 'Looks Good!',
    creator: 'Approve',
    pro: 'Approve',
  },
  'reject': {
    story: 'Try Again',
    creator: 'Reject',
    pro: 'Reject',
  },
  'regenerate': {
    story: 'Make a New One',
    creator: 'Regenerate',
    pro: 'Regenerate',
  },
  'retry': {
    story: 'Try Again',
    creator: 'Retry',
    pro: 'Retry',
  },
  'cancel': {
    story: 'Stop',
    creator: 'Cancel',
    pro: 'Cancel',
  },
  'skip': {
    story: 'Skip for Now',
    creator: 'Skip',
    pro: 'Skip',
  },
};

// Steven's contextual messages for different situations
export const STEVEN_MESSAGES = {
  welcome: [
    "Hey there! I'm Steven, your director's assistant. Ready to make a movie together?",
    "Welcome back! I've been keeping your project warm. Ready to continue?",
  ],
  uploadScript: [
    "Just drag your screenplay file here - I can read Fountain, Final Draft, or even PDF files.",
    "Got a script? Drop it right here and I'll start reading it immediately.",
  ],
  charactersFound: (count: number) =>
    `Great script! I found ${count} characters. Let's bring them to life with descriptions and voices.`,
  scenesReady: (count: number) =>
    `I've broken down your screenplay into ${count} scenes. Want me to plan the camera shots?`,
  generationStarted:
    "Alright, I'm sending your shots to our video creators. I'll keep you updated on progress!",
  generationComplete:
    "Your scenes are ready! Take a look and let me know if you want any changes.",
  error: (message: string) =>
    `Hmm, we hit a snag: ${message}. Don't worry, I can help you fix this.`,
  celebration: [
    "Your movie is done! Time to share it with the world!",
    "Another masterpiece in the making! Great work!",
  ],
  idle: [
    "I'm here if you need any help. Just ask!",
    "Take your time. I'll be right here when you're ready.",
    "Looking good so far! What would you like to work on next?",
  ],
};

interface ExperienceStoreState {
  // Global mode setting
  globalMode: ExperienceMode;

  // Per-feature overrides (null means use global)
  featureOverrides: Partial<Record<FeatureArea, ExperienceMode>>;

  // Remember preference globally
  rememberGlobal: boolean;

  // Steven Assistant state
  stevenEnabled: boolean;
  stevenMinimized: boolean;
  stevenLastMessage: string | null;
  stevenMessageHistory: Array<{
    message: string;
    timestamp: number;
    type: 'info' | 'success' | 'warning' | 'celebration';
  }>;

  // Actions
  setGlobalMode: (mode: ExperienceMode) => void;
  setFeatureMode: (feature: FeatureArea, mode: ExperienceMode | null) => void;
  getEffectiveMode: (feature?: FeatureArea) => ExperienceMode;
  resetFeatureOverrides: () => void;

  // Steven actions
  setStevenEnabled: (enabled: boolean) => void;
  setStevenMinimized: (minimized: boolean) => void;
  sendStevenMessage: (message: string, type?: 'info' | 'success' | 'warning' | 'celebration') => void;
  clearStevenHistory: () => void;

  // Helper functions
  getTerm: (technicalTerm: string, feature?: FeatureArea) => string;
  isSimplifiedMode: (feature?: FeatureArea) => boolean;
  shouldShowTechnical: (feature?: FeatureArea) => boolean;
  shouldShowSteven: () => boolean;
}

export const useExperienceStore = create<ExperienceStoreState>()(
  devtools(
    persist(
      immer((set, get) => ({
        // Initial state
        globalMode: 'creator',
        featureOverrides: {},
        rememberGlobal: true,
        stevenEnabled: true,
        stevenMinimized: false,
        stevenLastMessage: null,
        stevenMessageHistory: [],

        // Set global mode
        setGlobalMode: (mode) => set((state) => {
          state.globalMode = mode;
          // Clear overrides if remembering globally
          if (state.rememberGlobal) {
            state.featureOverrides = {};
          }
        }),

        // Set per-feature mode override
        setFeatureMode: (feature, mode) => set((state) => {
          if (mode === null) {
            delete state.featureOverrides[feature];
          } else {
            state.featureOverrides[feature] = mode;
          }
        }),

        // Get the effective mode for a feature
        getEffectiveMode: (feature) => {
          const state = get();
          if (feature && state.featureOverrides[feature]) {
            return state.featureOverrides[feature]!;
          }
          return state.globalMode;
        },

        // Reset all feature overrides
        resetFeatureOverrides: () => set((state) => {
          state.featureOverrides = {};
        }),

        // Steven controls
        setStevenEnabled: (enabled) => set((state) => {
          state.stevenEnabled = enabled;
        }),

        setStevenMinimized: (minimized) => set((state) => {
          state.stevenMinimized = minimized;
        }),

        sendStevenMessage: (message, type = 'info') => set((state) => {
          state.stevenLastMessage = message;
          state.stevenMessageHistory.push({
            message,
            timestamp: Date.now(),
            type,
          });
          // Keep only last 50 messages
          if (state.stevenMessageHistory.length > 50) {
            state.stevenMessageHistory = state.stevenMessageHistory.slice(-50);
          }
        }),

        clearStevenHistory: () => set((state) => {
          state.stevenMessageHistory = [];
          state.stevenLastMessage = null;
        }),

        // Get user-friendly term based on current mode
        getTerm: (technicalTerm, feature) => {
          const mode = get().getEffectiveMode(feature);
          const termMap = FRIENDLY_TERMS[technicalTerm.toLowerCase()];
          if (termMap) {
            return termMap[mode];
          }
          // If no translation, return original in non-story modes
          if (mode === 'story') {
            // Try to make it more friendly
            return technicalTerm
              .replace(/_/g, ' ')
              .replace(/([a-z])([A-Z])/g, '$1 $2')
              .toLowerCase();
          }
          return technicalTerm;
        },

        // Check if we're in a simplified mode
        isSimplifiedMode: (feature) => {
          return get().getEffectiveMode(feature) === 'story';
        },

        // Check if technical details should be shown
        shouldShowTechnical: (feature) => {
          const mode = get().getEffectiveMode(feature);
          return mode === 'pro' || mode === 'creator';
        },

        // Check if Steven should be visible
        shouldShowSteven: () => {
          const state = get();
          return state.stevenEnabled && !state.stevenMinimized;
        },
      })),
      {
        name: 'scenemachine-experience-store',
        partialize: (state) => ({
          globalMode: state.globalMode,
          featureOverrides: state.featureOverrides,
          rememberGlobal: state.rememberGlobal,
          stevenEnabled: state.stevenEnabled,
          stevenMinimized: state.stevenMinimized,
        }),
      }
    ),
    { name: 'ExperienceStore' }
  )
);

// Hook for easy access to current mode info
export function useExperienceMode(feature?: FeatureArea) {
  const store = useExperienceStore();
  const mode = store.getEffectiveMode(feature);
  const info = MODE_INFO[mode];

  return {
    mode,
    info,
    isStory: mode === 'story',
    isCreator: mode === 'creator',
    isPro: mode === 'pro',
    getTerm: (term: string) => store.getTerm(term, feature),
    shouldShowTechnical: store.shouldShowTechnical(feature),
  };
}
