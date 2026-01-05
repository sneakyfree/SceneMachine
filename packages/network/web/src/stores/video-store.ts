/**
 * Video Store
 *
 * Manages video playback state and current video data.
 */

import { create } from 'zustand';
import { api, Video, Comment, PaginatedResponse } from '../lib/api-client';

// =============================================================================
// TYPES
// =============================================================================

interface VideoState {
  // Current video
  currentVideo: Video | null;
  isLoading: boolean;
  error: string | null;

  // Playback state
  isPlaying: boolean;
  currentTime: number;
  duration: number;
  volume: number;
  isMuted: boolean;
  isFullscreen: boolean;
  quality: string;
  playbackRate: number;

  // User interactions
  userReaction: 'like' | 'love' | 'fire' | null;
  isInWatchlist: boolean;

  // Comments
  comments: Comment[];
  commentsLoading: boolean;
  commentsPage: number;
  hasMoreComments: boolean;

  // Recommendations
  recommendations: Video[];

  // Actions
  loadVideo: (videoId: string) => Promise<void>;
  clearVideo: () => void;

  // Playback actions
  setPlaying: (isPlaying: boolean) => void;
  setCurrentTime: (time: number) => void;
  setDuration: (duration: number) => void;
  setVolume: (volume: number) => void;
  setMuted: (isMuted: boolean) => void;
  setFullscreen: (isFullscreen: boolean) => void;
  setQuality: (quality: string) => void;
  setPlaybackRate: (rate: number) => void;

  // Interaction actions
  toggleReaction: (type: 'like' | 'love' | 'fire') => Promise<void>;
  toggleWatchlist: () => Promise<void>;

  // Comment actions
  loadComments: (sortBy?: 'newest' | 'top') => Promise<void>;
  loadMoreComments: () => Promise<void>;
  addComment: (content: string, parentId?: string) => Promise<Comment>;
  deleteComment: (commentId: string) => Promise<void>;

  // Progress tracking
  saveProgress: () => Promise<void>;
}

// =============================================================================
// STORE
// =============================================================================

export const useVideoStore = create<VideoState>()((set, get) => ({
  // Initial state
  currentVideo: null,
  isLoading: false,
  error: null,

  isPlaying: false,
  currentTime: 0,
  duration: 0,
  volume: 1,
  isMuted: false,
  isFullscreen: false,
  quality: 'auto',
  playbackRate: 1,

  userReaction: null,
  isInWatchlist: false,

  comments: [],
  commentsLoading: false,
  commentsPage: 1,
  hasMoreComments: false,

  recommendations: [],

  // Load video data
  loadVideo: async (videoId: string) => {
    set({ isLoading: true, error: null });

    try {
      // Load video, user status, and recommendations in parallel
      const [video, reaction, watchlistStatus, recommendations] = await Promise.all([
        api.getVideo(videoId),
        api.isAuthenticated() ? api.getReaction(videoId).catch(() => ({ type: null })) : Promise.resolve({ type: null }),
        api.isAuthenticated() ? api.isInWatchlist(videoId).catch(() => false) : Promise.resolve(false),
        api.getRecommendations(videoId).catch(() => []),
      ]);

      set({
        currentVideo: video,
        userReaction: reaction.type as 'like' | 'love' | 'fire' | null,
        isInWatchlist: watchlistStatus,
        recommendations,
        isLoading: false,
        currentTime: 0,
        isPlaying: false,
      });

      // Load comments
      get().loadComments();
    } catch (error) {
      set({
        error: 'Failed to load video',
        isLoading: false,
      });
      throw error;
    }
  },

  // Clear video state
  clearVideo: () => {
    set({
      currentVideo: null,
      isLoading: false,
      error: null,
      isPlaying: false,
      currentTime: 0,
      duration: 0,
      userReaction: null,
      isInWatchlist: false,
      comments: [],
      recommendations: [],
    });
  },

  // Playback state setters
  setPlaying: (isPlaying) => set({ isPlaying }),
  setCurrentTime: (currentTime) => set({ currentTime }),
  setDuration: (duration) => set({ duration }),
  setVolume: (volume) => set({ volume, isMuted: volume === 0 }),
  setMuted: (isMuted) => set({ isMuted }),
  setFullscreen: (isFullscreen) => set({ isFullscreen }),
  setQuality: (quality) => set({ quality }),
  setPlaybackRate: (playbackRate) => set({ playbackRate }),

  // Toggle reaction
  toggleReaction: async (type) => {
    const { currentVideo, userReaction } = get();
    if (!currentVideo) return;

    const previousReaction = userReaction;

    try {
      if (userReaction === type) {
        // Remove reaction
        set({ userReaction: null });
        await api.removeReaction(currentVideo.id);
      } else {
        // Set new reaction
        set({ userReaction: type });
        await api.react(currentVideo.id, type);
      }
    } catch {
      // Revert on error
      set({ userReaction: previousReaction });
    }
  },

  // Toggle watchlist
  toggleWatchlist: async () => {
    const { currentVideo, isInWatchlist } = get();
    if (!currentVideo) return;

    const previousState = isInWatchlist;

    try {
      if (isInWatchlist) {
        set({ isInWatchlist: false });
        await api.removeFromWatchlist(currentVideo.id);
      } else {
        set({ isInWatchlist: true });
        await api.addToWatchlist(currentVideo.id);
      }
    } catch {
      // Revert on error
      set({ isInWatchlist: previousState });
    }
  },

  // Load comments
  loadComments: async (sortBy = 'top') => {
    const { currentVideo } = get();
    if (!currentVideo) return;

    set({ commentsLoading: true });

    try {
      const response = await api.getComments(currentVideo.id, 1, 20, sortBy);
      set({
        comments: response.items,
        commentsPage: 1,
        hasMoreComments: response.has_more,
        commentsLoading: false,
      });
    } catch {
      set({ commentsLoading: false });
    }
  },

  // Load more comments
  loadMoreComments: async () => {
    const { currentVideo, commentsPage, hasMoreComments, commentsLoading } = get();
    if (!currentVideo || !hasMoreComments || commentsLoading) return;

    set({ commentsLoading: true });

    try {
      const nextPage = commentsPage + 1;
      const response = await api.getComments(currentVideo.id, nextPage, 20);
      set((state) => ({
        comments: [...state.comments, ...response.items],
        commentsPage: nextPage,
        hasMoreComments: response.has_more,
        commentsLoading: false,
      }));
    } catch {
      set({ commentsLoading: false });
    }
  },

  // Add comment
  addComment: async (content, parentId) => {
    const { currentVideo } = get();
    if (!currentVideo) throw new Error('No video loaded');

    const comment = await api.addComment(currentVideo.id, content, parentId);

    set((state) => ({
      comments: [comment, ...state.comments],
    }));

    return comment;
  },

  // Delete comment
  deleteComment: async (commentId) => {
    await api.deleteComment(commentId);

    set((state) => ({
      comments: state.comments.filter((c) => c.id !== commentId),
    }));
  },

  // Save watch progress
  saveProgress: async () => {
    const { currentVideo, currentTime } = get();
    if (!currentVideo || !api.isAuthenticated()) return;

    try {
      await api.updateWatchProgress(currentVideo.id, Math.floor(currentTime));
    } catch {
      // Ignore progress save errors
    }
  },
}));

// =============================================================================
// SELECTORS
// =============================================================================

export const selectCurrentVideo = (state: VideoState) => state.currentVideo;
export const selectIsPlaying = (state: VideoState) => state.isPlaying;
export const selectProgress = (state: VideoState) => ({
  currentTime: state.currentTime,
  duration: state.duration,
  percent: state.duration > 0 ? (state.currentTime / state.duration) * 100 : 0,
});

export default useVideoStore;
