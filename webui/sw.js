/* Minimal service worker: shell + recently read /content for offline re-read */
const CACHE = "skycache-shell-v2";
const CONTENT_CACHE = "skycache-content-v1";
const SHELL = ["/", "/static/css/app.css", "/static/js/app.js", "/static/i18n/en.json"];

self.addEventListener("install", (event) => {
  event.waitUntil(caches.open(CACHE).then((c) => c.addAll(SHELL)).then(() => self.skipWaiting()));
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(
        keys
          .filter((k) => k !== CACHE && k !== CONTENT_CACHE && k.startsWith("skycache-"))
          .map((k) => caches.delete(k))
      )
    ).then(() => self.clients.claim())
  );
});

self.addEventListener("fetch", (event) => {
  const url = new URL(event.request.url);
  if (event.request.method !== "GET") return;

  // Live catalog always network
  if (url.pathname.startsWith("/api/")) {
    return;
  }

  // Content: network-first, then cache (offline re-read after first open)
  if (url.pathname.startsWith("/content/")) {
    event.respondWith(
      fetch(event.request)
        .then((res) => {
          if (res && res.ok) {
            const clone = res.clone();
            caches.open(CONTENT_CACHE).then((c) => c.put(event.request, clone));
          }
          return res;
        })
        .catch(() => caches.match(event.request))
    );
    return;
  }

  // App shell: cache-first with network fallback
  event.respondWith(
    caches.match(event.request).then((hit) => hit || fetch(event.request).catch(() => caches.match("/")))
  );
});
