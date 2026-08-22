"""Adversarial re-check of kurtogram prep claims on Bearing1_3 file 155.
Independent recompute using bw_dsp primitives only."""
import sys
sys.path.insert(0, '/private/tmp/claude-501/-Users-vinhle-NVIDIA-x-Dell/6607c0ed-43f4-4df2-abe6-2f22ffb845fb/scratchpad')
import numpy as np
import bw_dsp

x = bw_dsp.load_h('/Users/vinhle/NVIDIA-x-Dell/data/XJTU-SY/35Hz12kN/Bearing1_3/155.csv')
print(f"n samples = {len(x)}")

# --- band grid: bandwidths 4000/2000/1000/500, half-overlap steps, within 1000-12200 Hz ---
bands = []
for bw in (4000.0, 2000.0, 1000.0, 500.0):
    lo = 1000.0
    while lo + bw <= 12200.0 + 1e-9:
        bands.append((lo, lo + bw))
        lo += bw / 2.0
print(f"candidate bands = {len(bands)}")

kt, ke = {}, {}
for b in bands:
    xb = bw_dsp.bandpass(x, b[0], b[1])
    kt[b] = bw_dsp.excess_kurtosis(xb)
    env, _ = bw_dsp.envelope(x, b)
    ke[b] = bw_dsp.excess_kurtosis(env)

top_t = sorted(bands, key=lambda b: kt[b], reverse=True)
top_e = sorted(bands, key=lambda b: ke[b], reverse=True)
print("\nTop-5 by k_time:")
for b in top_t[:5]:
    print(f"  {b[0]:7.0f}-{b[1]:7.0f}  k_time={kt[b]:.4f}  k_env={ke[b]:.4f}")
print("Top-5 by k_env:")
for b in top_e[:5]:
    print(f"  {b[0]:7.0f}-{b[1]:7.0f}  k_time={kt[b]:.4f}  k_env={ke[b]:.4f}")
print(f"\nCLAIM 1: winner both rankings = 11500-12000?  time#1={top_t[0]}  env#1={top_e[0]}  agree={top_t[0]==top_e[0]}")
w = (11500.0, 12000.0)
print(f"CLAIM 2: winner scores  k_env={ke[w]:.4f} (claim 8.228)   k_time={kt[w]:.4f} (claim 3.777)")

# --- BPFO family check ---
def family(band):
    freqs, amp = bw_dsp.envelope_spectrum(x, band)
    med = float(np.median(amp[(freqs >= 5.0) & (freqs <= 500.0)]))
    best = None
    # f0 within +/-2.5% of predicted 107.907 -> 105.2 .. 110.6
    for f0 in freqs[(freqs >= 105.2) & (freqs <= 110.6)]:
        peaks = [float(amp[np.abs(freqs - k * f0) <= 1.5].max()) for k in (1, 2, 3)]
        s = float(sum(peaks))
        if best is None or s > best[1]:
            best = (float(f0), s, peaks)
    return best[0], best[1], best[2], med, best[1] / med

f0w, sw, pw, medw, rw = family(w)
print(f"\nCLAIM 3: winner family  f0={f0w:.3f} (claim 107.031)  fam_sum={sw:.5f} (claim 0.18521)")
print(f"         peaks={pw[0]:.5f}/{pw[1]:.5f}/{pw[2]:.5f} (claim 0.1002/0.0522/0.03276)")
print(f"         median={medw:.6f} (claim 0.016276)  ratio={rw:.2f}x (claim 11.4x)")

fb = (2000.0, 4000.0)
f0f, sf, pf, medf, rf = family(fb)
print(f"\nCLAIM 4: fallback 2-4 kHz  f0={f0f:.3f} (claim 107.031)  fam_sum={sf:.5f} (claim 1.4492)")
print(f"         fundamental={pf[0]:.5f} (claim 0.63763)  median={medf:.6f} (claim 0.048141)  ratio={rf:.2f}x (claim 30.1x)")
print(f"         fallback k_env={ke[fb]:.4f} (claim 0.454)  k_time={kt[fb]:.4f} (claim 0.174)")

print(f"\nCLAIM 5: winner vs fallback  fund ratio={pw[0]/pf[0]:.3f} (claim 0.16x)  "
      f"sum ratio={sw/sf:.3f} (claim 0.13x)")

# --- full-sweep family scan for best-band claims ---
fam_all = {b: family(b) for b in bands}
best_snr = max(bands, key=lambda b: fam_all[b][4])
best_sum = max(bands, key=lambda b: fam_all[b][1])
b1, b2 = best_snr, best_sum
print(f"\nCLAIM 6: best family SNR band = {b1[0]:.0f}-{b1[1]:.0f} (claim 1000-1500)  "
      f"ratio={fam_all[b1][4]:.1f}x (claim 80.9x)  sum={fam_all[b1][1]:.4f} (claim 3.789)")
print(f"CLAIM 7: largest family sum band = {b2[0]:.0f}-{b2[1]:.0f} (claim 1000-5000)  "
      f"sum={fam_all[b2][1]:.4f} (claim 4.315)  ratio={fam_all[b2][4]:.1f}x (claim 53.3x)")

# f0 identical across top-5 bands of both rankings?
checked = list(dict.fromkeys(top_t[:5] + top_e[:5]))
f0s = {b: fam_all[b][0] for b in checked}
print(f"\nCLAIM 8: f0 across {len(checked)} top-5 bands: {sorted(set(round(v,3) for v in f0s.values()))}")
print(f"slip check: 107.031/107.907 = {107.03125/107.907:.5f} (~{(1-107.03125/107.907)*100:.2f}% low)")
