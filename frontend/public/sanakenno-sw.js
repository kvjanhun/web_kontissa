// Sanakenno Service Worker — minimal, cache app shell + static assets
const CACHE_NAME = 'sanakenno-v1'

const PRECACHE = [
  '/sanakenno-favicon-v2.png',
  '/sanakenno-apple-touch-icon.png',
  '/sanakenno-icon-192.png',
  '/sanakenno-icon-512.png',
]

// Install: pre-cache icons
self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => cache.addAll(PRECACHE))
  )
  self.skipWaiting()
})

// Activate: clean old caches
self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.filter((k) => k !== CACHE_NAME).map((k) => caches.delete(k)))
    )
  )
  self.clients.claim()
})

// Fetch strategy:
// - API calls: passthrough (game needs fresh puzzles)
// - Navigation (HTML): network-first, cache fallback for offline
// - Static assets (JS/CSS/images): stale-while-revalidate
self.addEventListener('fetch', (event) => {
  const url = new URL(event.request.url)

  // API calls: let browser handle normally
  if (url.pathname.startsWith('/api/')) {
    return
  }

  // Navigation requests: network-first so the page always gets fresh HTML+JS
  if (event.request.mode === 'navigate') {
    event.respondWith(
      fetch(event.request)
        .then((response) => {
          const clone = response.clone()
          caches.open(CACHE_NAME).then((cache) => cache.put(event.request, clone))
          return response
        })
        .catch(() => caches.match(event.request))
    )
    return
  }

  // Static assets: stale-while-revalidate
  event.respondWith(
    caches.open(CACHE_NAME).then((cache) =>
      cache.match(event.request).then((cached) => {
        const fetchPromise = fetch(event.request).then((response) => {
          if (response.ok) {
            cache.put(event.request, response.clone())
          }
          return response
        })
        return cached || fetchPromise
      })
    )
  )
})
