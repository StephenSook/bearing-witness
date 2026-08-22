// Preloader: warm field + thin centered progress bar, then hands off to the
// pinhole reveal. Pure 2D, no dependencies. Killed entirely when BW_FX=off.
(function () {
  if (window.__bwFxOff) return;
  const dark = document.body.classList.contains('body--dark');
  const field = dark ? '#191b1b' : '#efede7';
  const ink = dark ? '#efede7' : '#111512';
  const el = document.createElement('div');
  el.id = 'bw-preloader';
  el.style.cssText = `position:fixed;inset:0;z-index:9999;background:${field};` +
    'display:flex;align-items:center;justify-content:center;transition:opacity .4s cubic-bezier(.66,0,.01,1)';
  el.innerHTML = `<div style="width:min(320px,60vw)">
    <div style="font:700 11px 'Geist Mono',monospace;letter-spacing:.18em;color:${ink};margin-bottom:10px">BEARING WITNESS</div>
    <div style="height:2px;background:${ink}22"><div id="bw-prebar" style="height:2px;width:0%;background:${ink};transition:width .2s"></div></div>
  </div>`;
  document.body.appendChild(el);
  let p = 0;
  const t = setInterval(() => {
    p = Math.min(96, p + 7 + Math.random() * 9);
    const bar = document.getElementById('bw-prebar');
    if (bar) bar.style.width = p + '%';
  }, 90);
  window.addEventListener('load', () => {
    setTimeout(() => {
      clearInterval(t);
      const bar = document.getElementById('bw-prebar');
      if (bar) bar.style.width = '100%';
      setTimeout(() => {
        el.style.opacity = '0';
        setTimeout(() => { el.remove(); if (window.bwPinhole) window.bwPinhole.open(); }, 400);
      }, 180);
    }, 250);
  });
})();
