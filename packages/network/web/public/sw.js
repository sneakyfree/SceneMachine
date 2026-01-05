/**
 * Service Worker for SceneMachine Network PWA.
 *
 * Handles:
 * - Offline caching of app shell
 * - Background sync for watchlist
 * - Video caching for offline viewing
 * - Push notifications
 */

const CACHE_VERSION = 'v1';
const STATIC_CACHE = `static-${CACHE_VERSION}`;
const DYNAMIC_CACHE = `dynamic-${CACHE_VERSION}`;
const VIDEO_CACHE = `videos-${CACHE_VERSION}`;

// Files to cache immediately (app shell)
const STATIC_ASSETS = [
  '/',
  '/index.html',
  '/manifest.json',
  '/offline.html',
  '/icons/icon-192x192.png',
  '/icons/icon-512x512.png',
];

// API routes to cache with network-first strategy
const API_CACHE_ROUTES = [
  '/api/v1/feed',
  '/api/v1/watchlist',
  '/api/v1/me',
];

// Maximum items in dynamic cache
const MAX_DYNAMIC_CACHE_ITEMS = 50;

// Maximum video cache size (500MB)
const MAX_VIDEO_CACHE_SIZE = 500 * 1024 * 1024;

/**
 * Install event - cache static assets
 */
self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(STATIC_CACHE).then((cache) => {
      console.log('[SW] Caching static assets');
      return cache.addAll(STATIC_ASSETS);
    })
  );
  // Activate immediately
  self.skipWaiting();
});

/**
 * Activate event - clean up old caches
 */
self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) => {
      return Promise.all(
        keys
          .filter((key) =>
            key.startsWith('static-') ||
            key.startsWith('dynamic-') ||
            key.startsWith('videos-')
          )
          .filter((key) =>
            key !== STATIC_CACHE &&
            key !== DYNAMIC_CACHE &&
            key !== VIDEO_CACHE
          )
          .map((key) => {
            console.log('[SW] Deleting old cache:', key);
            return caches.delete(key);
          })
      );
    })
  );
  // Take control immediately
  self.clients.claim();
});

/**
 * Fetch event - serve from cache or network
 */
self.addEventListener('fetch', (event) => {
  const { request } = event;
  const url = new URL(request.url);

  // Skip non-GET requests
  if (request.method !== 'GET') {
    return;
  }

  // Handle API requests (network-first)
  if (url.pathname.startsWith('/api/')) {
    event.respondWith(networkFirst(request));
    return;
  }

  // Handle video/audio requests (cache-first for downloaded, network for streaming)
  if (
    request.destination === 'video' ||
    request.destination === 'audio' ||
    url.pathname.includes('/stream/')
  ) {
    event.respondWith(handleMediaRequest(request));
    return;
  }

  // Handle static assets (cache-first)
  if (
    request.destination === 'style' ||
    request.destination === 'script' ||
    request.destination === 'font' ||
    request.destination === 'image'
  ) {
    event.respondWith(cacheFirst(request));
    return;
  }

  // Handle navigation (network-first with offline fallback)
  if (request.mode === 'navigate') {
    event.respondWith(navigationHandler(request));
    return;
  }

  // Default: network-first
  event.respondWith(networkFirst(request));
});

/**
 * Cache-first strategy
 */
async function cacheFirst(request) {
  const cached = await caches.match(request);
  if (cached) {
    return cached;
  }

  try {
    const response = await fetch(request);
    if (response.ok) {
      const cache = await caches.open(DYNAMIC_CACHE);
      cache.put(request, response.clone());
      trimCache(DYNAMIC_CACHE, MAX_DYNAMIC_CACHE_ITEMS);
    }
    return response;
  } catch (error) {
    console.error('[SW] Fetch failed:', error);
    return new Response('Offline', { status: 503 });
  }
}

/**
 * Network-first strategy
 */
async function networkFirst(request) {
  try {
    const response = await fetch(request);
    if (response.ok) {
      const cache = await caches.open(DYNAMIC_CACHE);
      cache.put(request, response.clone());
    }
    return response;
  } catch (error) {
    const cached = await caches.match(request);
    if (cached) {
      return cached;
    }
    return new Response(JSON.stringify({ error: 'Offline' }), {
      status: 503,
      headers: { 'Content-Type': 'application/json' },
    });
  }
}

/**
 * Navigation handler with offline fallback
 */
async function navigationHandler(request) {
  try {
    const response = await fetch(request);
    return response;
  } catch (error) {
    const cached = await caches.match(request);
    if (cached) {
      return cached;
    }
    // Return offline page
    return caches.match('/offline.html');
  }
}

/**
 * Handle media requests (video/audio)
 */
async function handleMediaRequest(request) {
  // Check if video is in cache (downloaded for offline)
  const cached = await caches.match(request);
  if (cached) {
    return cached;
  }

  // Stream from network
  try {
    return await fetch(request);
  } catch (error) {
    console.error('[SW] Media fetch failed:', error);
    return new Response('Media not available offline', { status: 503 });
  }
}

/**
 * Trim cache to maximum size
 */
async function trimCache(cacheName, maxItems) {
  const cache = await caches.open(cacheName);
  const keys = await cache.keys();
  if (keys.length > maxItems) {
    // Delete oldest items
    const toDelete = keys.slice(0, keys.length - maxItems);
    await Promise.all(toDelete.map((key) => cache.delete(key)));
  }
}

/**
 * Download video for offline viewing
 */
async function downloadVideoForOffline(videoId, videoUrl) {
  const cache = await caches.open(VIDEO_CACHE);

  // Check current cache size
  const keys = await cache.keys();
  let totalSize = 0;
  for (const key of keys) {
    const response = await cache.match(key);
    if (response) {
      const blob = await response.blob();
      totalSize += blob.size;
    }
  }

  // Fetch video
  const response = await fetch(videoUrl);
  const blob = await response.blob();

  // Check if we have space
  if (totalSize + blob.size > MAX_VIDEO_CACHE_SIZE) {
    // Remove oldest videos until we have space
    for (const key of keys) {
      const cachedResponse = await cache.match(key);
      if (cachedResponse) {
        const cachedBlob = await cachedResponse.blob();
        await cache.delete(key);
        totalSize -= cachedBlob.size;
        if (totalSize + blob.size <= MAX_VIDEO_CACHE_SIZE) {
          break;
        }
      }
    }
  }

  // Cache the video
  await cache.put(videoUrl, new Response(blob, {
    headers: response.headers,
  }));

  // Notify client
  const clients = await self.clients.matchAll();
  clients.forEach((client) => {
    client.postMessage({
      type: 'VIDEO_DOWNLOADED',
      videoId,
    });
  });
}

/**
 * Remove video from offline cache
 */
async function removeVideoFromOffline(videoUrl) {
  const cache = await caches.open(VIDEO_CACHE);
  await cache.delete(videoUrl);
}

/**
 * Message handler for client communication
 */
self.addEventListener('message', (event) => {
  const { type, payload } = event.data;

  switch (type) {
    case 'DOWNLOAD_VIDEO':
      downloadVideoForOffline(payload.videoId, payload.videoUrl);
      break;

    case 'REMOVE_VIDEO':
      removeVideoFromOffline(payload.videoUrl);
      break;

    case 'GET_CACHED_VIDEOS':
      getCachedVideos().then((videos) => {
        event.source.postMessage({
          type: 'CACHED_VIDEOS',
          videos,
        });
      });
      break;

    case 'SKIP_WAITING':
      self.skipWaiting();
      break;
  }
});

/**
 * Get list of cached videos
 */
async function getCachedVideos() {
  const cache = await caches.open(VIDEO_CACHE);
  const keys = await cache.keys();
  return keys.map((request) => request.url);
}

/**
 * Background sync for watchlist
 */
self.addEventListener('sync', (event) => {
  if (event.tag === 'sync-watchlist') {
    event.waitUntil(syncWatchlist());
  }
});

/**
 * Sync watchlist with server
 */
async function syncWatchlist() {
  // Get pending watchlist changes from IndexedDB
  // This would be implemented with actual IndexedDB operations
  console.log('[SW] Syncing watchlist...');
}

/**
 * Push notification handler
 */
self.addEventListener('push', (event) => {
  if (!event.data) return;

  const data = event.data.json();
  const options = {
    body: data.body,
    icon: '/icons/icon-192x192.png',
    badge: '/icons/badge-72x72.png',
    image: data.image,
    vibrate: [100, 50, 100],
    data: {
      url: data.url,
    },
    actions: data.actions || [],
  };

  event.waitUntil(
    self.registration.showNotification(data.title, options)
  );
});

/**
 * Notification click handler
 */
self.addEventListener('notificationclick', (event) => {
  event.notification.close();

  const url = event.notification.data?.url || '/';

  event.waitUntil(
    self.clients.matchAll({ type: 'window' }).then((clients) => {
      // Check if a window is already open
      for (const client of clients) {
        if (client.url === url && 'focus' in client) {
          return client.focus();
        }
      }
      // Open new window
      if (self.clients.openWindow) {
        return self.clients.openWindow(url);
      }
    })
  );
});
