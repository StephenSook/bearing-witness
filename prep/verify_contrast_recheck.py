import sys
sys.path.insert(0, '/private/tmp/claude-501/-Users-vinhle-NVIDIA-x-Dell/6607c0ed-43f4-4df2-abe6-2f22ffb845fb/scratchpad')
import numpy as np
import bw_dsp

DATA = '/Users/vinhle/NVIDIA-x-Dell/data/XJTU-SY/35Hz12kN/Bearing1_3'
BPFO = 107.907
FTF = 13.488
REL = 0.025
hw = BPFO * REL   # 2.6977 -> window 105.209 - 110.605
print(f"BPFO window: {BPFO-hw:.3f} - {BPFO+hw:.3f} Hz")

def top_peak(freqs, amp, lo, hi):
    m = (freqs >= lo) & (freqs <= hi)
    i = int(np.argmax(amp[m]))
    return float(freqs[m][i]), float(amp[m][i])

res = {}
for fn in (2, 8, 155):
    x = bw_dsp.load_h(f"{DATA}/{fn}.csv")
    print(f"file {fn}: n_samples={len(x)}")
    freqs, amp = bw_dsp.envelope_spectrum(x, bw_dsp.DEMOD_BAND)
    mb = (freqs >= 5.0) & (freqs <= 500.0)
    med = float(np.median(amp[mb]))
    f_top, a_top = top_peak(freqs, amp, 5.0, 500.0)
    f_b, a_b = top_peak(freqs, amp, BPFO - hw, BPFO + hw)
    print(f"  median 5-500 Hz: {med:.4e}")
    print(f"  top peak 5-500: {a_top:.4e} at {f_top:.3f} Hz ({a_top/med:.2f}x median)")
    print(f"  BPFO-window peak: {a_b:.4e} at {f_b:.3f} Hz ({a_b/med:.2f}x median)")
    res[fn] = dict(med=med, f_top=f_top, a_top=a_top, f_b=f_b, a_b=a_b)
    for k in (2, 3):
        hwk = k * BPFO * REL
        fk, ak = top_peak(freqs, amp, k*BPFO - hwk, k*BPFO + hwk)
        loc = (freqs >= k*BPFO - 25) & (freqs <= k*BPFO + 25)
        med_loc = float(np.median(amp[loc]))
        print(f"  {k}xBPFO peak: {ak:.4e} at {fk:.3f} Hz ({ak/med_loc:.2f}x local median {med_loc:.4e})")
    for sign, tag in ((-1,'BPFO-FTF'), (+1,'BPFO+FTF')):
        fc = BPFO + sign*FTF
        hws = fc * REL
        fsb, asb = top_peak(freqs, amp, fc - hws, fc + hws)
        print(f"  sideband {tag}: {asb:.4e} at {fsb:.3f} Hz ({asb/med:.2f}x median)")

print(f"\nlate/early ratio 155 vs 2: {res[155]['a_b']/res[2]['a_b']:.2f}x")
print(f"late/early ratio 155 vs 8: {res[155]['a_b']/res[8]['a_b']:.2f}x")

# Stage-1 baseline files 1-10
feats = []
for i in range(1, 11):
    x = bw_dsp.load_h(f"{DATA}/{i}.csv")
    feats.append(bw_dsp.features(x))
keys = list(feats[0].keys())
print("\nBaseline files 1-10 median / MAD:")
for k in keys:
    v = np.array([f[k] for f in feats])
    med = float(np.median(v))
    mad = float(np.median(np.abs(v - med)))
    print(f"  {k:>16s}: median={med:.6g}  MAD={mad:.6g}")
