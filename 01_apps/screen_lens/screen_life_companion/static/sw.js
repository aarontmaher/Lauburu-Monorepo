self.addEventListener('install', (e) => {
  e.waitUntil(
    caches.open('life-companion-store').then((cache) => cache.addAll([
      '/',
      '/settings',
      '/static/manifest.json'
    ])),
  );
});

self.addEventListener('fetch', (e) => {
  e.respondWith(
    caches.match(e.request).then((response) => response || fetch(e.request)),
  );
});
