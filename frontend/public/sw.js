const CACHE_NAME = 'sylus-shell-v6';
const SHELL_FILES = ['/', '/index.html', '/manifest.webmanifest', '/icon.svg'];

self.addEventListener('install', event => {
  event.waitUntil(caches.open(CACHE_NAME).then(cache => cache.addAll(SHELL_FILES.map(path => new Request(path, { cache: 'reload' })))));
  self.skipWaiting();
});

self.addEventListener('activate', event => {
  event.waitUntil(
    caches.keys()
      .then(keys => Promise.all(keys.filter(key => key !== CACHE_NAME).map(key => caches.delete(key))))
      .then(() => self.clients.claim())
  );
});

self.addEventListener('push', event => {
  let payload = {};
  try { payload = event.data ? event.data.json() : {}; } catch { payload = { body: event.data?.text() || '' }; }
  const title = payload.title || 'Sylus';
  const incomingCall = (payload.url || '').includes('incoming-call=1');
  const options = {
    body: payload.body || 'A message for you.',
    icon: '/icon.svg',
    badge: '/icon.svg',
    tag: incomingCall ? 'sylus-incoming-call' : 'sylus-proactive-message',
    renotify: incomingCall,
    requireInteraction: incomingCall,
    silent: false,
    vibrate: incomingCall ? [450, 180, 450, 180, 700] : [180, 100, 180],
    actions: incomingCall ? [{ action: 'open-call', title: 'Open call' }] : [],
    data: { url: payload.url || '/' }
  };
  event.waitUntil(self.registration.showNotification(title, options));
});

self.addEventListener('notificationclick', event => {
  event.notification.close();
  const target = new URL(event.notification.data?.url || '/', self.location.origin).href;
  event.waitUntil(
    self.clients.matchAll({ type: 'window', includeUncontrolled: true }).then(clients => {
      for (const client of clients) {
        if (client.url.startsWith(self.location.origin) && 'focus' in client) {
          client.navigate(target);
          return client.focus();
        }
      }
      return self.clients.openWindow(target);
    })
  );
});

self.addEventListener('fetch', event => {
  const request = event.request;
  if (request.method !== 'GET') return;
  const url = new URL(request.url);
  if (url.origin !== self.location.origin || url.pathname.startsWith('/v1/') || url.pathname === '/health') return;
  if (request.mode === 'navigate') {
    event.respondWith(fetch(request).catch(() => caches.match('/index.html')));
    return;
  }
  if (url.pathname.startsWith('/assets/') || url.pathname === '/manifest.webmanifest' || url.pathname === '/icon.svg') {
    event.respondWith(caches.match(request).then(cached => cached || fetch(request).then(response => {
      if (response.ok) {
        const copy = response.clone();
        caches.open(CACHE_NAME).then(cache => cache.put(request, copy));
      }
      return response;
    })));
  }
});
