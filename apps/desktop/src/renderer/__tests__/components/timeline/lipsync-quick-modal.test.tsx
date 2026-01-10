/**
 * Tests for LipSyncQuickModal component.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { LipSyncQuickModal } from '../../../components/timeline/lipsync-quick-modal';

// Mock the lip sync store
const mockStartLipSync = vi.fn();
const mockFetchProviders = vi.fn();
const mockClearError = vi.fn();

vi.mock('../../../stores/lipsync-store', () => ({
  useLipSyncStore: (selector: (state: any) => any) => {
    const state = {
      providers: [
        { provider: 'mock', name: 'Mock Provider', available: true },
        { provider: 'rhubarb', name: 'Rhubarb', available: true },
      ],
      jobs: [],
      error: null,
      startLipSync: mockStartLipSync,
      fetchProviders: mockFetchProviders,
      clearError: mockClearError,
    };
    return selector(state);
  },
  selectAvailableProviders: (state: any) => state.providers,
  selectProcessingJobs: (state: any) =>
    state.jobs.filter((j: any) => j.status === 'processing' || j.status === 'queued'),
}));

describe('LipSyncQuickModal', () => {
  const defaultProps = {
    isOpen: true,
    onClose: vi.fn(),
    clipId: 'clip-1',
    clipLabel: 'Shot 1 (Scene 1)',
    availableAudioTracks: [
      { id: 'audio-1', label: 'Dialogue Track 1', path: '/audio/dialogue-1.wav' },
      { id: 'audio-2', label: 'Dialogue Track 2', path: '/audio/dialogue-2.wav' },
    ],
    onSuccess: vi.fn(),
  };

  beforeEach(() => {
    vi.clearAllMocks();
    mockStartLipSync.mockResolvedValue({ job_id: 'job-1' });
  });

  describe('Rendering', () => {
    it('should render modal when open', () => {
      render(<LipSyncQuickModal {...defaultProps} />);
      expect(screen.getByRole('dialog')).toBeInTheDocument();
    });

    it('should not render modal when closed', () => {
      render(<LipSyncQuickModal {...defaultProps} isOpen={false} />);
      expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
    });

    it('should display clip label', () => {
      render(<LipSyncQuickModal {...defaultProps} />);
      expect(screen.getByText('Shot 1 (Scene 1)')).toBeInTheDocument();
    });

    it('should render audio track selector', () => {
      render(<LipSyncQuickModal {...defaultProps} />);
      expect(screen.getByLabelText('Audio Track')).toBeInTheDocument();
    });

    it('should render provider selector', () => {
      render(<LipSyncQuickModal {...defaultProps} />);
      expect(screen.getByLabelText('Provider')).toBeInTheDocument();
    });

    it('should render Apply and Cancel buttons', () => {
      render(<LipSyncQuickModal {...defaultProps} />);
      expect(screen.getByText('Apply')).toBeInTheDocument();
      expect(screen.getByText('Cancel')).toBeInTheDocument();
    });

    it('should show empty state when no audio tracks available', () => {
      render(<LipSyncQuickModal {...defaultProps} availableAudioTracks={[]} />);
      expect(screen.getByText('No audio tracks available')).toBeInTheDocument();
    });
  });

  describe('Audio Track Selection', () => {
    it('should display available audio tracks', () => {
      render(<LipSyncQuickModal {...defaultProps} />);
      expect(screen.getByText('Dialogue Track 1')).toBeInTheDocument();
      expect(screen.getByText('Dialogue Track 2')).toBeInTheDocument();
    });

    it('should allow selecting audio track', () => {
      render(<LipSyncQuickModal {...defaultProps} />);
      const select = screen.getByLabelText('Audio Track');
      fireEvent.change(select, { target: { value: 'audio-1' } });
      expect(select).toHaveValue('audio-1');
    });

    it('should auto-select when only one audio track available', () => {
      render(
        <LipSyncQuickModal
          {...defaultProps}
          availableAudioTracks={[{ id: 'audio-1', label: 'Only Track', path: '/audio.wav' }]}
        />
      );
      const select = screen.getByLabelText('Audio Track');
      expect(select).toHaveValue('audio-1');
    });
  });

  describe('Provider Selection', () => {
    it('should display available providers', () => {
      render(<LipSyncQuickModal {...defaultProps} />);
      expect(screen.getByText('Mock Provider (Fast)')).toBeInTheDocument();
      expect(screen.getByText('Rhubarb (Recommended)')).toBeInTheDocument();
    });

    it('should allow selecting provider', () => {
      render(<LipSyncQuickModal {...defaultProps} />);
      const select = screen.getByLabelText('Provider');
      fireEvent.change(select, { target: { value: 'rhubarb' } });
      expect(select).toHaveValue('rhubarb');
    });

    it('should show provider description', () => {
      render(<LipSyncQuickModal {...defaultProps} />);
      expect(
        screen.getByText('Mock provider for testing purposes')
      ).toBeInTheDocument();
    });
  });

  describe('Apply Action', () => {
    it('should disable Apply button when no audio selected', () => {
      render(<LipSyncQuickModal {...defaultProps} />);
      const applyButton = screen.getByText('Apply');
      expect(applyButton).toBeDisabled();
    });

    it('should enable Apply button when audio is selected', () => {
      render(<LipSyncQuickModal {...defaultProps} />);
      const select = screen.getByLabelText('Audio Track');
      fireEvent.change(select, { target: { value: 'audio-1' } });
      const applyButton = screen.getByText('Apply');
      expect(applyButton).not.toBeDisabled();
    });

    it('should call startLipSync when Apply is clicked', async () => {
      render(<LipSyncQuickModal {...defaultProps} />);
      const audioSelect = screen.getByLabelText('Audio Track');
      fireEvent.change(audioSelect, { target: { value: 'audio-1' } });

      const applyButton = screen.getByText('Apply');
      fireEvent.click(applyButton);

      await waitFor(() => {
        expect(mockStartLipSync).toHaveBeenCalledWith('clip-1', 'audio-1', 'mock');
      });
    });

    it('should call onSuccess with job ID after successful start', async () => {
      render(<LipSyncQuickModal {...defaultProps} />);
      const audioSelect = screen.getByLabelText('Audio Track');
      fireEvent.change(audioSelect, { target: { value: 'audio-1' } });

      const applyButton = screen.getByText('Apply');
      fireEvent.click(applyButton);

      await waitFor(() => {
        expect(defaultProps.onSuccess).toHaveBeenCalledWith('job-1');
      });
    });

    it('should close modal after successful start', async () => {
      render(<LipSyncQuickModal {...defaultProps} />);
      const audioSelect = screen.getByLabelText('Audio Track');
      fireEvent.change(audioSelect, { target: { value: 'audio-1' } });

      const applyButton = screen.getByText('Apply');
      fireEvent.click(applyButton);

      await waitFor(() => {
        expect(defaultProps.onClose).toHaveBeenCalled();
      });
    });
  });

  describe('Cancel Action', () => {
    it('should call onClose when Cancel is clicked', () => {
      render(<LipSyncQuickModal {...defaultProps} />);
      fireEvent.click(screen.getByText('Cancel'));
      expect(defaultProps.onClose).toHaveBeenCalled();
    });

    it('should close modal on Escape key', () => {
      render(<LipSyncQuickModal {...defaultProps} />);
      fireEvent.keyDown(document, { key: 'Escape' });
      expect(defaultProps.onClose).toHaveBeenCalled();
    });

    it('should close modal on backdrop click', () => {
      render(<LipSyncQuickModal {...defaultProps} />);
      // Click on the backdrop (the fixed overlay)
      const backdrop = screen.getByRole('dialog').parentElement;
      if (backdrop) {
        fireEvent.click(backdrop);
        expect(defaultProps.onClose).toHaveBeenCalled();
      }
    });
  });

  describe('Error Handling', () => {
    it('should show error message when start fails', async () => {
      mockStartLipSync.mockRejectedValue(new Error('Failed to start'));

      render(<LipSyncQuickModal {...defaultProps} />);
      const audioSelect = screen.getByLabelText('Audio Track');
      fireEvent.change(audioSelect, { target: { value: 'audio-1' } });

      const applyButton = screen.getByText('Apply');
      fireEvent.click(applyButton);

      await waitFor(() => {
        expect(screen.getByText('Failed to start')).toBeInTheDocument();
      });
    });
  });

  describe('Accessibility', () => {
    it('should have proper dialog role and label', () => {
      render(<LipSyncQuickModal {...defaultProps} />);
      const dialog = screen.getByRole('dialog');
      expect(dialog).toHaveAttribute('aria-modal', 'true');
      expect(dialog).toHaveAttribute('aria-labelledby', 'lipsync-modal-title');
    });

    it('should have close button with aria-label', () => {
      render(<LipSyncQuickModal {...defaultProps} />);
      expect(screen.getByLabelText('Close')).toBeInTheDocument();
    });
  });
});
