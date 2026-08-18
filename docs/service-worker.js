importScripts("./cache-manifest.js");

const CACHE_PREFIX = "paleoveg-";

function cacheableRequest(request) {
  const url = new URL(request.url);
  return request.method === "GET" && (
    url.origin === self.location.origin || url.href.startsWith(self.PALEOVEG_PYODIDE_PREFIX)
  );
}

async function cacheFirst(request) {
  const cached = await caches.match(request);
  if (cached) return cached;
  const response = await fetch(request);
  if (response.ok || response.type === "opaque") {
    const target = new URL(request.url).origin === self.location.origin
      ? self.PALEOVEG_RUNTIME_CACHE
      : self.PALEOVEG_RUNTIME_CACHE;
    caches.open(target).then(cache => cache.put(request, response.clone())).catch(() => {});
  }
  return response;
}

async function networkFirst(request) {
  try {
    const response = await fetch(request);
    if (response.ok) {
      caches.open(self.PALEOVEG_APP_CACHE).then(cache => cache.put(request, response.clone())).catch(() => {});
    }
    return response;
  } catch {
    const cached = await caches.match(request);
    if (cached) return cached;
    throw new Error("No network or cached response is available.");
  }
}

self.addEventListener("install", event => {
  event.waitUntil((async () => {
    const cache = await caches.open(self.PALEOVEG_APP_CACHE);
    await cache.addAll(self.PALEOVEG_PRECACHE);
    await self.skipWaiting();
  })());
});

self.addEventListener("activate", event => {
  event.waitUntil((async () => {
    const names = await caches.keys();
    await Promise.all(names
      .filter(name => name.startsWith(CACHE_PREFIX) && ![self.PALEOVEG_APP_CACHE, self.PALEOVEG_RUNTIME_CACHE].includes(name))
      .map(name => caches.delete(name)));
    await self.clients.claim();
  })());
});

self.addEventListener("fetch", event => {
  const url = new URL(event.request.url);
  const isApplicationEntry = url.origin === self.location.origin && (
    event.request.mode === "navigate" ||
    url.pathname.endsWith("/index.html") ||
    url.pathname.endsWith("/cache-manifest.js")
  );
  if (isApplicationEntry) event.respondWith(networkFirst(event.request));
  else if (cacheableRequest(event.request)) event.respondWith(cacheFirst(event.request));
});
