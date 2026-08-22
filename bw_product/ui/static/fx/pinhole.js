// Halftone pinhole reveal (2D canvas port of haoqi's MaskedDotsEffect idea):
// a radial mask dilates open and the covered region renders as a dot matrix
// whose dot size follows the mask edge. Used on first paint and theme flips.
(function () {
  if (window.__bwFxOff) { window.bwPinhole = { open: () => {}, wipe: (cb) => cb && cb() }; return; }
  const EASE = t => 1 - Math.pow(1 - t, 3);
  const CELL = Math.max(10, Math.round(14 / (window.devicePixelRatio > 1.5 ? 1 : 1)));

  function run(mode, cb) {
    const dark = document.body.classList.contains('body--dark');
    const field = dark ? '#191b1b' : '#efede7';
    const c = document.createElement('canvas');
    c.style.cssText = 'position:fixed;inset:0;z-index:9998;pointer-events:none';
    const dpr = Math.min(2, window.devicePixelRatio || 1);
    c.width = innerWidth * dpr; c.height = innerHeight * dpr;
    document.body.appendChild(c);
    const ctx = c.getContext('2d');
    ctx.scale(dpr, dpr);
    const cx = innerWidth / 2, cy = innerHeight / 2;
    const maxR = Math.hypot(cx, cy) * 1.05;
    const t0 = performance.now(), DUR = 900;

    function frame(now) {
      const t = Math.min(1, (now - t0) / DUR);
      const r = maxR * EASE(mode === 'open' ? t : 1 - t);
      ctx.clearRect(0, 0, innerWidth, innerHeight);
      ctx.fillStyle = field;
      for (let y = CELL / 2; y < innerHeight + CELL; y += CELL) {
        for (let x = CELL / 2; x < innerWidth + CELL; x += CELL) {
          const d = Math.hypot(x - cx, y - cy);
          // inside r: revealed (dot shrinks to 0); at the edge: halftone ramp
          const k = Math.max(0, Math.min(1, (d - r) / (CELL * 6)));
          const rad = (CELL * 0.72) * k;
          if (rad > 0.4) { ctx.beginPath(); ctx.arc(x, y, rad, 0, 6.2832); ctx.fill(); }
        }
      }
      if (t < 1) requestAnimationFrame(frame);
      else { c.remove(); cb && cb(); }
    }
    requestAnimationFrame(frame);
  }

  window.bwPinhole = {
    open: cb => run('open', cb),
    // wipe: close fully then let the caller change the page, it reopens itself
    wipe: cb => run('close', () => { cb && cb(); setTimeout(() => run('open'), 60); }),
  };
})();
