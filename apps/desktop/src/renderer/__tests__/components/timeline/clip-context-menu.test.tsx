/**
 * Tests for ClipContextMenu component.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { ClipContextMenu } from '../../../components/timeline/clip-context-menu';

describe('ClipContextMenu', () => {
  const defaultProps = {
    isOpen: true,
    position: { x: 100, y: 100 },
    onClose: vi.fn(),
    clipId: 'clip-1',
    isLocked: false,
    isVisible: true,
    hasVideo: true,
    onApplyLipSync: vi.fn(),
    onDelete: vi.fn(),
    onToggleLock: vi.fn(),
    onToggleVisibility: vi.fn(),
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('Rendering', () => {
    it('should render menu when open', () => {
      render(<ClipContextMenu {...defaultProps} />);
      expect(screen.getByRole('menu')).toBeInTheDocument();
    });

    it('should not render menu when closed', () => {
      render(<ClipContextMenu {...defaultProps} isOpen={false} />);
      expect(screen.queryByRole('menu')).not.toBeInTheDocument();
    });

    it('should render Apply Lip Sync option for video clips', () => {
      render(<ClipContextMenu {...defaultProps} />);
      expect(screen.getByText('Apply Lip Sync...')).toBeInTheDocument();
    });

    it('should not render Apply Lip Sync option for non-video clips', () => {
      render(<ClipContextMenu {...defaultProps} hasVideo={false} />);
      expect(screen.queryByText('Apply Lip Sync...')).not.toBeInTheDocument();
    });

    it('should render lock/unlock option', () => {
      render(<ClipContextMenu {...defaultProps} />);
      expect(screen.getByText('Lock Clip')).toBeInTheDocument();
    });

    it('should show Unlock when clip is locked', () => {
      render(<ClipContextMenu {...defaultProps} isLocked={true} />);
      expect(screen.getByText('Unlock Clip')).toBeInTheDocument();
    });

    it('should render visibility toggle option', () => {
      render(<ClipContextMenu {...defaultProps} />);
      expect(screen.getByText('Hide Clip')).toBeInTheDocument();
    });

    it('should show Show Clip when clip is hidden', () => {
      render(<ClipContextMenu {...defaultProps} isVisible={false} />);
      expect(screen.getByText('Show Clip')).toBeInTheDocument();
    });

    it('should render delete option', () => {
      render(<ClipContextMenu {...defaultProps} />);
      expect(screen.getByText('Delete Clip')).toBeInTheDocument();
    });
  });

  describe('Interactions', () => {
    it('should call onApplyLipSync when clicking Apply Lip Sync', () => {
      render(<ClipContextMenu {...defaultProps} />);
      fireEvent.click(screen.getByText('Apply Lip Sync...'));
      expect(defaultProps.onApplyLipSync).toHaveBeenCalled();
      expect(defaultProps.onClose).toHaveBeenCalled();
    });

    it('should call onToggleLock when clicking Lock Clip', () => {
      render(<ClipContextMenu {...defaultProps} />);
      fireEvent.click(screen.getByText('Lock Clip'));
      expect(defaultProps.onToggleLock).toHaveBeenCalled();
      expect(defaultProps.onClose).toHaveBeenCalled();
    });

    it('should call onToggleVisibility when clicking Hide Clip', () => {
      render(<ClipContextMenu {...defaultProps} />);
      fireEvent.click(screen.getByText('Hide Clip'));
      expect(defaultProps.onToggleVisibility).toHaveBeenCalled();
      expect(defaultProps.onClose).toHaveBeenCalled();
    });

    it('should call onDelete when clicking Delete Clip', () => {
      render(<ClipContextMenu {...defaultProps} />);
      fireEvent.click(screen.getByText('Delete Clip'));
      expect(defaultProps.onDelete).toHaveBeenCalled();
      expect(defaultProps.onClose).toHaveBeenCalled();
    });

    it('should close menu on Escape key', () => {
      render(<ClipContextMenu {...defaultProps} />);
      fireEvent.keyDown(document, { key: 'Escape' });
      expect(defaultProps.onClose).toHaveBeenCalled();
    });

    it('should close menu on click outside', () => {
      render(
        <div>
          <div data-testid="outside">Outside</div>
          <ClipContextMenu {...defaultProps} />
        </div>
      );
      fireEvent.mouseDown(screen.getByTestId('outside'));
      expect(defaultProps.onClose).toHaveBeenCalled();
    });
  });

  describe('Disabled States', () => {
    it('should disable Apply Lip Sync when clip is locked', () => {
      render(<ClipContextMenu {...defaultProps} isLocked={true} />);
      const lipSyncButton = screen.getByText('Apply Lip Sync...').closest('button');
      expect(lipSyncButton).toBeDisabled();
    });

    it('should disable Delete when clip is locked', () => {
      render(<ClipContextMenu {...defaultProps} isLocked={true} />);
      const deleteButton = screen.getByText('Delete Clip').closest('button');
      expect(deleteButton).toBeDisabled();
    });
  });

  describe('Optional Actions', () => {
    it('should render Preview option when onPreview is provided', () => {
      render(<ClipContextMenu {...defaultProps} onPreview={vi.fn()} />);
      expect(screen.getByText('Preview Clip')).toBeInTheDocument();
    });

    it('should render Duplicate option when onDuplicate is provided', () => {
      render(<ClipContextMenu {...defaultProps} onDuplicate={vi.fn()} />);
      expect(screen.getByText('Duplicate')).toBeInTheDocument();
    });

    it('should render Split option when onSplit is provided', () => {
      render(<ClipContextMenu {...defaultProps} onSplit={vi.fn()} />);
      expect(screen.getByText('Split at Playhead')).toBeInTheDocument();
    });
  });

  describe('Accessibility', () => {
    it('should have proper role attribute', () => {
      render(<ClipContextMenu {...defaultProps} />);
      expect(screen.getByRole('menu')).toHaveAttribute('aria-label', 'Clip actions');
    });

    it('should show keyboard shortcuts', () => {
      render(<ClipContextMenu {...defaultProps} />);
      expect(screen.getByText('Del')).toBeInTheDocument();
    });
  });

  describe('Position Adjustment', () => {
    it('should position menu at specified coordinates', () => {
      render(<ClipContextMenu {...defaultProps} position={{ x: 200, y: 300 }} />);
      const menu = screen.getByRole('menu');
      expect(menu).toHaveStyle({ left: '200px', top: '300px' });
    });
  });
});
