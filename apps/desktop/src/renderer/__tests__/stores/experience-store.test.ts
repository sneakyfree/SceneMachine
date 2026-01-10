/**
 * Experience store unit tests.
 */

import { describe, it, expect, beforeEach, vi } from 'vitest';
import { act } from '@testing-library/react';
import { useExperienceStore } from '../../stores/experience-store';

describe('ExperienceStore', () => {
  beforeEach(() => {
    // Reset store state before each test
    useExperienceStore.setState({
      onboardingCompleted: false,
      onboardingStep: 0,
      tourCompleted: false,
      tourStep: 0,
      showWelcomeModal: true,
      showWhatsNew: false,
      lastSeenVersion: null,
      featureFlags: {},
      userPreferences: {
        showTips: true,
        animationsEnabled: true,
        soundEnabled: true,
      },
      completedTutorials: new Set(),
      dismissedTips: new Set(),
    });
    vi.clearAllMocks();
  });

  describe('setOnboardingCompleted', () => {
    it('should set onboarding completed state', () => {
      const { setOnboardingCompleted } = useExperienceStore.getState();

      act(() => {
        setOnboardingCompleted(true);
      });

      expect(useExperienceStore.getState().onboardingCompleted).toBe(true);
    });
  });

  describe('setOnboardingStep', () => {
    it('should set onboarding step', () => {
      const { setOnboardingStep } = useExperienceStore.getState();

      act(() => {
        setOnboardingStep(3);
      });

      expect(useExperienceStore.getState().onboardingStep).toBe(3);
    });
  });

  describe('nextOnboardingStep', () => {
    it('should increment onboarding step', () => {
      useExperienceStore.setState({ onboardingStep: 2 });

      const { nextOnboardingStep } = useExperienceStore.getState();

      act(() => {
        nextOnboardingStep();
      });

      expect(useExperienceStore.getState().onboardingStep).toBe(3);
    });
  });

  describe('prevOnboardingStep', () => {
    it('should decrement onboarding step', () => {
      useExperienceStore.setState({ onboardingStep: 3 });

      const { prevOnboardingStep } = useExperienceStore.getState();

      act(() => {
        prevOnboardingStep();
      });

      expect(useExperienceStore.getState().onboardingStep).toBe(2);
    });

    it('should not go below 0', () => {
      useExperienceStore.setState({ onboardingStep: 0 });

      const { prevOnboardingStep } = useExperienceStore.getState();

      act(() => {
        prevOnboardingStep();
      });

      expect(useExperienceStore.getState().onboardingStep).toBe(0);
    });
  });

  describe('setTourCompleted', () => {
    it('should set tour completed state', () => {
      const { setTourCompleted } = useExperienceStore.getState();

      act(() => {
        setTourCompleted(true);
      });

      expect(useExperienceStore.getState().tourCompleted).toBe(true);
    });
  });

  describe('setTourStep', () => {
    it('should set tour step', () => {
      const { setTourStep } = useExperienceStore.getState();

      act(() => {
        setTourStep(5);
      });

      expect(useExperienceStore.getState().tourStep).toBe(5);
    });
  });

  describe('setShowWelcomeModal', () => {
    it('should set welcome modal visibility', () => {
      const { setShowWelcomeModal } = useExperienceStore.getState();

      act(() => {
        setShowWelcomeModal(false);
      });

      expect(useExperienceStore.getState().showWelcomeModal).toBe(false);
    });
  });

  describe('setShowWhatsNew', () => {
    it('should set whats new visibility', () => {
      const { setShowWhatsNew } = useExperienceStore.getState();

      act(() => {
        setShowWhatsNew(true);
      });

      expect(useExperienceStore.getState().showWhatsNew).toBe(true);
    });
  });

  describe('setLastSeenVersion', () => {
    it('should set last seen version', () => {
      const { setLastSeenVersion } = useExperienceStore.getState();

      act(() => {
        setLastSeenVersion('2.0.0');
      });

      expect(useExperienceStore.getState().lastSeenVersion).toBe('2.0.0');
    });
  });

  describe('setFeatureFlag', () => {
    it('should set a feature flag', () => {
      const { setFeatureFlag } = useExperienceStore.getState();

      act(() => {
        setFeatureFlag('newFeature', true);
      });

      expect(useExperienceStore.getState().featureFlags['newFeature']).toBe(true);
    });
  });

  describe('getFeatureFlag', () => {
    it('should get a feature flag value', () => {
      useExperienceStore.setState({
        featureFlags: { testFeature: true },
      });

      const { getFeatureFlag } = useExperienceStore.getState();
      expect(getFeatureFlag('testFeature')).toBe(true);
    });

    it('should return false for non-existent flag', () => {
      const { getFeatureFlag } = useExperienceStore.getState();
      expect(getFeatureFlag('nonexistent')).toBe(false);
    });
  });

  describe('setUserPreference', () => {
    it('should set a user preference', () => {
      const { setUserPreference } = useExperienceStore.getState();

      act(() => {
        setUserPreference('showTips', false);
      });

      expect(useExperienceStore.getState().userPreferences.showTips).toBe(false);
    });
  });

  describe('markTutorialCompleted', () => {
    it('should mark a tutorial as completed', () => {
      const { markTutorialCompleted } = useExperienceStore.getState();

      act(() => {
        markTutorialCompleted('intro-tutorial');
      });

      expect(useExperienceStore.getState().completedTutorials.has('intro-tutorial')).toBe(true);
    });
  });

  describe('isTutorialCompleted', () => {
    it('should check if tutorial is completed', () => {
      useExperienceStore.setState({
        completedTutorials: new Set(['tutorial-1']),
      });

      const { isTutorialCompleted } = useExperienceStore.getState();
      expect(isTutorialCompleted('tutorial-1')).toBe(true);
      expect(isTutorialCompleted('tutorial-2')).toBe(false);
    });
  });

  describe('dismissTip', () => {
    it('should dismiss a tip', () => {
      const { dismissTip } = useExperienceStore.getState();

      act(() => {
        dismissTip('tip-1');
      });

      expect(useExperienceStore.getState().dismissedTips.has('tip-1')).toBe(true);
    });
  });

  describe('isTipDismissed', () => {
    it('should check if tip is dismissed', () => {
      useExperienceStore.setState({
        dismissedTips: new Set(['tip-1']),
      });

      const { isTipDismissed } = useExperienceStore.getState();
      expect(isTipDismissed('tip-1')).toBe(true);
      expect(isTipDismissed('tip-2')).toBe(false);
    });
  });

  describe('completeOnboarding', () => {
    it('should complete onboarding and hide welcome modal', () => {
      const { completeOnboarding } = useExperienceStore.getState();

      act(() => {
        completeOnboarding();
      });

      const state = useExperienceStore.getState();
      expect(state.onboardingCompleted).toBe(true);
      expect(state.showWelcomeModal).toBe(false);
    });
  });

  describe('resetExperience', () => {
    it('should reset experience state', () => {
      useExperienceStore.setState({
        onboardingCompleted: true,
        onboardingStep: 5,
        tourCompleted: true,
        completedTutorials: new Set(['t1']),
        dismissedTips: new Set(['tip1']),
      });

      const { resetExperience } = useExperienceStore.getState();

      act(() => {
        resetExperience();
      });

      const state = useExperienceStore.getState();
      expect(state.onboardingCompleted).toBe(false);
      expect(state.onboardingStep).toBe(0);
      expect(state.tourCompleted).toBe(false);
      expect(state.completedTutorials.size).toBe(0);
      expect(state.dismissedTips.size).toBe(0);
    });
  });
});
