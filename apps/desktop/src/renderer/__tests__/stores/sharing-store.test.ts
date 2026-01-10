/**
 * Sharing store unit tests.
 */

import { describe, it, expect, beforeEach, vi } from 'vitest';
import { act } from '@testing-library/react';
import { useSharingStore } from '../../stores/sharing-store';

// Mock the API client
vi.mock('../../api/client', () => ({
  api: {
    createShareLink: vi.fn(),
    getShareLinks: vi.fn(),
    deleteShareLink: vi.fn(),
    getShareAnalytics: vi.fn(),
    exportProject: vi.fn(),
  },
}));

const mockShareLink = {
  id: 'share-1',
  projectId: 'project-1',
  url: 'https://share.scenemachine.com/abc123',
  accessLevel: 'view' as const,
  expiresAt: new Date(Date.now() + 86400000).toISOString(),
  createdAt: new Date().toISOString(),
  viewCount: 5,
};

describe('SharingStore', () => {
  beforeEach(() => {
    // Reset store state before each test
    useSharingStore.setState({
      shareLinks: [],
      activeShareLink: null,
      shareAnalytics: null,
      isCreatingLink: false,
      isLoadingLinks: false,
      isDeletingLink: false,
      isExporting: false,
      exportProgress: 0,
      error: null,
    });
    vi.clearAllMocks();
  });

  describe('setShareLinks', () => {
    it('should set share links', () => {
      const { setShareLinks } = useSharingStore.getState();

      act(() => {
        setShareLinks([mockShareLink]);
      });

      expect(useSharingStore.getState().shareLinks).toHaveLength(1);
      expect(useSharingStore.getState().shareLinks[0]).toEqual(mockShareLink);
    });
  });

  describe('addShareLink', () => {
    it('should add a share link', () => {
      const { addShareLink } = useSharingStore.getState();

      act(() => {
        addShareLink(mockShareLink);
      });

      expect(useSharingStore.getState().shareLinks).toHaveLength(1);
    });

    it('should add to existing links', () => {
      useSharingStore.setState({ shareLinks: [mockShareLink] });

      const newLink = { ...mockShareLink, id: 'share-2' };
      const { addShareLink } = useSharingStore.getState();

      act(() => {
        addShareLink(newLink);
      });

      expect(useSharingStore.getState().shareLinks).toHaveLength(2);
    });
  });

  describe('removeShareLink', () => {
    it('should remove a share link by ID', () => {
      useSharingStore.setState({
        shareLinks: [mockShareLink, { ...mockShareLink, id: 'share-2' }],
      });

      const { removeShareLink } = useSharingStore.getState();

      act(() => {
        removeShareLink('share-1');
      });

      expect(useSharingStore.getState().shareLinks).toHaveLength(1);
      expect(useSharingStore.getState().shareLinks[0].id).toBe('share-2');
    });

    it('should clear activeShareLink if it was removed', () => {
      useSharingStore.setState({
        shareLinks: [mockShareLink],
        activeShareLink: mockShareLink,
      });

      const { removeShareLink } = useSharingStore.getState();

      act(() => {
        removeShareLink('share-1');
      });

      expect(useSharingStore.getState().activeShareLink).toBeNull();
    });
  });

  describe('setActiveShareLink', () => {
    it('should set the active share link', () => {
      const { setActiveShareLink } = useSharingStore.getState();

      act(() => {
        setActiveShareLink(mockShareLink);
      });

      expect(useSharingStore.getState().activeShareLink).toEqual(mockShareLink);
    });

    it('should allow clearing the active link', () => {
      useSharingStore.setState({ activeShareLink: mockShareLink });

      const { setActiveShareLink } = useSharingStore.getState();

      act(() => {
        setActiveShareLink(null);
      });

      expect(useSharingStore.getState().activeShareLink).toBeNull();
    });
  });

  describe('setShareAnalytics', () => {
    it('should set share analytics', () => {
      const analytics = { totalViews: 100, uniqueViewers: 50 };
      const { setShareAnalytics } = useSharingStore.getState();

      act(() => {
        setShareAnalytics(analytics);
      });

      expect(useSharingStore.getState().shareAnalytics).toEqual(analytics);
    });
  });

  describe('setExportProgress', () => {
    it('should set export progress', () => {
      const { setExportProgress } = useSharingStore.getState();

      act(() => {
        setExportProgress(75);
      });

      expect(useSharingStore.getState().exportProgress).toBe(75);
    });
  });

  describe('setError', () => {
    it('should set error message', () => {
      const { setError } = useSharingStore.getState();

      act(() => {
        setError('Share failed');
      });

      expect(useSharingStore.getState().error).toBe('Share failed');
    });
  });

  describe('clearError', () => {
    it('should clear the error', () => {
      useSharingStore.setState({ error: 'Previous error' });

      const { clearError } = useSharingStore.getState();

      act(() => {
        clearError();
      });

      expect(useSharingStore.getState().error).toBeNull();
    });
  });

  describe('getActiveLinks', () => {
    it('should return non-expired links', () => {
      const expiredLink = {
        ...mockShareLink,
        id: 'expired',
        expiresAt: new Date(Date.now() - 86400000).toISOString(),
      };
      useSharingStore.setState({
        shareLinks: [mockShareLink, expiredLink],
      });

      const { getActiveLinks } = useSharingStore.getState();
      const activeLinks = getActiveLinks();

      expect(activeLinks).toHaveLength(1);
      expect(activeLinks[0].id).toBe('share-1');
    });
  });

  describe('getLinksByAccessLevel', () => {
    it('should filter links by access level', () => {
      const editLink = { ...mockShareLink, id: 'edit-1', accessLevel: 'edit' as const };
      useSharingStore.setState({
        shareLinks: [mockShareLink, editLink],
      });

      const { getLinksByAccessLevel } = useSharingStore.getState();
      const viewLinks = getLinksByAccessLevel('view');

      expect(viewLinks).toHaveLength(1);
      expect(viewLinks[0].accessLevel).toBe('view');
    });
  });

  describe('reset', () => {
    it('should reset store to initial state', () => {
      useSharingStore.setState({
        shareLinks: [mockShareLink],
        activeShareLink: mockShareLink,
        error: 'Some error',
        exportProgress: 50,
      });

      const { reset } = useSharingStore.getState();

      act(() => {
        reset();
      });

      const state = useSharingStore.getState();
      expect(state.shareLinks).toHaveLength(0);
      expect(state.activeShareLink).toBeNull();
      expect(state.error).toBeNull();
      expect(state.exportProgress).toBe(0);
    });
  });
});
