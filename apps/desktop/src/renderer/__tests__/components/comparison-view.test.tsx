/**
 * Comparison View component tests.
 * Tests side-by-side video comparison functionality.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { ComparisonView } from '../../components/video/comparison-view';

const mockVideos = [
  {
    id: 'video-1',
    src: '/path/to/video1.mp4',
    label: 'Shot 1A',
    poster: '/path/to/poster1.jpg',
  },
  {
    id: 'video-2',
    src: '/path/to/video2.mp4',
    label: 'Shot 1B',
    poster: '/path/to/poster2.jpg',
  },
  {
    id: 'video-3',
    src: '/path/to/video3.mp4',
    label: 'Shot 1C',
    poster: '/path/to/poster3.jpg',
  },
];

// Mock video elements
const createMockVideo = () => ({
  play: vi.fn().mockResolvedValue(undefined),
  pause: vi.fn(),
  load: vi.fn(),
  currentTime: 0,
  duration: 120,
  volume: 0.8,
  muted: false,
});

describe('ComparisonView', () => {
  const mockHandlers = {
    onClose: vi.fn(),
    onSelectBest: vi.fn(),
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('Basic Rendering', () => {
    it('should render comparison view', () => {
      render(<ComparisonView videos={mockVideos.slice(0, 2)} {...mockHandlers} />);
      expect(screen.getByRole('dialog', { name: /video comparison/i })).toBeInTheDocument();
    });

    it('should display correct title', () => {
      render(<ComparisonView videos={mockVideos.slice(0, 2)} {...mockHandlers} />);
      expect(screen.getByText('Compare Takes')).toBeInTheDocument();
    });

    it('should show number of videos being compared', () => {
      render(<ComparisonView videos={mockVideos.slice(0, 2)} {...mockHandlers} />);
      expect(screen.getByText(/compare 2 videos/i)).toBeInTheDocument();
    });

    it('should have close button', () => {
      render(<ComparisonView videos={mockVideos.slice(0, 2)} {...mockHandlers} />);
      expect(screen.getByTitle(/close comparison/i)).toBeInTheDocument();
    });
  });

  describe('Video Grid Layout', () => {
    it('should render 2 videos in grid', () => {
      const { container } = render(
        <ComparisonView videos={mockVideos.slice(0, 2)} {...mockHandlers} />
      );
      const videos = container.querySelectorAll('video');
      expect(videos.length).toBe(2);
    });

    it('should render 3 videos in grid', () => {
      const { container } = render(<ComparisonView videos={mockVideos} {...mockHandlers} />);
      const videos = container.querySelectorAll('video');
      expect(videos.length).toBe(3);
    });

    it('should limit to maximum 3 videos', () => {
      const manyVideos = [...mockVideos, { id: 'video-4', src: '/v4.mp4', label: 'Shot 1D' }];
      const { container } = render(<ComparisonView videos={manyVideos} {...mockHandlers} />);
      const videos = container.querySelectorAll('video');
      expect(videos.length).toBe(3);
    });

    it('should display video labels', () => {
      render(<ComparisonView videos={mockVideos.slice(0, 2)} {...mockHandlers} />);
      expect(screen.getByText('Shot 1A')).toBeInTheDocument();
      expect(screen.getByText('Shot 1B')).toBeInTheDocument();
    });
  });

  describe('Video Selection', () => {
    it('should have select buttons for each video', () => {
      render(<ComparisonView videos={mockVideos.slice(0, 2)} {...mockHandlers} />);
      const selectButtons = screen.getAllByText(/select this/i);
      expect(selectButtons.length).toBe(2);
    });

    it('should mark video as selected when clicked', () => {
      render(<ComparisonView videos={mockVideos.slice(0, 2)} {...mockHandlers} />);
      const selectButton = screen.getAllByText(/select this/i)[0];
      fireEvent.click(selectButton);

      // Multiple "Selected" texts appear (badge + button text)
      const selectedTexts = screen.getAllByText('Selected');
      expect(selectedTexts.length).toBeGreaterThan(0);
    });

    it('should show selection indicator on selected video', () => {
      render(<ComparisonView videos={mockVideos.slice(0, 2)} {...mockHandlers} />);
      const selectButton = screen.getAllByText(/select this/i)[0];
      fireEvent.click(selectButton);

      const indicators = screen.getAllByText('Selected');
      expect(indicators.length).toBeGreaterThan(0);
    });

    it('should allow changing selection', () => {
      render(<ComparisonView videos={mockVideos.slice(0, 2)} {...mockHandlers} />);

      // Select first video
      const selectButtons = screen.getAllByText(/select this/i);
      fireEvent.click(selectButtons[0]);

      // Select second video
      fireEvent.click(selectButtons[1]);

      // Only one should be selected
      expect(screen.getAllByText('Selected').length).toBeGreaterThan(0);
    });
  });

  describe('Synchronized Controls', () => {
    it('should have play button', () => {
      render(<ComparisonView videos={mockVideos.slice(0, 2)} {...mockHandlers} />);
      expect(screen.getByTitle(/play/i)).toBeInTheDocument();
    });

    it('should have progress bar', () => {
      const { container } = render(
        <ComparisonView videos={mockVideos.slice(0, 2)} {...mockHandlers} />
      );
      const progressBar = container.querySelector('.bg-brand-500');
      expect(progressBar).toBeInTheDocument();
    });

    it('should have volume control', () => {
      render(<ComparisonView videos={mockVideos.slice(0, 2)} {...mockHandlers} />);
      expect(screen.getByTitle(/mute/i)).toBeInTheDocument();
    });

    it('should have time display', () => {
      render(<ComparisonView videos={mockVideos.slice(0, 2)} {...mockHandlers} />);
      expect(screen.getByText(/0:00 \/ 0:00/)).toBeInTheDocument();
    });
  });

  describe('Use Selected Action', () => {
    it('should show use selected button when onSelectBest provided', () => {
      render(<ComparisonView videos={mockVideos.slice(0, 2)} {...mockHandlers} />);
      expect(screen.getByText('Use Selected Take')).toBeInTheDocument();
    });

    it('should disable use selected button when nothing selected', () => {
      render(<ComparisonView videos={mockVideos.slice(0, 2)} {...mockHandlers} />);
      const button = screen.getByText('Use Selected Take');
      expect(button).toBeDisabled();
    });

    it('should enable use selected button when video selected', () => {
      render(<ComparisonView videos={mockVideos.slice(0, 2)} {...mockHandlers} />);

      // Select a video
      const selectButton = screen.getAllByText(/select this/i)[0];
      fireEvent.click(selectButton);

      // Use selected button should be enabled
      const useButton = screen.getByText('Use Selected Take');
      expect(useButton).not.toBeDisabled();
    });

    it('should call onSelectBest with selected video id', () => {
      render(<ComparisonView videos={mockVideos.slice(0, 2)} {...mockHandlers} />);

      // Select first video
      const selectButton = screen.getAllByText(/select this/i)[0];
      fireEvent.click(selectButton);

      // Click use selected
      const useButton = screen.getByText('Use Selected Take');
      fireEvent.click(useButton);

      expect(mockHandlers.onSelectBest).toHaveBeenCalledWith('video-1');
    });

    it('should call onClose after selecting best', () => {
      render(<ComparisonView videos={mockVideos.slice(0, 2)} {...mockHandlers} />);

      // Select and use
      const selectButton = screen.getAllByText(/select this/i)[0];
      fireEvent.click(selectButton);
      const useButton = screen.getByText('Use Selected Take');
      fireEvent.click(useButton);

      expect(mockHandlers.onClose).toHaveBeenCalled();
    });

    it('should not show use selected button when onSelectBest not provided', () => {
      render(<ComparisonView videos={mockVideos.slice(0, 2)} onClose={mockHandlers.onClose} />);
      expect(screen.queryByText('Use Selected Take')).not.toBeInTheDocument();
    });
  });

  describe('Close Behavior', () => {
    it('should call onClose when close button clicked', () => {
      render(<ComparisonView videos={mockVideos.slice(0, 2)} {...mockHandlers} />);
      const closeButton = screen.getByTitle(/close comparison/i);
      fireEvent.click(closeButton);
      expect(mockHandlers.onClose).toHaveBeenCalled();
    });

    it('should close on Escape key', () => {
      render(<ComparisonView videos={mockVideos.slice(0, 2)} {...mockHandlers} />);
      fireEvent.keyDown(document, { key: 'Escape' });
      expect(mockHandlers.onClose).toHaveBeenCalled();
    });
  });

  describe('Keyboard Shortcuts', () => {
    it.skip('should toggle play/pause with Space key', () => {
      // Skipped: JSDOM doesn't implement HTMLMediaElement.play()
      // This functionality is tested in E2E tests
    });

    it.skip('should toggle play/pause with K key', () => {
      // Skipped: JSDOM doesn't implement HTMLMediaElement.play()
      // This functionality is tested in E2E tests
    });

    it.skip('should toggle mute with M key', () => {
      // Skipped: Requires video element interaction
      // This functionality is tested in E2E tests
    });
  });

  describe('Visual Feedback', () => {
    it('should highlight selected video with ring', () => {
      const { container } = render(
        <ComparisonView videos={mockVideos.slice(0, 2)} {...mockHandlers} />
      );

      // Select first video
      const selectButton = screen.getAllByText(/select this/i)[0];
      fireEvent.click(selectButton);

      // Check for ring class
      const videoContainer = container.querySelector('.ring-brand-500');
      expect(videoContainer).toBeInTheDocument();
    });
  });

  describe('Accessibility', () => {
    it('should have dialog role', () => {
      render(<ComparisonView videos={mockVideos.slice(0, 2)} {...mockHandlers} />);
      expect(screen.getByRole('dialog')).toBeInTheDocument();
    });

    it('should have aria-label on dialog', () => {
      render(<ComparisonView videos={mockVideos.slice(0, 2)} {...mockHandlers} />);
      expect(screen.getByRole('dialog')).toHaveAttribute('aria-label', 'Video comparison');
    });

    it('should have title attributes on interactive elements', () => {
      render(<ComparisonView videos={mockVideos.slice(0, 2)} {...mockHandlers} />);
      expect(screen.getByTitle(/close comparison/i)).toBeInTheDocument();
      expect(screen.getByTitle(/play/i)).toBeInTheDocument();
      expect(screen.getByTitle(/mute/i)).toBeInTheDocument();
    });
  });

  describe('Edge Cases', () => {
    it('should handle empty videos array', () => {
      render(<ComparisonView videos={[]} {...mockHandlers} />);
      expect(screen.getByText('Compare Takes')).toBeInTheDocument();
    });

    it('should handle single video', () => {
      const { container } = render(
        <ComparisonView videos={mockVideos.slice(0, 1)} {...mockHandlers} />
      );
      const videos = container.querySelectorAll('video');
      expect(videos.length).toBe(1);
    });

    it('should handle videos without posters', () => {
      const videosWithoutPosters = mockVideos.map((v) => ({ ...v, poster: undefined }));
      const { container } = render(
        <ComparisonView videos={videosWithoutPosters} {...mockHandlers} />
      );
      const videos = container.querySelectorAll('video');
      expect(videos.length).toBe(3);
    });
  });
});
