/**
 * Offline Cache Hook
 *
 * React hook for interacting with the offline cache service.
 * Provides caching utilities with React integration.
 */

import { useState, useEffect, useCallback, useRef } from 'react';
import {
  offlineCache,
  CachedProject,
  CachedVideo,
  SyncQueueItem,
} from '../lib/offline-cache';
import { useOnlineStatus } from './use-online-status';

export interface UseOfflineCacheOptions {
  /**
   * Auto-initialize on mount
   * @default true
   */
  autoInit?: boolean;

  /**
   * Auto-sync queue when coming online
   * @default true
   */
  autoSync?: boolean;
}

export interface UseOfflineCacheReturn {
  /**
   * Whether the cache is initialized
   */
  isReady: boolean;

  /**
   * Cache statistics
   */
  stats: {
    projectCount: number;
    projectDetailsCount: number;
    videoCount: number;
    totalVideoSizeMB: number;
    syncQueueCount: number;
  } | null;

  /**
   * Items pending sync
   */
  pendingSync: SyncQueueItem[];

  /**
   * Whether sync is in progress
   */
  isSyncing: boolean;

  /**
   * Cache project list
   */
  cacheProjects: (projects: CachedProject[]) => Promise<void>;

  /**
   * Get cached project list
   */
  getCachedProjects: () => Promise<CachedProject[]>;

  /**
   * Cache project details
   */
  cacheProjectDetails: (projectId: string, data: unknown) => Promise<void>;

  /**
   * Get cached project details
   */
  getCachedProjectDetails: (projectId: string) => Promise<unknown | null>;

  /**
   * Cache a video
   */
  cacheVideo: (
    videoId: string,
    projectId: string,
    blob: Blob,
    metadata: CachedVideo['metadata'],
    thumbnailBlob?: Blob
  ) => Promise<void>;

  /**
   * Get cached video URL (creates object URL)
   */
  getCachedVideoUrl: (videoId: string) => Promise<string | null>;

  /**
   * Check if something is cached
   */
  isCached: (type: 'project' | 'projectDetails' | 'video', id: string) => Promise<boolean>;

  /**
   * Queue an edit for sync when online
   */
  queueEdit: (
    type: 'update' | 'create' | 'delete',
    entity: 'project' | 'character' | 'scene' | 'shot',
    entityId: string,
    data: unknown
  ) => Promise<string>;

  /**
   * Process sync queue (called automatically when online)
   */
  processQueue: (
    syncFn: (item: SyncQueueItem) => Promise<boolean>
  ) => Promise<void>;

  /**
   * Clear all cached data
   */
  clearCache: () => Promise<void>;

  /**
   * Refresh stats
   */
  refreshStats: () => Promise<void>;
}

/**
 * Hook for offline cache operations
 */
export function useOfflineCache(
  options: UseOfflineCacheOptions = {}
): UseOfflineCacheReturn {
  const { autoInit = true, autoSync = true } = options;

  const [isReady, setIsReady] = useState(false);
  const [stats, setStats] = useState<UseOfflineCacheReturn['stats']>(null);
  const [pendingSync, setPendingSync] = useState<SyncQueueItem[]>([]);
  const [isSyncing, setIsSyncing] = useState(false);

  const { isOnline } = useOnlineStatus();
  const syncFnRef = useRef<((item: SyncQueueItem) => Promise<boolean>) | null>(null);

  // Initialize cache
  useEffect(() => {
    if (!autoInit) return;

    const init = async () => {
      try {
        await offlineCache.init();
        setIsReady(true);
        // Load initial stats and queue
        const [statsData, queueData] = await Promise.all([
          offlineCache.getStats(),
          offlineCache.getSyncQueue(),
        ]);
        setStats(statsData);
        setPendingSync(queueData);
      } catch (error) {
        console.error('Failed to initialize offline cache:', error);
      }
    };

    init();
  }, [autoInit]);

  // Refresh stats
  const refreshStats = useCallback(async () => {
    if (!isReady) return;
    try {
      const statsData = await offlineCache.getStats();
      setStats(statsData);
    } catch (error) {
      console.error('Failed to refresh cache stats:', error);
    }
  }, [isReady]);

  // Cache projects
  const cacheProjects = useCallback(
    async (projects: CachedProject[]) => {
      if (!isReady) return;
      await offlineCache.cacheProjectList(projects);
      await refreshStats();
    },
    [isReady, refreshStats]
  );

  // Get cached projects
  const getCachedProjects = useCallback(async () => {
    if (!isReady) return [];
    return offlineCache.getProjectList();
  }, [isReady]);

  // Cache project details
  const cacheProjectDetails = useCallback(
    async (projectId: string, data: unknown) => {
      if (!isReady) return;
      await offlineCache.cacheProjectDetails(projectId, data);
      await refreshStats();
    },
    [isReady, refreshStats]
  );

  // Get cached project details
  const getCachedProjectDetails = useCallback(
    async (projectId: string) => {
      if (!isReady) return null;
      return offlineCache.getProjectDetails(projectId);
    },
    [isReady]
  );

  // Cache video
  const cacheVideo = useCallback(
    async (
      videoId: string,
      projectId: string,
      blob: Blob,
      metadata: CachedVideo['metadata'],
      thumbnailBlob?: Blob
    ) => {
      if (!isReady) return;
      await offlineCache.cacheVideo(videoId, projectId, blob, metadata, thumbnailBlob);
      await refreshStats();
    },
    [isReady, refreshStats]
  );

  // Get cached video URL
  const getCachedVideoUrl = useCallback(
    async (videoId: string) => {
      if (!isReady) return null;
      return offlineCache.getVideoUrl(videoId);
    },
    [isReady]
  );

  // Check if cached
  const isCached = useCallback(
    async (type: 'project' | 'projectDetails' | 'video', id: string) => {
      if (!isReady) return false;
      return offlineCache.isCached(type, id);
    },
    [isReady]
  );

  // Queue an edit for sync
  const queueEdit = useCallback(
    async (
      type: 'update' | 'create' | 'delete',
      entity: 'project' | 'character' | 'scene' | 'shot',
      entityId: string,
      data: unknown
    ) => {
      if (!isReady) throw new Error('Cache not ready');
      const id = await offlineCache.addToSyncQueue({ type, entity, entityId, data });
      const queue = await offlineCache.getSyncQueue();
      setPendingSync(queue);
      await refreshStats();
      return id;
    },
    [isReady, refreshStats]
  );

  // Process sync queue
  const processQueue = useCallback(
    async (syncFn: (item: SyncQueueItem) => Promise<boolean>) => {
      if (!isReady || isSyncing) return;

      syncFnRef.current = syncFn;
      setIsSyncing(true);

      try {
        const queue = await offlineCache.getSyncQueue();

        for (const item of queue) {
          try {
            const success = await syncFn(item);
            if (success) {
              await offlineCache.removeFromSyncQueue(item.id);
            } else {
              await offlineCache.incrementSyncRetry(item.id);
            }
          } catch (error) {
            console.error(`Failed to sync item ${item.id}:`, error);
            await offlineCache.incrementSyncRetry(item.id);
          }
        }

        // Refresh pending items
        const updatedQueue = await offlineCache.getSyncQueue();
        setPendingSync(updatedQueue);
        await refreshStats();
      } finally {
        setIsSyncing(false);
      }
    },
    [isReady, isSyncing, refreshStats]
  );

  // Auto-sync when coming online
  useEffect(() => {
    if (!autoSync || !isOnline || !isReady || isSyncing) return;

    // If we have a sync function registered and items to sync, process them
    if (syncFnRef.current && pendingSync.length > 0) {
      processQueue(syncFnRef.current);
    }
  }, [autoSync, isOnline, isReady, isSyncing, pendingSync.length, processQueue]);

  // Clear cache
  const clearCache = useCallback(async () => {
    if (!isReady) return;
    await offlineCache.clearAll();
    setPendingSync([]);
    await refreshStats();
  }, [isReady, refreshStats]);

  return {
    isReady,
    stats,
    pendingSync,
    isSyncing,
    cacheProjects,
    getCachedProjects,
    cacheProjectDetails,
    getCachedProjectDetails,
    cacheVideo,
    getCachedVideoUrl,
    isCached,
    queueEdit,
    processQueue,
    clearCache,
    refreshStats,
  };
}

/**
 * Hook for caching project data with automatic cache-first pattern
 */
export function useCachedProject(projectId: string | null) {
  const [data, setData] = useState<unknown | null>(null);
  const [isCached, setIsCached] = useState(false);
  const [isLoading, setIsLoading] = useState(true);

  const { isReady, getCachedProjectDetails, cacheProjectDetails } = useOfflineCache();
  const { isOnline } = useOnlineStatus();

  // Load from cache first
  useEffect(() => {
    if (!isReady || !projectId) {
      setIsLoading(false);
      return;
    }

    const load = async () => {
      setIsLoading(true);
      try {
        const cached = await getCachedProjectDetails(projectId);
        if (cached) {
          setData(cached);
          setIsCached(true);
        }
      } catch (error) {
        console.error('Failed to load from cache:', error);
      } finally {
        setIsLoading(false);
      }
    };

    load();
  }, [isReady, projectId, getCachedProjectDetails]);

  // Update cache when new data is loaded
  const updateCache = useCallback(
    async (newData: unknown) => {
      if (!projectId || !isReady) return;
      setData(newData);
      await cacheProjectDetails(projectId, newData);
      setIsCached(true);
    },
    [projectId, isReady, cacheProjectDetails]
  );

  return {
    data,
    isCached,
    isLoading,
    isOnline,
    updateCache,
  };
}

export default useOfflineCache;
