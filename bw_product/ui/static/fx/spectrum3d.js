// Dark corroboration screen: the warp tunnel is the measured envelope spectrum.
// Every streak's length and brightness comes from a real amplitude bin; the
// three lime wireframe rings echo the bearing races (outer, cage, inner).
// Nothing decorative carries a fake value. three.js is vendored, no CDN.
import * as THREE from '/static/vendor/three.module.js';

export function init(containerId, data) {
  const el = document.getElementById(containerId);
  if (!el) return;
  const W = el.clientWidth, H = el.clientHeight;
  const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: false });
  renderer.setPixelRatio(Math.min(2, window.devicePixelRatio || 1));
  renderer.setSize(W, H);
  el.appendChild(renderer.domElement);

  const scene = new THREE.Scene();
  scene.background = new THREE.Color(0x0f1111);
  scene.fog = new THREE.Fog(0x0f1111, 14, 46);
  const camera = new THREE.PerspectiveCamera(62, W / H, 0.1, 100);
  camera.position.set(0, 0, 16);

  const [freqs, amps] = data.envelope;
  const maxAmp = Math.max(...amps, 1e-9);

  // streak tunnel from the spectrum: one radial streak per bin (subsampled)
  const step = Math.max(1, Math.floor(freqs.length / 420));
  const positions = [], colors = [];
  const cCold = new THREE.Color(0x1f4fa3), cHot = new THREE.Color(0x64c3ff);
  const cPeak = new THREE.Color(0xd8ff3e);
  for (let i = 0; i < freqs.length; i += step) {
    const a = amps[i] / maxAmp;
    const ang = (freqs[i] / freqs[freqs.length - 1]) * Math.PI * 6 + (i % 7);
    const r0 = 2.2, r1 = 2.2 + 1.5 + a * 14;
    const z = -((i / freqs.length) * 34);
    positions.push(Math.cos(ang) * r0, Math.sin(ang) * r0, z,
                   Math.cos(ang) * r1, Math.sin(ang) * r1, z);
    const c = a > 0.5 ? cPeak : cCold.clone().lerp(cHot, a * 1.6);
    colors.push(c.r, c.g, c.b, c.r, c.g, c.b);
  }
  const geo = new THREE.BufferGeometry();
  geo.setAttribute('position', new THREE.Float32BufferAttribute(positions, 3));
  geo.setAttribute('color', new THREE.Float32BufferAttribute(colors, 3));
  const streaks = new THREE.LineSegments(
    geo, new THREE.LineBasicMaterial({ vertexColors: true, transparent: true, opacity: 0.9 }));
  scene.add(streaks);

  // bearing races: outer, cage, inner as lime wireframe rings
  const rings = new THREE.Group();
  for (const [radius, tube] of [[6.2, 0.05], [4.6, 0.04], [3.2, 0.05]]) {
    const ring = new THREE.Mesh(
      new THREE.TorusGeometry(radius, tube, 8, 96),
      new THREE.MeshBasicMaterial({ color: 0xd8ff3e, wireframe: true, transparent: true, opacity: 0.5 }));
    rings.add(ring);
  }
  scene.add(rings);

  let raf, t = 0;
  function frame() {
    if (!renderer.domElement.isConnected) {  // route changed: tear down
      cancelAnimationFrame(raf); geo.dispose(); renderer.dispose(); return;
    }
    t += 0.004;
    streaks.rotation.z = t * 0.5;
    rings.rotation.x = Math.sin(t) * 0.18;
    rings.rotation.y = t * 0.35;
    camera.position.z = 16 - Math.sin(t * 0.7) * 2.2;
    renderer.render(scene, camera);
    raf = requestAnimationFrame(frame);
  }
  frame();

  window.addEventListener('resize', () => {
    if (!renderer.domElement.isConnected) return;
    camera.aspect = el.clientWidth / el.clientHeight;
    camera.updateProjectionMatrix();
    renderer.setSize(el.clientWidth, el.clientHeight);
  });
}
