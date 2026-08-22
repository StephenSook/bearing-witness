import sys
sys.path.insert(0, '/private/tmp/claude-501/-Users-vinhle-NVIDIA-x-Dell/6607c0ed-43f4-4df2-abe6-2f22ffb845fb/scratchpad')
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import bw_dsp

SCRATCH = '/private/tmp/claude-501/-Users-vinhle-NVIDIA-x-Dell/6607c0ed-43f4-4df2-abe6-2f22ffb845fb/scratchpad'
DATA = '/Users/vinhle/NVIDIA-x-Dell/data/XJTU-SY/35Hz12kN/Bearing1_3'
BAND = (2000.0, 4000.0)

BPFO_PRED = 107.907
FTF_PRED = 13.488
REL = 0.025
hw = bw_dsp.half_width(BPFO_PRED, rel_unc=REL)
print(f"BPFO predicted {BPFO_PRED:.3f} Hz, half_width(rel_unc={REL}) = {hw:.3f} Hz")
print(f"BPFO search window: {BPFO_PRED-hw:.2f} - {BPFO_PRED+hw:.2f} Hz")

def peak_in(freqs, amp, lo, hi):
    m = (freqs >= lo) & (freqs <= hi)
    if not m.any():
        return None, 0.0
    i = np.argmax(amp[m])
    return float(freqs[m][i]), float(amp[m][i])

results = {}
spectra = {}
for fn in [2, 8, 155]:
    x = bw_dsp.load_h(f"{DATA}/{fn}.csv")
    freqs, amp = bw_dsp.envelope_spectrum(x, BAND)
    spectra[fn] = (freqs, amp)
    # broad-band stats 5-500
    mb = (freqs >= 5.0) & (freqs <= 500.0)
    med = float(np.median(amp[mb]))
    f_top, a_top = peak_in(freqs, amp, 5.0, 500.0)
    # BPFO window
    f_bpfo, a_bpfo = peak_in(freqs, amp, BPFO_PRED - hw, BPFO_PRED + hw)
    r = {
        'median_5_500': med,
        'top_freq': f_top, 'top_amp': a_top, 'top_mult': a_top / med,
        'bpfo_freq': f_bpfo, 'bpfo_amp': a_bpfo, 'bpfo_mult': a_bpfo / med,
    }
    # harmonic ladder: measure f0 = detected bpfo_freq for late; for family test use k*f_bpfo windows
    f0 = f_bpfo
    harm = {}
    for k in (2, 3):
        hwk = bw_dsp.half_width(k * BPFO_PRED, rel_unc=REL)
        fk, ak = peak_in(freqs, amp, k * BPFO_PRED - hwk, k * BPFO_PRED + hwk)
        # local noise floor: median in +/-20 Hz around k*BPFO_PRED excluding the window itself
        loc = (freqs >= k * BPFO_PRED - 25) & (freqs <= k * BPFO_PRED + 25)
        med_loc = float(np.median(amp[loc]))
        harm[k] = (fk, ak, ak / med_loc if med_loc > 0 else 0.0)
        r[f'h{k}_freq'], r[f'h{k}_amp'], r[f'h{k}_local_mult'] = fk, ak, harm[k][2]
    # cage sidebands around BPFO: BPFO +/- FTF
    for sign, tag in ((-1, 'sb_lo'), (+1, 'sb_hi')):
        fc = BPFO_PRED + sign * FTF_PRED
        hws = bw_dsp.half_width(fc, rel_unc=REL)
        fsb, asb = peak_in(freqs, amp, fc - hws, fc + hws)
        r[f'{tag}_freq'], r[f'{tag}_amp'], r[f'{tag}_mult'] = fsb, asb, asb / med
    results[fn] = r
    print(f"\n--- File {fn}.csv (band {BAND[0]:.0f}-{BAND[1]:.0f} Hz) ---")
    print(f"  median amp 5-500 Hz          : {med:.6e}")
    print(f"  strongest peak 5-500 Hz      : {a_top:.6e} at {f_top:.3f} Hz  ({a_top/med:.1f}x median)")
    print(f"  strongest in BPFO win        : {a_bpfo:.6e} at {f_bpfo:.3f} Hz  ({a_bpfo/med:.1f}x median)")
    for k in (2, 3):
        fk, ak, lm = harm[k]
        print(f"  {k}xBPFO window peak           : {ak:.6e} at {fk:.3f} Hz  ({lm:.1f}x local median)")
    print(f"  sideband BPFO-FTF            : {r['sb_lo_amp']:.6e} at {r['sb_lo_freq']:.3f} Hz  ({r['sb_lo_mult']:.1f}x median)")
    print(f"  sideband BPFO+FTF            : {r['sb_hi_amp']:.6e} at {r['sb_hi_freq']:.3f} Hz  ({r['sb_hi_mult']:.1f}x median)")

# family verdict for early files: fundamental >=5x median AND 2x harmonic >=3x local median
print("\n=== Family verdict (criterion: BPFO peak >=5x 5-500 median AND 2xBPFO >=3x local median) ===")
family = {}
for fn in [2, 8, 155]:
    r = results[fn]
    has = (r['bpfo_mult'] >= 5.0) and (r['h2_local_mult'] >= 3.0)
    family[fn] = has
    print(f"  file {fn}: bpfo_mult={r['bpfo_mult']:.2f}, h2_local_mult={r['h2_local_mult']:.2f} -> family={'YES' if has else 'NO'}")

# ratios late/early
for fn in [2, 8]:
    ratio = results[155]['bpfo_amp'] / results[fn]['bpfo_amp']
    print(f"\nRatio late/early BPFO-window amp: 155 vs {fn} = {results[155]['bpfo_amp']:.6e} / {results[fn]['bpfo_amp']:.6e} = {ratio:.1f}x")

# ---- Stage-1 baseline features, files 1..10 ----
rows = []
for i in range(1, 11):
    x = bw_dsp.load_h(f"{DATA}/{i}.csv")
    f = bw_dsp.features(x)
    f['file'] = i
    rows.append(f)
df = pd.DataFrame(rows).set_index('file')
csv_path = f"{SCRATCH}/contrast_baseline_features.csv"
df.to_csv(csv_path)
print(f"\nSaved baseline features -> {csv_path}")
print("\n=== Baseline (files 1-10): median and MAD per feature ===")
stats = {}
for col in df.columns:
    med = float(df[col].median())
    mad = float(np.median(np.abs(df[col] - med)))
    stats[col] = (med, mad)
    print(f"  {col:>16s}: median={med:.6g}  MAD={mad:.6g}")

# ---- Figure: file 2 vs file 155, shared y-scale ----
fig, axes = plt.subplots(2, 1, figsize=(10, 6.5), sharex=True, sharey=True)
ymax = 0.0
for fn in (2, 155):
    fr, am = spectra[fn]
    m = (fr >= 0) & (fr <= 500)
    ymax = max(ymax, am[m].max())
for ax, fn, ttl in zip(axes, (2, 155), ('File 2 (early life, ~min 2)', 'File 155 (late life, outer-race failure)')):
    fr, am = spectra[fn]
    m = (fr >= 0) & (fr <= 500)
    ax.plot(fr[m], am[m], lw=0.8, color='#1f77b4')
    meas_bpfo = results[155]['bpfo_freq']
    for k in (1, 2, 3, 4):
        ax.axvline(k * meas_bpfo, color='crimson', ls='--', lw=0.9, alpha=0.75)
        ax.text(k * meas_bpfo + 3, ymax * 0.92, f"{k}xBPFO", color='crimson', fontsize=8, rotation=90, va='top')
    ax.set_title(ttl, fontsize=10)
    ax.set_ylabel('Envelope amp')
    ax.set_ylim(0, ymax * 1.05)
axes[1].set_xlabel('Frequency (Hz)')
fig.suptitle(f"Envelope spectrum (band 2-4 kHz), shared y-scale — BPFO lines at measured {results[155]['bpfo_freq']:.2f} Hz", fontsize=11)
fig.tight_layout(rect=[0, 0, 1, 0.97])
png_path = f"{SCRATCH}/contrast_early_vs_late.png"
fig.savefig(png_path, dpi=140)
print(f"\nSaved figure -> {png_path}")
