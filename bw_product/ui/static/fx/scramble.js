// ASCII scramble mount animation (80 ms per letter, like the haoqi labels).
// Applies to [data-scramble] (every mount) and [data-scramble-once] (first
// mount only). A MutationObserver catches sub-page re-renders.
(function () {
  if (window.__bwFxOff) return;
  const GLYPHS = '#/\\|+*=<>[]{}%$&@!?';
  function scramble(el) {
    if (el.__bwScrambling) return;
    const final = el.dataset.finalText || el.textContent;
    el.dataset.finalText = final;
    el.__bwScrambling = true;
    const t0 = performance.now(), PER = 80;
    function frame(now) {
      const done = Math.floor((now - t0) / PER);
      let out = '';
      for (let i = 0; i < final.length; i++) {
        out += i < done ? final[i]
          : (final[i] === ' ' ? ' ' : GLYPHS[(Math.random() * GLYPHS.length) | 0]);
      }
      el.textContent = out;
      if (done < final.length) requestAnimationFrame(frame);
      else { el.textContent = final; el.__bwScrambling = false; }
    }
    requestAnimationFrame(frame);
  }
  function sweep(root) {
    root.querySelectorAll('[data-scramble]').forEach(scramble);
    root.querySelectorAll('[data-scramble-once]:not([data-scrambled])').forEach(el => {
      el.setAttribute('data-scrambled', '1'); scramble(el);
    });
  }
  new MutationObserver(muts => {
    for (const m of muts) for (const n of m.addedNodes) {
      if (n.nodeType === 1) sweep(n.matches('[data-scramble],[data-scramble-once]') ? n.parentElement || n : n);
    }
  }).observe(document.body, { childList: true, subtree: true });
  window.addEventListener('load', () => sweep(document));
})();
