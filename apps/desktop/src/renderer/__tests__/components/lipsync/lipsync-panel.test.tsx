/**
 * Lip Sync Panel component tests.
 * Tests lip sync UI functionality and integration.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { LipSyncPanel } from '../../../components/lipsync/lipsync-panel';
import { useLipSyncStore } from '../../../stores/lipsync-store';

// Mock Electron API with default implementation
const mockBackendRequest = vi.fn().mockImplementation((endpoint, _params) => {
  // Default response for get providers
  if (endpoint === 'lipSync.getProviders') {
    return Promise.resolve({ providers: [] });
  }
  return Promise.resolve({});
});

global.window.electronAPI = {
  backendRequest: mockBackendRequest,
} as any;

const mockVideos = [
  { id: 'video-1', label: 'Shot 1A', path: '/path/to/video1.mp4' },
  { id: 'video-2', label: 'Shot 1B', path: '/path/to/video2.mp4' },
];

const mockAudio = [
  { id: 'audio-1', label: 'Dialogue 1', path: '/path/to/audio1.wav' },
  { id: 'audio-2', label: 'Dialogue 2', path: '/path/to/audio2.wav' },
];

const mockProviders = [
  { provider: 'mock', name: 'Mock Lip Sync', available: true },
  { provider: 'rhubarb', name: 'Rhubarb Lip Sync', available: true },
];

const mockJob = {
  job_id: 'lipsync-1',
  video_id: 'video-1',
  audio_id: 'audio-1',
  provider: 'mock',
  status: 'processing' as const,
  progress_percent: 45,
  progress_message: 'Analyzing audio...',
  output_path: null,
  error_message: null,
  created_at: new Date().toISOString(),
  completed_at: null,
};

describe('LipSyncPanel', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    // Reset store before each test
    useLipSyncStore.setState({
      jobs: [],
      activeJobId: null,
      providers: [],
      isLoadingProviders: false,
      error: null,
    });
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  describe('Panel Visibility', () => {
    it('should not render when closed', () => {
      const { container } = render(
        <LipSyncPanel
          isOpen={false}
          onClose={vi.fn()}
          availableVideos={mockVideos}
          availableAudio={mockAudio}
        />
      );
      expect(container.firstChild).toBeNull();
    });

    it('should render when open', () => {
      render(
        <LipSyncPanel
          isOpen={true}
          onClose={vi.fn()}
          availableVideos={mockVideos}
          availableAudio={mockAudio}
        />
      );
      expect(screen.getByRole('dialog', { name: /lip sync panel/i })).toBeInTheDocument();
    });

    it('should call onClose when close button clicked', () => {
      const onClose = vi.fn();
      render(
        <LipSyncPanel
          isOpen={true}
          onClose={onClose}
          availableVideos={mockVideos}
          availableAudio={mockAudio}
        />
      );

      const closeButton = screen.getByTitle('Close panel');
      fireEvent.click(closeButton);

      expect(onClose).toHaveBeenCalled();
    });
  });

  describe('Form Rendering', () => {
    it('should render video selector', () => {
      render(
        <LipSyncPanel
          isOpen={true}
          onClose={vi.fn()}
          availableVideos={mockVideos}
          availableAudio={mockAudio}
        />
      );

      expect(screen.getByLabelText('Video Clip')).toBeInTheDocument();
      expect(screen.getByText('Shot 1A')).toBeInTheDocument();
      expect(screen.getByText('Shot 1B')).toBeInTheDocument();
    });

    it('should render audio selector', () => {
      render(
        <LipSyncPanel
          isOpen={true}
          onClose={vi.fn()}
          availableVideos={mockVideos}
          availableAudio={mockAudio}
        />
      );

      expect(screen.getByLabelText('Audio Track')).toBeInTheDocument();
      expect(screen.getByText('Dialogue 1')).toBeInTheDocument();
      expect(screen.getByText('Dialogue 2')).toBeInTheDocument();
    });

    it('should render provider selector', () => {
      useLipSyncStore.setState({ providers: mockProviders });

      render(
        <LipSyncPanel
          isOpen={true}
          onClose={vi.fn()}
          availableVideos={mockVideos}
          availableAudio={mockAudio}
        />
      );

      expect(screen.getByLabelText('Provider')).toBeInTheDocument();
    });

    it('should render apply button', () => {
      render(
        <LipSyncPanel
          isOpen={true}
          onClose={vi.fn()}
          availableVideos={mockVideos}
          availableAudio={mockAudio}
        />
      );

      expect(screen.getByText('Apply Lip Sync')).toBeInTheDocument();
    });
  });

  describe('Form Interaction', () => {
    it('should update selected video', () => {
      render(
        <LipSyncPanel
          isOpen={true}
          onClose={vi.fn()}
          availableVideos={mockVideos}
          availableAudio={mockAudio}
        />
      );

      const videoSelect = screen.getByLabelText('Video Clip') as HTMLSelectElement;
      fireEvent.change(videoSelect, { target: { value: 'video-1' } });

      expect(videoSelect.value).toBe('video-1');
    });

    it('should update selected audio', () => {
      render(
        <LipSyncPanel
          isOpen={true}
          onClose={vi.fn()}
          availableVideos={mockVideos}
          availableAudio={mockAudio}
        />
      );

      const audioSelect = screen.getByLabelText('Audio Track') as HTMLSelectElement;
      fireEvent.change(audioSelect, { target: { value: 'audio-1' } });

      expect(audioSelect.value).toBe('audio-1');
    });

    it('should disable apply button when no video selected', () => {
      render(
        <LipSyncPanel
          isOpen={true}
          onClose={vi.fn()}
          availableVideos={mockVideos}
          availableAudio={mockAudio}
        />
      );

      const applyButton = screen.getByText('Apply Lip Sync');
      expect(applyButton).toBeDisabled();
    });

    it('should disable apply button when no audio selected', () => {
      render(
        <LipSyncPanel
          isOpen={true}
          onClose={vi.fn()}
          availableVideos={mockVideos}
          availableAudio={mockAudio}
        />
      );

      // Select video but not audio
      const videoSelect = screen.getByLabelText('Video Clip');
      fireEvent.change(videoSelect, { target: { value: 'video-1' } });

      const applyButton = screen.getByText('Apply Lip Sync');
      expect(applyButton).toBeDisabled();
    });

    it('should enable apply button when video and audio selected', () => {
      useLipSyncStore.setState({ providers: mockProviders });

      render(
        <LipSyncPanel
          isOpen={true}
          onClose={vi.fn()}
          availableVideos={mockVideos}
          availableAudio={mockAudio}
        />
      );

      // Select both video and audio
      const videoSelect = screen.getByLabelText('Video Clip');
      fireEvent.change(videoSelect, { target: { value: 'video-1' } });

      const audioSelect = screen.getByLabelText('Audio Track');
      fireEvent.change(audioSelect, { target: { value: 'audio-1' } });

      const applyButton = screen.getByText('Apply Lip Sync');
      expect(applyButton).not.toBeDisabled();
    });
  });

  describe('Provider Fetching', () => {
    it('should fetch providers on open', async () => {
      const mockBackendRequest = vi.fn().mockResolvedValue({ providers: mockProviders });
      window.electronAPI.backendRequest = mockBackendRequest;

      render(
        <LipSyncPanel
          isOpen={true}
          onClose={vi.fn()}
          availableVideos={mockVideos}
          availableAudio={mockAudio}
        />
      );

      await waitFor(() => {
        expect(mockBackendRequest).toHaveBeenCalledWith('lipSync.getProviders', {});
      });
    });

    it('should display available providers', async () => {
      useLipSyncStore.setState({ providers: mockProviders });

      render(
        <LipSyncPanel
          isOpen={true}
          onClose={vi.fn()}
          availableVideos={mockVideos}
          availableAudio={mockAudio}
        />
      );

      expect(screen.getByText(/Mock Lip Sync/)).toBeInTheDocument();
      expect(screen.getByText(/Rhubarb Lip Sync/)).toBeInTheDocument();
    });
  });

  describe('Starting Lip Sync', () => {
    it('should call startLipSync when apply clicked', async () => {
      const mockBackendRequest = vi.fn().mockResolvedValue(mockJob);
      window.electronAPI.backendRequest = mockBackendRequest;

      useLipSyncStore.setState({ providers: mockProviders });

      render(
        <LipSyncPanel
          isOpen={true}
          onClose={vi.fn()}
          availableVideos={mockVideos}
          availableAudio={mockAudio}
        />
      );

      // Select video and audio
      const videoSelect = screen.getByLabelText('Video Clip');
      fireEvent.change(videoSelect, { target: { value: 'video-1' } });

      const audioSelect = screen.getByLabelText('Audio Track');
      fireEvent.change(audioSelect, { target: { value: 'audio-1' } });

      // Click apply
      const applyButton = screen.getByText('Apply Lip Sync');
      fireEvent.click(applyButton);

      await waitFor(() => {
        expect(mockBackendRequest).toHaveBeenCalledWith('lipsync.start', {
          video_id: 'video-1',
          audio_id: 'audio-1',
          provider: 'mock',
        });
      });
    });

    it('should reset selection after successful start', async () => {
      const mockBackendRequest = vi.fn().mockResolvedValue(mockJob);
      window.electronAPI.backendRequest = mockBackendRequest;

      useLipSyncStore.setState({ providers: mockProviders });

      render(
        <LipSyncPanel
          isOpen={true}
          onClose={vi.fn()}
          availableVideos={mockVideos}
          availableAudio={mockAudio}
        />
      );

      // Select and start
      const videoSelect = screen.getByLabelText('Video Clip') as HTMLSelectElement;
      fireEvent.change(videoSelect, { target: { value: 'video-1' } });

      const audioSelect = screen.getByLabelText('Audio Track') as HTMLSelectElement;
      fireEvent.change(audioSelect, { target: { value: 'audio-1' } });

      const applyButton = screen.getByText('Apply Lip Sync');
      fireEvent.click(applyButton);

      await waitFor(() => {
        expect(videoSelect.value).toBe('');
        expect(audioSelect.value).toBe('');
      });
    });
  });

  describe('Job Display', () => {
    it('should show empty state when no jobs', () => {
      render(
        <LipSyncPanel
          isOpen={true}
          onClose={vi.fn()}
          availableVideos={mockVideos}
          availableAudio={mockAudio}
        />
      );

      expect(screen.getByText('No lip sync jobs yet')).toBeInTheDocument();
    });

    it('should display processing job', () => {
      useLipSyncStore.setState({ jobs: [mockJob] });

      render(
        <LipSyncPanel
          isOpen={true}
          onClose={vi.fn()}
          availableVideos={mockVideos}
          availableAudio={mockAudio}
        />
      );

      expect(screen.getByText(/Job 1/)).toBeInTheDocument();
      expect(screen.getByText('Processing')).toBeInTheDocument();
      expect(screen.getByText('Analyzing audio...')).toBeInTheDocument();
      expect(screen.getByText('45%')).toBeInTheDocument();
    });

    it('should display completed job', () => {
      const completedJob = {
        ...mockJob,
        status: 'completed' as const,
        progress_percent: 100,
        progress_message: 'Complete',
        output_path: '/path/to/output.mp4',
        completed_at: new Date().toISOString(),
      };

      useLipSyncStore.setState({ jobs: [completedJob] });

      render(
        <LipSyncPanel
          isOpen={true}
          onClose={vi.fn()}
          availableVideos={mockVideos}
          availableAudio={mockAudio}
        />
      );

      expect(screen.getByText('Completed')).toBeInTheDocument();
      expect(screen.getByText('Download')).toBeInTheDocument();
    });

    it('should display failed job', () => {
      const failedJob = {
        ...mockJob,
        status: 'failed' as const,
        error_message: 'Provider timeout',
      };

      useLipSyncStore.setState({ jobs: [failedJob] });

      render(
        <LipSyncPanel
          isOpen={true}
          onClose={vi.fn()}
          availableVideos={mockVideos}
          availableAudio={mockAudio}
        />
      );

      expect(screen.getByText('Failed')).toBeInTheDocument();
      expect(screen.getByText('Provider timeout')).toBeInTheDocument();
      expect(screen.getByText('Retry')).toBeInTheDocument();
    });
  });

  describe('Job Actions', () => {
    it('should cancel processing job', async () => {
      const mockBackendRequest = vi.fn().mockResolvedValue({ status: 'cancelled' });
      window.electronAPI.backendRequest = mockBackendRequest;

      useLipSyncStore.setState({ jobs: [mockJob] });

      render(
        <LipSyncPanel
          isOpen={true}
          onClose={vi.fn()}
          availableVideos={mockVideos}
          availableAudio={mockAudio}
        />
      );

      const cancelButton = screen.getByText('Cancel');
      fireEvent.click(cancelButton);

      await waitFor(() => {
        expect(mockBackendRequest).toHaveBeenCalledWith('lipsync.cancel', {
          job_id: 'lipsync-1',
        });
      });
    });

    it('should download completed job', async () => {
      const mockBackendRequest = vi.fn().mockResolvedValue({ success: true });
      window.electronAPI.backendRequest = mockBackendRequest;

      const completedJob = {
        ...mockJob,
        status: 'completed' as const,
        output_path: '/path/to/output.mp4',
      };

      useLipSyncStore.setState({ jobs: [completedJob] });

      render(
        <LipSyncPanel
          isOpen={true}
          onClose={vi.fn()}
          availableVideos={mockVideos}
          availableAudio={mockAudio}
        />
      );

      const downloadButton = screen.getByText('Download');
      fireEvent.click(downloadButton);

      await waitFor(() => {
        expect(mockBackendRequest).toHaveBeenCalledWith('files.downloadFile', {
          path: '/path/to/output.mp4',
          filename: 'lipsync-lipsync-1.mp4',
        });
      });
    });
  });

  describe('Error Handling', () => {
    it('should display error message', async () => {
      render(
        <LipSyncPanel
          isOpen={true}
          onClose={vi.fn()}
          availableVideos={mockVideos}
          availableAudio={mockAudio}
        />
      );

      // Set error after component is rendered
      useLipSyncStore.setState({ error: 'Provider not available' });

      await waitFor(() => {
        expect(screen.getByText('Provider not available')).toBeInTheDocument();
      });
    });

    it('should dismiss error when clicked', async () => {
      render(
        <LipSyncPanel
          isOpen={true}
          onClose={vi.fn()}
          availableVideos={mockVideos}
          availableAudio={mockAudio}
        />
      );

      // Set error after component is rendered
      useLipSyncStore.setState({ error: 'Provider not available' });

      await waitFor(() => {
        expect(screen.getByText('Provider not available')).toBeInTheDocument();
      });

      const dismissButton = screen.getByText('Dismiss');
      fireEvent.click(dismissButton);

      expect(useLipSyncStore.getState().error).toBeNull();
    });
  });

  describe('Processing State', () => {
    it('should disable form when processing', () => {
      useLipSyncStore.setState({
        jobs: [mockJob],
        providers: mockProviders,
      });

      render(
        <LipSyncPanel
          isOpen={true}
          onClose={vi.fn()}
          availableVideos={mockVideos}
          availableAudio={mockAudio}
        />
      );

      const videoSelect = screen.getByLabelText('Video Clip');
      const audioSelect = screen.getByLabelText('Audio Track');
      const providerSelect = screen.getByLabelText('Provider');

      expect(videoSelect).toBeDisabled();
      expect(audioSelect).toBeDisabled();
      expect(providerSelect).toBeDisabled();
    });

    it('should show processing state in button', () => {
      useLipSyncStore.setState({ jobs: [mockJob] });

      render(
        <LipSyncPanel
          isOpen={true}
          onClose={vi.fn()}
          availableVideos={mockVideos}
          availableAudio={mockAudio}
        />
      );

      expect(screen.getByText('Processing...')).toBeInTheDocument();
    });
  });

  describe('Accessibility', () => {
    it('should have dialog role', () => {
      render(
        <LipSyncPanel
          isOpen={true}
          onClose={vi.fn()}
          availableVideos={mockVideos}
          availableAudio={mockAudio}
        />
      );

      expect(screen.getByRole('dialog')).toBeInTheDocument();
    });

    it('should have accessible labels', () => {
      render(
        <LipSyncPanel
          isOpen={true}
          onClose={vi.fn()}
          availableVideos={mockVideos}
          availableAudio={mockAudio}
        />
      );

      expect(screen.getByLabelText('Video Clip')).toBeInTheDocument();
      expect(screen.getByLabelText('Audio Track')).toBeInTheDocument();
      expect(screen.getByLabelText('Provider')).toBeInTheDocument();
    });

    it('should have title attributes on buttons', () => {
      render(
        <LipSyncPanel
          isOpen={true}
          onClose={vi.fn()}
          availableVideos={mockVideos}
          availableAudio={mockAudio}
        />
      );

      expect(screen.getByTitle('Close panel')).toBeInTheDocument();
    });
  });
});
