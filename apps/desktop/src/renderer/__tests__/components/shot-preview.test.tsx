/**
 * Shot Preview component tests.
 * Tests inline video preview functionality and integration.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, within } from '@testing-library/react';
import { ShotPreview } from '../../components/shot-preview';

// Mock VideoPlayer component
vi.mock('../../components/video-player', () => ({
  VideoPlayer: ({ src, poster, onError, className }: any) => (
    <div data-testid="video-player" data-src={src} data-poster={poster} className={className}>
      Video Player Mock
      <button onClick={() => onError?.('Test error')}>Trigger Error</button>
    </div>
  ),
  useVideoPlayer: () => ({
    ref: { current: null },
    play: vi.fn(),
    pause: vi.fn(),
    seek: vi.fn(),
    getCurrentTime: () => 0,
    getDuration: () => 120,
  }),
}));

// Mock Electron API
global.window.electronAPI = {
  backendRequest: vi.fn(),
} as any;

const mockShot = {
  id: 'shot-123',
  shotNumber: '1A',
  description: 'Wide shot of character entering room',
  state: 'generated',
  outputVideoPath: '/path/to/video.mp4',
  outputThumbnailPath: '/path/to/thumbnail.jpg',
  durationSeconds: 5.5,
};

const mockJob = {
  id: 'job-456',
  jobNumber: 1,
  status: 'completed',
  progressPercent: 100,
  progressMessage: 'Complete',
  outputPath: '/path/to/video.mp4',
};

describe('ShotPreview', () => {
  const mockHandlers = {
    onApprove: vi.fn(),
    onReject: vi.fn(),
    onRegenerate: vi.fn(),
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('Basic Rendering', () => {
    it('should render shot preview card', () => {
      render(<ShotPreview shot={mockShot} {...mockHandlers} />);
      expect(screen.getByText('1A')).toBeInTheDocument();
      expect(screen.getByText(/5.5s/)).toBeInTheDocument();
    });

    it('should display shot description', () => {
      render(<ShotPreview shot={mockShot} {...mockHandlers} />);
      expect(screen.getByText('Wide shot of character entering room')).toBeInTheDocument();
    });

    it('should show thumbnail when not playing', () => {
      const { container } = render(<ShotPreview shot={mockShot} {...mockHandlers} />);
      const thumbnail = container.querySelector('img');
      expect(thumbnail).toBeInTheDocument();
      expect(thumbnail).toHaveAttribute('src', 'file:///path/to/thumbnail.jpg');
    });
  });

  describe('Video Player Integration', () => {
    it('should show thumbnail by default', () => {
      const { container } = render(<ShotPreview shot={mockShot} {...mockHandlers} />);
      const thumbnail = container.querySelector('img');
      expect(thumbnail).toBeInTheDocument();
      expect(screen.queryByTestId('video-player')).not.toBeInTheDocument();
    });

    it('should show video player when play button clicked', () => {
      render(<ShotPreview shot={mockShot} {...mockHandlers} />);

      // Find and click the play overlay button
      const playButton = screen.getByRole('button', { name: /click to preview/i });
      fireEvent.click(playButton);

      // Video player should now be visible
      expect(screen.getByTestId('video-player')).toBeInTheDocument();
    });

    it('should pass correct props to video player', () => {
      render(<ShotPreview shot={mockShot} {...mockHandlers} />);

      // Expand to video player
      const playButton = screen.getByRole('button', { name: /click to preview/i });
      fireEvent.click(playButton);

      const videoPlayer = screen.getByTestId('video-player');
      expect(videoPlayer).toHaveAttribute('data-src', '/path/to/video.mp4');
      expect(videoPlayer).toHaveAttribute('data-poster', '/path/to/thumbnail.jpg');
    });

    it('should show collapse button when video is playing', () => {
      render(<ShotPreview shot={mockShot} {...mockHandlers} />);

      // Expand video
      const playButton = screen.getByRole('button', { name: /click to preview/i });
      fireEvent.click(playButton);

      // Collapse button should be visible
      expect(screen.getByTitle('Close player')).toBeInTheDocument();
    });

    it('should collapse video player when collapse button clicked', () => {
      render(<ShotPreview shot={mockShot} {...mockHandlers} />);

      // Expand video
      const playButton = screen.getByRole('button', { name: /click to preview/i });
      fireEvent.click(playButton);

      // Click collapse button
      const collapseButton = screen.getByTitle('Close player');
      fireEvent.click(collapseButton);

      // Should return to thumbnail view
      expect(screen.queryByTestId('video-player')).not.toBeInTheDocument();
    });

    it('should handle video player errors', () => {
      render(<ShotPreview shot={mockShot} {...mockHandlers} />);

      // Expand video
      const playButton = screen.getByRole('button', { name: /click to preview/i });
      fireEvent.click(playButton);

      // Trigger error in video player
      const errorButton = screen.getByText('Trigger Error');
      fireEvent.click(errorButton);

      // Should collapse back to thumbnail
      expect(screen.queryByTestId('video-player')).not.toBeInTheDocument();
    });
  });

  describe('Quick Action Buttons', () => {
    it('should show quick actions when video is playing', () => {
      render(<ShotPreview shot={mockShot} {...mockHandlers} />);

      // Expand video
      const playButton = screen.getByRole('button', { name: /click to preview/i });
      fireEvent.click(playButton);

      // Quick action buttons should be visible
      expect(screen.getByTitle('Approve this take')).toBeInTheDocument();
      expect(screen.getByTitle('Generate another take')).toBeInTheDocument();
      expect(screen.getByTitle('Download video file')).toBeInTheDocument();
    });

    it('should not show quick actions when video is not playing', () => {
      render(<ShotPreview shot={mockShot} {...mockHandlers} />);

      // Quick actions should not be visible
      expect(screen.queryByTitle('Approve this take')).not.toBeInTheDocument();
    });

    it('should call onApprove and collapse when Use This Take clicked', () => {
      render(<ShotPreview shot={mockShot} {...mockHandlers} />);

      // Expand video
      const playButton = screen.getByRole('button', { name: /click to preview/i });
      fireEvent.click(playButton);

      // Click Use This Take
      const approveButton = screen.getByTitle('Approve this take');
      fireEvent.click(approveButton);

      expect(mockHandlers.onApprove).toHaveBeenCalledWith('shot-123');
      // Should collapse
      expect(screen.queryByTestId('video-player')).not.toBeInTheDocument();
    });

    it('should call onRegenerate and collapse when Regenerate clicked', () => {
      render(<ShotPreview shot={mockShot} {...mockHandlers} />);

      // Expand video
      const playButton = screen.getByRole('button', { name: /click to preview/i });
      fireEvent.click(playButton);

      // Click Regenerate
      const regenerateButton = screen.getByTitle('Generate another take');
      fireEvent.click(regenerateButton);

      expect(mockHandlers.onRegenerate).toHaveBeenCalledWith('shot-123');
      expect(screen.queryByTestId('video-player')).not.toBeInTheDocument();
    });

    it('should trigger download when Download button clicked', async () => {
      render(<ShotPreview shot={mockShot} {...mockHandlers} />);

      // Expand video
      const playButton = screen.getByRole('button', { name: /click to preview/i });
      fireEvent.click(playButton);

      // Click Download
      const downloadButton = screen.getByTitle('Download video file');
      fireEvent.click(downloadButton);

      expect(window.electronAPI.backendRequest).toHaveBeenCalledWith('files.downloadFile', {
        path: '/path/to/video.mp4',
        filename: 'shot-1A.mp4',
      });
    });

    it('should disable approve button when shot is already approved', () => {
      const approvedShot = { ...mockShot, state: 'approved' };
      render(<ShotPreview shot={approvedShot} {...mockHandlers} />);

      // Expand video
      const playButton = screen.getByRole('button', { name: /click to preview/i });
      fireEvent.click(playButton);

      const approveButton = screen.getByTitle('Approve this take');
      expect(approveButton).toBeDisabled();
    });
  });

  describe('Shot States', () => {
    it('should show generating state', () => {
      const generatingJob = { ...mockJob, status: 'running', progressPercent: 45 };
      render(
        <ShotPreview
          shot={{ ...mockShot, state: 'generating' }}
          latestJob={generatingJob}
          {...mockHandlers}
        />
      );

      expect(screen.getByText(/generating/i)).toBeInTheDocument();
    });

    it('should show failed state with retry button', () => {
      const failedJob = {
        ...mockJob,
        status: 'failed',
        errorMessage: 'Provider timeout',
      };
      render(
        <ShotPreview
          shot={{ ...mockShot, state: 'failed' }}
          latestJob={failedJob}
          {...mockHandlers}
        />
      );

      expect(screen.getByText('Generation Failed')).toBeInTheDocument();
      expect(screen.getByText('Provider timeout')).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /retry/i })).toBeInTheDocument();
    });

    it('should show approved badge', () => {
      const approvedShot = { ...mockShot, state: 'approved' };
      const { container } = render(<ShotPreview shot={approvedShot} {...mockHandlers} />);

      // Check for the approved badge (with icon)
      const badge = container.querySelector('.bg-green-500\\/90');
      expect(badge).toBeInTheDocument();
      expect(badge).toHaveTextContent('Approved');
    });

    it('should hide play button when no video path', () => {
      const shotWithoutVideo = { ...mockShot, outputVideoPath: undefined };
      render(<ShotPreview shot={shotWithoutVideo} {...mockHandlers} />);

      expect(screen.queryByRole('button', { name: /click to preview/i })).not.toBeInTheDocument();
    });
  });

  describe('Standard Action Buttons', () => {
    it('should show approve/reject buttons for generated shots', () => {
      render(<ShotPreview shot={mockShot} {...mockHandlers} />);

      expect(screen.getByRole('button', { name: /approve/i })).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /reject/i })).toBeInTheDocument();
    });

    it('should not show approve/reject for approved shots when not playing', () => {
      const approvedShot = { ...mockShot, state: 'approved' };
      render(<ShotPreview shot={approvedShot} {...mockHandlers} />);

      // Standard approve/reject buttons should not be visible for approved shots
      const approveButtons = screen.queryAllByText(/approve/i);
      const rejectButtons = screen.queryAllByText(/reject/i);

      // Should not find the standard Approve/Reject action buttons
      expect(rejectButtons.length).toBe(0);
    });

    it('should open reject modal when reject clicked', () => {
      render(<ShotPreview shot={mockShot} {...mockHandlers} />);

      const rejectButton = screen.getByRole('button', { name: /reject/i });
      fireEvent.click(rejectButton);

      // Check for modal content (using getAllByText since modal title and button have same text)
      const rejectTexts = screen.getAllByText('Reject Shot');
      expect(rejectTexts.length).toBeGreaterThan(0); // Modal opened
      expect(screen.getByPlaceholderText(/character looks different/i)).toBeInTheDocument();
    });
  });

  describe('Status Badge', () => {
    it('should show correct status for each state', () => {
      const states = [
        { state: 'approved', expectedText: 'Approved' },
        { state: 'generated', expectedText: 'Generated' },
        { state: 'generating', expectedText: 'Generating' },
        { state: 'queued', expectedText: 'Queued' },
        { state: 'failed', expectedText: 'Failed' },
        { state: 'rejected', expectedText: 'Rejected' },
        { state: 'planned', expectedText: 'Planned' },
      ];

      states.forEach(({ state, expectedText }) => {
        const { container, unmount } = render(
          <ShotPreview shot={{ ...mockShot, state }} {...mockHandlers} />
        );
        // Find status badge specifically (not the approval badge)
        const statusBadge = container.querySelector('.text-xs.px-2.py-0\\.5.rounded-full');
        expect(statusBadge).toHaveTextContent(expectedText);
        unmount();
      });
    });
  });

  describe('Disabled State', () => {
    it('should disable action buttons when disabled prop is true', () => {
      render(<ShotPreview shot={mockShot} disabled={true} {...mockHandlers} />);

      // Get action buttons (Approve, Reject, Regenerate)
      const approveButton = screen.getByRole('button', { name: /approve/i });
      const rejectButton = screen.getByRole('button', { name: /reject/i });

      expect(approveButton).toBeDisabled();
      expect(rejectButton).toBeDisabled();
    });
  });

  describe('Accessibility', () => {
    it('should have accessible button labels', () => {
      render(<ShotPreview shot={mockShot} {...mockHandlers} />);

      // Expand video
      const playButton = screen.getByRole('button', { name: /click to preview/i });
      fireEvent.click(playButton);

      // Check all action buttons have titles
      expect(screen.getByTitle('Approve this take')).toBeInTheDocument();
      expect(screen.getByTitle('Generate another take')).toBeInTheDocument();
      expect(screen.getByTitle('Download video file')).toBeInTheDocument();
      expect(screen.getByTitle('Close player')).toBeInTheDocument();
    });
  });
});
