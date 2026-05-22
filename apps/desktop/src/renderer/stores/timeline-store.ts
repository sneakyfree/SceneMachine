/**
 * Timeline Store
 * Zustand store for timeline tracks and clips, wired to backend API
 */

import { create } from 'zustand';

// API base URL
const API_BASE = 'http://localhost:8000/api';

// Types
export interface Track {
  id: string;
  project_id: string;
  name: string;
  track_type: string;
  order: number;
  color: string | null;
  is_visible: boolean;
  is_locked: boolean;
  is_solo: boolean;
  is_muted: boolean;
  volume: number;
  pan: number;
  clips: Clip[];
}

export interface Clip {
  id: string;
  track_id: string;
  source_id: string;
  source_type: string;
  start_time: number;
  duration: number;
  trim_start: number;
  trim_end: number;
  z_index: number;
  name: string | null;
  volume: number;
  fade_in: number;
  fade_out: number;
}

interface TimelineState {
  tracks: Track[];
  selectedClipId: string | null;
  selectedTrackId: string | null;
  isLoading: boolean;
  error: string | null;
  isSaving: boolean;
}

interface TimelineActions {
  fetchTracks: (projectId: string) => Promise<void>;
  createTrack: (
    projectId: string,
    data: { name: string; track_type: string; color?: string }
  ) => Promise<Track | null>;
  updateTrack: (trackId: string, data: Partial<Track>) => Promise<Track | null>;
  deleteTrack: (trackId: string) => Promise<boolean>;
  reorderTracks: (projectId: string, trackIds: string[]) => Promise<void>;
  createClip: (trackId: string, data: Partial<Clip>) => Promise<Clip | null>;
  updateClip: (clipId: string, data: Partial<Clip>) => Promise<Clip | null>;
  deleteClip: (clipId: string) => Promise<boolean>;
  trimClip: (clipId: string, trimStart: number, trimEnd: number) => Promise<Clip | null>;
  splitClip: (clipId: string, splitTime: number) => Promise<{ first: Clip; second: Clip } | null>;
  rippleDelete: (clipId: string, trackId: string) => Promise<void>;
  moveClip: (clipId: string, targetTrackId: string, startTime?: number) => Promise<Clip | null>;
  selectClip: (clipId: string | null) => void;
  selectTrack: (trackId: string | null) => void;
  clearError: () => void;
}

type TimelineStore = TimelineState & TimelineActions;

// Get auth token
const getToken = (): string | null => {
  try {
    const stored = localStorage.getItem('scenemachine-auth');
    if (stored) {
      const parsed = JSON.parse(stored);
      return parsed.state?.accessToken || null;
    }
  } catch {
    return null;
  }
  return null;
};

// Helper for authenticated requests
const authFetch = async (url: string, options: RequestInit = {}): Promise<Response> => {
  const token = getToken();
  const headers: HeadersInit = {
    'Content-Type': 'application/json',
    ...options.headers,
  };

  if (token) {
    (headers as Record<string, string>)['Authorization'] = `Bearer ${token}`;
  }

  return fetch(`${API_BASE}${url}`, { ...options, headers });
};

export const useTimelineStore = create<TimelineStore>((set, get) => ({
  // Initial state
  tracks: [],
  selectedClipId: null,
  selectedTrackId: null,
  isLoading: false,
  error: null,
  isSaving: false,

  // Fetch tracks
  fetchTracks: async (projectId: string) => {
    set({ isLoading: true, error: null });

    try {
      const response = await authFetch(`/timeline/projects/${projectId}/tracks`);

      if (!response.ok) {
        throw new Error('Failed to fetch tracks');
      }

      const tracks = await response.json();
      set({ tracks, isLoading: false });
    } catch (err) {
      set({
        isLoading: false,
        error: err instanceof Error ? err.message : 'Failed to fetch tracks',
      });
    }
  },

  // Create track
  createTrack: async (projectId, data) => {
    set({ isSaving: true });

    try {
      const response = await authFetch(`/timeline/projects/${projectId}/tracks`, {
        method: 'POST',
        body: JSON.stringify(data),
      });

      if (!response.ok) {
        throw new Error('Failed to create track');
      }

      const track = await response.json();
      track.clips = [];
      set((state) => ({
        tracks: [...state.tracks, track],
        isSaving: false,
      }));
      return track;
    } catch (err) {
      set({
        isSaving: false,
        error: err instanceof Error ? err.message : 'Failed to create track',
      });
      return null;
    }
  },

  // Update track
  updateTrack: async (trackId, data) => {
    set({ isSaving: true });

    try {
      const response = await authFetch(`/timeline/tracks/${trackId}`, {
        method: 'PATCH',
        body: JSON.stringify(data),
      });

      if (!response.ok) {
        throw new Error('Failed to update track');
      }

      const updated = await response.json();
      set((state) => ({
        tracks: state.tracks.map((t) => (t.id === trackId ? { ...updated, clips: t.clips } : t)),
        isSaving: false,
      }));
      return updated;
    } catch (err) {
      set({
        isSaving: false,
        error: err instanceof Error ? err.message : 'Failed to update track',
      });
      return null;
    }
  },

  // Delete track
  deleteTrack: async (trackId) => {
    try {
      const response = await authFetch(`/timeline/tracks/${trackId}`, {
        method: 'DELETE',
      });

      if (!response.ok) {
        throw new Error('Failed to delete track');
      }

      set((state) => ({
        tracks: state.tracks.filter((t) => t.id !== trackId),
      }));
      return true;
    } catch {
      return false;
    }
  },

  // Reorder tracks
  reorderTracks: async (projectId, trackIds) => {
    set({ isSaving: true });

    try {
      const response = await authFetch(`/timeline/projects/${projectId}/tracks/reorder`, {
        method: 'PUT',
        body: JSON.stringify({ track_ids: trackIds }),
      });

      if (!response.ok) {
        throw new Error('Failed to reorder tracks');
      }

      const tracks = await response.json();
      // Preserve clips from current state
      const clipsMap = new Map(get().tracks.map((t) => [t.id, t.clips]));
      set({
        tracks: tracks.map((t: Track) => ({ ...t, clips: clipsMap.get(t.id) || [] })),
        isSaving: false,
      });
    } catch (err) {
      set({
        isSaving: false,
        error: err instanceof Error ? err.message : 'Failed to reorder tracks',
      });
    }
  },

  // Create clip
  createClip: async (trackId, data) => {
    set({ isSaving: true });

    try {
      const response = await authFetch(`/timeline/tracks/${trackId}/clips`, {
        method: 'POST',
        body: JSON.stringify(data),
      });

      if (!response.ok) {
        throw new Error('Failed to create clip');
      }

      const clip = await response.json();
      set((state) => ({
        tracks: state.tracks.map((t) =>
          t.id === trackId
            ? { ...t, clips: [...t.clips, clip].sort((a, b) => a.start_time - b.start_time) }
            : t
        ),
        isSaving: false,
      }));
      return clip;
    } catch (err) {
      set({ isSaving: false, error: err instanceof Error ? err.message : 'Failed to create clip' });
      return null;
    }
  },

  // Update clip
  updateClip: async (clipId, data) => {
    set({ isSaving: true });

    try {
      const response = await authFetch(`/timeline/clips/${clipId}`, {
        method: 'PATCH',
        body: JSON.stringify(data),
      });

      if (!response.ok) {
        throw new Error('Failed to update clip');
      }

      const updated = await response.json();
      set((state) => ({
        tracks: state.tracks.map((t) => ({
          ...t,
          clips: t.clips.map((c) => (c.id === clipId ? updated : c)),
        })),
        isSaving: false,
      }));
      return updated;
    } catch (err) {
      set({ isSaving: false, error: err instanceof Error ? err.message : 'Failed to update clip' });
      return null;
    }
  },

  // Delete clip
  deleteClip: async (clipId) => {
    try {
      const response = await authFetch(`/timeline/clips/${clipId}`, {
        method: 'DELETE',
      });

      if (!response.ok) {
        throw new Error('Failed to delete clip');
      }

      set((state) => ({
        tracks: state.tracks.map((t) => ({
          ...t,
          clips: t.clips.filter((c) => c.id !== clipId),
        })),
        selectedClipId: state.selectedClipId === clipId ? null : state.selectedClipId,
      }));
      return true;
    } catch {
      return false;
    }
  },

  // Trim clip
  trimClip: async (clipId, trimStart, trimEnd) => {
    set({ isSaving: true });

    try {
      const response = await authFetch(`/timeline/clips/${clipId}/trim`, {
        method: 'POST',
        body: JSON.stringify({ trim_start: trimStart, trim_end: trimEnd }),
      });

      if (!response.ok) {
        throw new Error('Failed to trim clip');
      }

      const updated = await response.json();
      set((state) => ({
        tracks: state.tracks.map((t) => ({
          ...t,
          clips: t.clips.map((c) => (c.id === clipId ? updated : c)),
        })),
        isSaving: false,
      }));
      return updated;
    } catch (err) {
      set({ isSaving: false, error: err instanceof Error ? err.message : 'Failed to trim clip' });
      return null;
    }
  },

  // Split clip
  splitClip: async (clipId, splitTime) => {
    set({ isSaving: true });

    try {
      const response = await authFetch(`/timeline/clips/${clipId}/split`, {
        method: 'POST',
        body: JSON.stringify({ split_time: splitTime }),
      });

      if (!response.ok) {
        throw new Error('Failed to split clip');
      }

      const { first_clip, second_clip } = await response.json();
      set((state) => ({
        tracks: state.tracks.map((t) => ({
          ...t,
          clips: t.clips
            .map((c) => (c.id === clipId ? first_clip : c))
            .concat(t.clips.some((c) => c.id === clipId) ? [second_clip] : [])
            .sort((a, b) => a.start_time - b.start_time),
        })),
        isSaving: false,
      }));
      return { first: first_clip, second: second_clip };
    } catch (err) {
      set({ isSaving: false, error: err instanceof Error ? err.message : 'Failed to split clip' });
      return null;
    }
  },

  // Ripple delete
  rippleDelete: async (clipId, trackId) => {
    try {
      const response = await authFetch(`/timeline/clips/${clipId}/ripple?track_id=${trackId}`, {
        method: 'DELETE',
      });

      if (!response.ok) {
        throw new Error('Failed to ripple delete');
      }

      const clips = await response.json();
      set((state) => ({
        tracks: state.tracks.map((t) => (t.id === trackId ? { ...t, clips } : t)),
      }));
    } catch (err) {
      set({ error: err instanceof Error ? err.message : 'Failed to ripple delete' });
    }
  },

  // Move clip
  moveClip: async (clipId, targetTrackId, startTime) => {
    set({ isSaving: true });

    try {
      const response = await authFetch(`/timeline/clips/${clipId}/move`, {
        method: 'POST',
        body: JSON.stringify({ target_track_id: targetTrackId, start_time: startTime }),
      });

      if (!response.ok) {
        throw new Error('Failed to move clip');
      }

      const moved = await response.json();

      // Remove from old track, add to new track
      set((state) => {
        const oldTrackId = state.tracks.find((t) => t.clips.some((c) => c.id === clipId))?.id;
        return {
          tracks: state.tracks.map((t) => {
            if (t.id === oldTrackId) {
              return { ...t, clips: t.clips.filter((c) => c.id !== clipId) };
            }
            if (t.id === targetTrackId) {
              return {
                ...t,
                clips: [...t.clips, moved].sort((a, b) => a.start_time - b.start_time),
              };
            }
            return t;
          }),
          isSaving: false,
        };
      });
      return moved;
    } catch (err) {
      set({ isSaving: false, error: err instanceof Error ? err.message : 'Failed to move clip' });
      return null;
    }
  },

  // Selection
  selectClip: (clipId) => set({ selectedClipId: clipId }),
  selectTrack: (trackId) => set({ selectedTrackId: trackId }),
  clearError: () => set({ error: null }),
}));
