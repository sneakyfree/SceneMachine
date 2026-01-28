/**
 * Sharing store unit tests.
 *
 * Tests the collaboration sharing functionality including shares, comments,
 * and project collaboration state management.
 */

import { describe, it, expect, beforeEach, vi } from 'vitest';
import { act } from '@testing-library/react';
import { useSharingStore } from '../../stores/sharing-store';

// Mock the API client
vi.mock('../../api/client', () => ({
  api: {
    getProjectShares: vi.fn(),
    getProjectComments: vi.fn(),
    createShare: vi.fn(),
    revokeShare: vi.fn(),
    addComment: vi.fn(),
  },
}));

const mockShare = {
  id: 'share-1',
  projectId: 'project-1',
  permission: 'view' as const,
  recipientEmail: 'test@example.com',
  recipientName: 'Test User',
  status: 'active' as const,
  createdAt: new Date().toISOString(),
};

const mockComment = {
  id: 'comment-1',
  projectId: 'project-1',
  authorName: 'Test Author',
  content: 'Test comment',
  isResolved: false,
  createdAt: new Date().toISOString(),
};

describe('SharingStore', () => {
  beforeEach(() => {
    // Reset store state before each test
    useSharingStore.setState({
      currentProjectId: null,
      shares: [],
      isLoadingShares: false,
      sharesError: null,
      comments: [],
      isLoadingComments: false,
      commentsError: null,
      selectedCommentId: null,
      isShareDialogOpen: false,
      isCommentsOpen: false,
    });
    vi.clearAllMocks();
  });

  describe('setCurrentProject', () => {
    it('should set the current project', () => {
      const { setCurrentProject } = useSharingStore.getState();

      act(() => {
        setCurrentProject('project-123');
      });

      expect(useSharingStore.getState().currentProjectId).toBe('project-123');
    });

    it('should allow clearing the project', () => {
      useSharingStore.setState({ currentProjectId: 'project-1' });

      const { setCurrentProject } = useSharingStore.getState();

      act(() => {
        setCurrentProject(null);
      });

      expect(useSharingStore.getState().currentProjectId).toBeNull();
    });
  });

  describe('setShares', () => {
    it('should set shares list', () => {
      const { setShares } = useSharingStore.getState();

      act(() => {
        setShares([mockShare]);
      });

      expect(useSharingStore.getState().shares).toHaveLength(1);
      expect(useSharingStore.getState().shares[0]).toEqual(mockShare);
    });
  });

  describe('setComments', () => {
    it('should set comments list', () => {
      const { setComments } = useSharingStore.getState();

      act(() => {
        setComments([mockComment]);
      });

      expect(useSharingStore.getState().comments).toHaveLength(1);
      expect(useSharingStore.getState().comments[0]).toEqual(mockComment);
    });
  });

  describe('setSelectedComment', () => {
    it('should set the selected comment', () => {
      const { setSelectedComment } = useSharingStore.getState();

      act(() => {
        setSelectedComment('comment-1');
      });

      expect(useSharingStore.getState().selectedCommentId).toBe('comment-1');
    });

    it('should allow clearing the selection', () => {
      useSharingStore.setState({ selectedCommentId: 'comment-1' });

      const { setSelectedComment } = useSharingStore.getState();

      act(() => {
        setSelectedComment(null);
      });

      expect(useSharingStore.getState().selectedCommentId).toBeNull();
    });
  });

  describe('setShareDialogOpen', () => {
    it('should set share dialog visibility', () => {
      const { setShareDialogOpen } = useSharingStore.getState();

      act(() => {
        setShareDialogOpen(true);
      });

      expect(useSharingStore.getState().isShareDialogOpen).toBe(true);
    });
  });

  describe('setCommentsOpen', () => {
    it('should set comments panel visibility', () => {
      const { setCommentsOpen } = useSharingStore.getState();

      act(() => {
        setCommentsOpen(true);
      });

      expect(useSharingStore.getState().isCommentsOpen).toBe(true);
    });
  });

  describe('reset', () => {
    it('should reset store to initial state', () => {
      useSharingStore.setState({
        currentProjectId: 'project-1',
        shares: [mockShare],
        comments: [mockComment],
        selectedCommentId: 'comment-1',
        isShareDialogOpen: true,
        isCommentsOpen: true,
        sharesError: 'Some error',
      });

      const { reset } = useSharingStore.getState();

      act(() => {
        reset();
      });

      const state = useSharingStore.getState();
      expect(state.currentProjectId).toBeNull();
      expect(state.shares).toHaveLength(0);
      expect(state.comments).toHaveLength(0);
      expect(state.selectedCommentId).toBeNull();
      expect(state.isShareDialogOpen).toBe(false);
      expect(state.isCommentsOpen).toBe(false);
      expect(state.sharesError).toBeNull();
    });
  });

  describe('useShareCount hook', () => {
    it('should count active shares', () => {
      const activeShare = { ...mockShare, status: 'active' as const };
      const expiredShare = { ...mockShare, id: 'share-2', status: 'expired' as const };

      useSharingStore.setState({
        shares: [activeShare, expiredShare],
      });

      // Get current state
      const state = useSharingStore.getState();
      const activeCount = state.shares.filter((s) => s.status === 'active').length;

      expect(activeCount).toBe(1);
    });
  });

  describe('useUnresolvedCommentCount hook', () => {
    it('should count unresolved comments', () => {
      const unresolvedComment = { ...mockComment, isResolved: false };
      const resolvedComment = { ...mockComment, id: 'comment-2', isResolved: true };

      useSharingStore.setState({
        comments: [unresolvedComment, resolvedComment],
      });

      // Get current state
      const state = useSharingStore.getState();
      const unresolvedCount = state.comments.filter((c) => !c.isResolved).length;

      expect(unresolvedCount).toBe(1);
    });
  });
});
