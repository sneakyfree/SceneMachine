/**
 * Tests for the audio store.
 */

import { describe, it, expect, beforeEach, vi } from 'vitest';
import { useAudioStore } from '../../stores/audio-store';

describe('AudioStore', () => {
  beforeEach(() => {
    // Reset store state before each test
    useAudioStore.setState({
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
    });
  });

  describe('Initial State', () => {
    it('should have correct initial values', () => {
      const state = useAudioStore.getState();

      expect(state.providers).toEqual([]);
      expect(state.voices).toEqual([]);
      expect(state.characterVoices).toEqual({});
      expect(state.selectedProvider).toBe('mock');
      expect(state.isLoadingProviders).toBe(false);
      expect(state.isLoadingVoices).toBe(false);
      expect(state.isGenerating).toBe(false);
      expect(state.previewAudioUrl).toBeNull();
      expect(state.previewPlaying).toBe(false);
      expect(state.error).toBeNull();
    });
  });

  describe('Provider Management', () => {
    it('should set providers', () => {
      const { setProviders } = useAudioStore.getState();

      const providers = [
        {
          id: 'elevenlabs',
          name: 'ElevenLabs',
          available: true,
          voices_count: 100,
          requires_api_key: true,
          description: 'High-quality voices',
        },
        {
          id: 'kokoro',
          name: 'Kokoro',
          available: true,
          voices_count: 20,
          requires_api_key: false,
          description: 'Local TTS',
        },
      ];

      setProviders(providers);

      const state = useAudioStore.getState();
      expect(state.providers).toHaveLength(2);
      expect(state.providers[0].name).toBe('ElevenLabs');
    });

    it('should set selected provider', () => {
      const { setSelectedProvider } = useAudioStore.getState();

      setSelectedProvider('elevenlabs');

      expect(useAudioStore.getState().selectedProvider).toBe('elevenlabs');
    });
  });

  describe('Voice Management', () => {
    it('should set voices', () => {
      const { setVoices } = useAudioStore.getState();

      const voices = [
        {
          id: 'voice-1',
          name: 'Rachel',
          provider: 'elevenlabs',
          gender: 'female',
          language: 'en',
        },
        {
          id: 'voice-2',
          name: 'Adam',
          provider: 'elevenlabs',
          gender: 'male',
          language: 'en',
        },
      ];

      setVoices(voices);

      const state = useAudioStore.getState();
      expect(state.voices).toHaveLength(2);
      expect(state.voices[0].name).toBe('Rachel');
    });
  });

  describe('Character Voice Assignment', () => {
    it('should set character voice', () => {
      const { setCharacterVoice } = useAudioStore.getState();

      const characterVoice = {
        character_id: 'char-1',
        character_name: 'ALEX',
        voice_id: 'voice-1',
        voice_name: 'Rachel',
        provider: 'elevenlabs',
      };

      setCharacterVoice('char-1', characterVoice);

      const state = useAudioStore.getState();
      expect(state.characterVoices['char-1']).toEqual(characterVoice);
    });

    it('should update character voice', () => {
      const { setCharacterVoice } = useAudioStore.getState();

      setCharacterVoice('char-1', {
        character_id: 'char-1',
        character_name: 'ALEX',
        voice_id: 'voice-1',
        voice_name: 'Rachel',
        provider: 'elevenlabs',
      });

      setCharacterVoice('char-1', {
        character_id: 'char-1',
        character_name: 'ALEX',
        voice_id: 'voice-2',
        voice_name: 'Adam',
        provider: 'elevenlabs',
      });

      const state = useAudioStore.getState();
      expect(state.characterVoices['char-1'].voice_name).toBe('Adam');
    });

    it('should handle multiple character voices', () => {
      const { setCharacterVoice } = useAudioStore.getState();

      setCharacterVoice('char-1', {
        character_id: 'char-1',
        character_name: 'ALEX',
        voice_id: 'voice-1',
        voice_name: 'Rachel',
        provider: 'elevenlabs',
      });

      setCharacterVoice('char-2', {
        character_id: 'char-2',
        character_name: 'SARAH',
        voice_id: 'voice-2',
        voice_name: 'Adam',
        provider: 'elevenlabs',
      });

      const state = useAudioStore.getState();
      expect(Object.keys(state.characterVoices)).toHaveLength(2);
    });
  });

  describe('Preview State', () => {
    it('should set preview audio URL', () => {
      const { setPreviewAudioUrl } = useAudioStore.getState();

      setPreviewAudioUrl('file:///path/to/audio.mp3');

      expect(useAudioStore.getState().previewAudioUrl).toBe('file:///path/to/audio.mp3');
    });

    it('should clear preview audio URL', () => {
      const { setPreviewAudioUrl } = useAudioStore.getState();

      setPreviewAudioUrl('file:///path/to/audio.mp3');
      setPreviewAudioUrl(null);

      expect(useAudioStore.getState().previewAudioUrl).toBeNull();
    });

    it('should set preview playing state', () => {
      const { setPreviewPlaying } = useAudioStore.getState();

      setPreviewPlaying(true);
      expect(useAudioStore.getState().previewPlaying).toBe(true);

      setPreviewPlaying(false);
      expect(useAudioStore.getState().previewPlaying).toBe(false);
    });
  });

  describe('Loading States', () => {
    it('should track loading providers state', () => {
      useAudioStore.setState((state) => ({
        ...state,
        isLoadingProviders: true,
      }));

      expect(useAudioStore.getState().isLoadingProviders).toBe(true);
    });

    it('should track loading voices state', () => {
      useAudioStore.setState((state) => ({
        ...state,
        isLoadingVoices: true,
      }));

      expect(useAudioStore.getState().isLoadingVoices).toBe(true);
    });

    it('should track generating state', () => {
      useAudioStore.setState((state) => ({
        ...state,
        isGenerating: true,
      }));

      expect(useAudioStore.getState().isGenerating).toBe(true);
    });
  });

  describe('Error Handling', () => {
    it('should set error', () => {
      const { setError } = useAudioStore.getState();

      setError('Failed to generate speech');

      expect(useAudioStore.getState().error).toBe('Failed to generate speech');
    });

    it('should clear error', () => {
      const { setError } = useAudioStore.getState();

      setError('Some error');
      setError(null);

      expect(useAudioStore.getState().error).toBeNull();
    });
  });

  describe('Reset', () => {
    it('should reset all state', () => {
      const { setProviders, setVoices, setCharacterVoice, setSelectedProvider, setError, reset } =
        useAudioStore.getState();

      // Modify state
      setProviders([
        {
          id: 'elevenlabs',
          name: 'ElevenLabs',
          available: true,
          voices_count: 100,
          requires_api_key: true,
          description: 'High-quality voices',
        },
      ]);
      setVoices([
        {
          id: 'voice-1',
          name: 'Rachel',
          provider: 'elevenlabs',
          gender: 'female',
          language: 'en',
        },
      ]);
      setCharacterVoice('char-1', {
        character_id: 'char-1',
        character_name: 'ALEX',
        voice_id: 'voice-1',
        voice_name: 'Rachel',
        provider: 'elevenlabs',
      });
      setSelectedProvider('elevenlabs');
      setError('Some error');

      // Reset
      reset();

      const state = useAudioStore.getState();
      expect(state.providers).toEqual([]);
      expect(state.voices).toEqual([]);
      expect(state.characterVoices).toEqual({});
      expect(state.selectedProvider).toBe('mock');
      expect(state.error).toBeNull();
    });
  });
});
