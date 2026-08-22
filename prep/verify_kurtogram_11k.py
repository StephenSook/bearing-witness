import sys
sys.path.insert(0, '/private/tmp/claude-501/-Users-vinhle-NVIDIA-x-Dell/6607c0ed-43f4-4df2-abe6-2f22ffb845fb/scratchpad')
import numpy as np, bw_dsp
x = bw_dsp.load_h('/Users/vinhle/NVIDIA-x-Dell/data/XJTU-SY/35Hz12kN/Bearing1_3/155.csv')
freqs, amp = bw_dsp.envelope_spectrum(x, (11000.0, 12000.0))
med = float(np.median(amp[(freqs >= 5.0) & (freqs <= 500.0)]))
best = None
for f0 in freqs[(freqs >= 105.2) & (freqs <= 110.6)]:
    peaks = [float(amp[np.abs(freqs - k * f0) <= 1.5].max()) for k in (1, 2, 3)]
    s = sum(peaks)
    if best is None or s > best[1]:
        best = (float(f0), s, peaks)
print(f"11000-12000: f0={best[0]:.3f} peaks={best[2][0]:.4f}/{best[2][1]:.4f}/{best[2][2]:.4f} "
      f"sum={best[1]:.5f} median={med:.6f} ratio={best[1]/med:.2f}x (claims: 0.2741/0.1258/0.07349, med 0.047475, 9.97x)")
