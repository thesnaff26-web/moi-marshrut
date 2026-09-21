const CACHE='rabochee-vremya-v19';
const APP_SHELL=['./','./index.html','./manifest.json','./icon.svg'];

self.addEventListener('install',event=>{
  event.waitUntil(
    caches.open(CACHE).then(cache=>cache.addAll(APP_SHELL)).then(()=>self.skipWaiting())
  );
});

self.addEventListener('activate',event=>{
  event.waitUntil(
    caches.keys().then(keys=>Promise.all(keys.filter(k=>k!==CACHE).map(k=>caches.delete(k))))
      .then(()=>self.clients.claim())
  );
});

self.addEventListener('fetch',event=>{
  const req=event.request;
  if(req.method!=='GET') return;

  if(req.mode==='navigate'){
    event.respondWith(
      caches.match('./index.html').then(cached=>{
        if(cached){
          event.waitUntil(
            fetch(req).then(resp=>{
              if(resp && resp.ok) return caches.open(CACHE).then(c=>c.put('./index.html',resp.clone()));
            }).catch(()=>{})
          );
          return cached;
        }
        return fetch(req).then(resp=>{
          if(resp && resp.ok) caches.open(CACHE).then(c=>c.put('./index.html',resp.clone()));
          return resp;
        }).catch(()=>caches.match('./index.html'));
      })
    );
    return;
  }

  event.respondWith(
    caches.match(req).then(cached=>{
      if(cached) return cached;
      return fetch(req).then(resp=>{
        if(resp && resp.ok && new URL(req.url).origin===self.location.origin){
          const copy=resp.clone();
          caches.open(CACHE).then(c=>c.put(req,copy));
        }
        return resp;
      });
    })
  );
});
