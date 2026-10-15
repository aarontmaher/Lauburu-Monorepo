// Terminal IDE Lauburu - High-Performance Offline Service Worker
const CACHE_NAME = 'terminal-ide-lauburu-v1';
const STATIC_ASSETS = [
  './',
  './index.html',
  './manifest.json',
  './icon.svg'
];

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
      console.log('[Terminal IDE ServiceWorker] Pre-caching offline shell');
      return cache.addAll(STATIC_ASSETS);
    }).then(() => self.skipWaiting())
  );
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) => {
      return Promise.all(
        keys.map((key) => {
          if (key !== CACHE_NAME) {
            console.log('[Terminal IDE ServiceWorker] Purging stale cache:', key);
            return caches.delete(key);
          }
        })
      );
    }).then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', (event) => {
  const url = new URL(event.request.url);
  
  // Do not intercept WebSocket or local streaming/IPC endpoints
  if (url.protocol === 'ws:' || url.protocol === 'wss:' || url.pathname.startsWith('/ws') || url.pathname.startsWith('/stream')) {
    return;
  }

  // Network-first for dynamic API endpoints (:8082, :8081, :4000, /api/)
  if (url.pathname.startsWith('/api') || url.port === '8082' || url.port === '8081' || url.port === '9999') {
    event.respondWith(
      fetch(event.request).catch(() => {
        return new Response(JSON.stringify({ 
          status: 'offline', 
          message: 'Local mesh daemon unreachable in offline mode. Waiting for reconnect (--).' 
        }), {
          headers: { 'Content-Type': 'application/json' }
        });
      })
    );
    return;
  }

  // Cache-first, network fallback for static shell assets
  event.respondWith(
    caches.match(event.request).then((cachedResponse) => {
      if (cachedResponse) {
        return cachedResponse;
      }
      return fetch(event.request).then((networkResponse) => {
        if (!networkResponse || networkResponse.status !== 200 || networkResponse.type !== 'basic') {
          return networkResponse;
        }
        const responseToCache = networkResponse.clone();
        caches.open(CACHE_NAME).then((cache) => {
          cache.put(event.request, responseToCache);
        });
        return networkResponse;
      });
    })
  );
});
