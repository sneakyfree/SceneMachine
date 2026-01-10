/**
 * Tests for the character store.
 */

import { describe, it, expect, beforeEach, vi } from 'vitest';
import { useCharacterStore } from '../../stores/character-store';

describe('CharacterStore', () => {
  beforeEach(() => {
    // Reset store state before each test
    useCharacterStore.setState({
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
    });
  });

  describe('Initial State', () => {
    it('should have correct initial values', () => {
      const state = useCharacterStore.getState();

      expect(state.characters).toEqual([]);
      expect(state.characterMap).toEqual({});
      expect(state.selectedCharacterId).toBeNull();
      expect(state.selectedCharacter).toBeNull();
      expect(state.isUploadingReference).toBe(false);
      expect(state.uploadProgress).toBe(0);
      expect(state.isGeneratingDescription).toBe(false);
      expect(state.isLoading).toBe(false);
      expect(state.isUpdating).toBeNull();
      expect(state.error).toBeNull();
    });
  });

  describe('Character List Management', () => {
    it('should set characters and create character map', () => {
      const { setCharacters } = useCharacterStore.getState();

      const characters = [
        { id: 'char-1', name: 'ALEX', lockState: 'unlocked' as const },
        { id: 'char-2', name: 'SARAH', lockState: 'locked' as const },
      ];

      setCharacters(characters as any);

      const state = useCharacterStore.getState();
      expect(state.characters).toHaveLength(2);
      expect(state.characterMap['char-1']).toBeDefined();
      expect(state.characterMap['char-2']).toBeDefined();
      expect(state.characterMap['char-1'].name).toBe('ALEX');
    });

    it('should update character map when setting characters', () => {
      const { setCharacters } = useCharacterStore.getState();

      setCharacters([
        { id: 'char-1', name: 'ALEX', lockState: 'unlocked' as const },
      ] as any);

      setCharacters([
        { id: 'char-2', name: 'SARAH', lockState: 'locked' as const },
      ] as any);

      const state = useCharacterStore.getState();
      expect(state.characters).toHaveLength(1);
      expect(state.characterMap['char-1']).toBeUndefined();
      expect(state.characterMap['char-2']).toBeDefined();
    });
  });

  describe('Character Selection', () => {
    it('should select a character', () => {
      const { setCharacters, setSelectedCharacterId } = useCharacterStore.getState();

      const characters = [
        { id: 'char-1', name: 'ALEX', lockState: 'unlocked' as const },
        { id: 'char-2', name: 'SARAH', lockState: 'locked' as const },
      ];

      setCharacters(characters as any);
      setSelectedCharacterId('char-1');

      const state = useCharacterStore.getState();
      expect(state.selectedCharacterId).toBe('char-1');
      expect(state.selectedCharacter?.name).toBe('ALEX');
    });

    it('should clear selection when null is passed', () => {
      const { setCharacters, setSelectedCharacterId } = useCharacterStore.getState();

      setCharacters([
        { id: 'char-1', name: 'ALEX', lockState: 'unlocked' as const },
      ] as any);

      setSelectedCharacterId('char-1');
      setSelectedCharacterId(null);

      const state = useCharacterStore.getState();
      expect(state.selectedCharacterId).toBeNull();
      expect(state.selectedCharacter).toBeNull();
    });

    it('should return null for non-existent character selection', () => {
      const { setSelectedCharacterId } = useCharacterStore.getState();

      setSelectedCharacterId('non-existent');

      const state = useCharacterStore.getState();
      expect(state.selectedCharacterId).toBe('non-existent');
      expect(state.selectedCharacter).toBeNull();
    });
  });

  describe('Error Handling', () => {
    it('should set error', () => {
      const { setError } = useCharacterStore.getState();

      setError('Failed to load characters');

      expect(useCharacterStore.getState().error).toBe('Failed to load characters');
    });

    it('should clear error', () => {
      const { setError } = useCharacterStore.getState();

      setError('Some error');
      setError(null);

      expect(useCharacterStore.getState().error).toBeNull();
    });
  });

  describe('Computed Helpers', () => {
    beforeEach(() => {
      const { setCharacters } = useCharacterStore.getState();
      setCharacters([
        { id: 'char-1', name: 'ALEX', lockState: 'unlocked' as const, voiceId: null },
        { id: 'char-2', name: 'SARAH', lockState: 'locked' as const, voiceId: 'voice-1' },
        { id: 'char-3', name: 'BOB', lockState: 'locked_with_reference' as const, voiceId: 'voice-2' },
        { id: 'char-4', name: 'JANE', lockState: 'unlocked' as const, voiceId: 'voice-3' },
      ] as any);
    });

    it('should get character by ID', () => {
      const { getCharacterById } = useCharacterStore.getState();

      const character = getCharacterById('char-2');
      expect(character?.name).toBe('SARAH');
    });

    it('should return undefined for non-existent character ID', () => {
      const { getCharacterById } = useCharacterStore.getState();

      const character = getCharacterById('non-existent');
      expect(character).toBeUndefined();
    });

    it('should get locked characters', () => {
      const { getLockedCharacters } = useCharacterStore.getState();

      const locked = getLockedCharacters();
      expect(locked).toHaveLength(2);
      expect(locked.map(c => c.name)).toContain('SARAH');
      expect(locked.map(c => c.name)).toContain('BOB');
    });

    it('should get unlocked characters', () => {
      const { getUnlockedCharacters } = useCharacterStore.getState();

      const unlocked = getUnlockedCharacters();
      expect(unlocked).toHaveLength(2);
      expect(unlocked.map(c => c.name)).toContain('ALEX');
      expect(unlocked.map(c => c.name)).toContain('JANE');
    });

    it('should get characters with voice', () => {
      const { getCharactersWithVoice } = useCharacterStore.getState();

      const withVoice = getCharactersWithVoice();
      expect(withVoice).toHaveLength(3);
    });

    it('should get characters needing voice', () => {
      const { getCharactersNeedingVoice } = useCharacterStore.getState();

      const needingVoice = getCharactersNeedingVoice();
      expect(needingVoice).toHaveLength(1);
      expect(needingVoice[0].name).toBe('ALEX');
    });
  });

  describe('Loading States', () => {
    it('should track updating state', () => {
      useCharacterStore.setState((state) => ({
        ...state,
        isUpdating: 'char-1',
      }));

      const state = useCharacterStore.getState();
      expect(state.isUpdating).toBe('char-1');
    });

    it('should track uploading reference state', () => {
      useCharacterStore.setState((state) => ({
        ...state,
        isUploadingReference: true,
        uploadProgress: 50,
      }));

      const state = useCharacterStore.getState();
      expect(state.isUploadingReference).toBe(true);
      expect(state.uploadProgress).toBe(50);
    });

    it('should track generating description state', () => {
      useCharacterStore.setState((state) => ({
        ...state,
        isGeneratingDescription: true,
      }));

      const state = useCharacterStore.getState();
      expect(state.isGeneratingDescription).toBe(true);
    });
  });

  describe('Reset', () => {
    it('should reset all state', () => {
      const { setCharacters, setSelectedCharacterId, setError, reset } =
        useCharacterStore.getState();

      // Modify state
      setCharacters([
        { id: 'char-1', name: 'ALEX', lockState: 'locked' as const },
      ] as any);
      setSelectedCharacterId('char-1');
      setError('Some error');

      // Reset
      reset();

      const state = useCharacterStore.getState();
      expect(state.characters).toEqual([]);
      expect(state.characterMap).toEqual({});
      expect(state.selectedCharacterId).toBeNull();
      expect(state.selectedCharacter).toBeNull();
      expect(state.error).toBeNull();
    });
  });
});
