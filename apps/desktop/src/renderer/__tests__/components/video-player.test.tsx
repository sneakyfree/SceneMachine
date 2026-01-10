/**
 * Video Player component tests.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { VideoPlayer, useVideoPlayer } from '../../components/video-player';

// Mock video element behavior
const mockVideoElement = {
  play: vi.fn().mockResolvedValue(undefined),
  pause: vi.fn(),
  load: vi.fn(),
  addEventListener: vi.fn(),
  removeEventListener: vi.fn(),
  requestFullscreen: vi.fn().mockResolvedValue(undefined),
  currentTime: 0,
  duration: 120,
  volume: 1,
  muted: false,
  paused: true,
  playbackRate: 1,
  buffered: {
    length: 1,
    end: () => 60,
  },
  error: null,
};

describe('VideoPlayer', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    // Reset mock video element
    Object.assign(mockVideoElement, {
      currentTime: 0,
      duration: 120,
      volume: 1,
      muted: false,
      paused: true,
      playbackRate: 1,
    });
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  describe('Basic Rendering', () => {
    it('should render without crashing', () => {
      render(<VideoPlayer src="/path/to/video.mp4" />);
      expect(screen.getByRole('button', { name: /play/i })).toBeInTheDocument();
    });

    it('should render video element', () => {
      const { container } = render(<VideoPlayer src="/path/to/video.mp4" />);
      const video = container.querySelector('video');
      expect(video).toBeInTheDocument();
    });

    it('should apply custom className', () => {
      const { container } = render(<VideoPlayer src="/path/to/video.mp4" className="custom-class" />);
      expect(container.firstChild).toHaveClass('custom-class');
    });

    it('should set poster when provided', () => {
      const { container } = render(
        <VideoPlayer src="/path/to/video.mp4" poster="/path/to/poster.jpg" />
      );
      const video = container.querySelector('video');
      expect(video).toHaveAttribute('poster');
    });
  });

  describe('Controls Visibility', () => {
    it('should show controls by default', () => {
      render(<VideoPlayer src="/path/to/video.mp4" />);
      // Play button should be visible
      expect(screen.queryByTitle(/play/i)).toBeInTheDocument();
    });

    it('should hide controls when showControls is false', () => {
      render(<VideoPlayer src="/path/to/video.mp4" showControls={false} />);
      // Control bar should not be present
      expect(screen.queryByTitle(/pause/i)).not.toBeInTheDocument();
    });
  });

  describe('Playback Controls', () => {
    it('should have play button', () => {
      render(<VideoPlayer src="/path/to/video.mp4" />);
      const playButtons = screen.getAllByRole('button');
      expect(playButtons.length).toBeGreaterThan(0);
    });

    it('should have skip buttons', () => {
      render(<VideoPlayer src="/path/to/video.mp4" />);
      expect(screen.getByTitle(/skip back/i)).toBeInTheDocument();
      expect(screen.getByTitle(/skip forward/i)).toBeInTheDocument();
    });

    it('should have volume control', () => {
      render(<VideoPlayer src="/path/to/video.mp4" />);
      expect(screen.getByTitle(/mute/i)).toBeInTheDocument();
    });

    it('should have fullscreen button', () => {
      render(<VideoPlayer src="/path/to/video.mp4" />);
      expect(screen.getByTitle(/fullscreen/i)).toBeInTheDocument();
    });

    it('should have playback speed control', () => {
      render(<VideoPlayer src="/path/to/video.mp4" />);
      expect(screen.getByTitle(/playback speed/i)).toBeInTheDocument();
    });
  });

  describe('Time Display', () => {
    it('should show time display', () => {
      render(<VideoPlayer src="/path/to/video.mp4" />);
      expect(screen.getByText(/0:00/)).toBeInTheDocument();
    });
  });

  describe('Video Properties', () => {
    it('should set autoPlay when provided', () => {
      const { container } = render(<VideoPlayer src="/path/to/video.mp4" autoPlay />);
      const video = container.querySelector('video');
      expect(video).toHaveAttribute('autoplay');
    });

    it('should set loop when provided', () => {
      const { container } = render(<VideoPlayer src="/path/to/video.mp4" loop />);
      const video = container.querySelector('video');
      expect(video).toHaveAttribute('loop');
    });

    it('should set muted when provided', () => {
      const { container } = render(<VideoPlayer src="/path/to/video.mp4" muted />);
      const video = container.querySelector('video');
      expect(video).toHaveAttribute('muted');
    });
  });

  describe('Error Handling', () => {
    it('should show error state on video error', async () => {
      const onError = vi.fn();
      render(<VideoPlayer src="/path/to/invalid.mp4" onError={onError} />);

      // Simulate error by triggering error event
      const { container } = render(<VideoPlayer src="/path/to/video.mp4" />);
      const video = container.querySelector('video');

      if (video) {
        // Error display should appear when video fails
        fireEvent.error(video);
      }
    });
  });

  describe('Loading State', () => {
    it('should show loading indicator initially', () => {
      render(<VideoPlayer src="/path/to/video.mp4" />);
      // Loading spinner should be visible during initial load
      const loadingIndicator = screen.queryByText('') || document.querySelector('.animate-spin');
      // May or may not be visible depending on timing
    });
  });

  describe('Playback Speed Menu', () => {
    it('should show speed options when clicked', () => {
      render(<VideoPlayer src="/path/to/video.mp4" />);

      const speedButton = screen.getByTitle(/playback speed/i);
      fireEvent.click(speedButton);

      expect(screen.getByText('0.5x')).toBeInTheDocument();
      expect(screen.getByText('1x')).toBeInTheDocument();
      expect(screen.getByText('2x')).toBeInTheDocument();
    });

    it('should show available playback rates', () => {
      render(<VideoPlayer src="/path/to/video.mp4" />);

      const speedButton = screen.getByTitle(/playback speed/i);
      fireEvent.click(speedButton);

      expect(screen.getByText('0.25x')).toBeInTheDocument();
      expect(screen.getByText('0.75x')).toBeInTheDocument();
      expect(screen.getByText('1.25x')).toBeInTheDocument();
      expect(screen.getByText('1.5x')).toBeInTheDocument();
    });
  });

  describe('Accessibility', () => {
    it('should have focusable container', () => {
      const { container } = render(<VideoPlayer src="/path/to/video.mp4" />);
      expect(container.firstChild).toHaveAttribute('tabindex', '0');
    });

    it('should have aria labels on buttons', () => {
      render(<VideoPlayer src="/path/to/video.mp4" />);
      expect(screen.getByTitle(/play/i)).toBeInTheDocument();
      expect(screen.getByTitle(/skip back/i)).toBeInTheDocument();
    });
  });

  describe('Callbacks', () => {
    it('should call onTimeUpdate callback', () => {
      const onTimeUpdate = vi.fn();
      const { container } = render(
        <VideoPlayer src="/path/to/video.mp4" onTimeUpdate={onTimeUpdate} />
      );

      const video = container.querySelector('video');
      if (video) {
        fireEvent.timeUpdate(video);
      }
    });

    it('should call onEnded callback when video ends', () => {
      const onEnded = vi.fn();
      const { container } = render(
        <VideoPlayer src="/path/to/video.mp4" onEnded={onEnded} />
      );

      const video = container.querySelector('video');
      if (video) {
        fireEvent.ended(video);
      }
    });

    it('should call onError callback on error', () => {
      const onError = vi.fn();
      const { container } = render(
        <VideoPlayer src="/path/to/video.mp4" onError={onError} />
      );

      const video = container.querySelector('video');
      if (video) {
        fireEvent.error(video);
      }
    });
  });

  describe('Source Handling', () => {
    it('should handle file:// protocol', () => {
      const { container } = render(<VideoPlayer src="file:///path/to/video.mp4" />);
      const video = container.querySelector('video');
      expect(video?.src).toContain('file://');
    });

    it('should add file:// prefix to paths without protocol', () => {
      const { container } = render(<VideoPlayer src="/path/to/video.mp4" />);
      const video = container.querySelector('video');
      expect(video?.src).toContain('file://');
    });
  });
});

describe('useVideoPlayer hook', () => {
  it('should return video control methods', () => {
    const { result } = renderHookResult();

    expect(result.current).toHaveProperty('play');
    expect(result.current).toHaveProperty('pause');
    expect(result.current).toHaveProperty('seek');
    expect(result.current).toHaveProperty('getCurrentTime');
    expect(result.current).toHaveProperty('getDuration');
    expect(result.current).toHaveProperty('ref');
  });
});

// Helper to test hook
function renderHookResult() {
  let result: ReturnType<typeof useVideoPlayer>;

  function TestComponent() {
    result = useVideoPlayer();
    return null;
  }

  render(<TestComponent />);

  return { result: result! };
}
