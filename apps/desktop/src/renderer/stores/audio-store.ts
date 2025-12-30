/**
 * Audio/Voice state store using Zustand.
 * Manages TTS providers, voices, and character voice assignments.
 */

import { create } from 'zustand';
import { devtools } from 'zustand/middleware';
import { immer } from 'zustand/middleware/immer';

// Voice information
export interface Voice {
  id: string;
  name: string;
  provider: string;
  gender?: string;
  language?: string;
  preview_url?: string;
  labels?: Record<string, string>;
}

// TTS Provider information
export interface TTSProvider {
  id: string;
  name: string;
  available: boolean;
  voices_count: number;
  requires_api_key: boolean;
  description: string;
}

// Character voice assignment
export interface CharacterVoice {
  character_id: string;
  character_name: string;
  voice_id: string | null;
  voice_name: string | null;
  provider: string | null;
}

// Speech generation result
export interface SpeechResult {
  audio_path: string;
  duration_seconds: number;
  provider: string;
  voice_id: string;
}

interface AudioStoreState {
  // Data
  providers: TTSProvider[];
  voices: Voice[];
  characterVoices: Record<string, CharacterVoice>;
  selectedProvider: string;

  // Loading states
  isLoadingProviders: boolean;
  isLoadingVoices: boolean;
  isGenerating: boolean;

  // Preview state
  previewAudioUrl: string | null;
  previewPlaying: boolean;

  // Error state
  error: string | null;

  // Actions
  setProviders: (providers: TTSProvider[]) => void;
  setVoices: (voices: Voice[]) => void;
  setSelectedProvider: (provider: string) => void;
  setCharacterVoice: (characterId: string, voice: CharacterVoice) => void;
  setPreviewAudioUrl: (url: string | null) => void;
  setPreviewPlaying: (playing: boolean) => void;
  setError: (error: string | null) => void;
  reset: () => void;

  // Async actions
  fetchProviders: () => Promise<void>;
  fetchVoices: (provider?: string) => Promise<void>;
  assignVoice: (characterId: string, voiceId: string, provider: string) => Promise<void>;
  getCharacterVoice: (characterId: string) => Promise<CharacterVoice | null>;
  generateSpeech: (text: string, voiceId: string, provider?: string) => Promise<SpeechResult>;
  previewVoice: (voiceId: string, provider: string, sampleText?: string) => Promise<void>;
}

const initialState = {
  providers: [],
  voices: [],
  characterVoices: {},
  selectedProvider: 'mock',
  isLoadingProviders: false,
  isLoadingVoices: false,
  isGenerating: false,
  previewAudioUrl: null,
  previewPlaying: false,
  error: null,
};

export const useAudioStore = create<AudioStoreState>()(
  devtools(
    immer((set, get) => ({
      ...initialState,

      setProviders: (providers) =>
        set((state) => {
          state.providers = providers;
        }),

      setVoices: (voices) =>
        set((state) => {
          state.voices = voices;
        }),

      setSelectedProvider: (provider) =>
        set((state) => {
          state.selectedProvider = provider;
        }),

      setCharacterVoice: (characterId, voice) =>
        set((state) => {
          state.characterVoices[characterId] = voice;
        }),

      setPreviewAudioUrl: (url) =>
        set((state) => {
          state.previewAudioUrl = url;
        }),

      setPreviewPlaying: (playing) =>
        set((state) => {
          state.previewPlaying = playing;
        }),

      setError: (error) =>
        set((state) => {
          state.error = error;
        }),

      reset: () => set(initialState),

      // Async actions
      fetchProviders: async () => {
        set((state) => {
          state.isLoadingProviders = true;
          state.error = null;
        });

        try {
          const providers = await window.electronAPI.backendRequest<TTSProvider[]>(
            'audio.getProviders',
            {}
          );
          set((state) => {
            state.providers = providers;
            state.isLoadingProviders = false;
            // Set first available provider as default if current is not available
            const currentAvailable = providers.find(
              (p) => p.id === state.selectedProvider && p.available
            );
            if (!currentAvailable) {
              const firstAvailable = providers.find((p) => p.available);
              if (firstAvailable) {
                state.selectedProvider = firstAvailable.id;
              }
            }
          });
        } catch (error) {
          set((state) => {
            state.error = error instanceof Error ? error.message : 'Failed to fetch TTS providers';
            state.isLoadingProviders = false;
          });
        }
      },

      fetchVoices: async (provider?: string) => {
        const providerToUse = provider || get().selectedProvider;

        set((state) => {
          state.isLoadingVoices = true;
          state.error = null;
        });

        try {
          const voices = await window.electronAPI.backendRequest<Voice[]>('audio.getVoices', {
            provider: providerToUse,
          });
          set((state) => {
            state.voices = voices;
            state.isLoadingVoices = false;
          });
        } catch (error) {
          set((state) => {
            state.error = error instanceof Error ? error.message : 'Failed to fetch voices';
            state.isLoadingVoices = false;
          });
        }
      },

      assignVoice: async (characterId, voiceId, provider) => {
        try {
          const result = await window.electronAPI.backendRequest<CharacterVoice>(
            'audio.assignVoice',
            {
              character_id: characterId,
              voice_id: voiceId,
              provider,
            }
          );
          set((state) => {
            state.characterVoices[characterId] = result;
          });
        } catch (error) {
          set((state) => {
            state.error = error instanceof Error ? error.message : 'Failed to assign voice';
          });
          throw error;
        }
      },

      getCharacterVoice: async (characterId) => {
        try {
          const result = await window.electronAPI.backendRequest<CharacterVoice | null>(
            'audio.getCharacterVoice',
            { character_id: characterId }
          );
          if (result) {
            set((state) => {
              state.characterVoices[characterId] = result;
            });
          }
          return result;
        } catch (error) {
          console.error('Failed to get character voice:', error);
          return null;
        }
      },

      generateSpeech: async (text, voiceId, provider) => {
        const providerToUse = provider || get().selectedProvider;

        set((state) => {
          state.isGenerating = true;
          state.error = null;
        });

        try {
          const result = await window.electronAPI.backendRequest<SpeechResult>(
            'audio.generateSpeech',
            {
              text,
              voice_id: voiceId,
              provider: providerToUse,
            }
          );
          set((state) => {
            state.isGenerating = false;
          });
          return result;
        } catch (error) {
          set((state) => {
            state.error = error instanceof Error ? error.message : 'Failed to generate speech';
            state.isGenerating = false;
          });
          throw error;
        }
      },

      previewVoice: async (voiceId, provider, sampleText) => {
        const text = sampleText || 'Hello, this is a preview of my voice.';

        set((state) => {
          state.isGenerating = true;
          state.previewAudioUrl = null;
          state.error = null;
        });

        try {
          const result = await window.electronAPI.backendRequest<SpeechResult>(
            'audio.generateSpeech',
            {
              text,
              voice_id: voiceId,
              provider,
            }
          );
          set((state) => {
            state.previewAudioUrl = `file://${result.audio_path}`;
            state.isGenerating = false;
          });
        } catch (error) {
          set((state) => {
            state.error = error instanceof Error ? error.message : 'Failed to preview voice';
            state.isGenerating = false;
          });
        }
      },
    })),
    { name: 'AudioStore' }
  )
);
