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
