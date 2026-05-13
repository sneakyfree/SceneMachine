/**
 * Offline Cache utilities for SceneMachine
 * Provides caching for offline-first functionality
 */

// ============================================================================
// Types
// ============================================================================

export interface CacheEntry<T> {
    data: T;
    timestamp: number;
    expiresAt: number;
}

export interface CacheOptions {
    ttl?: number; // Time to live in milliseconds
    key?: string;
}

// ============================================================================
// Default TTL values
// ============================================================================

const DEFAULT_TTL = 5 * 60 * 1000; // 5 minutes
const LONG_TTL = 30 * 60 * 1000; // 30 minutes
const SHORT_TTL = 60 * 1000; // 1 minute

// ============================================================================
// In-memory cache
// ============================================================================

const memoryCache = new Map<string, CacheEntry<unknown>>();

/**
 * Get an item from the cache
 */
export function getCached<T>(key: string): T | null {
    const entry = memoryCache.get(key) as CacheEntry<T> | undefined;

    if (!entry) {
        return null;
    }

    // Check if expired
    if (Date.now() > entry.expiresAt) {
        memoryCache.delete(key);
        return null;
    }

    return entry.data;
}

/**
 * Set an item in the cache
 */
export function setCached<T>(key: string, data: T, options: CacheOptions = {}): void {
    const ttl = options.ttl ?? DEFAULT_TTL;
    const now = Date.now();

    memoryCache.set(key, {
        data,
        timestamp: now,
        expiresAt: now + ttl,
    });
}

/**
 * Remove an item from the cache
 */
export function removeCached(key: string): void {
    memoryCache.delete(key);
}

/**
 * Clear all cached items
 */
export function clearCache(): void {
    memoryCache.clear();
}

/**
 * Clear expired entries from cache
 */
export function cleanupExpired(): void {
    const now = Date.now();
    for (const [key, entry] of memoryCache.entries()) {
        if (now > entry.expiresAt) {
            memoryCache.delete(key);
        }
    }
}

// ============================================================================
// LocalStorage persistence
// ============================================================================

const STORAGE_PREFIX = 'scenemachine_cache_';

/**
 * Save data to persistent storage
 */
export function persistCache<T>(key: string, data: T, options: CacheOptions = {}): void {
    const ttl = options.ttl ?? LONG_TTL;
    const now = Date.now();

    const entry: CacheEntry<T> = {
        data,
        timestamp: now,
        expiresAt: now + ttl,
    };

    try {
        localStorage.setItem(STORAGE_PREFIX + key, JSON.stringify(entry));
    } catch (e) {
        console.warn('Failed to persist cache:', e);
    }
}

/**
 * Load data from persistent storage
 */
export function loadPersistedCache<T>(key: string): T | null {
    try {
        const stored = localStorage.getItem(STORAGE_PREFIX + key);
        if (!stored) return null;

        const entry = JSON.parse(stored) as CacheEntry<T>;

        // Check if expired
        if (Date.now() > entry.expiresAt) {
            localStorage.removeItem(STORAGE_PREFIX + key);
            return null;
        }

        return entry.data;
    } catch (e) {
        console.warn('Failed to load persisted cache:', e);
        return null;
    }
}

/**
 * Clear persisted cache
 */
export function clearPersistedCache(): void {
    try {
        const keys = Object.keys(localStorage);
        for (const key of keys) {
            if (key.startsWith(STORAGE_PREFIX)) {
                localStorage.removeItem(key);
            }
        }
    } catch (e) {
        console.warn('Failed to clear persisted cache:', e);
    }
}

// ============================================================================
// Cache with fetch pattern
// ============================================================================

/**
 * Get cached data or fetch if not available
 */
export async function getOrFetch<T>(
    key: string,
    fetcher: () => Promise<T>,
    options: CacheOptions = {}
): Promise<T> {
    // Try memory cache first
    const cached = getCached<T>(key);
    if (cached !== null) {
        return cached;
    }

    // Try persistent cache
    const persisted = loadPersistedCache<T>(key);
    if (persisted !== null) {
        // Also store in memory for faster access
        setCached(key, persisted, options);
        return persisted;
    }

    // Fetch fresh data
    const data = await fetcher();

    // Cache in both memory and persistence
    setCached(key, data, options);
    persistCache(key, data, options);

    return data;
}

// ============================================================================
// Offline-first cache service
// Used by hooks/use-offline-cache.ts and the project/timeline views.
//
// Implementation note: this is an in-memory + localStorage shim. An
// IndexedDB-backed implementation is the longer-term plan (see
// docs/UPGRADE_ROADMAP.md). For now this is correct enough that
// app builds, hooks work, and the data flow is exercised in dev mode.
// ============================================================================

export interface CachedProject {
    id: string;
    name: string;
    status?: string;
    updatedAt: string;
    description?: string;
    thumbnailUrl?: string;
    sceneCount?: number;
}

export interface CachedVideo {
    id: string;
    projectId: string;
    blob: Blob;
    thumbnailBlob?: Blob;
    metadata: {
        duration: number;
        resolution: string;
        fileSize: number;
        cachedAt: number;
    };
}

export interface SyncQueueItem {
    id: string;
    type: 'update' | 'create' | 'delete';
    entity: 'project' | 'character' | 'scene' | 'shot';
    entityId: string;
    data: unknown;
    createdAt: number;
    attempts?: number;
    lastError?: string;
}

class OfflineCacheService {
    private initialized = false;
    private projects: CachedProject[] = [];
    private projectDetails = new Map<string, unknown>();
    private videos = new Map<string, CachedVideo>();
    private objectUrls = new Map<string, string>();
    private syncQueue: SyncQueueItem[] = [];

    async init(): Promise<void> {
        if (this.initialized) return;
        // Load sync queue from localStorage so edits made offline survive
        // a reload.
        try {
            const raw = localStorage.getItem('scenemachine_sync_queue');
            if (raw) {
                const parsed = JSON.parse(raw);
                if (Array.isArray(parsed)) this.syncQueue = parsed;
            }
        } catch (e) {
            console.warn('Failed to restore sync queue from localStorage:', e);
        }
        this.initialized = true;
    }

    private persistSyncQueue(): void {
        try {
            localStorage.setItem('scenemachine_sync_queue', JSON.stringify(this.syncQueue));
        } catch (e) {
            console.warn('Failed to persist sync queue:', e);
        }
    }

    async getStats(): Promise<{
        projectCount: number;
        projectDetailsCount: number;
        videoCount: number;
        totalVideoSizeMB: number;
        syncQueueCount: number;
    }> {
        let totalBytes = 0;
        for (const v of this.videos.values()) totalBytes += v.metadata.fileSize;
        return {
            projectCount: this.projects.length,
            projectDetailsCount: this.projectDetails.size,
            videoCount: this.videos.size,
            totalVideoSizeMB: totalBytes / (1024 * 1024),
            syncQueueCount: this.syncQueue.length,
        };
    }

    async cacheProjects(projects: CachedProject[]): Promise<void> {
        this.projects = [...projects];
    }
    async getCachedProjects(): Promise<CachedProject[]> {
        return [...this.projects];
    }
    async cacheProjectDetails(projectId: string, data: unknown): Promise<void> {
        this.projectDetails.set(projectId, data);
    }
    async getCachedProjectDetails(projectId: string): Promise<unknown | null> {
        return this.projectDetails.get(projectId) ?? null;
    }

    async cacheVideo(
        videoId: string,
        projectId: string,
        blob: Blob,
        metadata: CachedVideo['metadata'],
        thumbnailBlob?: Blob,
    ): Promise<void> {
        this.videos.set(videoId, { id: videoId, projectId, blob, metadata, thumbnailBlob });
    }
    async getCachedVideoUrl(videoId: string): Promise<string | null> {
        const v = this.videos.get(videoId);
        if (!v) return null;
        if (!this.objectUrls.has(videoId)) {
            this.objectUrls.set(videoId, URL.createObjectURL(v.blob));
        }
        return this.objectUrls.get(videoId) ?? null;
    }

    async isCached(type: 'project' | 'projectDetails' | 'video', id: string): Promise<boolean> {
        if (type === 'project') return this.projects.some((p) => p.id === id);
        if (type === 'projectDetails') return this.projectDetails.has(id);
        if (type === 'video') return this.videos.has(id);
        return false;
    }

    async queueEdit(
        type: 'update' | 'create' | 'delete',
        entity: 'project' | 'character' | 'scene' | 'shot',
        entityId: string,
        data: unknown,
    ): Promise<string> {
        const item: SyncQueueItem = {
            id: `${entity}_${entityId}_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`,
            type,
            entity,
            entityId,
            data,
            createdAt: Date.now(),
            attempts: 0,
        };
        this.syncQueue.push(item);
        this.persistSyncQueue();
        return item.id;
    }

    async getSyncQueue(): Promise<SyncQueueItem[]> {
        return [...this.syncQueue];
    }

    async processQueue(
        syncFn: (item: SyncQueueItem) => Promise<boolean>,
    ): Promise<void> {
        const queue = [...this.syncQueue];
        for (const item of queue) {
            try {
                const ok = await syncFn(item);
                if (ok) {
                    this.syncQueue = this.syncQueue.filter((x) => x.id !== item.id);
                } else {
                    item.attempts = (item.attempts ?? 0) + 1;
                }
            } catch (e) {
                item.attempts = (item.attempts ?? 0) + 1;
                item.lastError = e instanceof Error ? e.message : String(e);
            }
        }
        this.persistSyncQueue();
    }

    async clearCache(): Promise<void> {
        this.projects = [];
        this.projectDetails.clear();
        for (const url of this.objectUrls.values()) URL.revokeObjectURL(url);
        this.objectUrls.clear();
        this.videos.clear();
        this.syncQueue = [];
        this.persistSyncQueue();
    }
}

export const offlineCache = new OfflineCacheService();

/**
 * Invalidate cache for a key pattern
 */
export function invalidatePattern(pattern: string): void {
    // Memory cache
    for (const key of memoryCache.keys()) {
        if (key.includes(pattern)) {
            memoryCache.delete(key);
        }
    }

    // Persistent cache
    try {
        const keys = Object.keys(localStorage);
        for (const key of keys) {
            if (key.startsWith(STORAGE_PREFIX) && key.includes(pattern)) {
                localStorage.removeItem(key);
            }
        }
    } catch (e) {
        console.warn('Failed to invalidate persistent cache:', e);
    }
}

// Export TTL constants
export { DEFAULT_TTL, LONG_TTL, SHORT_TTL };
