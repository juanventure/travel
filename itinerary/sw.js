/**
 * Horizon Voyages - Itinerary Service Worker (v2)
 * Network-first strategy with cache fallback for offline at-sea access.
 */

const CACHE_NAME = 'horizon-itinerary-v3';
const ASSETS_TO_CACHE = [
  './',
  './index.html',
  './style.css',
  './data.js',
  './app.js',
  './manifest.json',
  './assets/cruise_mediterranean.png',
  './assets/advisor_portrait.png',
  './assets/hero_cruise.png'
];

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
      console.log('[ServiceWorker v2] Pre-caching itinerary assets');
      return cache.addAll(ASSETS_TO_CACHE).catch((err) => {
        console.warn('[ServiceWorker v2] Some assets could not be pre-cached:', err);
      });
    })
  );
  self.skipWaiting();
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keyList) => {
      return Promise.all(
        keyList.map((key) => {
          if (key !== CACHE_NAME) {
            console.log('[ServiceWorker v2] Removing old cache', key);
            return caches.delete(key);
          }
        })
      );
    })
  );
  self.clients.claim();
});

self.addEventListener('fetch', (event) => {
  // Network-First with Cache Fallback: Always serve newest changes when connected; fallback to cache when offline
  if (event.request.method !== 'GET') return;

  event.respondWith(
    fetch(event.request)
      .then((networkResponse) => {
        if (networkResponse && networkResponse.status === 200) {
          const responseClone = networkResponse.clone();
          caches.open(CACHE_NAME).then((cache) => {
            cache.put(event.request, responseClone);
          });
        }
        return networkResponse;
      })
      .catch(() => {
        // Network failed (e.g. offline at sea) -> serve from cache
        return caches.match(event.request).then((cachedResponse) => {
          return cachedResponse || caches.match('./index.html');
        });
      })
  );
});
