"""Independent adversarial re-check of stage1 claims. Fresh code; uses bw_dsp only."""
import sys
sys.path.insert(0, '/private/tmp/claude-501/-Users-vinhle-NVIDIA-x-Dell/6607c0ed-43f4-4df2-abe6-2f22ffb845fb/scratchpad')
import bw_dsp
import numpy as np

DATA = '/Users/vinhle/NVIDIA-x-Dell/data/XJTU-SY/35Hz12kN/Bearing1_3'
NW = 158
FEATS = None

# ---- recompute features from raw data ----
rows = {}
for w in range(1, NW + 1):
    x = bw_dsp.load_h(f'{DATA}/{w}.csv')
    assert len(x) == 32768, (w, len(x))
    rows[w] = bw_dsp.features(x)
FEATS = rows
cols = list(rows[1].keys())
print('feature columns:', cols)

# baseline stats: windows 1..10, median + MAD per feature
import statistics
med, mad = {}, {}
for c in cols:
    vals = [rows[w][c] for w in range(1, 11)]
    m = float(np.median(vals))
    med[c] = m
    mad[c] = float(np.median([abs(v - m) for v in vals]))

def zrow(w):
    return {c: bw_dsp.robust_z(rows[w][c], med[c], mad[c]) for c in cols}

# ---- replay state machine (two-sided |z|>=5, >=2 groups, persistence 3, eval from 11) ----
states = {}
run = 0
onset = None
abn = []
watch_early = []
for w in range(1, NW + 1):
    if w <= 10:
        states[w] = 'BASELINE'
        continue
    z = zrow(w)
    moved = [g for g, ms in bw_dsp.FEATURE_GROUPS.items()
             if any(abs(z[m]) >= 5.0 for m in ms)]
    if len(moved) >= 2:
        states[w] = 'ABNORMAL'
        abn.append(w)
        run += 1
        if run == 3 and onset is None:
            onset = w - 2
    else:
        run = 0
        if moved and set(moved) <= {'hf_band', 'envelope'}:
            states[w] = 'WATCH_EARLY'
            watch_early.append(w)
        elif moved:
            states[w] = 'WATCH'
        else:
            states[w] = 'NORMAL'

print(f'\nCLAIM 1 onset window: {onset} (claimed 59); persistence run = {onset},{onset+1},{onset+2}' if onset else 'no onset')
print(f'lead time = {NW - onset} minutes (claimed 99)')
zo = zrow(onset)
print('z at onset:', {m: round(zo[m], 2) for m in ['rms','p2p','be_6000_8000','crest','kurtosis_excess','env_energy']})
print('shape max z at onset:', round(max(zo['crest'], zo['kurtosis_excess']), 2),
      '| hf all:', {m: round(zo[m],2) for m in bw_dsp.FEATURE_GROUPS['hf_band']})
pre_watch = [w for w in watch_early if w < onset]
print(f'WATCH_EARLY before onset ({len(pre_watch)}): {pre_watch} (claimed 25,28,34,35,36,37,38,42,48,52,56,57)')
pre_abn = [w for w in abn if w < onset]
print(f'ABNORMAL before onset: {pre_abn} (claimed isolated singles 24,29,33)')

# ---- build test: inject 107.907 Hz tone at 5x RMS into window 3 ----
x3 = bw_dsp.load_h(f'{DATA}/3.csv')
rms3 = float(np.sqrt(np.mean(x3 ** 2)))
t = np.arange(len(x3)) / bw_dsp.FS
xm = x3 + 5.0 * rms3 * np.sin(2 * np.pi * 107.907 * t)
fm = bw_dsp.features(xm)
zm = {c: bw_dsp.robust_z(fm[c], med[c], mad[c]) for c in cols}
print('\nCLAIM 2 build test z (modified window 3):')
for c in cols:
    print(f'  {c:16s} z = {zm[c]:+9.2f}')
moved2 = [g for g, ms in bw_dsp.FEATURE_GROUPS.items() if any(abs(zm[m]) >= 5.0 for m in ms)]
print(f'two-sided groups moved: {len(moved2)} {moved2} -> {"ABNORMAL" if len(moved2)>=2 else "NOT ABNORMAL"} (claimed 2: energy+shape, ABNORMAL)')
moved1 = [g for g, ms in bw_dsp.FEATURE_GROUPS.items() if any(zm[m] >= 5.0 for m in ms)]
print(f'one-sided groups moved: {len(moved1)} {moved1} -> {"ABNORMAL" if len(moved1)>=2 else "NOT ABNORMAL"} (claimed 1: energy, NOT ABNORMAL)')

# one-sided replay onset
run = 0; onset1 = None
for w in range(11, NW + 1):
    z = zrow(w)
    moved = [g for g, ms in bw_dsp.FEATURE_GROUPS.items() if any(z[m] >= 5.0 for m in ms)]
    if len(moved) >= 2:
        run += 1
        if run == 3 and onset1 is None:
            onset1 = w - 2
    else:
        run = 0
print(f'one-sided replay onset: {onset1} (claimed unchanged at 59)')

# ---- envelope-spectrum BPFO window check ----
BPFO = 107.907
hw = bw_dsp.half_width(BPFO, rel_unc=0.025)
freqs, ao = bw_dsp.envelope_spectrum(x3, bw_dsp.DEMOD_BAND)
_, am = bw_dsp.envelope_spectrum(xm, bw_dsp.DEMOD_BAND)
sel = (freqs >= BPFO - hw) & (freqs <= BPFO + hw)
po, pm = ao[sel].max(), am[sel].max()
fo, fmx = freqs[sel][ao[sel].argmax()], freqs[sel][am[sel].argmax()]
print(f'\nCLAIM 3 envelope spectrum (band 2000-4000), search {BPFO:.3f} +/- {hw:.3f} Hz:')
print(f'  unmodified max = {po:.6e} at {fo:.3f} Hz (claimed 1.618564e-3 at 105.469)')
print(f'  modified   max = {pm:.6e} at {fmx:.3f} Hz (claimed 1.618778e-3 at 105.469)')
print(f'  ratio = {pm/po:.4f} (claimed 1.0001)')
tone_res = bw_dsp.bandpass(np.sin(2 * np.pi * BPFO * t), 2000.0, 4000.0)
print(f'  unit-tone band-pass residue RMS = {np.sqrt(np.mean(tone_res**2)):.3e} (claimed 8.05e-6)')
