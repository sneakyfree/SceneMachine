/**
 * Experience store unit tests.
 *
 * Tests the experience mode switching functionality (Story/Creator/Pro modes)
 * and Steven assistant state management.
 */

import { describe, it, expect, beforeEach } from 'vitest';
import { act } from '@testing-library/react';
import { useExperienceStore, MODE_INFO, FRIENDLY_TERMS } from '../../stores/experience-store';

describe('ExperienceStore', () => {
  beforeEach(() => {
    // Reset store state before each test
    useExperienceStore.setState({
      globalMode: 'creator',
      featureOverrides: {},
      rememberGlobal: true,
      stevenEnabled: true,
      stevenMinimized: false,
      stevenLastMessage: null,
      stevenMessageHistory: [],
    });
  });

  describe('setGlobalMode', () => {
    it('should set the global experience mode', () => {
      const { setGlobalMode } = useExperienceStore.getState();

      act(() => {
        setGlobalMode('story');
      });

      expect(useExperienceStore.getState().globalMode).toBe('story');
    });

    it('should clear feature overrides when rememberGlobal is true', () => {
      useExperienceStore.setState({
        rememberGlobal: true,
        featureOverrides: { screenplay: 'pro' },
      });

      const { setGlobalMode } = useExperienceStore.getState();

      act(() => {
        setGlobalMode('story');
      });

      expect(useExperienceStore.getState().featureOverrides).toEqual({});
    });
  });

  describe('setFeatureMode', () => {
    it('should set per-feature mode override', () => {
      const { setFeatureMode } = useExperienceStore.getState();

      act(() => {
        setFeatureMode('screenplay', 'pro');
      });

      expect(useExperienceStore.getState().featureOverrides.screenplay).toBe('pro');
    });

    it('should clear override when mode is null', () => {
      useExperienceStore.setState({
        featureOverrides: { screenplay: 'pro' },
      });

      const { setFeatureMode } = useExperienceStore.getState();

      act(() => {
        setFeatureMode('screenplay', null);
      });

      expect(useExperienceStore.getState().featureOverrides.screenplay).toBeUndefined();
    });
  });

  describe('getEffectiveMode', () => {
    it('should return global mode when no feature override exists', () => {
      useExperienceStore.setState({ globalMode: 'pro' });

      const { getEffectiveMode } = useExperienceStore.getState();

      expect(getEffectiveMode('screenplay')).toBe('pro');
    });

    it('should return feature override when it exists', () => {
      useExperienceStore.setState({
        globalMode: 'creator',
        featureOverrides: { screenplay: 'story' },
      });

      const { getEffectiveMode } = useExperienceStore.getState();

      expect(getEffectiveMode('screenplay')).toBe('story');
    });

    it('should return global mode when no feature specified', () => {
      useExperienceStore.setState({ globalMode: 'story' });

      const { getEffectiveMode } = useExperienceStore.getState();

      expect(getEffectiveMode()).toBe('story');
    });
  });

  describe('resetFeatureOverrides', () => {
    it('should clear all feature overrides', () => {
      useExperienceStore.setState({
        featureOverrides: { screenplay: 'pro', characters: 'story' },
      });

      const { resetFeatureOverrides } = useExperienceStore.getState();

      act(() => {
        resetFeatureOverrides();
      });

      expect(useExperienceStore.getState().featureOverrides).toEqual({});
    });
  });

  describe('Steven Assistant', () => {
    it('should set Steven enabled state', () => {
      const { setStevenEnabled } = useExperienceStore.getState();

      act(() => {
        setStevenEnabled(false);
      });

      expect(useExperienceStore.getState().stevenEnabled).toBe(false);
    });

    it('should set Steven minimized state', () => {
      const { setStevenMinimized } = useExperienceStore.getState();

      act(() => {
        setStevenMinimized(true);
      });

      expect(useExperienceStore.getState().stevenMinimized).toBe(true);
    });

    it('should send Steven message and add to history', () => {
      const { sendStevenMessage } = useExperienceStore.getState();

      act(() => {
        sendStevenMessage('Test message', 'info');
      });

      const state = useExperienceStore.getState();
      expect(state.stevenLastMessage).toBe('Test message');
      expect(state.stevenMessageHistory).toHaveLength(1);
      expect(state.stevenMessageHistory[0].message).toBe('Test message');
      expect(state.stevenMessageHistory[0].type).toBe('info');
    });

    it('should clear Steven history', () => {
      useExperienceStore.setState({
        stevenLastMessage: 'Test',
        stevenMessageHistory: [{ message: 'Test', timestamp: Date.now(), type: 'info' }],
      });

      const { clearStevenHistory } = useExperienceStore.getState();

      act(() => {
        clearStevenHistory();
      });

      const state = useExperienceStore.getState();
      expect(state.stevenLastMessage).toBeNull();
      expect(state.stevenMessageHistory).toHaveLength(0);
    });

    it('should check if Steven should be shown', () => {
      useExperienceStore.setState({
        stevenEnabled: true,
        stevenMinimized: false,
      });

      const { shouldShowSteven } = useExperienceStore.getState();

      expect(shouldShowSteven()).toBe(true);
    });

    it('should not show Steven when minimized', () => {
      useExperienceStore.setState({
        stevenEnabled: true,
        stevenMinimized: true,
      });

      const { shouldShowSteven } = useExperienceStore.getState();

      expect(shouldShowSteven()).toBe(false);
    });
  });

  describe('getTerm', () => {
    it('should return friendly term for story mode', () => {
      useExperienceStore.setState({ globalMode: 'story' });

      const { getTerm } = useExperienceStore.getState();

      expect(getTerm('1080p')).toBe('Great Quality (Looks great on any TV)');
    });

    it('should return technical term for pro mode', () => {
      useExperienceStore.setState({ globalMode: 'pro' });

      const { getTerm } = useExperienceStore.getState();

      expect(getTerm('1080p')).toBe('1920×1080 (1080p)');
    });

    it('should return original term if no translation exists', () => {
      useExperienceStore.setState({ globalMode: 'pro' });

      const { getTerm } = useExperienceStore.getState();

      expect(getTerm('unknownTerm')).toBe('unknownTerm');
    });
  });

  describe('isSimplifiedMode', () => {
    it('should return true for story mode', () => {
      useExperienceStore.setState({ globalMode: 'story' });

      const { isSimplifiedMode } = useExperienceStore.getState();

      expect(isSimplifiedMode()).toBe(true);
    });

    it('should return false for creator mode', () => {
      useExperienceStore.setState({ globalMode: 'creator' });

      const { isSimplifiedMode } = useExperienceStore.getState();

      expect(isSimplifiedMode()).toBe(false);
    });
  });

  describe('shouldShowTechnical', () => {
    it('should return false for story mode', () => {
      useExperienceStore.setState({ globalMode: 'story' });

      const { shouldShowTechnical } = useExperienceStore.getState();

      expect(shouldShowTechnical()).toBe(false);
    });

    it('should return true for pro mode', () => {
      useExperienceStore.setState({ globalMode: 'pro' });

      const { shouldShowTechnical } = useExperienceStore.getState();

      expect(shouldShowTechnical()).toBe(true);
    });

    it('should return true for creator mode', () => {
      useExperienceStore.setState({ globalMode: 'creator' });

      const { shouldShowTechnical } = useExperienceStore.getState();

      expect(shouldShowTechnical()).toBe(true);
    });
  });

  describe('MODE_INFO', () => {
    it('should have info for all modes', () => {
      expect(MODE_INFO.story).toBeDefined();
      expect(MODE_INFO.creator).toBeDefined();
      expect(MODE_INFO.pro).toBeDefined();
    });

    it('should have required properties for each mode', () => {
      for (const mode of Object.values(MODE_INFO)) {
        expect(mode.name).toBeDefined();
        expect(mode.shortName).toBeDefined();
        expect(mode.description).toBeDefined();
        expect(mode.icon).toBeDefined();
        expect(mode.color).toBeDefined();
      }
    });
  });

  describe('FRIENDLY_TERMS', () => {
    it('should have translations for common terms', () => {
      expect(FRIENDLY_TERMS['1080p']).toBeDefined();
      expect(FRIENDLY_TERMS['h264']).toBeDefined();
      expect(FRIENDLY_TERMS['queued']).toBeDefined();
    });

    it('should provide different translations per mode', () => {
      const term = FRIENDLY_TERMS['1080p'];
      expect(term.story).not.toBe(term.pro);
    });
  });
});
