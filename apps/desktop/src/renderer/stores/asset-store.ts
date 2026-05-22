/**
 * Asset Store
 * Zustand store for asset management, wired to backend API
 */

import { create } from 'zustand';

// API base URL
const API_BASE = 'http://localhost:8000/api';

// Types
export interface Asset {
  id: string;
  project_id: string;
  character_id: string | null;
  shot_id: string | null;
  scene_id: string | null;
  asset_type: string;
  status: string;
  filename: string;
  file_path: string;
  file_hash: string | null;
  file_size_bytes: number | null;
  mime_type: string | null;
  display_name: string | null;
  description: string | null;
  asset_metadata: Record<string, unknown> | null;
  created_at: string;
  updated_at: string;
}

interface AssetFilters {
  search?: string;
  type?: string;
  character_id?: string;
  shot_id?: string;
  scene_id?: string;
}

interface AssetState {
  assets: Asset[];
  selectedAssets: Set<string>;
  currentAsset: Asset | null;
  isLoading: boolean;
  error: string | null;
  total: number;
  offset: number;
  limit: number;
  filters: AssetFilters;
}

interface AssetActions {
  fetchAssets: (projectId: string) => Promise<void>;
  fetchAsset: (assetId: string) => Promise<Asset | null>;
  createAsset: (projectId: string, data: Partial<Asset>) => Promise<Asset | null>;
  updateAsset: (assetId: string, data: Partial<Asset>) => Promise<Asset | null>;
  deleteAsset: (assetId: string) => Promise<boolean>;
  bulkDelete: (projectId: string, assetIds: string[]) => Promise<number>;
  duplicateAsset: (assetId: string) => Promise<Asset | null>;
  selectAsset: (assetId: string) => void;
  deselectAsset: (assetId: string) => void;
  toggleAsset: (assetId: string) => void;
  selectAll: () => void;
  deselectAll: () => void;
  setFilters: (filters: AssetFilters) => void;
  setCurrentAsset: (asset: Asset | null) => void;
  clearError: () => void;
}

type AssetStore = AssetState & AssetActions;

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

export const useAssetStore = create<AssetStore>((set, get) => ({
  // Initial state
  assets: [],
  selectedAssets: new Set(),
  currentAsset: null,
  isLoading: false,
  error: null,
  total: 0,
  offset: 0,
  limit: 50,
  filters: {},

  // Fetch assets
  fetchAssets: async (projectId: string) => {
    set({ isLoading: true, error: null });

    try {
      const { filters, offset, limit } = get();
      const params = new URLSearchParams();
      if (filters.search) params.set('search', filters.search);
      if (filters.type) params.set('asset_type', filters.type);
      if (filters.character_id) params.set('character_id', filters.character_id);
      if (filters.shot_id) params.set('shot_id', filters.shot_id);
      if (filters.scene_id) params.set('scene_id', filters.scene_id);
      params.set('offset', String(offset));
      params.set('limit', String(limit));

      const response = await authFetch(`/assets/projects/${projectId}/assets?${params}`);

      if (!response.ok) {
        throw new Error('Failed to fetch assets');
      }

      const data = await response.json();
      set({
        assets: data.items,
        total: data.total,
        isLoading: false,
      });
    } catch (err) {
      set({
        isLoading: false,
        error: err instanceof Error ? err.message : 'Failed to fetch assets',
      });
    }
  },

  // Fetch single asset
  fetchAsset: async (assetId: string) => {
    try {
      const response = await authFetch(`/assets/assets/${assetId}`);
      if (!response.ok) return null;
      return await response.json();
    } catch {
      return null;
    }
  },

  // Create asset
  createAsset: async (projectId: string, data: Partial<Asset>) => {
    set({ isLoading: true, error: null });

    try {
      const response = await authFetch(`/assets/projects/${projectId}/assets`, {
        method: 'POST',
        body: JSON.stringify(data),
      });

      if (!response.ok) {
        throw new Error('Failed to create asset');
      }

      const asset = await response.json();
      set((state) => ({
        assets: [asset, ...state.assets],
        isLoading: false,
      }));
      return asset;
    } catch (err) {
      set({
        isLoading: false,
        error: err instanceof Error ? err.message : 'Failed to create asset',
      });
      return null;
    }
  },

  // Update asset
  updateAsset: async (assetId: string, data: Partial<Asset>) => {
    try {
      const response = await authFetch(`/assets/assets/${assetId}`, {
        method: 'PATCH',
        body: JSON.stringify(data),
      });

      if (!response.ok) {
        throw new Error('Failed to update asset');
      }

      const updated = await response.json();
      set((state) => ({
        assets: state.assets.map((a) => (a.id === assetId ? updated : a)),
        currentAsset: state.currentAsset?.id === assetId ? updated : state.currentAsset,
      }));
      return updated;
    } catch (err) {
      set({ error: err instanceof Error ? err.message : 'Failed to update asset' });
      return null;
    }
  },

  // Delete asset
  deleteAsset: async (assetId: string) => {
    try {
      const response = await authFetch(`/assets/assets/${assetId}`, {
        method: 'DELETE',
      });

      if (!response.ok) {
        throw new Error('Failed to delete asset');
      }

      set((state) => ({
        assets: state.assets.filter((a) => a.id !== assetId),
        selectedAssets: new Set([...state.selectedAssets].filter((id) => id !== assetId)),
      }));
      return true;
    } catch {
      return false;
    }
  },

  // Bulk delete
  bulkDelete: async (projectId: string, assetIds: string[]) => {
    try {
      const response = await authFetch(`/assets/projects/${projectId}/assets/bulk-delete`, {
        method: 'POST',
        body: JSON.stringify({ asset_ids: assetIds, delete_files: true }),
      });

      if (!response.ok) {
        throw new Error('Failed to delete assets');
      }

      const result = await response.json();
      set((state) => ({
        assets: state.assets.filter((a) => !assetIds.includes(a.id)),
        selectedAssets: new Set(),
      }));
      return result.deleted_count;
    } catch {
      return 0;
    }
  },

  // Duplicate asset
  duplicateAsset: async (assetId: string) => {
    try {
      const response = await authFetch(`/assets/assets/${assetId}/duplicate`, {
        method: 'POST',
      });

      if (!response.ok) {
        throw new Error('Failed to duplicate asset');
      }

      const duplicate = await response.json();
      set((state) => ({
        assets: [duplicate, ...state.assets],
      }));
      return duplicate;
    } catch {
      return null;
    }
  },

  // Selection management
  selectAsset: (assetId: string) => {
    set((state) => ({
      selectedAssets: new Set([...state.selectedAssets, assetId]),
    }));
  },

  deselectAsset: (assetId: string) => {
    set((state) => ({
      selectedAssets: new Set([...state.selectedAssets].filter((id) => id !== assetId)),
    }));
  },

  toggleAsset: (assetId: string) => {
    const { selectedAssets } = get();
    if (selectedAssets.has(assetId)) {
      get().deselectAsset(assetId);
    } else {
      get().selectAsset(assetId);
    }
  },

  selectAll: () => {
    set((state) => ({
      selectedAssets: new Set(state.assets.map((a) => a.id)),
    }));
  },

  deselectAll: () => {
    set({ selectedAssets: new Set() });
  },

  setFilters: (filters: AssetFilters) => {
    set({ filters, offset: 0 });
  },

  setCurrentAsset: (asset: Asset | null) => {
    set({ currentAsset: asset });
  },

  clearError: () => set({ error: null }),
}));
