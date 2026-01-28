/**
 * SceneMachine Service Worker
 * 
 * Provides:
 * - Cache-first for static assets
 * - Network-first for API calls
 * - Offline fallback pages
 * - Background sync for queued actions
 */

/// <reference lib="webworker" />

declare const self: ServiceWorkerGlobalScope;

const CACHE_NAME = 'scenemachine-v1';
const STATIC_CACHE = 'scenemachine-static-v1';
const DYNAMIC_CACHE = 'scenemachine-dynamic-v1';

// Static assets to cache on install
const STATIC_ASSETS = [
    '/',
    '/index.html',
    '/manifest.json',
    '/offline.html',
    // Add CSS and JS bundles here (they'll be added by build process)
];

// API endpoints to cache with network-first strategy
const API_CACHE_PATTERNS = [
    /\/api\/v1\/projects$/,
    /\/api\/v1\/characters/,
    /\/api\/v1\/voices/,
];

// ============================================================================
// Install Event
// ============================================================================

self.addEventListener('install', (event) => {
    console.log('[SW] Installing Service Worker...');

    event.waitUntil(
        caches.open(STATIC_CACHE)
            .then((cache) => {
                console.log('[SW] Caching static assets');
                return cache.addAll(STATIC_ASSETS);
            })
            .then(() => {
                console.log('[SW] Static assets cached');
                return self.skipWaiting();
            })
            .catch((err) => {
                console.error('[SW] Install failed:', err);
            })
    );
});

// ============================================================================
// Activate Event
// ============================================================================

self.addEventListener('activate', (event) => {
    console.log('[SW] Activating Service Worker...');

    event.waitUntil(
        caches.keys()
            .then((cacheNames) => {
                return Promise.all(
                    cacheNames
                        .filter((name) => name !== STATIC_CACHE && name !== DYNAMIC_CACHE)
                        .map((name) => {
                            console.log('[SW] Deleting old cache:', name);
                            return caches.delete(name);
                        })
                );
            })
            .then(() => {
                console.log('[SW] Service Worker activated');
                return self.clients.claim();
            })
    );
});

// ============================================================================
// Fetch Event
// ============================================================================

self.addEventListener('fetch', (event) => {
    const { request } = event;
    const url = new URL(request.url);

    // Skip non-GET requests
    if (request.method !== 'GET') {
        return;
    }

    // Skip chrome-extension and other non-http requests
    if (!url.protocol.startsWith('http')) {
        return;
    }

    // API requests: Network-first with cache fallback
    if (url.pathname.startsWith('/api/')) {
        event.respondWith(networkFirstStrategy(request));
        return;
    }

    // Static assets: Cache-first with network fallback
    event.respondWith(cacheFirstStrategy(request));
});

// ============================================================================
// Caching Strategies
// ============================================================================

/**
 * Cache-first strategy: Try cache, then network
 * Best for static assets (HTML, CSS, JS, images)
 */
async function cacheFirstStrategy(request: Request): Promise<Response> {
    const cachedResponse = await caches.match(request);

    if (cachedResponse) {
        // Return cached response and update cache in background
        updateCache(request);
        return cachedResponse;
    }

    try {
        const networkResponse = await fetch(request);

        // Cache successful responses
        if (networkResponse.ok) {
            const cache = await caches.open(STATIC_CACHE);
            cache.put(request, networkResponse.clone());
        }

        return networkResponse;
    } catch (error) {
        // Return offline page for navigation requests
        if (request.mode === 'navigate') {
            const offlinePage = await caches.match('/offline.html');
            if (offlinePage) {
                return offlinePage;
            }
        }

        throw error;
    }
}

/**
 * Network-first strategy: Try network, then cache
 * Best for API requests and dynamic data
 */
async function networkFirstStrategy(request: Request): Promise<Response> {
    try {
        const networkResponse = await fetch(request);

        // Cache successful GET responses for API data
        if (networkResponse.ok && shouldCacheApiResponse(request)) {
            const cache = await caches.open(DYNAMIC_CACHE);
            cache.put(request, networkResponse.clone());
        }

        return networkResponse;
    } catch (error) {
        // Fallback to cache on network failure
        const cachedResponse = await caches.match(request);

        if (cachedResponse) {
            console.log('[SW] Returning cached API response for:', request.url);
            return cachedResponse;
        }

        // Return offline JSON response for API requests
        return new Response(
            JSON.stringify({
                error: 'offline',
                message: 'You are offline. Please check your connection.',
            }),
            {
                status: 503,
                statusText: 'Service Unavailable',
                headers: { 'Content-Type': 'application/json' },
            }
        );
    }
}

/**
 * Update cache in background
 */
async function updateCache(request: Request): Promise<void> {
    try {
        const networkResponse = await fetch(request);
        if (networkResponse.ok) {
            const cache = await caches.open(STATIC_CACHE);
            cache.put(request, networkResponse);
        }
    } catch (error) {
        // Silently fail background updates
    }
}

/**
 * Check if API response should be cached
 */
function shouldCacheApiResponse(request: Request): boolean {
    const url = new URL(request.url);
    return API_CACHE_PATTERNS.some((pattern) => pattern.test(url.pathname));
}

// ============================================================================
// Background Sync
// ============================================================================

interface SyncEvent extends ExtendableEvent {
    tag: string;
}

self.addEventListener('sync', (event: SyncEvent) => {
    console.log('[SW] Background sync:', event.tag);

    if (event.tag === 'sync-pending-actions') {
        event.waitUntil(syncPendingActions());
    }
});

/**
 * Sync pending actions that were queued while offline
 */
async function syncPendingActions(): Promise<void> {
    // Get pending actions from IndexedDB
    const db = await openDatabase();
    const pendingActions = await getPendingActions(db);

    for (const action of pendingActions) {
        try {
            const response = await fetch(action.url, {
                method: action.method,
                headers: action.headers,
                body: action.body,
            });

            if (response.ok) {
                await removePendingAction(db, action.id);
                console.log('[SW] Synced action:', action.id);
            }
        } catch (error) {
            console.error('[SW] Failed to sync action:', action.id, error);
        }
    }
}

// ============================================================================
// IndexedDB Helpers
// ============================================================================

const DB_NAME = 'scenemachine-sw';
const DB_VERSION = 1;
const PENDING_STORE = 'pending-actions';

interface PendingAction {
    id: string;
    url: string;
    method: string;
    headers: Record<string, string>;
    body?: string;
    timestamp: number;
}

function openDatabase(): Promise<IDBDatabase> {
    return new Promise((resolve, reject) => {
        const request = indexedDB.open(DB_NAME, DB_VERSION);

        request.onerror = () => reject(request.error);
        request.onsuccess = () => resolve(request.result);

        request.onupgradeneeded = (event) => {
            const db = (event.target as IDBOpenDBRequest).result;
            if (!db.objectStoreNames.contains(PENDING_STORE)) {
                db.createObjectStore(PENDING_STORE, { keyPath: 'id' });
            }
        };
    });
}

function getPendingActions(db: IDBDatabase): Promise<PendingAction[]> {
    return new Promise((resolve, reject) => {
        const transaction = db.transaction(PENDING_STORE, 'readonly');
        const store = transaction.objectStore(PENDING_STORE);
        const request = store.getAll();

        request.onerror = () => reject(request.error);
        request.onsuccess = () => resolve(request.result);
    });
}

function removePendingAction(db: IDBDatabase, id: string): Promise<void> {
    return new Promise((resolve, reject) => {
        const transaction = db.transaction(PENDING_STORE, 'readwrite');
        const store = transaction.objectStore(PENDING_STORE);
        const request = store.delete(id);

        request.onerror = () => reject(request.error);
        request.onsuccess = () => resolve();
    });
}

// ============================================================================
// Push Notifications
// ============================================================================

interface PushMessageData {
    title: string;
    body: string;
    icon?: string;
    badge?: string;
    tag?: string;
    data?: Record<string, unknown>;
}

self.addEventListener('push', (event) => {
    if (!event.data) {
        return;
    }

    try {
        const data: PushMessageData = event.data.json();

        event.waitUntil(
            self.registration.showNotification(data.title, {
                body: data.body,
                icon: data.icon || '/icons/icon-192x192.png',
                badge: data.badge || '/icons/badge-72x72.png',
                tag: data.tag,
                data: data.data,
            })
        );
    } catch (error) {
        console.error('[SW] Push notification error:', error);
    }
});

self.addEventListener('notificationclick', (event) => {
    event.notification.close();

    const urlToOpen = event.notification.data?.url || '/';

    event.waitUntil(
        self.clients.matchAll({ type: 'window', includeUncontrolled: true })
            .then((clientList) => {
                // Focus existing window if available
                for (const client of clientList) {
                    if (client.url === urlToOpen && 'focus' in client) {
                        return client.focus();
                    }
                }
                // Open new window
                return self.clients.openWindow(urlToOpen);
            })
    );
});

// ============================================================================
// Message Handler
// ============================================================================

self.addEventListener('message', (event) => {
    const { type, payload } = event.data || {};

    switch (type) {
        case 'SKIP_WAITING':
            self.skipWaiting();
            break;

        case 'CACHE_URLS':
            event.waitUntil(
                caches.open(STATIC_CACHE).then((cache) => cache.addAll(payload.urls))
            );
            break;

        case 'CLEAR_CACHE':
            event.waitUntil(
                caches.keys().then((names) =>
                    Promise.all(names.map((name) => caches.delete(name)))
                )
            );
            break;
    }
});

console.log('[SW] Service Worker loaded');
