const C = 'klipfox-v69', LIB = 'klipfox-lib';
self.addEventListener('install', (e) => { e.waitUntil(caches.open(C).then((c) => c.addAll(['./', 'index.html', 'manifest.webmanifest', 'apple-touch-icon.png', 'icon-192.png', 'icon-512.png']))); self.skipWaiting(); });
// keep the AI library (LIB) and old model downloads across app updates, so subtitles keep working offline
self.addEventListener('activate', (e) => { e.waitUntil(caches.keys().then((ks) => Promise.all(ks.filter((k) => k !== C && k !== LIB && k !== 'transformers-cache').map((k) => caches.delete(k))))); self.clients.claim(); });
self.addEventListener('fetch', (e) => {
  if (e.request.method !== 'GET') return;
  const u = new URL(e.request.url);
  const mine = u.origin === self.location.origin;
  // the AI model files are cached by the app itself; let everything else from other sites pass through
  const lib = u.hostname === 'cdn.jsdelivr.net' || u.hostname.startsWith('fonts.g') || u.hostname === 'storage.googleapis.com';
  if (!mine && !lib) return;
  // online services (proxied) and big media are always fetched fresh
  if (mine && (u.pathname.startsWith('/px/') || e.request.headers.has('range'))) return;
  const store = (lib || (mine && u.pathname.indexOf('/lib/') >= 0)) ? LIB : C;
  // the app page itself: newest from the network first (so an update shows on the next open), cached copy when offline
  if (mine && (e.request.mode === 'navigate' || u.pathname.endsWith('/') || u.pathname.endsWith('.html'))) {
    e.respondWith(fetch(e.request).then((res) => { if (res.ok) { const cp = res.clone(); caches.open(C).then((c) => c.put(e.request, cp)); } return res; }).catch(() => caches.match(e.request).then((hit) => hit || caches.match('index.html'))));
    return;
  }
  e.respondWith(caches.match(e.request).then((hit) => hit || fetch(e.request).then((res) => {
    if (res.ok) { const cp = res.clone(); caches.open(store).then((c) => c.put(e.request, cp)); }
    return res;
  }).catch(() => hit)));
});
