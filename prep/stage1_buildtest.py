"""Build test: prove an injected fake fault-frequency tone cannot bypass Stage 1.

Take window 3 (a baseline window), add a pure sinusoid at BPFO 107.907 Hz with
amplitude = 5x the window RMS (adversarially large). Recompute Stage-1 features,
score them against the SAME windows-1..10 baseline stats, and check whether the
window would classify ABNORMAL (needs >= 2 abnormal groups).

Then demodulate (band 2000-4000) and compare envelope-spectrum amplitude in the
BPFO search window for modified vs unmodified waveforms: the low-frequency tone
must not survive the band-pass, so no envelope peak should appear.
"""
import sys
sys.path.insert(0, '/private/tmp/claude-501/-Users-vinhle-NVIDIA-x-Dell/6607c0ed-43f4-4df2-abe6-2f22ffb845fb/scratchpad')
import bw_dsp
import numpy as np
import pandas as pd

SCRATCH = '/private/tmp/claude-501/-Users-vinhle-NVIDIA-x-Dell/6607c0ed-43f4-4df2-abe6-2f22ffb845fb/scratchpad'
DATA = '/Users/vinhle/NVIDIA-x-Dell/data/XJTU-SY/35Hz12kN/Bearing1_3'
Z_THRESH = 5.0
BPFO = 107.907

# same baseline stats as the replay (windows 1..10)
feat = pd.read_csv(f'{SCRATCH}/stage1_features.csv', index_col='window')
base = feat.loc[1:10]
med = base.median()
mad = (base - med).abs().median()

x = bw_dsp.load_h(f'{DATA}/3.csv')
rms3 = float(np.sqrt(np.mean(x ** 2)))
amp = 5.0 * rms3
t = np.arange(len(x)) / bw_dsp.FS
x_mod = x + amp * np.sin(2 * np.pi * BPFO * t)
print(f'window 3 RMS = {rms3:.6f}; injected tone: {BPFO} Hz, amplitude = {amp:.6f} (5x RMS)')

f_orig = bw_dsp.features(x)
f_mod = bw_dsp.features(x_mod)

print('\nfeature scores vs baseline (orig -> modified):')
group_hits = {}
for g, members in bw_dsp.FEATURE_GROUPS.items():
    hit = False
    for m in members:
        zo = bw_dsp.robust_z(f_orig[m], med[m], mad[m])
        zm = bw_dsp.robust_z(f_mod[m], med[m], mad[m])
        mark = ' <-- ABNORMAL' if abs(zm) >= Z_THRESH else ''
        print(f'  [{g:9s}] {m:16s} value {f_orig[m]:.5f} -> {f_mod[m]:.5f}   z {zo:+8.2f} -> {zm:+8.2f}{mark}')
        if abs(zm) >= Z_THRESH:
            hit = True
    group_hits[g] = hit

moved = [g for g, h in group_hits.items() if h]
n = len(moved)
verdict = 'ABNORMAL' if n >= 2 else 'NOT ABNORMAL'
print(f'\ngroups moved: {n} {moved}')
print(f'window classification: {verdict} (needs >= 2 groups)')
print(f'element call possible: {"YES - PROBLEM" if n >= 2 else "NO - Stage 1 blocks it, no element call can be produced"}')

# ---- envelope-spectrum check, demod band 2000-4000 ----
hw = bw_dsp.half_width(BPFO, rel_unc=0.025)
freqs, amp_o = bw_dsp.envelope_spectrum(x, bw_dsp.DEMOD_BAND)
_, amp_m = bw_dsp.envelope_spectrum(x_mod, bw_dsp.DEMOD_BAND)
sel = (freqs >= BPFO - hw) & (freqs <= BPFO + hw)
po, pm = amp_o[sel].max(), amp_m[sel].max()
fo, fm = freqs[sel][amp_o[sel].argmax()], freqs[sel][amp_m[sel].argmax()]
print(f'\nenvelope spectrum, demod band {bw_dsp.DEMOD_BAND}, BPFO search window {BPFO:.3f} +/- {hw:.3f} Hz:')
print(f'  unmodified: max amplitude = {po:.6e} at {fo:.3f} Hz')
print(f'  modified:   max amplitude = {pm:.6e} at {fm:.3f} Hz')
print(f'  ratio modified/unmodified = {pm/po:.4f}')

# tone attenuation through the band-pass itself, for context
xb = bw_dsp.bandpass(np.sin(2 * np.pi * BPFO * t), *bw_dsp.DEMOD_BAND)
print(f'  band-pass residue of a unit 107.907 Hz tone (RMS): {np.sqrt(np.mean(xb**2)):.3e} (vs 0.7071 input RMS)')
