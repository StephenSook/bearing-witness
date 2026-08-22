"""Supplementary: BPFO family sum and SNR for ALL swept bands + the 2-4 kHz fallback."""
import sys
sys.path.insert(0, '/private/tmp/claude-501/-Users-vinhle-NVIDIA-x-Dell/6607c0ed-43f4-4df2-abe6-2f22ffb845fb/scratchpad')
import numpy as np
import bw_dsp

x = bw_dsp.load_h('/Users/vinhle/NVIDIA-x-Dell/data/XJTU-SY/35Hz12kN/Bearing1_3/155.csv')

def family(band):
    freqs, amp = bw_dsp.envelope_spectrum(x, band)
    med = float(np.median(amp[(freqs >= 5.0) & (freqs <= 500.0)]))
    best = None
    for f0 in freqs[(freqs >= 105.2) & (freqs <= 110.6)]:
        s = sum(float(amp[np.abs(freqs - k * f0) <= 1.5].max()) for k in (1, 2, 3))
        if best is None or s > best[1]:
            best = (float(f0), s)
    return best[0], best[1], med, best[1] / med

bands = []
for bw in [4000.0, 2000.0, 1000.0, 500.0]:
    c = 1000.0 + bw / 2.0
    while c + bw / 2.0 <= 12200.0 + 1e-9:
        bands.append((c - bw / 2.0, c + bw / 2.0))
        c += bw / 2.0

res = []
for lo, hi in bands:
    f0, fs_, med, ratio = family((lo, hi))
    res.append((lo, hi, f0, fs_, med, ratio))

print("top 10 by family SUM:")
for lo, hi, f0, s, med, ratio in sorted(res, key=lambda r: r[3], reverse=True)[:10]:
    print(f"  {lo:7.0f}-{hi:7.0f}  f0={f0:.3f}  fam_sum={s:.5g}  ratio={ratio:.1f}x")
print("top 10 by family SNR (ratio to median):")
for lo, hi, f0, s, med, ratio in sorted(res, key=lambda r: r[5], reverse=True)[:10]:
    print(f"  {lo:7.0f}-{hi:7.0f}  f0={f0:.3f}  fam_sum={s:.5g}  ratio={ratio:.1f}x")
f0, s, med, ratio = family((2000.0, 4000.0))
print(f"fallback 2000-4000: f0={f0:.3f}  fam_sum={s:.5g}  median={med:.5g}  ratio={ratio:.1f}x")
