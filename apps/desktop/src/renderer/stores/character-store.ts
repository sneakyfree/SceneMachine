/**
 * Character state store using Zustand.
 *
 * Manages character data, references, locking, and voice assignments.
 */

import { create } from 'zustand';
import { devtools } from 'zustand/middleware';
import { immer } from 'zustand/middleware/immer';
import {
  api,
  type Character,
  type CharacterReference,
  type CharacterUpdateRequest,
  type GeneratedCharacterDescription,
  type CharacterPrompt,
} from '../api/client';

interface CharacterStoreState {
  // Characters list
  characters: Character[];
  characterMap: Record<string, Character>;

  // Currently selected/edited character
  selectedCharacterId: string | null;
  selectedCharacter: Character | null;

  // Reference upload state
  isUploadingReference: boolean;
  uploadProgress: number;

  // Generation state
  isGeneratingDescription: boolean;

  // Loading states
  isLoading: boolean;
  isUpdating: string | null; // character ID being updated
  error: string | null;

  // Actions - State setters
  setCharacters: (characters: Character[]) => void;
  setSelectedCharacterId: (id: string | null) => void;
  setError: (error: string | null) => void;

  // Async actions - List & Get
  fetchCharacters: (projectId: string) => Promise<Character[]>;
  fetchCharacter: (characterId: string) => Promise<Character | null>;

  // Async actions - Update
  updateCharacter: (characterId: string, data: CharacterUpdateRequest) => Promise<boolean>;

  // Async actions - Description generation
  generateDescription: (characterId: string) => Promise<GeneratedCharacterDescription | null>;

  // Async actions - References
  uploadReference: (
    characterId: string,
    filePath: string,
    filename: string,
    isPrimary?: boolean
  ) => Promise<CharacterReference | null>;
  deleteReference: (characterId: string, assetId: string) => Promise<boolean>;

  // Async actions - Locking
  lockCharacter: (characterId: string, primaryReferenceId?: string) => Promise<boolean>;
  unlockCharacter: (characterId: string) => Promise<boolean>;

  // Async actions - Voice
  updateVoice: (
    characterId: string,
    voiceId: string,
    voiceProvider: string,
    voiceName: string
  ) => Promise<boolean>;

  // Async actions - Prompts
  getPrompt: (characterId: string, sceneContext?: string) => Promise<CharacterPrompt | null>;

  // Computed helpers
  getCharacterById: (id: string) => Character | undefined;
  getLockedCharacters: () => Character[];
  getUnlockedCharacters: () => Character[];
  getCharactersWithVoice: () => Character[];
  getCharactersNeedingVoice: () => Character[];

  // Reset
  reset: () => void;
}

const initialState = {
  characters: [],
  characterMap: {},
  selectedCharacterId: null,
  selectedCharacter: null,
  isUploadingReference: false,
  uploadProgress: 0,
  isGeneratingDescription: false,
  isLoading: false,
  isUpdating: null,
  error: null,
};

export const useCharacterStore = create<CharacterStoreState>()(
  devtools(
    immer((set, get) => ({
      ...initialState,

      // State setters
      setCharacters: (characters) =>
        set((state) => {
          state.characters = characters;
          state.characterMap = {};
          characters.forEach((c) => {
            state.characterMap[c.id] = c;
          });
        }),

      setSelectedCharacterId: (id) =>
        set((state) => {
          state.selectedCharacterId = id;
          state.selectedCharacter = id ? (state.characterMap[id] ?? null) : null;
        }),

      setError: (error) =>
        set((state) => {
          state.error = error;
        }),

      // Async actions - List & Get
      fetchCharacters: async (projectId) => {
        set((state) => {
          state.isLoading = true;
          state.error = null;
        });
        try {
          const characters = await api.listCharacters(projectId);
          set((state) => {
            state.characters = characters;
            state.characterMap = {};
            characters.forEach((c) => {
              state.characterMap[c.id] = c;
            });
            state.isLoading = false;
          });
          return characters;
        } catch (error) {
          console.error('Failed to fetch characters:', error);
          set((state) => {
            state.isLoading = false;
            state.error = 'Failed to fetch characters';
          });
          return [];
        }
      },

      fetchCharacter: async (characterId) => {
        set((state) => {
          state.isLoading = true;
          state.error = null;
        });
        try {
          const character = await api.getCharacter(characterId);
          set((state) => {
            state.characterMap[characterId] = character;
            const idx = state.characters.findIndex((c) => c.id === characterId);
            if (idx >= 0) {
              state.characters[idx] = character;
            } else {
              state.characters.push(character);
            }
            if (state.selectedCharacterId === characterId) {
              state.selectedCharacter = character;
            }
            state.isLoading = false;
          });
          return character;
        } catch (error) {
          console.error('Failed to fetch character:', error);
          set((state) => {
            state.isLoading = false;
            state.error = 'Failed to fetch character';
          });
          return null;
        }
      },

      // Async actions - Update
      updateCharacter: async (characterId, data) => {
        set((state) => {
          state.isUpdating = characterId;
          state.error = null;
        });
        try {
          const result = await api.updateCharacter(characterId, data);
          set((state) => {
            const existing = state.characterMap[characterId];
            if (existing) {
              const updated = {
                ...existing,
                ...data,
                lockState: result.lockState as Character['lockState'],
                updatedAt: result.updatedAt,
              };
              state.characterMap[characterId] = updated;
              const idx = state.characters.findIndex((c) => c.id === characterId);
              if (idx >= 0) {
                state.characters[idx] = updated;
              }
              if (state.selectedCharacterId === characterId) {
                state.selectedCharacter = updated;
              }
            }
            state.isUpdating = null;
          });
          return true;
        } catch (error) {
          console.error('Failed to update character:', error);
          set((state) => {
            state.isUpdating = null;
            state.error = 'Failed to update character';
          });
          return false;
        }
      },

      // Async actions - Description generation
      generateDescription: async (characterId) => {
        set((state) => {
          state.isGeneratingDescription = true;
          state.error = null;
        });
        try {
          const description = await api.generateCharacterDescription(characterId);
          set((state) => {
            const existing = state.characterMap[characterId];
            if (existing) {
              const updated = {
                ...existing,
                physicalDescription: description.physicalDescription,
                personality: description.personality,
              };
              state.characterMap[characterId] = updated;
              const idx = state.characters.findIndex((c) => c.id === characterId);
              if (idx >= 0) {
                state.characters[idx] = updated;
              }
              if (state.selectedCharacterId === characterId) {
                state.selectedCharacter = updated;
              }
            }
            state.isGeneratingDescription = false;
          });
          return description;
        } catch (error) {
          console.error('Failed to generate character description:', error);
          set((state) => {
            state.isGeneratingDescription = false;
            state.error = 'Failed to generate description';
          });
          return null;
        }
      },

      // Async actions - References
      uploadReference: async (characterId, filePath, filename, isPrimary = false) => {
        set((state) => {
          state.isUploadingReference = true;
          state.uploadProgress = 0;
          state.error = null;
        });
        try {
          set((state) => {
            state.uploadProgress = 30;
          });
          const reference = await api.uploadCharacterReference(
            characterId,
            filePath,
            filename,
            isPrimary
          );
          set((state) => {
            state.uploadProgress = 100;
            const existing = state.characterMap[characterId];
            if (existing) {
              const updated = {
                ...existing,
                referenceImages: [...(existing.referenceImages ?? []), reference],
              };
              state.characterMap[characterId] = updated;
              const idx = state.characters.findIndex((c) => c.id === characterId);
              if (idx >= 0) {
                state.characters[idx] = updated;
              }
              if (state.selectedCharacterId === characterId) {
                state.selectedCharacter = updated;
              }
            }
            state.isUploadingReference = false;
          });
          return reference;
        } catch (error) {
          console.error('Failed to upload reference:', error);
          set((state) => {
            state.isUploadingReference = false;
            state.uploadProgress = 0;
            state.error = 'Failed to upload reference';
          });
          return null;
        }
      },

      deleteReference: async (characterId, assetId) => {
        try {
          const result = await api.deleteCharacterReference(characterId, assetId);
          if (result.success) {
            set((state) => {
              const existing = state.characterMap[characterId];
              if (existing) {
                const updated = {
                  ...existing,
                  referenceImages: (existing.referenceImages ?? []).filter((r) => r.id !== assetId),
                };
                state.characterMap[characterId] = updated;
                const idx = state.characters.findIndex((c) => c.id === characterId);
                if (idx >= 0) {
                  state.characters[idx] = updated;
                }
                if (state.selectedCharacterId === characterId) {
                  state.selectedCharacter = updated;
                }
              }
            });
          }
          return result.success;
        } catch (error) {
          console.error('Failed to delete reference:', error);
          set((state) => {
            state.error = 'Failed to delete reference';
          });
          return false;
        }
      },

      // Async actions - Locking
      lockCharacter: async (characterId, primaryReferenceId) => {
        set((state) => {
          state.isUpdating = characterId;
          state.error = null;
        });
        try {
          const result = await api.lockCharacter(characterId, primaryReferenceId);
          set((state) => {
            const existing = state.characterMap[characterId];
            if (existing) {
              const updated = {
                ...existing,
                lockState: result.lockState as Character['lockState'],
                lockedLikeness: result.lockedLikeness ?? null,
              };
              state.characterMap[characterId] = updated;
              const idx = state.characters.findIndex((c) => c.id === characterId);
              if (idx >= 0) {
                state.characters[idx] = updated;
              }
              if (state.selectedCharacterId === characterId) {
                state.selectedCharacter = updated;
              }
            }
            state.isUpdating = null;
          });
          return result.isLocked;
        } catch (error) {
          console.error('Failed to lock character:', error);
          set((state) => {
            state.isUpdating = null;
            state.error = 'Failed to lock character';
          });
          return false;
        }
      },

      unlockCharacter: async (characterId) => {
        set((state) => {
          state.isUpdating = characterId;
          state.error = null;
        });
        try {
          const result = await api.unlockCharacter(characterId);
          set((state) => {
            const existing = state.characterMap[characterId];
            if (existing) {
              const updated = {
                ...existing,
                lockState: result.lockState as Character['lockState'],
                lockedLikeness: null,
              };
              state.characterMap[characterId] = updated;
              const idx = state.characters.findIndex((c) => c.id === characterId);
              if (idx >= 0) {
                state.characters[idx] = updated;
              }
              if (state.selectedCharacterId === characterId) {
                state.selectedCharacter = updated;
              }
            }
            state.isUpdating = null;
          });
          return !result.isLocked;
        } catch (error) {
          console.error('Failed to unlock character:', error);
          set((state) => {
            state.isUpdating = null;
            state.error = 'Failed to unlock character';
          });
          return false;
        }
      },

      // Async actions - Voice
      updateVoice: async (characterId, voiceId, voiceProvider, voiceName) => {
        set((state) => {
          state.isUpdating = characterId;
          state.error = null;
        });
        try {
          const result = await api.updateCharacterVoice(
            characterId,
            voiceId,
            voiceProvider,
            voiceName
          );
          set((state) => {
            const existing = state.characterMap[characterId];
            if (existing) {
              const updated = {
                ...existing,
                voiceId: result.voiceId,
                voiceProvider: result.voiceProvider,
                voiceName: result.voiceName,
              };
              state.characterMap[characterId] = updated;
              const idx = state.characters.findIndex((c) => c.id === characterId);
              if (idx >= 0) {
                state.characters[idx] = updated;
              }
              if (state.selectedCharacterId === characterId) {
                state.selectedCharacter = updated;
              }
            }
            state.isUpdating = null;
          });
          return true;
        } catch (error) {
          console.error('Failed to update character voice:', error);
          set((state) => {
            state.isUpdating = null;
            state.error = 'Failed to update voice';
          });
          return false;
        }
      },

      // Async actions - Prompts
      getPrompt: async (characterId, sceneContext) => {
        try {
          return await api.getCharacterPrompt(characterId, sceneContext);
        } catch (error) {
          console.error('Failed to get character prompt:', error);
          return null;
        }
      },

      // Computed helpers
      getCharacterById: (id) => {
        return get().characterMap[id];
      },

      getLockedCharacters: () => {
        return get().characters.filter(
          (c) => c.lockState === 'locked' || c.lockState === 'locked_with_reference'
        );
      },

      getUnlockedCharacters: () => {
        return get().characters.filter((c) => c.lockState === 'unlocked');
      },

      getCharactersWithVoice: () => {
        return get().characters.filter((c) => c.voiceId !== null);
      },

      getCharactersNeedingVoice: () => {
        return get().characters.filter((c) => c.voiceId === null);
      },

      // Reset
      reset: () => set(initialState),
    })),
    { name: 'CharacterStore' }
  )
);

/**
 * Hook to get the count of locked characters.
 */
export function useLockedCharacterCount(): number {
  return useCharacterStore(
    (state) =>
      state.characters.filter(
        (c) => c.lockState === 'locked' || c.lockState === 'locked_with_reference'
      ).length
  );
}

/**
 * Hook to check if all characters are locked.
 */
export function useAllCharactersLocked(): boolean {
  return useCharacterStore((state) => {
    if (state.characters.length === 0) return false;
    return state.characters.every(
      (c) => c.lockState === 'locked' || c.lockState === 'locked_with_reference'
    );
  });
}

/**
 * Hook to get character completion percentage.
 */
export function useCharacterCompletion(): number {
  return useCharacterStore((state) => {
    if (state.characters.length === 0) return 0;
    const complete = state.characters.filter(
      (c) => c.physicalDescription && c.lockState !== 'unlocked' && c.voiceId !== null
    ).length;
    return Math.round((complete / state.characters.length) * 100);
  });
}
