/**
 * Sharing state store using Zustand.
 *
 * Manages project sharing and collaboration state including
 * shares, comments, and permissions.
 */

import { create } from 'zustand';
import { devtools } from 'zustand/middleware';
import { immer } from 'zustand/middleware/immer';
import type { ShareInfo, Comment, ShareResult } from '../api/client';
import { api } from '../api/client';

interface SharingStoreState {
  // Current project context
  currentProjectId: string | null;

  // Shares for current project
  shares: ShareInfo[];
  isLoadingShares: boolean;
  sharesError: string | null;

  // Comments for current project
  comments: Comment[];
  isLoadingComments: boolean;
  commentsError: string | null;

  // Selected comment for editing/replying
  selectedCommentId: string | null;

  // UI state
  isShareDialogOpen: boolean;
  isCommentsOpen: boolean;

  // Actions
  setCurrentProject: (projectId: string | null) => void;
  setShares: (shares: ShareInfo[]) => void;
  setComments: (comments: Comment[]) => void;
  setSelectedComment: (commentId: string | null) => void;
  setShareDialogOpen: (open: boolean) => void;
  setCommentsOpen: (open: boolean) => void;

  // Async actions
  fetchShares: (projectId: string) => Promise<void>;
  fetchComments: (projectId: string, options?: { shotId?: string; includeResolved?: boolean }) => Promise<void>;
  createShare: (options: {
    projectId: string;
    permission?: 'view' | 'comment' | 'edit';
    recipientEmail?: string;
    recipientName?: string;
    message?: string;
    expiresInDays?: number;
    isPublic?: boolean;
  }) => Promise<ShareResult>;
  revokeShare: (shareId: string) => Promise<void>;
  addComment: (options: {
    projectId: string;
    authorName: string;
    content: string;
    authorEmail?: string;
    shotId?: string;
    parentId?: string;
    timecodeSeconds?: number;
  }) => Promise<Comment>;
  resolveComment: (commentId: string) => Promise<void>;
  deleteComment: (commentId: string) => Promise<void>;
  reset: () => void;
}

const initialState = {
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
};

export const useSharingStore = create<SharingStoreState>()(
  devtools(
    immer((set, get) => ({
      ...initialState,

      setCurrentProject: (projectId) =>
        set((state) => {
          state.currentProjectId = projectId;
          // Reset data when project changes
          if (projectId !== state.currentProjectId) {
            state.shares = [];
            state.comments = [];
            state.selectedCommentId = null;
          }
        }),

      setShares: (shares) =>
        set((state) => {
          state.shares = shares;
        }),

      setComments: (comments) =>
        set((state) => {
          state.comments = comments;
        }),

      setSelectedComment: (commentId) =>
        set((state) => {
          state.selectedCommentId = commentId;
        }),

      setShareDialogOpen: (open) =>
        set((state) => {
          state.isShareDialogOpen = open;
        }),

      setCommentsOpen: (open) =>
        set((state) => {
          state.isCommentsOpen = open;
        }),

      fetchShares: async (projectId) => {
        set((state) => {
          state.isLoadingShares = true;
          state.sharesError = null;
        });

        try {
          const shares = await api.getProjectShares(projectId);
          set((state) => {
            state.shares = shares;
            state.isLoadingShares = false;
          });
        } catch (error) {
          set((state) => {
            state.sharesError = error instanceof Error ? error.message : 'Failed to fetch shares';
            state.isLoadingShares = false;
          });
        }
      },

      fetchComments: async (projectId, options) => {
        set((state) => {
          state.isLoadingComments = true;
          state.commentsError = null;
        });

        try {
          const comments = await api.getProjectComments(projectId, options);
          set((state) => {
            state.comments = comments;
            state.isLoadingComments = false;
          });
        } catch (error) {
          set((state) => {
            state.commentsError = error instanceof Error ? error.message : 'Failed to fetch comments';
            state.isLoadingComments = false;
          });
        }
      },

      createShare: async (options) => {
        const result = await api.createShare(options);
        if (result.success && options.projectId === get().currentProjectId) {
          // Refresh shares list
          await get().fetchShares(options.projectId);
        }
        return result;
      },

      revokeShare: async (shareId) => {
        await api.revokeShare(shareId);
        set((state) => {
          state.shares = state.shares.filter((s) => s.id !== shareId);
        });
      },

      addComment: async (options) => {
        const comment = await api.addComment(options);
        set((state) => {
          state.comments = [...state.comments, comment];
        });
        return comment;
      },

      resolveComment: async (commentId) => {
        // Call backend to resolve (mark as resolved)
        await window.electronAPI.backendRequest('sharing.resolveComment', {
          comment_id: commentId,
        });
        set((state) => {
          const comment = state.comments.find((c) => c.id === commentId);
          if (comment) {
            comment.isResolved = true;
          }
        });
      },

      deleteComment: async (commentId) => {
        await window.electronAPI.backendRequest('sharing.deleteComment', {
          comment_id: commentId,
        });
        set((state) => {
          state.comments = state.comments.filter((c) => c.id !== commentId);
        });
      },

      reset: () => set(initialState),
    })),
    { name: 'SharingStore' }
  )
);

/**
 * Hook to get share count for a project.
 */
export function useShareCount(): number {
  return useSharingStore((state) => state.shares.filter((s) => s.status === 'active').length);
}

/**
 * Hook to get unresolved comment count.
 */
export function useUnresolvedCommentCount(): number {
  return useSharingStore((state) => state.comments.filter((c) => !c.isResolved).length);
}
