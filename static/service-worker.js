const CACHE_NAME = "clinic-cache-v1";
const urlsToCache = [
  "/",
  "/static/icon-192.png",
  "/static/icon-512.png",
  "/static/manifest.json"
];

// تخزين الملفات عند التثبيت
self.addEventListener("install", event => {
  event.waitUntil(
    caches.open(CACHE_NAME).then(cache => cache.addAll(urlsToCache))
  );
});

// استخدام الملفات من الكاش إن لم يكن هناك اتصال
self.addEventListener("fetch", event => {
  event.respondWith(
    fetch(event.request).catch(() => caches.match(event.request))
  );
});
